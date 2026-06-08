"""Test that the schema-only migration creates both tables and is reversible."""
import os

import pytest
import sqlalchemy as sa

from alembic import command
from alembic.config import Config as AlembicConfig


_MIGRATIONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'arm', 'migrations',
)


def _make_config(db_path):
    """Build an Alembic Config pointed at a scratch SQLite DB."""
    cfg = AlembicConfig()
    cfg.set_main_option('script_location', _MIGRATIONS_DIR)
    cfg.set_main_option('sqlalchemy.url', f'sqlite:///{db_path}')
    return cfg


def test_migration_creates_both_tables(tmp_path):
    db_path = tmp_path / 'test.db'
    cfg = _make_config(str(db_path))
    command.upgrade(cfg, 'w8x9y0z1a2')

    engine = sa.create_engine(f'sqlite:///{db_path}')
    insp = sa.inspect(engine)
    tables = set(insp.get_table_names())
    assert "notification_channel" in tables
    assert "notification_outbox" in tables
    engine.dispose()


def test_migration_creates_composite_index(tmp_path):
    db_path = tmp_path / 'test.db'
    cfg = _make_config(str(db_path))
    command.upgrade(cfg, 'w8x9y0z1a2')

    engine = sa.create_engine(f'sqlite:///{db_path}')
    insp = sa.inspect(engine)
    indexes = {i["name"] for i in insp.get_indexes("notification_outbox")}
    assert "ix_notification_outbox_status_next" in indexes
    engine.dispose()


def test_migration_is_reversible(tmp_path):
    db_path = tmp_path / 'test.db'
    cfg = _make_config(str(db_path))
    command.upgrade(cfg, 'w8x9y0z1a2')
    command.downgrade(cfg, 'v7w8x9y0z1')

    engine = sa.create_engine(f'sqlite:///{db_path}')
    insp = sa.inspect(engine)
    tables = set(insp.get_table_names())
    assert "notification_channel" not in tables
    assert "notification_outbox" not in tables
    engine.dispose()
