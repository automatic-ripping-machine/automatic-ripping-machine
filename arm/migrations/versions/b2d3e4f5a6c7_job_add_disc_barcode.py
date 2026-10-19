"""Add disc_barcode and disc_barcode_title columns to job table

Revision ID: b2d3e4f5a6c7
Revises: a1c2d3e4f5b6
Create Date: 2026-10-18

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b2d3e4f5a6c7'
down_revision = 'a1c2d3e4f5b6'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add the barcode scanner columns to the job table.

    disc_barcode       - UPC/EAN scanned from the disc case before the tray closed
    disc_barcode_title - product title that barcode looked up to, offered as a title search
    """
    with op.batch_alter_table('job', schema=None) as batch_op:
        batch_op.add_column(sa.Column('disc_barcode', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('disc_barcode_title', sa.String(length=256), nullable=True))


def downgrade():
    with op.batch_alter_table('job', schema=None) as batch_op:
        batch_op.drop_column('disc_barcode_title')
        batch_op.drop_column('disc_barcode')
