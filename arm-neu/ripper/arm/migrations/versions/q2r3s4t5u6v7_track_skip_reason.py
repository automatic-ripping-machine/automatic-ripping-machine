"""track.skip_reason column

Revision ID: q2r3s4t5u6v7
Revises: p1q2r3s4t5u6
Create Date: 2026-05-01

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = 'q2r3s4t5u6v7'
down_revision = 'p1q2r3s4t5u6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('track') as batch:
        batch.add_column(sa.Column('skip_reason', sa.String(32), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('track') as batch:
        batch.drop_column('skip_reason')
