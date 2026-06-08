"""tracks process

Revision ID: 200cf208e048
Revises: 5bafd482b2c6
Create Date: 2024-11-04 22:17:34.942333

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '200cf208e048'
down_revision = '5bafd482b2c6'
branch_labels = None
depends_on = None


def upgrade():
    """
    Update Tracks table with a process column flag

    process - boolean
    - Used when running a manual job, allowing selection of tracks
    """
    op.add_column('track',
                  sa.Column('process', sa.Boolean(), nullable=True)
                  )


def downgrade():
    op.drop_column('track', 'process')
