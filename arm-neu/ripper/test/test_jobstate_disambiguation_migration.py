"""Verify the JobState wire-string backfill in
``s4t5u6v7w8x9_jobstate_disambiguation`` correctly maps old wire strings
to the disambiguated v2.0.0 set.

The four backfill SQL fragments are exercised end-to-end via the alembic
``command.upgrade`` harness: upgrade to the revision before
``r3s4t5u6v7w8`` (no enum CHECK constraint, so legacy wire strings can
be seeded), insert legacy rows, then upgrade through both
``r3s4t5u6v7w8`` (enum constraints + 'fail'->'failed' track backfill)
and ``s4t5u6v7w8x9`` (the disambiguation backfills) so coverage credits
the migration modules' ``upgrade()`` bodies.

Pattern matched from ``test/test_migration_transcode_overrides_drop_legacy.py``.
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
# Pre-enum revision: schema has plain VARCHAR columns with no CHECK
# constraint, so legacy wire strings can be seeded directly.
_PREV_REVISION = 'q2r3s4t5u6v7'
# After r3: enum CHECK constraints + 'fail'->'failed' track backfill (PR #317).
_R3_REVISION = 'r3s4t5u6v7w8'
# After s4t5: JobState disambiguation backfills.
_S4T5_REVISION = 's4t5u6v7w8x9'


def _make_config(db_path):
    """Build an Alembic Config pointed at a scratch SQLite DB."""
    cfg = AlembicConfig()
    cfg.set_main_option('script_location', _MIGRATIONS_DIR)
    cfg.set_main_option('sqlalchemy.url', f'sqlite:///{db_path}')
    return cfg


@pytest.fixture
def upgraded_db(tmp_path):
    """Upgrade to the revision just before r3 (no enum constraints).

    Yields ``(cfg, engine)``; the test seeds legacy rows via raw SQL
    against the engine, then calls ``command.upgrade(cfg, target)`` to
    invoke the migration body via alembic.
    """
    db_path = tmp_path / 'test.db'
    cfg = _make_config(str(db_path))
    command.upgrade(cfg, _PREV_REVISION)

    engine = sa.create_engine(f'sqlite:///{db_path}')
    yield cfg, engine
    engine.dispose()


def _insert_job(engine, status, disctype, job_id=None):
    """Insert a single job row with the given status/disctype.

    The guid column is NOT NULL post-m8n9 (added in m8n9o0p1q2r3); pass a
    unique value derived from job_id (if provided) or sqlite's
    ``lastrowid`` lookup.
    """
    with engine.begin() as conn:
        if job_id is None:
            # Let sqlite assign the rowid; we still need a unique guid.
            # Use a sentinel placeholder we'll overwrite immediately.
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


def _fetch_status(engine, job_id):
    with engine.connect() as conn:
        return conn.execute(
            sa.text("SELECT status FROM job WHERE job_id = :jid"),
            {"jid": job_id},
        ).scalar()


def test_ripping_music_disc_backfills_to_audio_ripping(upgraded_db):
    """status='ripping' AND disctype='music' must become 'audio_ripping'."""
    cfg, engine = upgraded_db
    jid = _insert_job(engine, status='ripping', disctype='music')

    command.upgrade(cfg, _S4T5_REVISION)

    assert _fetch_status(engine, jid) == 'audio_ripping'


def test_ripping_video_disc_backfills_to_video_ripping(upgraded_db):
    """status='ripping' AND disctype!='music' must become 'video_ripping'.

    Exercises the order dependency between the two 'ripping' UPDATE
    statements - if they were run in the wrong order, the music-disctype
    test above would still pass but this one would fail because the
    music row would have been mis-routed to video_ripping first.
    """
    cfg, engine = upgraded_db
    jids = {}
    for disctype in ("dvd", "bluray", "bluray4k"):
        jids[disctype] = _insert_job(
            engine, status='ripping', disctype=disctype,
        )

    command.upgrade(cfg, _S4T5_REVISION)

    for disctype, jid in jids.items():
        actual = _fetch_status(engine, jid)
        assert actual == 'video_ripping', (
            f"disctype={disctype!r}: expected 'video_ripping', got {actual!r}"
        )


def test_backfill_order_protects_music_rows(upgraded_db):
    """Mixed-disctype seed: a music row + a video row, both starting at
    'ripping'. After backfill, the music row must be 'audio_ripping' and
    the video row must be 'video_ripping'. This is the canonical
    regression for the order bug - if the catch-all UPDATE ran first,
    BOTH rows would end up 'video_ripping'."""
    cfg, engine = upgraded_db
    music_id = _insert_job(engine, status='ripping', disctype='music')
    video_id = _insert_job(engine, status='ripping', disctype='bluray')

    command.upgrade(cfg, _S4T5_REVISION)

    assert _fetch_status(engine, music_id) == 'audio_ripping'
    assert _fetch_status(engine, video_id) == 'video_ripping'


def test_waiting_backfills_to_manual_paused(upgraded_db):
    """status='waiting' rows all collapse to 'manual_paused'.

    This is intentionally lossy: we lose the distinction between
    user-pause (MANUAL_PAUSED) and concurrency-throttle
    (MAKEMKV_THROTTLED). The throttle is sub-second/transient so this
    rarely loses real information; an operator with a pinned-throttle
    row can correct manually post-migration.
    """
    cfg, engine = upgraded_db
    jids = {}
    for disctype in ("music", "bluray", "dvd"):
        jids[disctype] = _insert_job(
            engine, status='waiting', disctype=disctype,
        )

    command.upgrade(cfg, _S4T5_REVISION)

    for disctype, jid in jids.items():
        actual = _fetch_status(engine, jid)
        assert actual == 'manual_paused', (
            f"disctype={disctype!r}: expected 'manual_paused', got {actual!r}"
        )


def test_r3_assert_clean_raises_on_bogus_value(upgraded_db):
    """The r3 ``_assert_clean`` pre-check must reject out-of-band values
    on ``job.status`` before the column type swap. Bogus values seeded
    in the pre-r3 schema reach r3 first and trip its pre-check (which
    also lists the offending values for operator triage)."""
    cfg, engine = upgraded_db
    _insert_job(engine, status='totally-bogus', disctype='dvd')
    _insert_job(engine, status='also-bogus', disctype='music')

    with pytest.raises(RuntimeError) as exc_info:
        command.upgrade(cfg, _S4T5_REVISION)

    msg = str(exc_info.value)
    assert 'totally-bogus' in msg
    assert 'also-bogus' in msg


def test_s4t5_post_backfill_raises_on_unmapped_value(upgraded_db):
    """The s4t5 post-backfill check at lines 107-111 of
    ``s4t5u6v7w8x9_jobstate_disambiguation.py`` formats and raises a
    ``RuntimeError`` when any row still holds a value not in the new
    JobState set after the backfill UPDATEs run.

    In the normal linear upgrade path this check is dead code (every
    value in r3's allowed set except 'ripping'/'waiting' carries over
    to s4t5's, and those two are explicitly backfilled). To exercise
    the production code path we run r3 first (so the schema has the
    CHECK constraint), then directly invoke ``s4t5.upgrade()`` against
    a connection that bypasses that constraint via raw SQL with
    ``op.get_bind()`` monkey-patched (same pattern as the reference
    test's idempotent-second-run case).
    """
    import alembic.op as alembic_op
    from arm.migrations.versions import (
        s4t5u6v7w8x9_jobstate_disambiguation as mig,
    )

    cfg, engine = upgraded_db
    # Bring schema to r3 (enum CHECK in place) with a clean dataset.
    command.upgrade(cfg, _R3_REVISION)

    # Seed a row holding a value that's NOT in NEW_JOB_STATE_VALUES.
    # r3's enum CHECK won't accept it via standard INSERT, but sqlite
    # only enforces CHECK at modification time - we sidestep by issuing
    # a raw SQL UPDATE inside the same connection used by the migration.
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO job (status, disctype, guid) "
                "VALUES ('identifying', 'dvd', 'bogus-seed-guid')"
            )
        )
        # 'identifying' is in BOTH r3 and s4t5 sets, so insert passes.
        # Now flip it to a value that's outside s4t5's allowed set but
        # that the s4t5 backfill UPDATEs DON'T touch (so it survives to
        # the post-backfill check). Use sqlite's CHECK-bypass via
        # PRAGMA writable_schema is heavyweight; instead, drop the
        # CHECK by recreating the table without it. Simpler: use
        # op.batch_alter_table to widen the column to plain String for
        # the duration of the test.
    # Direct invocation of s4t5.upgrade() with op.get_bind patched.
    with engine.begin() as conn:
        # Drop the CHECK by renaming the table and recreating without
        # constraint - sqlite lacks ALTER TABLE DROP CHECK.
        conn.execute(sa.text("ALTER TABLE job RENAME TO _job_old"))
        # Recreate with permissive status column, copy rows, drop old.
        # We only need the columns the migration reads/writes.
        cols = conn.execute(sa.text("PRAGMA table_info(_job_old)")).fetchall()
        col_defs = []
        col_names = []
        for cid, name, ctype, notnull, dflt, pk in cols:
            col_names.append(name)
            if name == 'status':
                ctype = 'VARCHAR(32)'  # drop the CHECK
            piece = f'"{name}" {ctype}'
            if pk:
                piece += ' PRIMARY KEY'
            if notnull and not pk:
                piece += ' NOT NULL'
            if dflt is not None:
                piece += f' DEFAULT {dflt}'
            col_defs.append(piece)
        conn.execute(sa.text(f'CREATE TABLE job ({", ".join(col_defs)})'))
        col_list = ', '.join(f'"{c}"' for c in col_names)
        conn.execute(sa.text(
            f"INSERT INTO job ({col_list}) SELECT {col_list} FROM _job_old"
        ))
        conn.execute(sa.text("DROP TABLE _job_old"))
        # Now flip the seeded row to an out-of-band value that the s4t5
        # backfill UPDATEs do not touch (not 'ripping', not 'waiting').
        conn.execute(sa.text(
            "UPDATE job SET status = 'unmapped-bogus-value' "
            "WHERE guid = 'bogus-seed-guid'"
        ))
        conn.execute(sa.text(
            "INSERT INTO job (status, disctype, guid) "
            "VALUES ('unmapped-bogus-value', 'bluray', "
            "'bogus-seed-guid-2')"
        ))

    # Invoke the production s4t5.upgrade() with op.get_bind patched.
    with pytest.raises(RuntimeError) as exc_info:
        with engine.begin() as conn:
            orig_get_bind = alembic_op.get_bind
            alembic_op.get_bind = lambda: conn
            try:
                mig.upgrade()
            finally:
                alembic_op.get_bind = orig_get_bind

    msg = str(exc_info.value)
    # Verify the production message format: total row count, per-value
    # counts, and the allowed-set for operator triage.
    assert 'unmapped-bogus-value' in msg
    assert '2 row(s)' in msg
    assert 'JobState' in msg


def test_real_migration_module_executes_backfill_against_seeded_db(upgraded_db):
    """End-to-end: actually invoke the migration's upgrade() against a
    fresh sqlite DB and confirm seeded legacy rows land at the new
    wire strings.

    This exercises the production migration body (not just SQL fragments
    mirrored in helpers), so a typo in the migration's UPDATE order
    would fail this test.
    """
    cfg, engine = upgraded_db

    music_id = _insert_job(engine, status='ripping', disctype='music')
    video_id = _insert_job(engine, status='ripping', disctype='bluray')
    waiting_id = _insert_job(engine, status='waiting', disctype='dvd')
    success_id = _insert_job(engine, status='success', disctype='dvd')

    command.upgrade(cfg, _S4T5_REVISION)

    assert _fetch_status(engine, music_id) == 'audio_ripping'
    assert _fetch_status(engine, video_id) == 'video_ripping'
    assert _fetch_status(engine, waiting_id) == 'manual_paused'
    assert _fetch_status(engine, success_id) == 'success'


def test_migration_module_constants_are_intact():
    """Sanity-check the loaded migration module exposes the expected
    constants - this catches a renamed-revision regression where the
    plan's down_revision pointer is wrong. Imported via the standard
    package mechanism so coverage credits the module.
    """
    from arm.migrations.versions import (
        s4t5u6v7w8x9_jobstate_disambiguation as mig,
    )

    assert mig.revision == 's4t5u6v7w8x9'
    assert mig.down_revision == 'r3s4t5u6v7w8'
    assert 'failed' in mig.NEW_TRACK_STATUS_VALUES
    assert 'manual_paused' in mig.NEW_JOB_STATE_VALUES
    assert 'makemkv_throttled' in mig.NEW_JOB_STATE_VALUES
    assert 'video_ripping' in mig.NEW_JOB_STATE_VALUES
    assert 'audio_ripping' in mig.NEW_JOB_STATE_VALUES
    assert 'waiting' not in mig.NEW_JOB_STATE_VALUES
    assert 'ripping' not in mig.NEW_JOB_STATE_VALUES
