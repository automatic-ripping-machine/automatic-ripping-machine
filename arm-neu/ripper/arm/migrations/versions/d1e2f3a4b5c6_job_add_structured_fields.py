"""Job add structured metadata fields (artist, album, season, episode)

Revision ID: d1e2f3a4b5c6
Revises: c7d8e9f0a1b2
Create Date: 2026-02-27
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd1e2f3a4b5c6'
down_revision = 'c7d8e9f0a1b2'
branch_labels = None
depends_on = None

_COLUMNS = [
    ('artist',         sa.String(256)),
    ('artist_auto',    sa.String(256)),
    ('artist_manual',  sa.String(256)),
    ('album',          sa.String(256)),
    ('album_auto',     sa.String(256)),
    ('album_manual',   sa.String(256)),
    ('season',         sa.String(10)),
    ('season_auto',    sa.String(10)),
    ('season_manual',  sa.String(10)),
    ('episode',        sa.String(10)),
    ('episode_auto',   sa.String(10)),
    ('episode_manual', sa.String(10)),
]


def upgrade():
    for name, col_type in _COLUMNS:
        op.add_column('job', sa.Column(name, col_type, nullable=True))


def downgrade():
    for name, _ in _COLUMNS:
        op.drop_column('job', name)
