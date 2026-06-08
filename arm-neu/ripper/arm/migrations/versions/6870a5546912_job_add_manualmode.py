"""job add manualmode

Revision ID: 6870a5546912
Revises: daab0c779980
Create Date: 2024-11-13 16:05:48.027086

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6870a5546912'
down_revision = 'daab0c779980'
branch_labels = None
depends_on = None


def upgrade():
    """
        Update Job table with manual mode
        True when drive is set to manual
        False for all others

        manual_mode - boolean
        """
    op.add_column('job',
                  sa.Column('manual_mode', sa.Boolean(), nullable=True)
                  )


def downgrade():
    op.drop_column('job', 'manual_mode')
