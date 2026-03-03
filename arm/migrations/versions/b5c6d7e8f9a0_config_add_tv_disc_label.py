"""config: add USE_DISC_LABEL_FOR_TV and GROUP_TV_DISCS_UNDER_SERIES

Revision ID: b5c6d7e8f9a0
Revises: a4b5c6d7e8f9
Create Date: 2026-03-03

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b5c6d7e8f9a0'
down_revision = 'a4b5c6d7e8f9'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('config') as batch_op:
        batch_op.add_column(sa.Column('USE_DISC_LABEL_FOR_TV', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('GROUP_TV_DISCS_UNDER_SERIES', sa.Boolean(), nullable=True))


def downgrade():
    with op.batch_alter_table('config') as batch_op:
        batch_op.drop_column('GROUP_TV_DISCS_UNDER_SERIES')
        batch_op.drop_column('USE_DISC_LABEL_FOR_TV')
