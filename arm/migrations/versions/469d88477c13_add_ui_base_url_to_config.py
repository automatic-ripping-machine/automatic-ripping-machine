"""Add UI_BASE_URL to config

Revision ID: 469d88477c13
Revises: 2e0dc31fcb2e
Create Date: 2023-11-01 22:22:10.112867

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '469d88477c13'
down_revision = '2e0dc31fcb2e'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('config',
                  sa.Column('UI_BASE_URL', sa.String(length=128), nullable=True)
                  )


def downgrade():
    op.drop_column('config', 'UI_BASE_URL')
