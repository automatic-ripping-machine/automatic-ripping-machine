"""Tests for the expected_title table creation migration."""
import os

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import create_engine, inspect, text


_MIGRATIONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'arm', 'migrations',
)
_PREV_REVISION = 'o0p1q2r3s4t5'
_TARGET_REVISION = 'p1q2r3s4t5u6'


def _make_config(db_path):
    cfg = AlembicConfig()
    cfg.set_main_option('script_location', _MIGRATIONS_DIR)
    cfg.set_main_option('sqlalchemy.url', f'sqlite:///{db_path}')
    return cfg


@pytest.fixture
def db_at_prev_revision(tmp_path):
    db_path = tmp_path / 'test.db'
    cfg = _make_config(str(db_path))
    command.upgrade(cfg, _PREV_REVISION)
    engine = create_engine(f'sqlite:///{db_path}')
    yield cfg, engine
    engine.dispose()


def test_table_does_not_exist_before_migration(db_at_prev_revision):
    cfg, engine = db_at_prev_revision
    insp = inspect(engine)
    assert 'expected_title' not in insp.get_table_names()


def test_upgrade_creates_table_and_index(db_at_prev_revision):
    cfg, engine = db_at_prev_revision
    command.upgrade(cfg, _TARGET_REVISION)

    insp = inspect(engine)
    assert 'expected_title' in insp.get_table_names()

    cols = {c['name']: c for c in insp.get_columns('expected_title')}
    assert set(cols.keys()) == {
        'id', 'job_id', 'source', 'title', 'season', 'episode_number',
        'external_id', 'runtime_seconds', 'fetched_at',
    }
    assert cols['job_id']['nullable'] is False
    assert cols['source']['nullable'] is False
    assert cols['runtime_seconds']['nullable'] is True

    index_names = {ix['name'] for ix in insp.get_indexes('expected_title')}
    assert 'ix_expected_title_job_id' in index_names


def test_fk_to_job_works_after_upgrade(db_at_prev_revision):
    """Smoke test: confirm we can insert into expected_title with a valid
    job_id and read it back. Does not assert FK enforcement (SQLite's FK
    pragma is off by default); the FK shape is structural only here.
    """
    cfg, engine = db_at_prev_revision
    command.upgrade(cfg, _TARGET_REVISION)

    with engine.begin() as conn:
        # Insert a Job parent row, then a child expected_title.
        conn.execute(text(
            "INSERT INTO job (job_id, guid) VALUES (1, 'test-guid-1')"
        ))
        conn.execute(text(
            "INSERT INTO expected_title (job_id, source, title, runtime_seconds) "
            "VALUES (1, 'omdb', 'Test', 5712)"
        ))
        rows = conn.execute(text(
            "SELECT title, runtime_seconds FROM expected_title WHERE job_id = 1"
        )).fetchall()
        assert len(rows) == 1
        assert rows[0][0] == 'Test'
        assert rows[0][1] == 5712


def test_downgrade_drops_table(db_at_prev_revision):
    cfg, engine = db_at_prev_revision
    command.upgrade(cfg, _TARGET_REVISION)
    command.downgrade(cfg, _PREV_REVISION)

    insp = inspect(engine)
    assert 'expected_title' not in insp.get_table_names()
