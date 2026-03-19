"""Add setup_complete to app_state.

Revision ID: i3j4k5l6m7n8
Revises: h2i3j4k5l6m7
Create Date: 2026-03-19
"""
from alembic import op
import sqlalchemy as sa

revision = 'i3j4k5l6m7n8'
down_revision = 'h2i3j4k5l6m7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('app_state') as batch_op:
        batch_op.add_column(sa.Column('setup_complete', sa.Boolean(), nullable=False, server_default='0'))

    # Data migration: mark existing deployments as setup-complete so they
    # don't see the setup wizard on upgrade.  During a fresh `alembic upgrade
    # head` this migration is the newest, so no *other* revision will be in
    # alembic_version yet — the check below detects that and leaves the
    # default (False) in place.
    conn = op.get_bind()
    try:
        result = conn.execute(sa.text(
            "SELECT COUNT(*) FROM app_state WHERE id = 1"
        ))
        if result.scalar() > 0:
            # Row exists → this is an upgrade, not a fresh install
            conn.execute(sa.text(
                "UPDATE app_state SET setup_complete = 1 WHERE id = 1"
            ))
    except Exception:
        pass  # Table might not have any rows yet on fresh install


def downgrade():
    with op.batch_alter_table('app_state') as batch_op:
        batch_op.drop_column('setup_complete')
