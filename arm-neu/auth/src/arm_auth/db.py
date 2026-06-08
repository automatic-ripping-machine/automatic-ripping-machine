"""Auth database engine and session management.

Follows the same singleton pattern as ARM-neu's arm.database module.
"""

import logging
from contextlib import contextmanager

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

log = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Declarative base for all auth models."""
    pass


class AuthDB:
    """Database singleton for the auth system."""

    def __init__(self):
        self._engine = None
        self._session_factory = None

    def init_engine(self, db_uri: str, **engine_kw):
        """Create engine and session factory. No-op if already initialised."""
        if self._engine is not None:
            log.debug("Auth DB engine already initialised — skipping.")
            return
        engine_kw.setdefault("pool_pre_ping", True)
        self._engine = create_engine(db_uri, **engine_kw)

        @event.listens_for(self._engine, "connect")
        def _set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

        self._session_factory = sessionmaker(bind=self._engine)
        log.info("Auth DB engine initialised: %s", db_uri)

    def dispose(self):
        """Tear down engine — used by test fixtures."""
        if self._engine is not None:
            self._engine.dispose()
        self._engine = None
        self._session_factory = None

    @property
    def engine(self):
        if self._engine is None:
            raise RuntimeError("Auth DB not initialised — call init_engine() first")
        return self._engine

    @contextmanager
    def session(self):
        """Yield a session that auto-commits on success, rolls back on error."""
        if self._session_factory is None:
            raise RuntimeError("Auth DB not initialised — call init_engine() first")
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_all(self):
        """Create all tables."""
        Base.metadata.create_all(bind=self.engine)

    @staticmethod
    def text(sql: str):
        """Convenience wrapper for sqlalchemy.text()."""
        return text(sql)


# Module-level singleton
auth_db = AuthDB()
