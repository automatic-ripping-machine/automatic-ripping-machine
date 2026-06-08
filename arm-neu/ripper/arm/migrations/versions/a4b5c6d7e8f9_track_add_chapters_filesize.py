"""track: add chapters and filesize columns

Revision ID: a4b5c6d7e8f9
Revises: f3a4b5c6d7e8
Create Date: 2026-03-03

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a4b5c6d7e8f9'
down_revision = 'f3a4b5c6d7e8'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('track') as batch_op:
        batch_op.add_column(sa.Column('chapters', sa.Integer(), server_default='0'))
        batch_op.add_column(sa.Column('filesize', sa.BigInteger(), server_default='0'))


def downgrade():
    with op.batch_alter_table('track') as batch_op:
        batch_op.drop_column('filesize')
        batch_op.drop_column('chapters')
