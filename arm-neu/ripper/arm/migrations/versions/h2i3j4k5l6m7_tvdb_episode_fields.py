"""Add TVDB episode matching fields

Revision ID: h2i3j4k5l6m7
Revises: g1h2i3j4k5l6
Create Date: 2026-03-13

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'h2i3j4k5l6m7'
down_revision = 'g1h2i3j4k5l6'
branch_labels = None
depends_on = None


def upgrade():
    """Add episode_number and episode_name to track, tvdb_id to job."""
    conn = op.get_bind()

    track_cols = [r[1] for r in conn.execute(sa.text("PRAGMA table_info('track')")).fetchall()]
    if 'episode_number' not in track_cols:
        op.add_column('track', sa.Column('episode_number', sa.String(10), nullable=True))
    if 'episode_name' not in track_cols:
        op.add_column('track', sa.Column('episode_name', sa.String(256), nullable=True))

    job_cols = [r[1] for r in conn.execute(sa.text("PRAGMA table_info('job')")).fetchall()]
    if 'tvdb_id' not in job_cols:
        op.add_column('job', sa.Column('tvdb_id', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('track', 'episode_number')
    op.drop_column('track', 'episode_name')
    op.drop_column('job', 'tvdb_id')
