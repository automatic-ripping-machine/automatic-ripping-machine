"""merge add_drive_id and batch_rename

Revision ID: d4e5f6g7h8i9
Revises: a79af75f4b31, c3d4e5f6g7h8
Create Date: 2025-10-19 21:39:54.087000

"""
# no imports required, for the merge of forked databases
# from alembic import op
# import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd4e5f6g7h8i9'
down_revision = ('a79af75f4b31', 'c3d4e5f6g7h8')
branch_labels = None
depends_on = None


def upgrade():
    pass
    # nothing to upgrade or downgrade, merge two forked database migrations into one


def downgrade():
    pass
    # nothing to upgrade or downgrade, merge two forked database migrations into one
