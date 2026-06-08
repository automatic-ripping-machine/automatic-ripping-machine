"""SystemDrives add uhd_capable

Revision ID: c7d8e9f0a1b2
Revises: a1b2c3d4e5f6
Create Date: 2026-02-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c7d8e9f0a1b2'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('system_drives', sa.Column('uhd_capable', sa.Boolean))


def downgrade():
    op.drop_column('system_drives', 'uhd_capable')
