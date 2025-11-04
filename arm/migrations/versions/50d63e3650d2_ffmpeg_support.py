"""ffmpeg support

Revision ID: 50d63e3650d2
Revises: a79af75f4b31
Create Date: 2025-10-31 14:53:00.173047

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '50d63e3650d2'
down_revision = 'a79af75f4b31'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('config',
                sa.Column('FFMPEG_CLI', sa.String(length=256), nullable=True)
                  )
    op.add_column('config',
                sa.Column('FFMPEG_LOCAL', sa.String(length=256), nullable=True)
                  )
    op.add_column('config',
                sa.Column('USE_FFMPEG', sa.Boolean(), nullable=True)
                  )
    op.add_column('config',
                sa.Column('FFMPEG_PRE_FILE_ARGS', sa.String(length=512), nullable=True)
                  )
    op.add_column('config',
                sa.Column('FFMPEG_POST_FILE_ARGS', sa.String(length=512), nullable=True)
                  )


def downgrade():
    op.drop_column('config', 'FFMPEG_CLI')
    op.drop_column('config', 'FFMPEG_LOCAL')
    op.drop_column('config', 'USE_FFMPEG')
    op.drop_column('config', 'FFMPEG_PRE_FILE_ARGS')
    op.drop_column('config', 'FFMPEG_POST_FILE_ARGS')
