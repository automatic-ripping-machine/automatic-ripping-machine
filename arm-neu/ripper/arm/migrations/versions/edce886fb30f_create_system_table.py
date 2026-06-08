"""create system table

Revision ID: edce886fb30f
Revises: c54d68996895
Create Date: 2022-05-20 15:44:23.763174

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'edce886fb30f'
down_revision = 'c54d68996895'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'system_info',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('cpu', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Unicode(length=200), nullable=False),
        sa.Column('mem_total', sa.Float(), nullable=False)
        )
    op.create_table(
        'system_drives',
        sa.Column('drive_id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('mount', sa.String(length=100), nullable=False),
        sa.Column('open', sa.Boolean(), nullable=False),
        sa.Column('job_id_current', sa.Integer(), nullable=True),
        sa.Column('job_id_previous', sa.Integer(), nullable=True),
        sa.Column('description', sa.Unicode(length=200), nullable=False),
        sa.ForeignKeyConstraint(['job_id_current'], ['job.job_id'], ),
        sa.ForeignKeyConstraint(['job_id_previous'], ['job.job_id'], )
        )


def downgrade():
    op.drop_table('system_info')
    op.drop_table('system_drives')
