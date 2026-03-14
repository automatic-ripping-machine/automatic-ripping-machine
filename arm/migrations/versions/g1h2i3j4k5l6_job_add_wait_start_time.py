"""Job add wait_start_time

Revision ID: g1h2i3j4k5l6
Revises: f5a6b7c8d9e0
Create Date: 2026-03-12

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'g1h2i3j4k5l6'
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
