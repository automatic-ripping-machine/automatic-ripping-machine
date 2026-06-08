"""Tests for auth database initialization."""

import pytest

from arm_auth.db import AuthDB


class TestAuthDB:
    def test_init_engine_creates_engine(self, auth_db):
        """Engine should be created after init."""
        assert auth_db.engine is not None

    def test_session_works(self, auth_db):
        """Session should allow basic operations."""
        with auth_db.session() as session:
            result = session.execute(auth_db.text("SELECT 1"))
            assert result.scalar() == 1

    def test_dispose_and_reinit(self):
        """Dispose should allow re-initialization."""
        from sqlalchemy.pool import StaticPool

        db = AuthDB()
        db.init_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        db.create_all()
        db.dispose()

        db.init_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        db.create_all()
        with db.session() as session:
            result = session.execute(db.text("SELECT 1"))
            assert result.scalar() == 1
        db.dispose()

    def test_init_engine_idempotent(self, auth_db):
        """Calling init_engine twice should not error."""
        auth_db.init_engine("sqlite:///:memory:")  # should no-op

    def test_engine_not_initialised_raises(self):
        """Accessing engine before init should raise RuntimeError."""
        db = AuthDB()
        with pytest.raises(RuntimeError, match="not initialised"):
            _ = db.engine

    def test_session_not_initialised_raises(self):
        """Using session before init should raise RuntimeError."""
        db = AuthDB()
        with pytest.raises(RuntimeError, match="not initialised"):
            with db.session():
                pass

    def test_session_rollback_on_exception(self, auth_db):
        """An exception inside a session block should roll back changes."""
        from arm_auth.models import Group

        with pytest.raises(RuntimeError):
            with auth_db.session() as s:
                s.add(Group(name="doomed", scopes='["*"]'))
                s.flush()
                raise RuntimeError("simulated failure")

        with auth_db.session() as s:
            count = s.query(Group).filter_by(name="doomed").count()
            assert count == 0

