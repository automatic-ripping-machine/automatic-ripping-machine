"""Extend source_type enum with iso

Revision ID: 335d2d235fe0
Revises: s4t5u6v7w8x9
Create Date: 2026-05-04

The contracts v2.1.0 release adds SourceType.iso for ISO file imports.
This migration extends the CHECK constraint on ``job.source_type`` so
existing rows are unaffected and new rows may carry the new value.

The column uses ``sa.Enum(..., native_enum=False)`` (see
r3s4t5u6v7w8_enum_columns.py), which on every backend is enforced via a
CHECK constraint rather than a native database ENUM type. We therefore
swap the constraint via ``batch_alter_table`` (which on SQLite triggers a
table rebuild and on PostgreSQL drops + re-adds the CHECK clause). A
``ALTER TYPE ... ADD VALUE`` would only be needed if the column had been
declared with ``native_enum=True``.

The downgrade is best-effort: if any rows hold ``source_type='iso'`` at
downgrade time the CHECK swap will fail, which is the desired loud
failure (the operator must decide whether to delete those rows or stay
on the new schema).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = '335d2d235fe0'
down_revision = 's4t5u6v7w8x9'
branch_labels = None
depends_on = None


# Allowed value sets - duplicated here so the migration is self-contained
# (matches the convention from r3s4t5u6v7w8_enum_columns.py and
# s4t5u6v7w8x9_jobstate_disambiguation.py).
NEW_SOURCE_TYPE_VALUES = ('disc', 'folder', 'iso')
OLD_SOURCE_TYPE_VALUES = ('disc', 'folder')


def upgrade() -> None:
    with op.batch_alter_table('job') as batch_op:
        batch_op.alter_column(
            'source_type',
            existing_type=sa.Enum(*OLD_SOURCE_TYPE_VALUES,
                                  name='job_source_type_enum'),
            type_=sa.Enum(*NEW_SOURCE_TYPE_VALUES,
                          name='job_source_type_enum',
                          native_enum=False, validate_strings=True),
            existing_nullable=False,
            existing_server_default='disc',
        )


def downgrade() -> None:
    with op.batch_alter_table('job') as batch_op:
        batch_op.alter_column(
            'source_type',
            existing_type=sa.Enum(*NEW_SOURCE_TYPE_VALUES,
                                  name='job_source_type_enum'),
            type_=sa.Enum(*OLD_SOURCE_TYPE_VALUES,
                          name='job_source_type_enum',
                          native_enum=False, validate_strings=True),
            existing_nullable=False,
            existing_server_default='disc',
        )
