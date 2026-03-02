"""Job add transcode_overrides

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-03-01
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f3a4b5c6d7e8'
down_revision = 'e2f3a4b5c6d7'
branch_labels = None
depends_on = None


def upgrade():
    """Add transcode_overrides JSON text column to job table."""
    conn = op.get_bind()
    cols = [r[1] for r in conn.execute(sa.text("PRAGMA table_info('job')")).fetchall()]
    if 'transcode_overrides' not in cols:
        op.add_column('job',
                      sa.Column('transcode_overrides', sa.Text(), nullable=True)
                      )


def downgrade():
    op.drop_column('job', 'transcode_overrides')
