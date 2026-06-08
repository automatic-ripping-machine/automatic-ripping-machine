"""Disambiguate JobState aliases (ripping/waiting) on Job.status; add
TrackStatus.failed to track_status_enum allowed set.

Revision ID: s4t5u6v7w8x9
Revises: r3s4t5u6v7w8
Create Date: 2026-05-02

The contracts v2.0.0 release renamed two pairs of aliased JobState
members so each gets a distinct wire string:

  VIDEO_RIPPING       'ripping'  -> 'video_ripping'
  AUDIO_RIPPING       'ripping'  -> 'audio_ripping'
  MANUAL_WAIT_STARTED 'waiting'  -> 'manual_paused' (member -> MANUAL_PAUSED)
  VIDEO_WAITING       'waiting'  -> 'makemkv_throttled' (member -> MAKEMKV_THROTTLED)

This migration backfills any existing rows still holding the old wire
strings before swapping the CHECK constraint on ``job.status``. It also
extends ``track.status`` to include the new ``TrackStatus.failed``
member (additive; no row backfill required).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = 's4t5u6v7w8x9'
down_revision = 'r3s4t5u6v7w8'
branch_labels = None
depends_on = None


# Allowed value sets after this migration. Self-contained so the
# migration survives future enum drift (matches the pattern in
# r3s4t5u6v7w8_enum_columns.py).
NEW_JOB_STATE_VALUES = (
    'success', 'fail', 'manual_paused', 'identifying', 'ready',
    'video_ripping', 'audio_ripping', 'info', 'copying', 'ejecting',
    'transcoding', 'waiting_transcode', 'makemkv_throttled',
)
NEW_TRACK_STATUS_VALUES = (
    'pending', 'ripping', 'encoding', 'success',
    'transcoded', 'transcode_failed', 'failed',
)
OLD_JOB_STATE_VALUES = (
    'success', 'fail', 'waiting', 'identifying', 'ready', 'ripping',
    'info', 'copying', 'ejecting', 'transcoding', 'waiting_transcode',
)
OLD_TRACK_STATUS_VALUES = (
    'pending', 'ripping', 'encoding', 'success',
    'transcoded', 'transcode_failed',
)


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Backfill existing Job.status rows that hold the old wire
    #    strings.
    #
    #    'ripping' could have meant either VIDEO_RIPPING or
    #    AUDIO_RIPPING; we infer from Job.disctype (music ->
    #    audio_ripping; otherwise -> video_ripping).
    #
    #    'waiting' could have meant either MANUAL_WAIT_STARTED
    #    (user-pause; long-lived) or VIDEO_WAITING (concurrency
    #    throttle; transient). We collapse all to 'manual_paused' since
    #    only paused jobs persist long enough to be observed in this
    #    state. If an operator had a row that should have been
    #    'makemkv_throttled', they can manually correct after the
    #    migration. (The throttle is a sub-second status flip during
    #    makemkvcon info/rip startup; it shouldn't be a long-lived
    #    persisted state.)
    #
    #    Order matters: the audio_ripping update filters on
    #    disctype='music' first, so the second update (which catches
    #    everything still holding 'ripping') doesn't mis-route music
    #    rows to video_ripping.
    conn.execute(sa.text("""
        UPDATE job
        SET status = 'audio_ripping'
        WHERE status = 'ripping' AND disctype = 'music'
    """))
    conn.execute(sa.text("""
        UPDATE job
        SET status = 'video_ripping'
        WHERE status = 'ripping'
    """))
    conn.execute(sa.text("""
        UPDATE job
        SET status = 'manual_paused'
        WHERE status = 'waiting'
    """))

    # 2. Refuse to migrate if any row still holds a value not in the new
    #    enum set after backfill. Better to fail loudly here than to
    #    silently truncate. Report row counts per bad value so the
    #    operator can decide between manual fix vs. restore-from-backup.
    rows = conn.execute(sa.text(
        "SELECT status, COUNT(*) FROM job "
        "WHERE status IS NOT NULL AND status NOT IN :allowed "
        "GROUP BY status"
    ).bindparams(sa.bindparam('allowed', expanding=True)),
        {'allowed': list(NEW_JOB_STATE_VALUES)}
    ).fetchall()
    if rows:
        bad_summary = ', '.join(
            f"{value!r}: {count} row(s)" for value, count in sorted(rows)
        )
        total = sum(count for _, count in rows)
        raise RuntimeError(
            f"job.status contains {total} row(s) with values not in the "
            f"new JobState set ({bad_summary}). Allowed: "
            f"{sorted(NEW_JOB_STATE_VALUES)}. Fix the rows manually then "
            f"retry."
        )

    # 3. Swap the CHECK constraint on job.status to the new value set.
    with op.batch_alter_table('job') as batch_op:
        batch_op.alter_column(
            'status',
            existing_type=sa.Enum(name='job_state_enum'),
            type_=sa.Enum(*NEW_JOB_STATE_VALUES, name='job_state_enum',
                          native_enum=False, validate_strings=True),
            existing_nullable=False,
        )

    # 4. Extend track_status_enum to include 'failed' (additive; no
    #    row backfill needed - new value joins the allowed set).
    with op.batch_alter_table('track') as batch_op:
        batch_op.alter_column(
            'status',
            existing_type=sa.Enum(name='track_status_enum'),
            type_=sa.Enum(*NEW_TRACK_STATUS_VALUES, name='track_status_enum',
                          native_enum=False, validate_strings=True),
            existing_nullable=True,
        )


def downgrade() -> None:
    """Reverse the wire-string backfills and shrink TrackStatus.

    audio_ripping/video_ripping both collapse back to 'ripping' (lossy:
    we lose the disctype-derived disambiguation).
    manual_paused/makemkv_throttled both collapse back to 'waiting'
    (lossy: we lose the user-pause-vs-throttle disambiguation).
    Track.status='failed' rows are dropped down to 'pending' since the
    pre-rename column had no equivalent member.
    """
    conn = op.get_bind()

    conn.execute(sa.text(
        "UPDATE job SET status = 'ripping' "
        "WHERE status IN ('audio_ripping', 'video_ripping')"
    ))
    conn.execute(sa.text(
        "UPDATE job SET status = 'waiting' "
        "WHERE status IN ('manual_paused', 'makemkv_throttled')"
    ))
    conn.execute(sa.text(
        "UPDATE track SET status = 'pending' WHERE status = 'failed'"
    ))

    with op.batch_alter_table('job') as batch_op:
        batch_op.alter_column(
            'status',
            existing_type=sa.Enum(name='job_state_enum'),
            type_=sa.Enum(*OLD_JOB_STATE_VALUES, name='job_state_enum',
                          native_enum=False, validate_strings=True),
            existing_nullable=False,
        )
    with op.batch_alter_table('track') as batch_op:
        batch_op.alter_column(
            'status',
            existing_type=sa.Enum(name='track_status_enum'),
            type_=sa.Enum(*OLD_TRACK_STATUS_VALUES, name='track_status_enum',
                          native_enum=False, validate_strings=True),
            existing_nullable=True,
        )
