"""Tests for the legacy transcode_overrides drop migration.

Verifies that:
  - Old-shape rows are NULLed with a WARN log
  - New-shape rows are preserved untouched
  - Mixed table is partitioned correctly
  - Malformed JSON is NULLed (treated as old-shape)
  - Idempotent (re-running upgrade() against already-migrated data
    produces no new warnings and no changes)
"""
import json
import logging
import os

import pytest

from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import create_engine, text


_MIGRATIONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'arm', 'migrations',
)
_PREV_REVISION = 'n9o0p1q2r3s4'
_TARGET_REVISION = 'o0p1q2r3s4t5'


def _make_config(db_path):
    """Build an Alembic Config pointed at a scratch SQLite DB."""
    cfg = AlembicConfig()
    cfg.set_main_option('script_location', _MIGRATIONS_DIR)
    cfg.set_main_option('sqlalchemy.url', f'sqlite:///{db_path}')
    return cfg


@pytest.fixture
def upgraded_db(tmp_path):
    """Upgrade to the revision just before this migration; yield (cfg, engine).

    The fixture seeds the alembic_version table to the prior revision so the
    target migration can be applied on demand by the test.
    """
    db_path = tmp_path / 'test.db'
    cfg = _make_config(str(db_path))

    # Upgrade to the revision just before this migration so the schema
    # (including the job.transcode_overrides column) exists but our new
    # migration has not yet run.
    command.upgrade(cfg, _PREV_REVISION)

    engine = create_engine(f'sqlite:///{db_path}')
    yield cfg, engine
    engine.dispose()


def _insert_job(engine, job_id, transcode_overrides):
    """Insert a minimal row into the job table for the test.

    The guid column is NOT NULL (added in migration m8n9o0p1q2r3); any value
    unique per row is fine for these tests.
    """
    guid = f'test-guid-{job_id}'
    with engine.begin() as conn:
        if transcode_overrides is None:
            conn.execute(
                text(
                    "INSERT INTO job (job_id, guid, transcode_overrides) "
                    "VALUES (:jid, :guid, NULL)"
                ),
                {'jid': job_id, 'guid': guid},
            )
        else:
            conn.execute(
                text(
                    "INSERT INTO job (job_id, guid, transcode_overrides) "
                    "VALUES (:jid, :guid, :val)"
                ),
                {'jid': job_id, 'guid': guid, 'val': transcode_overrides},
            )


def _fetch_overrides(engine, job_id):
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT transcode_overrides FROM job WHERE job_id = :jid"),
            {'jid': job_id},
        ).scalar()


def test_old_shape_row_nulled_with_warning(upgraded_db, caplog):
    cfg, engine = upgraded_db
    old_shape = json.dumps({
        'video_encoder': 'nvenc_h265',
        'handbrake_preset': 'Foo',
    })
    _insert_job(engine, 1, old_shape)

    with caplog.at_level(logging.WARNING, logger='alembic.runtime.migration'):
        command.upgrade(cfg, _TARGET_REVISION)

    assert _fetch_overrides(engine, 1) is None

    warn_messages = [
        r.getMessage() for r in caplog.records
        if r.levelno == logging.WARNING
        and r.name == 'alembic.runtime.migration'
    ]
    combined = '\n'.join(warn_messages)
    assert 'job_id=1' in combined
    assert 'video_encoder' in combined or 'handbrake_preset' in combined


def test_new_shape_row_preserved(upgraded_db, caplog):
    cfg, engine = upgraded_db
    new_shape = json.dumps({
        'preset_slug': 'nvidia_balanced',
        'overrides': {},
    })
    _insert_job(engine, 2, new_shape)

    with caplog.at_level(logging.WARNING, logger='alembic.runtime.migration'):
        command.upgrade(cfg, _TARGET_REVISION)

    stored = _fetch_overrides(engine, 2)
    assert stored is not None
    assert json.loads(stored) == json.loads(new_shape)

    warn_messages = '\n'.join(
        r.getMessage() for r in caplog.records
        if r.levelno == logging.WARNING
        and r.name == 'alembic.runtime.migration'
    )
    assert 'job_id=2' not in warn_messages


def test_new_shape_with_output_extension_preserved(upgraded_db):
    cfg, engine = upgraded_db
    new_shape = json.dumps({
        'preset_slug': 'amd_balanced',
        'overrides': {'video_quality': 22},
        'delete_source': True,
        'output_extension': 'mkv',
    })
    _insert_job(engine, 5, new_shape)

    command.upgrade(cfg, _TARGET_REVISION)

    stored = _fetch_overrides(engine, 5)
    assert stored is not None
    assert json.loads(stored) == json.loads(new_shape)


def test_mixed_rows_partitioned(upgraded_db):
    cfg, engine = upgraded_db
    _insert_job(engine, 1, json.dumps({'video_encoder': 'x265'}))  # old
    _insert_job(engine, 2, json.dumps({'preset_slug': 'amd_balanced'}))  # new
    _insert_job(engine, 3, None)  # already null

    command.upgrade(cfg, _TARGET_REVISION)

    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT job_id, transcode_overrides FROM job ORDER BY job_id")
        ).fetchall()
    assert rows[0][1] is None  # old -> NULL
    assert json.loads(rows[1][1]) == {'preset_slug': 'amd_balanced'}
    assert rows[2][1] is None  # already NULL


def test_malformed_json_nulled(upgraded_db, caplog):
    cfg, engine = upgraded_db
    _insert_job(engine, 4, 'not json at all')

    with caplog.at_level(logging.WARNING, logger='alembic.runtime.migration'):
        command.upgrade(cfg, _TARGET_REVISION)

    assert _fetch_overrides(engine, 4) is None
    warn_messages = '\n'.join(
        r.getMessage() for r in caplog.records
        if r.levelno == logging.WARNING
        and r.name == 'alembic.runtime.migration'
    )
    assert 'job_id=4' in warn_messages
    assert 'malformed' in warn_messages.lower()


def test_non_dict_json_nulled(upgraded_db, caplog):
    """Top-level JSON arrays / strings are also old-shape."""
    cfg, engine = upgraded_db
    _insert_job(engine, 6, '["a", "b"]')

    with caplog.at_level(logging.WARNING, logger='alembic.runtime.migration'):
        command.upgrade(cfg, _TARGET_REVISION)

    assert _fetch_overrides(engine, 6) is None


def test_idempotent_data_transformation(upgraded_db, caplog):
    """Re-applying the migration's upgrade() logic on already-migrated data
    is a no-op: no rows change, no WARN logs are emitted.

    Alembic refuses to re-run a completed revision via command.upgrade, so we
    import the migration module directly and invoke upgrade() a second time
    with op.get_bind() monkey-patched to our test engine connection.
    """
    cfg, engine = upgraded_db

    # First run via the normal alembic upgrade path. Seed a mix.
    _insert_job(engine, 1, json.dumps({'video_encoder': 'x265'}))
    _insert_job(engine, 2, json.dumps({'preset_slug': 'amd_balanced'}))
    command.upgrade(cfg, _TARGET_REVISION)

    # After the first run: legacy row NULLed, new-shape row preserved.
    assert _fetch_overrides(engine, 1) is None
    assert _fetch_overrides(engine, 2) is not None

    # Second invocation: import migration module, call upgrade() directly
    # on a fresh connection with op.get_bind patched.
    from alembic.script import ScriptDirectory
    import alembic.op as alembic_op

    script = ScriptDirectory.from_config(cfg)
    revision = script.get_revision(_TARGET_REVISION)
    module = revision.module

    caplog.clear()
    with caplog.at_level(logging.WARNING, logger='alembic.runtime.migration'):
        with engine.begin() as conn:
            orig_get_bind = alembic_op.get_bind
            alembic_op.get_bind = lambda: conn
            try:
                module.upgrade()
            finally:
                alembic_op.get_bind = orig_get_bind

    # Row states unchanged by the second run.
    assert _fetch_overrides(engine, 1) is None
    assert json.loads(_fetch_overrides(engine, 2)) == {'preset_slug': 'amd_balanced'}

    # No fresh WARN logs: the second run finds no legacy rows.
    warn_records = [
        r for r in caplog.records
        if r.levelno == logging.WARNING
        and r.name == 'alembic.runtime.migration'
    ]
    assert warn_records == [], (
        f"Second run should be silent; got "
        f"{[r.getMessage() for r in warn_records]}"
    )
