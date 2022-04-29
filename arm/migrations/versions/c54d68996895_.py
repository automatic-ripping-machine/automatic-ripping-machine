"""

Revision ID: c54d68996895
Revises: 6dfe7244b18e
Create Date: 2021-08-21 06:49:37.250500

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c54d68996895'
down_revision = '6dfe7244b18e'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('job',
                  sa.Column('stage', sa.String())
                  )


def downgrade():
    op.drop_column('job', 'stage')
