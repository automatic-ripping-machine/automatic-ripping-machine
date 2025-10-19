"""Add GROUP_TV_DISCS_UNDER_SERIES to config

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2025-10-19 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6g7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    """Add GROUP_TV_DISCS_UNDER_SERIES column to config table."""
    op.add_column('config',
                  sa.Column('GROUP_TV_DISCS_UNDER_SERIES', sa.Boolean(), nullable=True)
                  )


def downgrade():
    """Remove GROUP_TV_DISCS_UNDER_SERIES column from config table."""
    op.drop_column('config', 'GROUP_TV_DISCS_UNDER_SERIES')
