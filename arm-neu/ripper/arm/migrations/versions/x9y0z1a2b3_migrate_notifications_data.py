"""Data migration: legacy notification config -> channel rows; drop
legacy notification columns from Config.

Schema-only changes for the new tables landed in w8x9y0z1a2. This
migration handles the one-shot data move and the legacy-column drop.
After this migration, the legacy field reads in arm/ripper/utils.py
are removed in the same release (sub-spec 2, task N19).

Only the legacy notification columns that actually exist in the DB
schema are processed (PB_KEY, IFTTT_*, PO_*, NOTIFY_RIP, NOTIFY_TRANSCODE).
The arm.yaml-only fields (JSON_URL, APPRISE, BASH_SCRIPT) are not
migrated automatically — they live in the YAML config and the YAML
reading code is removed in N19. Users with active YAML-based
notifications must recreate them via the new channels API after upgrade.

Revision ID: x9y0z1a2b3
Revises: w8x9y0z1a2
Create Date: 2026-05-18
"""
import datetime
import json
import logging

import sqlalchemy as sa
from alembic import op

from arm.notifications.migration_helpers import translate_legacy_config

revision = "x9y0z1a2b3"
down_revision = "w8x9y0z1a2"
branch_labels = None
depends_on = None

log = logging.getLogger("alembic.migration.notifications")

_LEGACY_COLS = [
    "PB_KEY", "IFTTT_KEY", "IFTTT_EVENT",
    "PO_USER_KEY", "PO_APP_KEY",
    "NOTIFY_RIP", "NOTIFY_TRANSCODE",
]


def upgrade():
    bind = op.get_bind()

    select_cols = ", ".join(_LEGACY_COLS)
    result = bind.execute(
        sa.text(f"SELECT {select_cols} FROM config LIMIT 1")
    ).fetchone()

    if result is not None:
        legacy = dict(zip(_LEGACY_COLS, result))
        for k, v in list(legacy.items()):
            if v is None:
                legacy[k] = ""

        channel_rows = translate_legacy_config(legacy)
        now = datetime.datetime.utcnow().isoformat()
        for r in channel_rows:
            bind.execute(
                sa.text(
                    "INSERT INTO notification_channel "
                    "(type, name, enabled, config, subscribed_events, "
                    "templates, created_at, updated_at) "
                    "VALUES (:type, :name, :enabled, :config, "
                    ":subscribed_events, :templates, :created_at, "
                    ":updated_at)"
                ),
                {
                    "type": r["type"],
                    "name": r["name"],
                    "enabled": r["enabled"],
                    "config": json.dumps(r["config"]),
                    "subscribed_events": json.dumps(r["subscribed_events"]),
                    "templates": json.dumps(r["templates"]),
                    "created_at": now,
                    "updated_at": now,
                },
            )
        log.info("migrated %d legacy notification entries to channels",
                 len(channel_rows))

    with op.batch_alter_table("config") as batch_op:
        for col in _LEGACY_COLS:
            try:
                batch_op.drop_column(col)
            except Exception as exc:
                log.debug("drop_column %s: %s", col, exc)


def downgrade():
    """Downgrade is not supported — the legacy columns are dropped with
    no schema-only way to recover the original types. A user truly
    needing to revert can restore from backup."""
    raise NotImplementedError(
        "downgrade from x9y0z1a2b3 is not supported; restore from backup."
    )
