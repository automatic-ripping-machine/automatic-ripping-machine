"""Job add wait_start_time

Revision ID: a1b2c3d4e5f6
Revises: f5a6b7c8d9e0
Create Date: 2026-03-12

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'f5a6b7c8d9e0'
branch_labels = None
depends_on = None


def upgrade():
    """Add wait_start_time column to job table."""
    conn = op.get_bind()
    cols = [r[1] for r in conn.execute(sa.text("PRAGMA table_info('job')")).fetchall()]
    if 'wait_start_time' not in cols:
        op.add_column('job',
                      sa.Column('wait_start_time', sa.DateTime(), nullable=True)
                      )


def downgrade():
    op.drop_column('job', 'wait_start_time')
