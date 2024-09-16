"""Job add isISO

Revision ID: b326a3663939
Revises: 469d88477c13
Create Date: 2024-03-29 21:14:59.834607

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b326a3663939'
down_revision = '469d88477c13'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('job',
                  sa.Column('is_iso', sa.Boolean())
                  )


def downgrade():
    op.drop_column('job', 'is_iso')
