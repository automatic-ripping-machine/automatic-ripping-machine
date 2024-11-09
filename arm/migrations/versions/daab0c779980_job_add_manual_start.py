"""Job manual start

Revision ID: daab0c779980
Revises: 200cf208e048
Create Date: 2024-11-09 23:03:11.307327

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'daab0c779980'
down_revision = '200cf208e048'
branch_labels = None
depends_on = None


def upgrade():
    """
    Update Job table with an additional column

    manual_start - boolean
    - Used as a check point against a manual job, is it ready to go
    """
    op.add_column('job',
                  sa.Column('manual_start', sa.Boolean(), nullable=True)
                  )


def downgrade():
    op.drop_column('job', 'manual_start')
