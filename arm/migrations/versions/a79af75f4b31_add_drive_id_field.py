"""Add drive id field

Revision ID: a79af75f4b31
Revises: 5ceacc391408
Create Date: 2025-01-04 14:39:09.972294

"""
from alembic import op
import sqlalchemy as sa

# pylint: disable=no-member

# revision identifiers, used by Alembic.
revision = 'a79af75f4b31'
down_revision = '5ceacc391408'
branch_labels = None
depends_on = None


def upgrade():
    # new static information
    op.add_column('system_drives', sa.Column('serial_id', sa.String(100)))


def downgrade():
    op.drop_column('system_drives', 'serial_id')
