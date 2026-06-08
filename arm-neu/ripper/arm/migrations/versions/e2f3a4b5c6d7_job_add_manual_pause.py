"""Job add manual_pause

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-02-28
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e2f3a4b5c6d7'
down_revision = 'd1e2f3a4b5c6'
branch_labels = None
depends_on = None


def upgrade():
    """Add manual_pause boolean to job table for per-job pause support."""
    op.add_column('job',
                  sa.Column('manual_pause', sa.Boolean(), nullable=True)
                  )


def downgrade():
    op.drop_column('job', 'manual_pause')
