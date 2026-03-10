"""track: add enabled column (replaces main_feature heuristic)

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-03-10

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c2d3e4f5a6b7'
down_revision = 'b1c2d3e4f5a6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('track') as batch_op:
        batch_op.add_column(sa.Column('enabled', sa.Boolean(), nullable=True, server_default='1'))


def downgrade():
    with op.batch_alter_table('track') as batch_op:
        batch_op.drop_column('enabled')
