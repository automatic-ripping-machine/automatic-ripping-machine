"""Create notification_channel and notification_outbox tables.

Schema-only migration. The legacy-config data translation runs in a
separate later migration so that step can be reviewed in isolation
and so this migration is fully reversible.

Revision ID: w8x9y0z1a2
Revises: v7w8x9y0z1
Create Date: 2026-05-19
"""
import sqlalchemy as sa
from alembic import op

revision = "w8x9y0z1a2"
down_revision = "v7w8x9y0z1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "notification_channel",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False,
                  server_default=sa.true()),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("subscribed_events", sa.JSON(), nullable=False,
                  server_default=sa.text("'[]'")),
        sa.Column("templates", sa.JSON(), nullable=False,
                  server_default=sa.text("'{}'")),
        sa.Column("last_fired_at", sa.DateTime(), nullable=True),
        sa.Column("last_success_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
    )

    op.create_table(
        "notification_outbox",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("channel_id", sa.Integer(),
                  sa.ForeignKey("notification_channel.id",
                                ondelete="CASCADE"),
                  nullable=False),
        sa.Column("event_key", sa.String(length=64), nullable=False),
        sa.Column("event_payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False,
                  server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False,
                  server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("last_error", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_notification_outbox_channel_id",
                    "notification_outbox", ["channel_id"])
    op.create_index("ix_notification_outbox_status",
                    "notification_outbox", ["status"])
    op.create_index("ix_notification_outbox_next_attempt_at",
                    "notification_outbox", ["next_attempt_at"])
    op.create_index("ix_notification_outbox_status_next",
                    "notification_outbox", ["status", "next_attempt_at"])


def downgrade():
    op.drop_index("ix_notification_outbox_status_next",
                  table_name="notification_outbox")
    op.drop_index("ix_notification_outbox_next_attempt_at",
                  table_name="notification_outbox")
    op.drop_index("ix_notification_outbox_status",
                  table_name="notification_outbox")
    op.drop_index("ix_notification_outbox_channel_id",
                  table_name="notification_outbox")
    op.drop_table("notification_outbox")
    op.drop_table("notification_channel")
