"""Tests for RetrySession - automatic retry on SQLite BUSY errors.

Verifies that db.session.commit() transparently retries when the
database is locked, rolls back on non-lock errors, respects the
timeout, and that an explicit rollback() clears stale session state
(the same primitive the per-endpoint cleanup wrapper relies on).
"""
import sqlite3
import threading
import time
import unittest.mock
import uuid
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session as BaseSession
from sqlalchemy.pool import StaticPool

from arm.database import db, RetrySession, _DEFAULT_COMMIT_TIMEOUT
from arm.models.job import Job


def _make_job(devpath="/dev/sr0", **overrides):
    """Create a Job without hardware access (mock udev/pid)."""
    with unittest.mock.patch.object(Job, 'parse_udev'), \
         unittest.mock.patch.object(Job, 'get_pid'):
        job = Job(devpath)
    job.status = overrides.pop("status", "active")
    job.title = overrides.pop("title", "Test")
    for k, v in overrides.items():
        setattr(job, k, v)
    return job


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def retry_db():
    """Create an in-memory SQLite database with RetrySession."""
    db.dispose()
    db.init_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    db.create_all()
    yield db
    db.dispose()


@pytest.fixture
def file_db(tmp_path):
    """Create a file-backed SQLite database for real concurrency tests."""
    db_path = tmp_path / "test.db"
    db.dispose()
    db.init_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    db.create_all()
    yield db, str(db_path)
    db.dispose()


# ---------------------------------------------------------------------------
# RetrySession class tests
# ---------------------------------------------------------------------------

class TestRetrySessionIsUsed:
    """Verify the session factory produces RetrySession instances."""

    def test_session_is_retry_session(self, retry_db):
        session = db.session()
        assert isinstance(session, RetrySession)

    def test_default_commit_timeout(self, retry_db):
        session = db.session()
        assert session.commit_timeout == _DEFAULT_COMMIT_TIMEOUT

    def test_custom_commit_timeout(self, retry_db):
        db.session.commit_timeout = 90
        assert db.session.commit_timeout == 90
        db.session.commit_timeout = _DEFAULT_COMMIT_TIMEOUT


class TestRetryOnLocked:
    """Verify commit retries when database is locked."""

    def test_succeeds_after_transient_lock(self, retry_db):
        """Commit succeeds on second attempt after a transient lock."""
        job = _make_job(title="Test Movie", status="success")
        db.session.add(job)

        # Patch the parent (BaseSession) commit to simulate a lock error
        # on the first call, then succeed on the second.
        call_count = {"n": 0}
        real_commit = BaseSession.commit

        def locked_then_ok(session_self):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise OperationalError(
                    "commit", {}, sqlite3.OperationalError("database is locked")
                )
            return real_commit(session_self)

        with patch.object(BaseSession, 'commit', locked_then_ok):
            db.session.commit()

        assert call_count["n"] == 2  # 1 failure + 1 success

    def test_dirty_state_preserved_across_retry(self, retry_db):
        """Modified attributes must persist after retry, not revert to DB values."""
        job = _make_job(title="Original", status='video_ripping')
        db.session.add(job)
        db.session.commit()

        # Modify attributes
        job.title = "Modified"
        job.status = "video_ripping"

        call_count = {"n": 0}
        real_commit = BaseSession.commit

        def locked_then_ok(session_self):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise OperationalError(
                    "commit", {}, sqlite3.OperationalError("database is locked")
                )
            return real_commit(session_self)

        with patch.object(BaseSession, 'commit', locked_then_ok):
            db.session.commit()

        # Verify the modified values persisted, not the originals
        db.session.expire_all()
        result = db.session.query(Job).first()
        assert result.title == "Modified", f"Expected 'Modified', got '{result.title}'"
        assert result.status == "video_ripping", f"Expected 'video_ripping', got '{result.status}'"

    def test_new_object_survives_retry(self, retry_db):
        """A newly added object must survive rollback+retry."""
        job = _make_job(title="NewJob", status="success")
        db.session.add(job)

        call_count = {"n": 0}
        real_commit = BaseSession.commit

        def locked_then_ok(session_self):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise OperationalError(
                    "commit", {}, sqlite3.OperationalError("database is locked")
                )
            return real_commit(session_self)

        with patch.object(BaseSession, 'commit', locked_then_ok):
            db.session.commit()

        result = db.session.query(Job).filter_by(title="NewJob").first()
        assert result is not None, "New object was lost after retry"

    def test_retries_with_backoff(self, retry_db):
        """Verify exponential backoff timing between retries."""
        lock_error = OperationalError(
            "commit", {}, sqlite3.OperationalError("database is locked")
        )
        timestamps = []
        real_commit = BaseSession.commit

        def counting_commit(session_self):
            timestamps.append(time.monotonic())
            if len(timestamps) < 4:
                raise lock_error
            return real_commit(session_self)

        db.session.commit_timeout = 10
        with patch.object(BaseSession, 'commit', counting_commit):
            db.session.commit()

        assert len(timestamps) == 4
        # Second gap should be >= first gap (exponential backoff)
        gap1 = timestamps[1] - timestamps[0]
        gap2 = timestamps[2] - timestamps[1]
        assert gap2 >= gap1 * 1.5

        db.session.commit_timeout = _DEFAULT_COMMIT_TIMEOUT

    def test_timeout_raises(self, retry_db):
        """Commit raises after timeout is exceeded."""
        lock_error = OperationalError(
            "commit", {}, sqlite3.OperationalError("database is locked")
        )

        def always_locked(session_self):
            raise lock_error

        db.session.commit_timeout = 0.3
        with patch.object(BaseSession, 'commit', always_locked):
            with pytest.raises(OperationalError, match="locked"):
                db.session.commit()

        db.session.commit_timeout = _DEFAULT_COMMIT_TIMEOUT


class TestRollbackOnError:
    """Verify non-lock errors trigger immediate rollback."""

    def test_non_lock_error_raises_immediately(self, retry_db):
        """Non-lock errors should not retry, just rollback and raise."""
        call_count = {"n": 0}

        def integrity_error(session_self):
            call_count["n"] += 1
            raise OperationalError(
                "commit", {}, sqlite3.IntegrityError("UNIQUE constraint failed")
            )

        with patch.object(BaseSession, 'commit', integrity_error):
            with pytest.raises(OperationalError, match="UNIQUE"):
                db.session.commit()

        assert call_count["n"] == 1  # No retry

    def test_session_usable_after_error(self, retry_db):
        """Session should be clean after a failed commit (auto-rollback)."""
        # Force an error
        def one_time_error(session_self):
            raise OperationalError(
                "commit", {}, sqlite3.OperationalError("some database error")
            )

        with patch.object(BaseSession, 'commit', one_time_error):
            with pytest.raises(OperationalError):
                db.session.commit()

        # Session should be usable - no PendingRollbackError
        job = _make_job(title="After Error", status="success")
        db.session.add(job)
        db.session.commit()

        result = db.session.query(Job).filter_by(title="After Error").first()
        assert result is not None


@patch.object(Job, 'parse_udev')
@patch.object(Job, 'get_pid')
class TestRealConcurrency:
    """Test with actual concurrent SQLite writers."""

    def test_concurrent_writes_succeed(self, mock_pid, mock_udev, file_db):
        """Two threads writing simultaneously should both succeed."""
        _, db_path = file_db
        errors = []
        success_count = {"n": 0}
        lock = threading.Lock()

        def writer(title, count):
            try:
                for i in range(count):
                    job = _make_job(title=f"{title}_{i}", status="success")
                    db.session.add(job)
                    db.session.commit()
                    with lock:
                        success_count["n"] += 1
            except Exception as e:
                errors.append(str(e))
            finally:
                db.session.remove()

        t1 = threading.Thread(target=writer, args=("thread1", 5))
        t2 = threading.Thread(target=writer, args=("thread2", 5))

        t1.start()
        t2.start()
        t1.join(timeout=30)
        t2.join(timeout=30)

        assert not errors, f"Concurrent writes failed: {errors}"
        assert success_count["n"] == 10

    def test_lock_during_long_transaction(self, mock_pid, mock_udev, file_db):
        """A commit during another thread's long transaction should retry."""
        _, db_path = file_db
        barrier = threading.Barrier(2, timeout=10)
        results = {"writer": None, "holder": None}

        def lock_holder():
            """Hold a write lock for 1 second."""
            import sqlite3
            try:
                conn = sqlite3.connect(db_path, timeout=5)
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("BEGIN IMMEDIATE")
                conn.execute(
                    "INSERT INTO job (devpath, status, guid) VALUES (?, ?, ?)",
                    ("/dev/sr1", "active", str(uuid.uuid4())),
                )
                barrier.wait()
                time.sleep(1)
                conn.commit()
                conn.close()
                results["holder"] = "ok"
            except Exception as e:
                results["holder"] = str(e)

        def retry_writer():
            """Try to commit while lock is held - should retry."""
            try:
                barrier.wait()
                time.sleep(0.1)  # Ensure holder has the lock
                job = _make_job(title="Retry Writer", status="success")
                db.session.add(job)
                db.session.commit()
                results["writer"] = "ok"
            except Exception as e:
                results["writer"] = str(e)
            finally:
                db.session.remove()

        t1 = threading.Thread(target=lock_holder)
        t2 = threading.Thread(target=retry_writer)
        t1.start()
        t2.start()
        t1.join(timeout=15)
        t2.join(timeout=15)

        assert results["holder"] == "ok", f"Lock holder failed: {results['holder']}"
        assert results["writer"] == "ok", f"Retry writer failed: {results['writer']}"


class TestDatabaseUpdaterSimplified:
    """Verify database_updater still works after simplification."""

    def test_sets_attributes_and_commits(self, retry_db):
        from arm.services.files import database_updater

        job = _make_job(title="Original", status='video_ripping')
        db.session.add(job)
        db.session.commit()

        result = database_updater({"title": "Updated", "status": "success"}, job)
        assert result is True
        assert job.title == "Updated"
        assert job.status == "success"

    def test_non_dict_rollback(self, retry_db):
        from arm.services.files import database_updater

        job = MagicMock()
        result = database_updater("not a dict", job)
        assert result is False

    def test_wait_time_accepted(self, retry_db):
        """wait_time parameter is accepted for backward compat."""
        from arm.services.files import database_updater

        job = _make_job(status='video_ripping')
        db.session.add(job)
        db.session.commit()

        result = database_updater({"status": "success"}, job, wait_time=90)
        assert result is True


class TestDatabaseAdderSimplified:
    """Verify database_adder still works after simplification."""

    def test_adds_object(self, retry_db):
        from arm.ripper.utils import database_adder

        job = _make_job(title="Added", status="success")
        result = database_adder(job)
        assert result is True

        found = db.session.query(Job).filter_by(title="Added").first()
        assert found is not None


class TestProactiveRollback:
    """Test that rollback clears stale session state.

    The per-endpoint session cleanup wrapper (arm.app._wrap_sync_endpoint)
    relies on this primitive: a poisoned session can be rescued by
    calling rollback() before the next operation.
    """

    def test_rollback_clears_pending_error(self, retry_db):
        """Simulate bad session state and verify rollback recovers it."""
        job = _make_job(status='video_ripping')
        db.session.add(job)
        db.session.commit()

        # Force the session into an error state
        try:
            db.session.execute(text("INVALID SQL"))
        except Exception:
            pass

        # Rollback should clear the error state
        db.session.rollback()

        # Session should be usable again
        job2 = _make_job(devpath="/dev/sr1", title="After Rollback", status="success")
        db.session.add(job2)
        db.session.commit()

        result = db.session.query(Job).filter_by(title="After Rollback").first()
        assert result is not None

    def test_remove_gives_clean_session(self, retry_db):
        """After remove(), next access gets a fresh session."""
        # Dirty the session
        job = _make_job(status='video_ripping')
        db.session.add(job)
        # Don't commit - just remove
        db.session.remove()

        # New session should be clean
        count = db.session.query(Job).count()
        assert count == 0  # The uncommitted job was discarded
