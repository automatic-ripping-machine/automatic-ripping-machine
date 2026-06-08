"""merge add_notification and create_sys_table

Revision ID: 95623e8c5d58
Revises: edce886fb30f, f1054468c1c7
Create Date: 2022-06-24 13:43:51.603433

"""
# no imports required, for the merge of forked databases
# from alembic import op
# import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '95623e8c5d58'
down_revision = ('edce886fb30f', 'f1054468c1c7')
branch_labels = None
depends_on = None


def upgrade():
    pass
    # nothing to upgrade or downgrade, merge two forked database migrations into one


def downgrade():
    pass
    # nothing to upgrade or downgrade, merge two forked database migrations into one
