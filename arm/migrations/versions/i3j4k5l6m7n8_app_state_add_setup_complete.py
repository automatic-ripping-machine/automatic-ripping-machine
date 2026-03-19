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
    # don't see the setup wizard on upgrade.  We detect an existing deployment
    # by checking if the job table has any rows — fresh installs have zero jobs.
    conn = op.get_bind()
    try:
        result = conn.execute(sa.text("SELECT COUNT(*) FROM job"))
        job_count = result.scalar()
        if job_count > 0:
            # Jobs exist → existing deployment, skip the wizard
            conn.execute(sa.text(
                "UPDATE app_state SET setup_complete = 1 WHERE id = 1"
            ))
    except Exception:
        pass  # job table might not exist yet during fresh alembic upgrade head


def downgrade():
    with op.batch_alter_table('app_state') as batch_op:
        batch_op.drop_column('setup_complete')
