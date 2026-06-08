"""drop legacy transcode_overrides JSON shape

NULL transcode_overrides values that use the pre-preset flat-key shape.
New-shape values (preset_slug / overrides / delete_source / output_extension
keys) are preserved. Migration is idempotent - re-running finds no
old-shape rows.

Revision ID: o0p1q2r3s4t5
Revises: n9o0p1q2r3s4
Create Date: 2026-04-21
"""
from __future__ import annotations

import json
import logging

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'o0p1q2r3s4t5'
down_revision = 'n9o0p1q2r3s4'
branch_labels = None
depends_on = None


# Keys recognized by the post-preset-rollout transcode_overrides shape.
# Anything else means the row predates the rollout and the transcoder
# will silently drop the fields at runtime.
#
# Kept as a literal (not imported from arm.api.v1.jobs) so that this
# migration remains self-contained and stable even if the runtime
# constant is renamed or moved in future code changes.
_NEW_SHAPE_KEYS = {
    'preset_slug',
    'overrides',
    'delete_source',
    'output_extension',
}


def _is_old_shape(raw):
    """Return (is_old_shape, offending_keys).

    Old-shape: any top-level key outside the allowlist. Malformed JSON
    or non-dict top-level values also count as old-shape (we'd rather
    NULL it than leave garbage that the transcoder silently drops).
    """
    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError):
        return True, ['<malformed JSON>']
    if not isinstance(parsed, dict):
        return True, ['<not a dict>']
    offending = sorted(set(parsed.keys()) - _NEW_SHAPE_KEYS)
    return bool(offending), offending


def upgrade():
    """NULL legacy transcode_overrides rows with a WARN log per row."""
    bind = op.get_bind()
    log = logging.getLogger('alembic.runtime.migration')

    rows = bind.execute(
        sa.text(
            "SELECT job_id, transcode_overrides FROM job "
            "WHERE transcode_overrides IS NOT NULL"
        )
    ).fetchall()

    legacy_ids = []
    for job_id, raw in rows:
        is_old, offending = _is_old_shape(raw)
        if is_old:
            log.warning(
                "Dropping legacy transcode_overrides on job_id=%s: "
                "offending keys=%s",
                job_id, offending,
            )
            legacy_ids.append(job_id)

    if legacy_ids:
        bind.execute(
            sa.text(
                "UPDATE job SET transcode_overrides = NULL "
                "WHERE job_id IN :ids"
            ).bindparams(sa.bindparam('ids', expanding=True)),
            {'ids': legacy_ids},
        )


def downgrade():
    """No-op.

    The legacy data cannot be recovered - it was NULLed, not moved.
    A downgrade path would need to read from a backup.
    """
    pass
