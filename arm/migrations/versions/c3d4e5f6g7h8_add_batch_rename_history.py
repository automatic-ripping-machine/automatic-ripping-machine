"""Add batch_rename_history table

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2025-10-19 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3d4e5f6g7h8'
down_revision = 'b2c3d4e5f6g7'
branch_labels = None
depends_on = None


def upgrade():
    """Add batch_rename_history table for tracking folder rename operations."""
    op.create_table(
        'batch_rename_history',
        sa.Column('history_id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('batch_id', sa.String(64), nullable=False, index=True),
        sa.Column('job_id', sa.Integer(), sa.ForeignKey('job.job_id'), nullable=False),
        sa.Column('old_path', sa.String(512), nullable=False),
        sa.Column('new_path', sa.String(512), nullable=False),
        sa.Column('old_folder_name', sa.String(256), nullable=False),
        sa.Column('new_folder_name', sa.String(256), nullable=False),
        sa.Column('series_name', sa.String(256)),
        sa.Column('disc_identifier', sa.String(32)),
        sa.Column('consolidated_under_series', sa.Boolean(), default=False),
        sa.Column('series_parent_folder', sa.String(256)),
        sa.Column('renamed_by', sa.String(64), nullable=False),
        sa.Column('renamed_at', sa.DateTime(), nullable=False),
        sa.Column('rolled_back', sa.Boolean(), default=False),
        sa.Column('rollback_at', sa.DateTime()),
        sa.Column('rollback_by', sa.String(64)),
        sa.Column('rename_success', sa.Boolean(), default=True),
        sa.Column('error_message', sa.Text()),
        sa.Column('naming_style', sa.String(32)),
        sa.Column('zero_padded', sa.Boolean())
    )
    
    # Create indexes for efficient querying
    op.create_index('idx_batch_id', 'batch_rename_history', ['batch_id'])
    op.create_index('idx_job_id', 'batch_rename_history', ['job_id'])
    op.create_index('idx_renamed_at', 'batch_rename_history', ['renamed_at'])


def downgrade():
    """Remove batch_rename_history table."""
    op.drop_index('idx_renamed_at', 'batch_rename_history')
    op.drop_index('idx_job_id', 'batch_rename_history')
    op.drop_index('idx_batch_id', 'batch_rename_history')
    op.drop_table('batch_rename_history')
