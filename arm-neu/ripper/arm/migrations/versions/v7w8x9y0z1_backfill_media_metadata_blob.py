"""Best-effort backfill of media_metadata_auto for pre-Phase-2 jobs.

The prior migration (u6v7w8x9y0) backfilled the blob from the legacy
poster_url_auto column. Jobs matched on the pre-Phase-2 code path often
had imdb_id_auto set without a poster_url_auto value, so the migration
correctly skipped them and they now have imdb_id but no blob.

This migration re-fetches metadata for those rows via the same adapter
the live matcher uses (metadata.get_details), so dashboard cards render
posters for already-completed jobs. Fail-soft: any row whose API call
errors is left as-is and the migration completes. The new code path
covers all future rips regardless.

Revision ID: v7w8x9y0z1
Revises: u6v7w8x9y0
Create Date: 2026-05-11
"""
import asyncio
import logging

import sqlalchemy as sa
from alembic import op


revision = 'v7w8x9y0z1'
down_revision = 'u6v7w8x9y0'
branch_labels = None
depends_on = None

log = logging.getLogger("alembic.runtime.migration")


def _normalize_video_type(value):
    """Map the legacy string to the contract enum, or None for anything else."""
    from arm_contracts.enums import VideoType
    if value == "movie":
        return VideoType.movie
    if value == "series":
        return VideoType.series
    return None


def _legacy_dict_to_blob(legacy):
    """Build a MediaMetadata JSON blob from the adapter's legacy-shape dict."""
    from arm_contracts import MediaMetadata
    payload = dict(legacy)
    payload["video_type"] = _normalize_video_type(payload.pop("video_type", None))
    allowed = set(MediaMetadata.model_fields.keys())
    filtered = {k: v for k, v in payload.items() if k in allowed and v not in (None, "", [])}
    return MediaMetadata(**filtered).model_dump_json()


def _candidates(bind):
    rows = bind.execute(sa.text(
        "SELECT job_id, imdb_id FROM job "
        "WHERE imdb_id IS NOT NULL AND imdb_id != '' "
        "AND (media_metadata_auto IS NULL OR media_metadata_auto = '')"
    )).fetchall()
    return [(r._mapping["job_id"], r._mapping["imdb_id"]) for r in rows]


def upgrade():
    # Import lazily so a missing-key environment (e.g. a fresh test DB
    # with no arm.yaml) still loads the migration module.
    from arm.services import metadata
    from arm.services.metadata import MetadataConfigError

    bind = op.get_bind()
    try:
        rows = _candidates(bind)
    except Exception as exc:
        log.warning("backfill-media-metadata: skip (candidate query failed): %s", exc)
        return

    if not rows:
        log.info("backfill-media-metadata: no jobs eligible")
        return

    log.info("backfill-media-metadata: %d job(s) eligible", len(rows))
    wrote = 0
    for job_id, imdb_id in rows:
        try:
            legacy = asyncio.run(metadata.get_details(imdb_id))
        except MetadataConfigError as exc:
            log.warning("backfill-media-metadata: stopping early - %s", exc)
            break
        except Exception as exc:
            log.debug("backfill-media-metadata: skip job %s (fetch error): %s", job_id, exc)
            continue

        if not legacy:
            continue

        try:
            blob = _legacy_dict_to_blob(legacy)
        except Exception as exc:
            log.debug("backfill-media-metadata: skip job %s (validate error): %s", job_id, exc)
            continue

        bind.execute(
            sa.text("UPDATE job SET media_metadata_auto = :blob WHERE job_id = :job_id"),
            {"blob": blob, "job_id": job_id},
        )
        wrote += 1
    log.info("backfill-media-metadata: wrote blob for %d/%d eligible jobs", wrote, len(rows))


def downgrade():
    # Best-effort backfill is idempotent and a downgrade has nothing to
    # actively undo - the upgrade only writes blob, never deletes.
    pass
