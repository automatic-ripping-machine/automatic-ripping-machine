"""Add makemkv_key_valid and makemkv_key_checked_at to app_state.

Revision ID: j4k5l6m7n8o9
Revises: i3j4k5l6m7n8
Create Date: 2026-03-22
"""
from alembic import op
import sqlalchemy as sa

revision = 'j4k5l6m7n8o9'
down_revision = 'i3j4k5l6m7n8'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('app_state') as batch_op:
        batch_op.add_column(sa.Column('makemkv_key_valid', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('makemkv_key_checked_at', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('app_state') as batch_op:
        batch_op.drop_column('makemkv_key_checked_at')
        batch_op.drop_column('makemkv_key_valid')
