"""Merge ffmpeg support and previous merge heads

Revision ID: e5f6g7h8i0j1
Revises: 50d63e3650d2, d4e5f6g7h8i9
Create Date: 2025-11-17 22:00:00.000000

"""
# no imports required, merge migration only

# revision identifiers, used by Alembic.
revision = 'e5f6g7h8i0j1'
down_revision = ('50d63e3650d2', 'd4e5f6g7h8i9')
branch_labels = None
depends_on = None


def upgrade():
    """No-op merge upgrade."""
    # This revision exists only to merge diverging heads in the migration graph.


def downgrade():
    """No-op merge downgrade."""
    # Nothing to downgrade for the merge-only revision.
