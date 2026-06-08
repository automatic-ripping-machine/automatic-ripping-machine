"""Add per-drive rip_speed column to system_drives.

Revision ID: l7m8n9o0p1q2
Revises: k6l7m8n9o0p1
Create Date: 2026-04-05
"""
from alembic import op
import sqlalchemy as sa

revision = 'l7m8n9o0p1q2'
down_revision = 'k6l7m8n9o0p1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('system_drives') as batch_op:
        batch_op.add_column(sa.Column('rip_speed', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('system_drives') as batch_op:
        batch_op.drop_column('rip_speed')
