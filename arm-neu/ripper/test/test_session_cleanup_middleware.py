"""Tests for the per-endpoint DB session cleanup wrapper.

Replaces the old SessionCleanupMiddleware (which was middleware-based and
did not work because middleware runs on the event loop while sync handlers
run on the AnyIO threadpool - scoped_session is keyed by thread, so
cleanup ran on the wrong thread and never released the worker thread's
connection).

The new implementation wraps each sync endpoint so cleanup runs on the
same thread that ran the handler. See arm/app.py:_install_session_cleanup.
"""
import threading
import unittest.mock

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import PendingRollbackError


def _make_app():
    """Build a minimal FastAPI app + endpoints, then install session cleanup.

    Tests below verify both correctness (sessions get cleaned, errors
    don't poison subsequent requests) and the absence of the pool leak
    that motivated this code.
    """
    from arm.app import _install_session_cleanup
    from arm.database import db

    app = FastAPI()
    router = APIRouter()

    @router.get("/test/ok")
    def ok_endpoint():
        return {"status": "ok"}

    @router.get("/test/db-read")
    def db_read_endpoint():
        result = db.session.execute(db.text("SELECT 1")).scalar()
        return {"result": result}

    @router.get("/test/poison")
    def poison_endpoint():
        db.session.execute(db.text("INSERT INTO nonexistent_table VALUES (1)"))

    @router.get("/test/pending-rollback")
    def pending_rollback_endpoint():
        """Raise PendingRollbackError directly. Tests that a handler raising
        this exception class doesn't crash subsequent requests - which is a
        weaker guarantee than recovering from a genuinely poisoned session.
        For that, see /test/leave-session-poisoned."""
        raise PendingRollbackError(
            "This Session's transaction has been rolled back",
            None, None, False
        )

    @router.get("/test/leave-session-poisoned")
    def leave_session_poisoned():
        """Catch a SQL error mid-handler and return 200 without rolling back.

        This is the real-world failure mode the cleanup must recover from:
        a handler swallows the underlying error and returns success, but
        the SQLAlchemy session is left needing rollback() before any
        further use. The cleanup wrapper's finally must rescue the next
        request on this thread.
        """
        try:
            db.session.execute(db.text("INSERT INTO nonexistent_table VALUES (1)"))
        except Exception:
            # Intentionally don't rollback - this is the poisoned-session case
            pass
        return {"swallowed": True}

    app.include_router(router)
    _install_session_cleanup(app)
    return app


@pytest.fixture
def test_client(app_context):
    """TestClient wired to the in-memory test DB from app_context."""
    app = _make_app()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


class TestSessionCleanupBasic:
    """Sanity checks: cleanup runs and recovers from poisoned sessions."""

    def test_successful_request_unaffected(self, test_client):
        resp = test_client.get("/test/ok")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_consecutive_successful_requests(self, test_client):
        for _ in range(5):
            resp = test_client.get("/test/ok")
            assert resp.status_code == 200

    def test_db_read_works(self, test_client):
        resp = test_client.get("/test/db-read")
        assert resp.status_code == 200
        assert resp.json() == {"result": 1}

    def test_handler_raising_pending_rollback_is_not_fatal(self, test_client):
        """Sanity: a handler raising PendingRollbackError shouldn't crash the
        next request. Weaker than the poisoned-session recovery test below."""
        resp = test_client.get("/test/pending-rollback")
        assert resp.status_code == 500
        resp = test_client.get("/test/db-read")
        assert resp.status_code == 200
        assert resp.json() == {"result": 1}

    def test_session_recovers_after_handler_swallowed_sql_error(self, test_client):
        """The real recovery case: a handler runs a SQL statement that fails,
        swallows the exception, and returns 200. The session is left needing
        rollback. The next request on this thread must still succeed because
        the cleanup wrapper's finally ran rollback() + remove()."""
        resp = test_client.get("/test/leave-session-poisoned")
        assert resp.status_code == 200
        assert resp.json() == {"swallowed": True}
        resp = test_client.get("/test/db-read")
        assert resp.status_code == 200
        assert resp.json() == {"result": 1}

    def test_session_recovers_after_bad_sql(self, test_client):
        """Bad SQL bubbles up as 500; session must still be usable next request."""
        resp = test_client.get("/test/poison")
        assert resp.status_code == 500
        resp = test_client.get("/test/db-read")
        assert resp.status_code == 200
        assert resp.json() == {"result": 1}

    def test_multiple_failures_then_recovery(self, test_client):
        for _ in range(3):
            resp = test_client.get("/test/pending-rollback")
            assert resp.status_code == 500
        resp = test_client.get("/test/db-read")
        assert resp.status_code == 200

    def test_interleaved_success_and_failure(self, test_client):
        for i in range(5):
            if i % 2 == 0:
                resp = test_client.get("/test/db-read")
                assert resp.status_code == 200
            else:
                resp = test_client.get("/test/poison")
                assert resp.status_code == 500
        resp = test_client.get("/test/db-read")
        assert resp.status_code == 200


class TestSessionCleanupMechanics:
    """Verify the wrapper actually intercepts each endpoint call."""

    def test_cleanup_runs_after_every_request(self, app_context):
        """db.session.remove() must fire on every request, not only on errors."""
        from arm.database import db

        app = _make_app()
        with unittest.mock.patch.object(db.session, "remove") as mock_rm:
            with TestClient(app, raise_server_exceptions=False) as c:
                c.get("/test/ok")
            assert mock_rm.called, "remove() must be called after a successful request"

    def test_cleanup_runs_when_handler_raises(self, app_context):
        """remove() must still fire when the handler raises an exception."""
        from arm.database import db

        app = _make_app()
        with unittest.mock.patch.object(db.session, "remove") as mock_rm:
            with TestClient(app, raise_server_exceptions=False) as c:
                c.get("/test/pending-rollback")
            assert mock_rm.called, "remove() must be called even when handler raises"

    def test_rollback_failure_does_not_prevent_remove(self, app_context):
        """If rollback() itself raises, remove() must still run."""
        from arm.database import db

        app = _make_app()
        with unittest.mock.patch.object(
            db.session, "rollback", side_effect=Exception("rollback boom")
        ), unittest.mock.patch.object(db.session, "remove") as mock_rm:
            with TestClient(app, raise_server_exceptions=False) as c:
                c.get("/test/ok")
            assert mock_rm.called, "remove() must be called even if rollback() fails"

    def test_async_endpoint_is_not_wrapped(self, app_context):
        """Async endpoints get no wrapping (cleanup wrapper would not help them)."""
        from arm.app import _install_session_cleanup, _wrap_sync_endpoint

        app = FastAPI()

        @app.get("/async")
        async def async_ep():
            return {"ok": True}

        @app.get("/sync")
        def sync_ep():
            return {"ok": True}

        _install_session_cleanup(app)

        # Find the routes and check whether the endpoint was rebound.
        endpoints = {r.path: r.endpoint for r in app.routes if hasattr(r, "path")}
        assert getattr(endpoints["/sync"], "__arm_session_wrapped__", False) is True
        assert getattr(endpoints["/async"], "__arm_session_wrapped__", False) is False

    def test_install_is_idempotent(self, app_context):
        """Calling _install_session_cleanup twice must not double-wrap endpoints."""
        from arm.app import _install_session_cleanup

        app = _make_app()  # already calls _install once
        _install_session_cleanup(app)  # second call must be a no-op for already-wrapped endpoints

        # Hitting the endpoint should still produce one cleanup, not two.
        from arm.database import db
        with unittest.mock.patch.object(db.session, "remove") as mock_rm:
            with TestClient(app, raise_server_exceptions=False) as c:
                c.get("/test/ok")
            assert mock_rm.call_count == 1


class TestPoolDoesNotLeak:
    """Regression test for the connection pool leak that motivated this code.

    Reproduces the original bug: with the old middleware-based cleanup,
    each unique threadpool worker thread leaked one connection because
    middleware ran on the event loop and operated on the wrong scoped
    session. After enough distinct workers had served requests, the pool
    was permanently exhausted.

    With the per-endpoint wrapper the cleanup runs on the worker thread,
    so the connection actually returns to the pool. We can saturate a
    tiny pool with many concurrent requests and still finish cleanly.
    """

    def test_concurrent_requests_do_not_exhaust_pool(self):
        """Drive more concurrent requests than the pool size and confirm none time out.

        Uses its own engine + pool (not the shared app_context fixture) so
        the pool sizing is under our control. Without the fix, this test
        wedges and times out.
        """
        from sqlalchemy.pool import QueuePool

        from arm.database import db
        db.dispose()
        # Pool of 3, no overflow, short timeout - must succeed despite 12 concurrent requests
        # because the wrapper releases each connection back to the pool on the worker thread.
        db.init_engine(
            "sqlite:///:memory:",
            poolclass=QueuePool,
            pool_size=3,
            max_overflow=0,
            pool_timeout=2,
            connect_args={"check_same_thread": False},
        )
        try:
            db.create_all()
            app = _make_app()

            results = []
            errors = []

            def hit():
                # TestClient is reusable across threads via the same FastAPI app.
                # Each call creates a fresh client to avoid TestClient internal locks.
                try:
                    with TestClient(app, raise_server_exceptions=False) as c:
                        r = c.get("/test/db-read")
                    results.append(r.status_code)
                except Exception as e:
                    errors.append(str(e))

            threads = [threading.Thread(target=hit) for _ in range(12)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=10)

            assert not errors, f"unexpected errors: {errors[:3]}"
            assert all(s == 200 for s in results), f"non-200 responses: {results}"
            # Pool should have at most 3 connections checked out at any time;
            # by the end, all should have been returned.
            assert db.engine.pool.checkedout() == 0, (
                f"pool leaked - checked out: {db.engine.pool.checkedout()}, "
                f"status: {db.engine.pool.status()}"
            )
        finally:
            db.dispose()
