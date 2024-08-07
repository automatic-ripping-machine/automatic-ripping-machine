"""modify job fields

Revision ID: fa70591aea9e
Revises: b326a3663939
Create Date: 2024-08-07 22:23:00.645755

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'fa70591aea9e'
down_revision = 'b326a3663939'
branch_labels = None
depends_on = None


def upgrade():
    # Amend year fields to be longer than 4 characters long
    # SQLite allowed values larger than 4, byt MYSQL fails to migrate old data
    op.alter_column('job',
                    'year',
                    existing_type=sa.String(length=4),
                    type_=sa.String(length=256),
                    existing_nullable=True)
    op.alter_column('job',
                    'year_auto',
                    existing_type=sa.String(length=4),
                    type_=sa.String(length=256),
                    existing_nullable=True)
    op.alter_column('job',
                    'year_manual',
                    existing_type=sa.String(length=4),
                    type_=sa.String(length=256),
                    existing_nullable=True)
    # Amend pid_hash values from being an int to a big int
    # Example value of hash '-1678122735945707182' doesn't fit in MYSQL Integer
    op.alter_column('job',
                    'pid_hash',
                    existing_type=sa.Integer(),
                    type_=sa.BigInteger(),
                    existing_nullable=True)


def downgrade():
    op.alter_column('job',
                    'year',
                    existing_type=sa.String(length=256),
                    type_=sa.String(length=4),
                    existing_nullable=True)
    op.alter_column('job',
                    'year_auto',
                    existing_type=sa.String(length=256),
                    type_=sa.String(length=4),
                    existing_nullable=True)
    op.alter_column('job',
                    'year_manual',
                    existing_type=sa.String(length=256),
                    type_=sa.String(length=4),
                    existing_nullable=True)
    op.alter_column('job',
                    'pid_hash',
                    existing_type=sa.BigInteger(),
                    type_=sa.Integer(),
                    existing_nullable=True)
