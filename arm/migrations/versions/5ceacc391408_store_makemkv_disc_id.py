"""Store MakeMKV disc id

Revision ID: 5ceacc391408
Revises: 2986d3f7ecf9
Create Date: 2024-12-05 22:38:52.709850

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5ceacc391408'
down_revision = '2986d3f7ecf9'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('system_drives', sa.Column('mdisc', sa.SmallInteger()))


def downgrade():
    op.drop_column('system_drives', 'mdisc')
