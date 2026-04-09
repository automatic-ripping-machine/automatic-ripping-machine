"""Add chapters and filesize columns to track table

Revision ID: edf2272c0a9d
Revises: 200cf208e048
Create Date: 2026-02-08

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'edf2272c0a9d'
down_revision = '50d63e3650d2'
branch_labels = None
depends_on = None


def upgrade():
    # Add chapters column with default 0
    with op.batch_alter_table('track', schema=None) as batch_op:
        batch_op.add_column(sa.Column('chapters', sa.Integer(), nullable=True, default=0))
        batch_op.add_column(sa.Column('filesize', sa.BigInteger(), nullable=True, default=0))

    # Set default values for existing rows
    op.execute("UPDATE track SET chapters = 0 WHERE chapters IS NULL")
    op.execute("UPDATE track SET filesize = 0 WHERE filesize IS NULL")


def downgrade():
    with op.batch_alter_table('track', schema=None) as batch_op:
        batch_op.drop_column('filesize')
        batch_op.drop_column('chapters')
