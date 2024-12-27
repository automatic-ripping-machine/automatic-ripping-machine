"""Extended Optical Drive Info

Revision ID: 2986d3f7ecf9
Revises: 6870a5546912
Create Date: 2024-11-27 10:15:32.678332

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2986d3f7ecf9'
down_revision = '6870a5546912'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('system_drives', 'type')  # can be generated
    op.drop_column('system_drives', 'open')  # cannot be treated as stateless
    # new static information
    op.add_column('system_drives', sa.Column('maker', sa.String(25)))
    op.add_column('system_drives', sa.Column('model', sa.String(50)))
    op.add_column('system_drives', sa.Column('serial', sa.String(25)))
    op.add_column('system_drives', sa.Column('connection', sa.String(5)))
    op.add_column('system_drives', sa.Column('read_cd', sa.Boolean))
    op.add_column('system_drives', sa.Column('read_dvd', sa.Boolean))
    op.add_column('system_drives', sa.Column('read_bd', sa.Boolean))
    # new dynamic information
    op.add_column('system_drives', sa.Column('firmware', sa.String(10)))
    op.add_column('system_drives', sa.Column('location', sa.String(255)))
    op.add_column('system_drives', sa.Column('stale', sa.Boolean))


def downgrade():
    op.add_column('system_drives', sa.Column('type', sa.String(20)))
    op.add_column('system_drives', sa.Column('open', sa.Column(sa.Boolean)))
    op.drop_column('system_drives', 'maker')
    op.drop_column('system_drives', 'model')
    op.drop_column('system_drives', 'serial')
    op.drop_column('system_drives', 'connection')
    op.drop_column('system_drives', 'read_cd')
    op.drop_column('system_drives', 'read_dvd')
    op.drop_column('system_drives', 'read_bd')
    op.drop_column('system_drives', 'firmware')
    op.drop_column('system_drives', 'location')
    op.drop_column('system_drives', 'stale')
