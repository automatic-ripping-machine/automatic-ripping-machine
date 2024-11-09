"""
System Drives
Add column drive_mode

Revision ID: 5bafd482b2c6
Revises: b326a3663939
Create Date: 2024-11-04 15:44:03.606200

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5bafd482b2c6'
down_revision = 'b326a3663939'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('system_drives',
                  sa.Column('drive_mode', sa.String(length=100), nullable=True)
                  )


def downgrade():
    op.drop_column('system_drives', 'drive_mode')
