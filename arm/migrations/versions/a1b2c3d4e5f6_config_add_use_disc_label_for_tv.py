"""Add USE_DISC_LABEL_FOR_TV to config

Revision ID: a1b2c3d4e5f6
Revises: 95623e8c5d58
Create Date: 2025-10-18 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '95623e8c5d58'
branch_labels = None
depends_on = None


def upgrade():
    """Add USE_DISC_LABEL_FOR_TV column to config table."""
    op.add_column('config',
                  sa.Column('USE_DISC_LABEL_FOR_TV', sa.Boolean(), nullable=True)
                  )


def downgrade():
    """Remove USE_DISC_LABEL_FOR_TV column from config table."""
    op.drop_column('config', 'USE_DISC_LABEL_FOR_TV')
