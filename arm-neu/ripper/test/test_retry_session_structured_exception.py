"""Verify RetrySession.commit() retry uses structured exception type
checking (sqlalchemy.exc.OperationalError + orig.__module__ check)
rather than substring matching the exception message."""
import sqlite3
import unittest.mock

import pytest
from sqlalchemy.exc import OperationalError


def _build_sqlite_locked_error():
    """Build the same OperationalError shape that pysqlite raises when
    the database file is locked: SQLAlchemy's OperationalError wrapping
    a sqlite3.OperationalError with 'database is locked' message."""
    orig = sqlite3.OperationalError("database is locked")
    return OperationalError("UPDATE foo SET bar = ?", {}, orig)


def _build_psycopg_unrelated_error():
    """Build an OperationalError shape that resembles what psycopg would
    raise for a NON-retryable problem (e.g. connection refused). The
    'orig' attribute does NOT have __module__='sqlite3' so the retry
    logic must NOT fire."""
    fake_orig = type("OperationalError", (Exception,), {})("connection refused")
    fake_orig.__class__.__module__ = "psycopg.errors"
    return OperationalError("SELECT 1", {}, fake_orig)


def test_commit_retries_on_sqlite_locked(app_context):
    """When commit raises OperationalError wrapping sqlite3.OperationalError
    with 'locked' in the message, the retry path fires and re-attempts
    the commit. After the lock clears, the second attempt succeeds."""
    from arm.database import db
    session = db.session()

    locked_error = _build_sqlite_locked_error()
    call_count = {"n": 0}

    def fake_super_commit():
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise locked_error
        # second call succeeds; nothing to do

    # Patch the parent class's commit method since RetrySession.commit
    # calls super().commit()
    from sqlalchemy.orm import Session
    with unittest.mock.patch.object(Session, "commit", side_effect=fake_super_commit):
        session.commit_timeout = 1.0  # short timeout, second attempt is immediate
        session.commit()  # must not raise

    assert call_count["n"] == 2  # one failed attempt, one retry


def test_commit_does_not_retry_on_non_sqlite_operational_error(app_context):
    """A psycopg-shaped OperationalError must NOT trigger the retry path.
    The retry logic is sqlite-specific; PG OperationalErrors (connection
    refused, etc.) are not retry-friendly the same way."""
    from arm.database import db
    session = db.session()

    psycopg_error = _build_psycopg_unrelated_error()

    from sqlalchemy.orm import Session
    with unittest.mock.patch.object(Session, "commit", side_effect=psycopg_error) as mock_commit:
        session.commit_timeout = 1.0
        with pytest.raises(OperationalError):
            session.commit()

    # commit() called once (no retry).
    assert mock_commit.call_count == 1


def test_commit_does_not_retry_on_unrelated_exception(app_context):
    """A non-OperationalError raised from commit must propagate immediately
    with no retry attempt and no snapshot replay. (Pre-refactor behavior:
    'locked' substring check would also miss this; keeping it documents
    the contract.)"""
    from arm.database import db
    session = db.session()

    from sqlalchemy.orm import Session
    with unittest.mock.patch.object(Session, "commit", side_effect=ValueError("boom")) as mock_commit:
        session.commit_timeout = 1.0
        with pytest.raises(ValueError, match="boom"):
            session.commit()

    assert mock_commit.call_count == 1


def test_commit_does_not_retry_on_sqlite_operational_non_locked(app_context):
    """A sqlite3.OperationalError that is NOT 'locked' (e.g. a constraint
    violation surfaced as OperationalError) must propagate immediately."""
    from arm.database import db
    session = db.session()

    orig = sqlite3.OperationalError("no such table: nonexistent")
    sqla_error = OperationalError("SELECT 1", {}, orig)

    from sqlalchemy.orm import Session
    with unittest.mock.patch.object(Session, "commit", side_effect=sqla_error) as mock_commit:
        session.commit_timeout = 1.0
        with pytest.raises(OperationalError):
            session.commit()

    assert mock_commit.call_count == 1
