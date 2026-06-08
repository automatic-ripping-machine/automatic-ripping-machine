"""notifications update

Revision ID: 2e0dc31fcb2e
Revises: 95623e8c5d58
Create Date: 2023-03-22 21:30:40.264918

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2e0dc31fcb2e'
down_revision = '95623e8c5d58'
branch_labels = None
depends_on = None


def upgrade():
    """
    add column to ui_settings table, for the duration of the notification notify_refresh
    set the default value to 6500 ms (6.5 s)
    """
    op.add_column('ui_settings',
                  sa.Column('notify_refresh', sa.Integer(), server_default="6500")
                  )

    """
    add colums to the notifications table, set a cleared and cleared time value
    For cleared, add the column, set nullable false and set a default of 0 - false
    """
    op.add_column('notifications',
                  sa.Column('cleared', sa.Boolean(), nullable=False, server_default="0")
                  )
    op.add_column('notifications',
                  sa.Column('cleared_time', sa.DateTime(), nullable=True)
                  )


def downgrade():
    op.drop_column('ui_settings', 'notify_refresh')
    op.drop_column('notifications', 'cleared')
    op.drop_column('notifications', 'cleared_time')
