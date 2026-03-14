"""config: add MUSIC_MULTI_DISC_SUBFOLDERS and MUSIC_DISC_FOLDER_PATTERN

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-03-11

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f5a6b7c8d9e0'
down_revision = 'e4f5a6b7c8d9'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('config') as batch_op:
        batch_op.add_column(sa.Column('MUSIC_MULTI_DISC_SUBFOLDERS', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('MUSIC_DISC_FOLDER_PATTERN', sa.String(50), nullable=True))


def downgrade():
    with op.batch_alter_table('config') as batch_op:
        batch_op.drop_column('MUSIC_DISC_FOLDER_PATTERN')
        batch_op.drop_column('MUSIC_MULTI_DISC_SUBFOLDERS')
