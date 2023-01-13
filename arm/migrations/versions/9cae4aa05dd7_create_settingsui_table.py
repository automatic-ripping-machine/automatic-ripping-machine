"""create settingsui table

Revision ID: 9cae4aa05dd7
Revises: e688fe04d305
Create Date: 2021-03-11 23:55:12.428608

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '9cae4aa05dd7'
down_revision = 'e688fe04d305'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('job',
                  sa.Column('path', sa.String())
                  )
    setting_table = op.create_table('ui_settings',
                                    sa.Column('id', sa.Integer(), nullable=False),
                                    sa.Column('use_icons', sa.Integer(), nullable=False),
                                    sa.Column('save_remote_images', sa.Integer(), nullable=False),
                                    sa.Column('bootstrap_skin', sa.String(length=64), nullable=False),
                                    sa.Column('language', sa.String(length=4), nullable=False),
                                    sa.Column('index_refresh', sa.Integer(), nullable=False),
                                    sa.Column('database_limit', sa.Integer(), nullable=False),
                                    sa.PrimaryKeyConstraint('id')
                                    )
    op.bulk_insert(setting_table,
                   [{
                       'id': 1,
                       'use_icons': 1,
                       'save_remote_images': 1,
                       'bootstrap_skin': "spacelab",
                       'language': "en",
                       'index_refresh': 2000,
                       'database_limit': 200,

                   }])


def downgrade():
    op.drop_table('ui_settings')
    with op.batch_alter_table("job") as batch_op:
        batch_op.drop_column('path')
