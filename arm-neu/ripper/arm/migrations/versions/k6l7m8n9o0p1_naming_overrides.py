"""Add per-job naming pattern overrides and per-track custom filename.

Revision ID: k6l7m8n9o0p1
Revises: k5l6m7n8o9p0
Create Date: 2026-03-25
"""
from alembic import op
import sqlalchemy as sa

revision = 'k6l7m8n9o0p1'
down_revision = 'k5l6m7n8o9p0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('job',
                  sa.Column('title_pattern_override', sa.String(512), nullable=True))
    op.add_column('job',
                  sa.Column('folder_pattern_override', sa.String(512), nullable=True))
    op.add_column('track',
                  sa.Column('custom_filename', sa.String(512), nullable=True))


def downgrade():
    op.drop_column('job', 'title_pattern_override')
    op.drop_column('job', 'folder_pattern_override')
    op.drop_column('track', 'custom_filename')
