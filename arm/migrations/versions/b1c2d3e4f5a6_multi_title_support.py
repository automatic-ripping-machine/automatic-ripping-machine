"""multi-title disc support: per-track metadata + job multi_title flag

Revision ID: b1c2d3e4f5a6
Revises: a4b5c6d7e8f9
Create Date: 2026-03-09

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b1c2d3e4f5a6'
down_revision = 'a4b5c6d7e8f9'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('track') as batch_op:
        batch_op.add_column(sa.Column('title', sa.String(256), nullable=True))
        batch_op.add_column(sa.Column('year', sa.String(4), nullable=True))
        batch_op.add_column(sa.Column('imdb_id', sa.String(15), nullable=True))
        batch_op.add_column(sa.Column('poster_url', sa.String(256), nullable=True))
        batch_op.add_column(sa.Column('video_type', sa.String(20), nullable=True))

    with op.batch_alter_table('job') as batch_op:
        batch_op.add_column(sa.Column('multi_title', sa.Boolean(), server_default='0'))


def downgrade():
    with op.batch_alter_table('job') as batch_op:
        batch_op.drop_column('multi_title')

    with op.batch_alter_table('track') as batch_op:
        batch_op.drop_column('video_type')
        batch_op.drop_column('poster_url')
        batch_op.drop_column('imdb_id')
        batch_op.drop_column('year')
        batch_op.drop_column('title')
