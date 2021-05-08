"""empty message

Revision ID: e688fe04d305
Revises: c3a3fa694636
Create Date: 2021-01-16 03:45:24.758050

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e688fe04d305'
down_revision = 'c3a3fa694636'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('user',
                    sa.Column('user_id', sa.Integer(), nullable=False),
                    sa.Column('email', sa.String(length=32), nullable=False),
                    sa.Column('password', sa.String(length=64), nullable=False),
                    sa.Column('hash', sa.String(length=256), nullable=False),
                    sa.PrimaryKeyConstraint('user_id')
                    )


def downgrade():
    op.drop_table('user')
