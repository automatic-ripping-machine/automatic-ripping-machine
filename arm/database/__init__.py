"""Shared database layer — standalone SQLAlchemy (no Flask).

Drop-in replacement for Flask-SQLAlchemy's ``db`` object.
All existing code continues to use ``from arm.database import db``
and call ``db.session``, ``db.Column``, ``Model.query``, etc.
"""
import re
import logging

from sqlalchemy import (
    BigInteger, Column, Integer, String, Boolean, Float, Text,
    DateTime, SmallInteger, Unicode, Enum, ForeignKey,
    create_engine, text, event,
)
from sqlalchemy.orm import (
    DeclarativeBase, relationship, backref,
    scoped_session, sessionmaker,
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
    ForeignKey = staticmethod(ForeignKey)

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
        # SQLite: enable WAL mode (readers never block writers) and set a
        # 30-second busy_timeout so concurrent writes wait instead of
        # immediately raising SQLITE_BUSY.
        if db_uri.startswith('sqlite'):
            connect_args = engine_kw.pop('connect_args', {})
            connect_args.setdefault('timeout', 30)
            engine_kw['connect_args'] = connect_args
        self._engine = create_engine(db_uri, **engine_kw)
        if db_uri.startswith('sqlite'):
            @event.listens_for(self._engine, "connect")
            def _set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.close()
        factory = sessionmaker(bind=self._engine)
        self._session_factory = scoped_session(factory)
        log.info("Database engine initialised: %s", db_uri)

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
