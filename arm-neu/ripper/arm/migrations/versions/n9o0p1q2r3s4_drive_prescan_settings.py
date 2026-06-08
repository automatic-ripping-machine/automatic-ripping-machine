"""Add per-drive prescan settings columns.

Revision ID: n9o0p1q2r3s4
Revises: m8n9o0p1q2r3
Create Date: 2026-04-06
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'n9o0p1q2r3s4'
down_revision = 'm8n9o0p1q2r3'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('system_drives') as batch_op:
        batch_op.add_column(sa.Column('prescan_cache_mb', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('prescan_timeout', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('prescan_retries', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('disc_enum_timeout', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('system_drives') as batch_op:
        batch_op.drop_column('disc_enum_timeout')
        batch_op.drop_column('prescan_retries')
        batch_op.drop_column('prescan_timeout')
        batch_op.drop_column('prescan_cache_mb')
