"""Add MakeMKV segment info to track and SKIP_DUPLICATE_TITLES to config

Revision ID: d4e5f6a7b8c9
Revises: b2d3e4f5a6c7
Create Date: 2026-10-19

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd4e5f6a7b8c9'
down_revision = 'b2d3e4f5a6c7'
branch_labels = None
depends_on = None


def upgrade():
    """
    track.source_file   - MakeMKV source file name of the title (TINFO id 16), e.g. 00800.mpls
    track.segment_map   - MakeMKV segment map of the title (TINFO id 26), e.g. "155,156,157"
    track.duplicate_of  - track_number of the title this one duplicates, when ARM skipped it
    config.SKIP_DUPLICATE_TITLES - rip titles that are copies of the same content only once
    """
    with op.batch_alter_table('track', schema=None) as batch_op:
        batch_op.add_column(sa.Column('source_file', sa.String(length=256), nullable=True))
        batch_op.add_column(sa.Column('segment_map', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('duplicate_of', sa.String(length=4), nullable=True))
    with op.batch_alter_table('config', schema=None) as batch_op:
        batch_op.add_column(sa.Column('SKIP_DUPLICATE_TITLES', sa.Boolean(), nullable=True))


def downgrade():
    with op.batch_alter_table('config', schema=None) as batch_op:
        batch_op.drop_column('SKIP_DUPLICATE_TITLES')
    with op.batch_alter_table('track', schema=None) as batch_op:
        batch_op.drop_column('duplicate_of')
        batch_op.drop_column('segment_map')
        batch_op.drop_column('source_file')
