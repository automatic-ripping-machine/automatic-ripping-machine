"""expected_titles table

Revision ID: p1q2r3s4t5u6
Revises: o0p1q2r3s4t5
Create Date: 2026-05-01

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = 'p1q2r3s4t5u6'
down_revision = 'o0p1q2r3s4t5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'expected_title',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('job_id', sa.Integer(),
                  sa.ForeignKey('job.job_id'), nullable=False),
        sa.Column('source', sa.String(16), nullable=False),
        sa.Column('title', sa.String(256), nullable=True),
        sa.Column('season', sa.Integer(), nullable=True),
        sa.Column('episode_number', sa.Integer(), nullable=True),
        sa.Column('external_id', sa.String(32), nullable=True),
        sa.Column('runtime_seconds', sa.Integer(), nullable=True),
        sa.Column('fetched_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_expected_title_job_id', 'expected_title', ['job_id'])


def downgrade() -> None:
    op.drop_index('ix_expected_title_job_id', table_name='expected_title')
    op.drop_table('expected_title')
