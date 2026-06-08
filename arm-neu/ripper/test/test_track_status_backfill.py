"""Verify the backfills in ``r3s4t5u6v7w8_enum_columns``:

  * ``transcode_failed:<msg>`` track rows are split into
    ``status='transcode_failed'`` + ``error='<msg>'``
  * ``Job.status`` NULL rows are backfilled to ``'identifying'`` before
    the NOT NULL flip
  * Legacy ``track.status='fail'`` rows are remapped to ``'failed'``
    (PR #317; real production rows were observed on hifi 2026-05-03).

All three tests use the proven alembic ``command.upgrade`` harness
(mirroring ``test/test_migration_transcode_overrides_drop_legacy.py``):
upgrade to the prior revision, seed legacy rows via raw SQL, then
invoke the migration via alembic so coverage credits the migration
module's ``upgrade()`` body.
"""
import os

import pytest
import sqlalchemy as sa

from alembic import command
from alembic.config import Config as AlembicConfig


_MIGRATIONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'arm', 'migrations',
)
# Pre-r3 revision: plain VARCHAR columns with no CHECK constraint, so
# legacy values like 'fail' / NULL / 'transcode_failed: <msg>' can be
# seeded directly.
_PREV_REVISION = 'q2r3s4t5u6v7'
# The migration under test (enum CHECK constraints + backfills).
_R3_REVISION = 'r3s4t5u6v7w8'


def _make_config(db_path):
    cfg = AlembicConfig()
    cfg.set_main_option('script_location', _MIGRATIONS_DIR)
    cfg.set_main_option('sqlalchemy.url', f'sqlite:///{db_path}')
    return cfg


@pytest.fixture
def upgraded_db(tmp_path):
    """Upgrade the schema to the revision just before r3, then yield
    ``(cfg, engine)``. Tests seed legacy rows against the engine and
    then call ``command.upgrade(cfg, _R3_REVISION)`` to invoke the
    migration body via alembic.
    """
    db_path = tmp_path / 'test.db'
    cfg = _make_config(str(db_path))
    command.upgrade(cfg, _PREV_REVISION)

    engine = sa.create_engine(f'sqlite:///{db_path}')
    yield cfg, engine
    engine.dispose()


def _insert_job(engine, status, disctype='dvd', job_id=None):
    """Insert a job row with the given status; returns ``job_id``."""
    with engine.begin() as conn:
        if job_id is None:
            result = conn.execute(
                sa.text(
                    "INSERT INTO job (status, disctype, guid) "
                    "VALUES (:status, :disctype, lower(hex(randomblob(16))))"
                ),
                {"status": status, "disctype": disctype},
            )
            return result.lastrowid
        result = conn.execute(
            sa.text(
                "INSERT INTO job (job_id, status, disctype, guid) "
                "VALUES (:jid, :status, :disctype, :guid)"
            ),
            {
                "jid": job_id,
                "status": status,
                "disctype": disctype,
                "guid": f"test-guid-{job_id}",
            },
        )
        return result.lastrowid


def _insert_track(engine, job_id, status, error=None):
    """Insert a track row. Returns the track_id."""
    with engine.begin() as conn:
        result = conn.execute(
            sa.text(
                "INSERT INTO track (job_id, track_number, length, "
                "aspect_ratio, fps, main_feature, basename, filename, "
                "source, status, error) VALUES (:jid, '1', 0, '', 0.0, 0, "
                "'b', 'f', 'x', :status, :error)"
            ),
            {"jid": job_id, "status": status, "error": error},
        )
        return result.lastrowid


def test_backfill_splits_prefix_and_message(upgraded_db):
    """When a Track had status='transcode_failed: oh no' before the
    migration, the new schema must hold status='transcode_failed' and
    error='oh no'."""
    from arm_contracts.enums import TrackStatus

    cfg, engine = upgraded_db
    jid = _insert_job(engine, status='ready')
    tid = _insert_track(
        engine,
        job_id=jid,
        status='transcode_failed: encoder crashed at frame 1234',
        error=None,
    )

    command.upgrade(cfg, _R3_REVISION)

    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT status, error FROM track WHERE track_id=:tid"),
            {"tid": tid},
        ).fetchone()

    assert row[0] == TrackStatus.transcode_failed.value
    assert row[1] == "encoder crashed at frame 1234"


def test_backfill_job_status_nulls_to_identifying(upgraded_db):
    """A pre-migration Job row with status=NULL must be backfilled to
    'identifying' before the NOT NULL flip. The migration's
    ``_assert_clean`` pre-check filters ``WHERE col IS NOT NULL``, so
    NULL rows would otherwise pass the pre-check and then trip the new
    NOT NULL constraint mid-ALTER. ``'identifying'`` matches the new
    ``Job.__init__`` default.
    """
    from arm_contracts.enums import JobState

    cfg, engine = upgraded_db
    jid = _insert_job(engine, status=None)

    # Sanity: confirm the row really landed with NULL (the column is
    # nullable at this revision).
    with engine.connect() as conn:
        pre = conn.execute(
            sa.text("SELECT status FROM job WHERE job_id=:jid"),
            {"jid": jid},
        ).scalar()
    assert pre is None

    command.upgrade(cfg, _R3_REVISION)

    with engine.connect() as conn:
        post = conn.execute(
            sa.text("SELECT status FROM job WHERE job_id=:jid"),
            {"jid": jid},
        ).scalar()
    assert post == JobState.IDENTIFYING.value


def test_backfill_remaps_legacy_track_status_fail_to_failed(upgraded_db):
    """Pre-disambiguation, the music-rip failure path wrote
    ``JobState.FAILURE.value`` ('fail') into ``track.status``. The
    ``TrackStatus`` enum has no 'fail' member - the right value is
    'failed' (the new member added in s4t5u6v7w8x9). Real production
    rows from before the fix were observed on hifi 2026-05-03 (12 rows
    in job_id=123).

    The r3s4t5u6v7w8 backfill must remap them so the column constraint
    accepts them; otherwise the migration's ``_assert_clean`` pre-check
    blocks the upgrade.
    """
    from arm_contracts.enums import TrackStatus

    cfg, engine = upgraded_db
    jid = _insert_job(engine, status='ready')
    # Seed 3 rows with the legacy 'fail' value (mirroring the prod
    # artifact: multiple tracks from a single failed music job).
    for _ in range(3):
        _insert_track(engine, job_id=jid, status='fail')

    command.upgrade(cfg, _R3_REVISION)

    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(
                "SELECT status, COUNT(*) FROM track "
                "WHERE job_id=:jid GROUP BY status"
            ),
            {"jid": jid},
        ).fetchall()
    assert rows == [(TrackStatus.failed.value, 3)]
