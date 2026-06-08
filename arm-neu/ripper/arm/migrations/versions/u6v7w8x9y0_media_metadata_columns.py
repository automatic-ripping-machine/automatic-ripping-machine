"""Add media_metadata_auto/manual JSON columns; backfill from legacy
poster_url/artist/album triple-columns; drop the retired triples.

Revision ID: u6v7w8x9y0
Revises: 335d2d235fe0
Create Date: 2026-05-10
"""
import json

import sqlalchemy as sa
from alembic import op


revision = 'u6v7w8x9y0'
down_revision = '335d2d235fe0'
branch_labels = None
depends_on = None


def _build_metadata_json(row, source):
    """Build a MediaMetadata-shaped dict from legacy column values.

    `source` is "auto" or "manual" - selects the *_auto or *_manual
    columns respectively. Returns a JSON string or None if all fields
    were null/empty.
    """
    suffix = f"_{source}" if source != "auto" else "_auto"

    def col(base):
        return row._mapping.get(f"{base}{suffix}")

    payload = {}
    if col("poster_url"):
        payload["poster_url"] = col("poster_url")
    if col("artist"):
        payload["artist"] = col("artist")
    if col("album"):
        payload["album"] = col("album")
    if not payload:
        return None
    return json.dumps(payload)


def upgrade():
    # 1. Add new columns
    op.add_column('job', sa.Column('media_metadata_auto', sa.Text(), nullable=True))
    op.add_column('job', sa.Column('media_metadata_manual', sa.Text(), nullable=True))

    # 2. Backfill from legacy triples
    bind = op.get_bind()
    rows = bind.execute(sa.text(
        "SELECT job_id, "
        "poster_url_auto, poster_url_manual, "
        "artist_auto, artist_manual, "
        "album_auto, album_manual "
        "FROM job"
    )).fetchall()

    for row in rows:
        auto_json = _build_metadata_json(row, "auto")
        manual_json = _build_metadata_json(row, "manual")
        if auto_json or manual_json:
            bind.execute(
                sa.text(
                    "UPDATE job SET "
                    "media_metadata_auto = :auto, "
                    "media_metadata_manual = :manual "
                    "WHERE job_id = :job_id"
                ),
                {"auto": auto_json, "manual": manual_json, "job_id": row._mapping["job_id"]},
            )

    # 3. Drop the legacy triple-columns. Use batch_alter_table for SQLite
    # which can't drop columns directly.
    with op.batch_alter_table('job', schema=None) as batch_op:
        batch_op.drop_column('poster_url')
        batch_op.drop_column('poster_url_auto')
        batch_op.drop_column('poster_url_manual')
        batch_op.drop_column('artist')
        batch_op.drop_column('artist_auto')
        batch_op.drop_column('artist_manual')
        batch_op.drop_column('album')
        batch_op.drop_column('album_auto')
        batch_op.drop_column('album_manual')


def downgrade():
    # Restore legacy triple-columns; data loss for any field not in those
    # triples (e.g. genres, directors) - downgrade is best-effort.
    with op.batch_alter_table('job', schema=None) as batch_op:
        batch_op.add_column(sa.Column('poster_url', sa.String(256), nullable=True))
        batch_op.add_column(sa.Column('poster_url_auto', sa.String(256), nullable=True))
        batch_op.add_column(sa.Column('poster_url_manual', sa.String(256), nullable=True))
        batch_op.add_column(sa.Column('artist', sa.String(256), nullable=True))
        batch_op.add_column(sa.Column('artist_auto', sa.String(256), nullable=True))
        batch_op.add_column(sa.Column('artist_manual', sa.String(256), nullable=True))
        batch_op.add_column(sa.Column('album', sa.String(256), nullable=True))
        batch_op.add_column(sa.Column('album_auto', sa.String(256), nullable=True))
        batch_op.add_column(sa.Column('album_manual', sa.String(256), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(sa.text(
        "SELECT job_id, media_metadata_auto, media_metadata_manual FROM job"
    )).fetchall()

    for row in rows:
        for source_col, target_suffix in (
            ("media_metadata_auto", "_auto"),
            ("media_metadata_manual", "_manual"),
        ):
            blob = row._mapping[source_col]
            if not blob:
                continue
            try:
                payload = json.loads(blob)
            except (ValueError, TypeError):
                continue
            updates = {}
            for legacy_field in ("poster_url", "artist", "album"):
                if legacy_field in payload and payload[legacy_field]:
                    updates[f"{legacy_field}{target_suffix}"] = payload[legacy_field]
            if updates:
                set_clause = ", ".join(f"{k} = :{k}" for k in updates)
                params = {**updates, "job_id": row._mapping["job_id"]}
                bind.execute(
                    sa.text(f"UPDATE job SET {set_clause} WHERE job_id = :job_id"),
                    params,
                )

    with op.batch_alter_table('job', schema=None) as batch_op:
        batch_op.drop_column('media_metadata_manual')
        batch_op.drop_column('media_metadata_auto')
