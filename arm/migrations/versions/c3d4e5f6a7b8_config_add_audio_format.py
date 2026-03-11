"""config: add AUDIO_FORMAT

Revision ID: c3d4e5f6a7b8
Revises: b5c6d7e8f9a0
Create Date: 2026-03-11

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c3d4e5f6a7b8'
down_revision = 'd3e4f5a6b7c8'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('config') as batch_op:
        batch_op.add_column(sa.Column('AUDIO_FORMAT', sa.String(20), nullable=True))


def downgrade():
    with op.batch_alter_table('config') as batch_op:
        batch_op.drop_column('AUDIO_FORMAT')
