"""Shared database layer — standalone SQLAlchemy (no Flask).

Drop-in replacement for Flask-SQLAlchemy's ``db`` object.
All existing code continues to use ``from arm.database import db``
and call ``db.session``, ``db.Column``, ``Model.query``, etc.

Includes a custom :class:`RetrySession` that automatically retries
``commit()`` on SQLite BUSY ("database is locked") errors with
exponential backoff, and rolls back on all other failures.  This
makes every ``db.session.commit()`` in the codebase safe without
requiring per-call-site exception handling.
"""
import re
import logging
from time import sleep

from sqlalchemy import (
    BigInteger, Column, Integer, String, Boolean, Float, Text,
    DateTime, SmallInteger, Unicode, Enum, ForeignKey, JSON, Index,
    create_engine, text, event,
)
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import (
    DeclarativeBase, relationship, backref,
    scoped_session, sessionmaker, Session,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Declarative base with Flask-SQLAlchemy-style __tablename__ generation
# ---------------------------------------------------------------------------

_camelcase_re = re.compile(r'((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))')


def _snake_case(name):
    """CamelCase → snake_case  (matches Flask-SQLAlchemy convention)."""
    return _camelcase_re.sub(r'_\1', name).lower()


class Base(DeclarativeBase):
    """Model base class — auto-generates ``__tablename__`` like Flask-SQLAlchemy."""

    def __init_subclass__(cls, **kw):
        # Only generate __tablename__ for concrete (non-abstract) mapped classes
        if not getattr(cls, '__abstract__', False) and '__tablename__' not in cls.__dict__:
            cls.__tablename__ = _snake_case(cls.__name__)
        super().__init_subclass__(**kw)


# ---------------------------------------------------------------------------
# Query property — gives every model a `.query` class attribute
# ---------------------------------------------------------------------------

class _QueryProperty:
    """Descriptor that returns ``session.query(ModelClass)``."""

    def __get__(self, obj, cls):
        return _db_instance._session_factory.query(cls)


Base.query = _QueryProperty()


# ---------------------------------------------------------------------------
# RetrySession — auto-retry commit on SQLite BUSY
# ---------------------------------------------------------------------------

# Default retry budget for db.session.commit().  API callers get 10s
# (fast failure for user-facing requests), ripper threads get 90s
# (tolerant of long NFS I/O holding the lock).  The per-thread value
# can be overridden via ``db.session.commit_timeout = 90``.
_DEFAULT_COMMIT_TIMEOUT = 10.0


class RetrySession(Session):
    """Session subclass that retries ``commit()`` on SQLite BUSY errors.

    When ``commit()`` raises an error containing "database is locked",
    the session snapshots all dirty/new/deleted state, rolls back the
    invalid transaction (required by SQLAlchemy), re-applies the
    snapshot, and retries with exponential backoff (0.1 s initial,
    2.0 s cap) until *commit_timeout* seconds have elapsed.

    Non-lock errors are rolled back and re-raised immediately.

    This makes every bare ``db.session.commit()`` in the codebase safe
    without requiring per-call-site ``try / except / rollback`` logic.
    """

    #: Maximum seconds to retry before raising.  Set per-thread via
    #: ``db.session.commit_timeout = <seconds>`` (e.g. ripper threads
    #: set 90).  Defaults to ``_DEFAULT_COMMIT_TIMEOUT``.
    commit_timeout: float = _DEFAULT_COMMIT_TIMEOUT

    @staticmethod
    def _snapshot_dirty(session):
        """Capture all pending mutations so they survive a rollback.

        Returns a list of (obj, {attr: value}) tuples for dirty objects,
        a list of new (transient) objects with their attribute dicts,
        and a list of objects marked for deletion.
        """
        dirty = []
        for obj in list(session.dirty):
            state = {}
            insp = getattr(obj, '__mapper__', None)
            if insp is None:
                continue
            for attr in insp.columns:
                key = attr.key
                hist = getattr(
                    obj.__class__, key
                ).impl.get_history(
                    obj._sa_instance_state, {}, passive=False
                )
                if hist.has_changes():
                    state[key] = getattr(obj, key)
            if state:
                dirty.append((obj, state))

        new = []
        for obj in list(session.new):
            attrs = {}
            insp = getattr(obj, '__mapper__', None)
            if insp is None:
                continue
            for attr in insp.columns:
                val = getattr(obj, attr.key, None)
                if val is not None:
                    attrs[attr.key] = val
            new.append((obj, attrs))

        deleted = list(session.deleted)
        return dirty, new, deleted

    @staticmethod
    def _restore_snapshot(session, dirty, new, deleted):
        """Re-apply mutations captured by ``_snapshot_dirty``."""
        for obj, attrs in dirty:
            for key, val in attrs.items():
                setattr(obj, key, val)
        for obj, attrs in new:
            # Re-add transient objects; restore their attributes
            # (rollback may have expunged or reset them).
            session.add(obj)
            for key, val in attrs.items():
                setattr(obj, key, val)
        for obj in deleted:
            try:
                session.delete(obj)
            except Exception:
                pass  # Object may no longer be in session

    def commit(self):
        elapsed = 0.0
        backoff = 0.1
        timeout = getattr(self, 'commit_timeout', _DEFAULT_COMMIT_TIMEOUT)
        while True:
            try:
                super().commit()
                return
            except OperationalError as exc:
                # SQLite raises OperationalError-wrapping-sqlite3.OperationalError
                # when the database file is locked. Retry only that specific
                # case; other OperationalErrors (connection refused, network,
                # constraint violations etc.) are not retry-friendly. PG
                # raises OperationalError for unrelated reasons that should
                # NOT be retried.
                # The substring 'locked' matches both SQLITE_BUSY ("database
                # is locked") and SQLITE_LOCKED (table-level lock conflict).
                # SQLITE_LOCKED is rare under WAL mode + BEGIN IMMEDIATE
                # (configured in _set_sqlite_pragma); when it does fire, the
                # snapshot-and-replay machinery handles it the same way.
                is_sqlite_busy = (
                    getattr(exc.orig, '__module__', '').startswith('sqlite3')
                    and 'locked' in str(exc.orig).lower()
                )
                if is_sqlite_busy and elapsed < timeout:
                    # Snapshot dirty state before rollback destroys it
                    dirty, new, deleted = self._snapshot_dirty(self)
                    self.rollback()
                    # Re-apply so next commit attempt has the same mutations
                    self._restore_snapshot(self, dirty, new, deleted)
                    sleep(backoff)
                    elapsed += backoff
                    log.debug(
                        "db commit: database locked, retrying in %.1fs "
                        "(%.1f/%.0fs elapsed)",
                        backoff, elapsed, timeout,
                    )
                    backoff = min(backoff * 2, 2.0)
                else:
                    log.warning("db commit failed: %s", exc)
                    self.rollback()
                    raise
            except Exception as exc:
                log.warning("db commit failed: %s", exc)
                self.rollback()
                raise


# ---------------------------------------------------------------------------
# DB singleton — drop-in for Flask-SQLAlchemy's db object
# ---------------------------------------------------------------------------

class _DB:
    """Drop-in replacement for ``flask_sqlalchemy.SQLAlchemy``."""

    # --- Declarative base ---
    Model = Base

    # --- Column types (used as db.Integer, db.String, etc.) ---
    BigInteger = BigInteger
    Column = staticmethod(Column)
    Integer = Integer
    String = String
    Boolean = Boolean
    Float = Float
    Text = Text
    DateTime = DateTime
    SmallInteger = SmallInteger
    Unicode = Unicode
    Enum = Enum
    JSON = JSON
    ForeignKey = staticmethod(ForeignKey)
    Index = staticmethod(Index)

    # --- Relationships ---
    relationship = staticmethod(relationship)
    backref = staticmethod(backref)

    # --- SQL text ---
    text = staticmethod(text)

    def __init__(self):
        self._engine = None
        self._session_factory = None

    # --- Engine lifecycle ---

    def init_engine(self, db_uri, **engine_kw):
        """Create engine and scoped session.  No-op if already initialised."""
        if self._engine is not None:
            log.debug("Database engine already initialised — skipping.")
            return
        engine_kw.setdefault('pool_pre_ping', True)
        # Increase pool size to handle concurrent background threads
        # (disc rips, folder rips, prescans all run in daemon threads).
        # Skip when caller provides a custom poolclass (e.g. StaticPool in tests).
        if 'poolclass' not in engine_kw:
            engine_kw.setdefault('pool_size', 20)
            engine_kw.setdefault('max_overflow', 10)
        # SQLite: enable WAL mode (readers never block writers) and set a
        # 30-second busy_timeout so concurrent writes wait instead of
        # immediately raising SQLITE_BUSY.
        if db_uri.startswith('sqlite'):
            connect_args = engine_kw.pop('connect_args', {})
            connect_args.setdefault('timeout', 30)
            engine_kw['connect_args'] = connect_args
        self._engine = create_engine(db_uri, **engine_kw)
        if db_uri.startswith('sqlite'):
            # Take full control of SQLite transaction handling.
            #
            # pysqlite (Python's sqlite3 module) has its own transaction
            # management that conflicts with SQLAlchemy's: it defers
            # BEGIN until the first DML statement and uses BEGIN DEFERRED
            # by default.  This causes two problems:
            #
            # 1. Transaction upgrade deadlock: BEGIN DEFERRED starts a
            #    read transaction. Upgrading to a write lock on the first
            #    INSERT/UPDATE fails instantly with SQLITE_BUSY -
            #    busy_timeout does NOT apply to lock upgrades.
            #
            # 2. Double-BEGIN: pysqlite and SQLAlchemy can both try to
            #    emit BEGIN, causing "cannot start a transaction within
            #    a transaction".
            #
            # Fix (per SQLAlchemy docs): disable pysqlite's transaction
            # management entirely (isolation_level=None), then emit our
            # own BEGIN IMMEDIATE via an event listener.  BEGIN IMMEDIATE
            # acquires the write lock up front so busy_timeout works and
            # concurrent writers queue instead of deadlocking.
            #
            # For in-memory databases (tests with StaticPool), we still
            # disable pysqlite's management but use plain BEGIN (no
            # contention with a single connection).

            @event.listens_for(self._engine, "connect")
            def _set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA busy_timeout=30000")
                cursor.close()

        factory = sessionmaker(bind=self._engine, class_=RetrySession)
        self._session_factory = scoped_session(factory)
        # Mask credentials in the log message to avoid leaking the DB
        # password (postgres DSNs include user:password@host). For sqlite
        # the masked output is identical to the input.
        try:
            from sqlalchemy.engine.url import make_url
            safe_uri = make_url(db_uri).render_as_string(hide_password=True)
        except Exception:
            safe_uri = '<unparseable>'
        log.info("Database engine initialised: %s", safe_uri)

    def dispose(self):
        """Tear down engine and session — used by test fixtures."""
        if self._session_factory is not None:
            self._session_factory.remove()
        if self._engine is not None:
            self._engine.dispose()
        self._engine = None
        self._session_factory = None

    @property
    def engine(self):
        if self._engine is None:
            raise RuntimeError("Database not initialised — call db.init_engine() first")
        return self._engine

    @property
    def session(self):
        if self._session_factory is None:
            raise RuntimeError("Database not initialised — call db.init_engine() first")
        return self._session_factory

    @property
    def metadata(self):
        return Base.metadata

    # --- Convenience helpers (match Flask-SQLAlchemy API) ---

    def create_all(self, **kw):
        Base.metadata.create_all(bind=self.engine, **kw)

    def drop_all(self, **kw):
        Base.metadata.drop_all(bind=self.engine, **kw)


# Module-level singleton
_db_instance = _DB()
db = _db_instance
