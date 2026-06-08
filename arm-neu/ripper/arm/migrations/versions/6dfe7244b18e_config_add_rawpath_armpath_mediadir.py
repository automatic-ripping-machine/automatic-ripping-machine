"""

Revision ID: 6dfe7244b18e
Revises: 9cae4aa05dd7
Create Date: 2021-03-19 19:22:53.502215

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '6dfe7244b18e'
down_revision = '9cae4aa05dd7'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("config", "RAWPATH", new_column_name="RAW_PATH")
    op.alter_column("config", "ARMPATH", new_column_name="TRANSCODE_PATH")
    op.alter_column("config", "MEDIA_DIR", new_column_name="COMPLETED_PATH")


def downgrade():
    op.alter_column("config", "RAW_PATH", new_column_name="RAWPATH")
    op.alter_column("config", "TRANSCODE_PATH", new_column_name="ARMPATH")
    op.alter_column("config", "COMPLETED_PATH", new_column_name="MEDIA_DIR")
