"""Add disc_photo and disc_photo_ocr columns to job table

Revision ID: a1c2d3e4f5b6
Revises: edf2272c0a9d
Create Date: 2026-10-18

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1c2d3e4f5b6'
down_revision = 'edf2272c0a9d'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add the disc camera columns to the job table.

    disc_photo     - filename of the webcam photo of the disc, inside DISC_PHOTO_PATH
    disc_photo_ocr - raw OCR text read from that photo, used as a fallback title search
    """
    with op.batch_alter_table('job', schema=None) as batch_op:
        batch_op.add_column(sa.Column('disc_photo', sa.String(length=256), nullable=True))
        batch_op.add_column(sa.Column('disc_photo_ocr', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('job', schema=None) as batch_op:
        batch_op.drop_column('disc_photo_ocr')
        batch_op.drop_column('disc_photo')
