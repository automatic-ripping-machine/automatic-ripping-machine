"""job: add disc_number and disc_total for multi-disc releases

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-03-11

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd3e4f5a6b7c8'
down_revision = 'c2d3e4f5a6b7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('job') as batch_op:
        batch_op.add_column(sa.Column('disc_number', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('disc_total', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('job') as batch_op:
        batch_op.drop_column('disc_total')
        batch_op.drop_column('disc_number')
