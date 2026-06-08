"""job add raw_path and transcode_path columns

Revision ID: b8f2a1c3d4e5
Revises: 50d63e3650d2
Create Date: 2026-02-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b8f2a1c3d4e5'
down_revision = '50d63e3650d2'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('job', sa.Column('raw_path', sa.String(256), nullable=True))
    op.add_column('job', sa.Column('transcode_path', sa.String(256), nullable=True))


def downgrade():
    op.drop_column('job', 'transcode_path')
    op.drop_column('job', 'raw_path')
