"""add notifications

Revision ID: f1054468c1c7
Revises: c54d68996895
Create Date: 2022-05-05 23:41:54.046714

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f1054468c1c7'
down_revision = 'c54d68996895'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('notifications',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('seen', sa.Boolean(), nullable=False),
                    sa.Column('trigger_time', sa.DateTime(), nullable=True),
                    sa.Column('dismiss_time', sa.DateTime(), nullable=True),
                    sa.Column('title', sa.String(length=256), nullable=True),
                    sa.Column('message', sa.String(length=256), nullable=True),
                    sa.PrimaryKeyConstraint('id')
                    )


def downgrade():
    op.drop_table('notifications')
