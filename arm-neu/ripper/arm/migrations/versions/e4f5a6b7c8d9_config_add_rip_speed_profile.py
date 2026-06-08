"""config: add RIP_SPEED_PROFILE

Revision ID: e4f5a6b7c8d9
Revises: c3d4e5f6a7b8
Create Date: 2026-03-11

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e4f5a6b7c8d9'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('config') as batch_op:
        batch_op.add_column(sa.Column('RIP_SPEED_PROFILE', sa.String(20), nullable=True))


def downgrade():
    with op.batch_alter_table('config') as batch_op:
        batch_op.drop_column('RIP_SPEED_PROFILE')
