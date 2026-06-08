"""Create app_state table

Revision ID: a1b2c3d4e5f6
Revises: b8f2a1c3d4e5
Create Date: 2026-02-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'b8f2a1c3d4e5'
branch_labels = None
depends_on = None


def upgrade():
    table = op.create_table(
        'app_state',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('ripping_paused', sa.Boolean(), nullable=False, server_default=sa.text('0')),
    )
    # Seed the singleton row
    op.bulk_insert(table, [{'id': 1, 'ripping_paused': False}])


def downgrade():
    op.drop_table('app_state')
