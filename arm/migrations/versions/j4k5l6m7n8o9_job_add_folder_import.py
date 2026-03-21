"""Add source_type and source_path columns for folder import support.

Revision ID: j4k5l6m7n8o9
Revises: i3j4k5l6m7n8
Create Date: 2026-03-21
"""
from alembic import op
import sqlalchemy as sa

revision = 'j4k5l6m7n8o9'
down_revision = 'i3j4k5l6m7n8'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('job') as batch_op:
        batch_op.add_column(
            sa.Column('source_type', sa.String(16), nullable=False, server_default='disc')
        )
        batch_op.add_column(
            sa.Column('source_path', sa.String(1024), nullable=True)
        )
        batch_op.alter_column('devpath', existing_type=sa.String(15), nullable=True)


def downgrade():
    with op.batch_alter_table('job') as batch_op:
        batch_op.alter_column('devpath', existing_type=sa.String(15), nullable=False)
        batch_op.drop_column('source_path')
        batch_op.drop_column('source_type')
