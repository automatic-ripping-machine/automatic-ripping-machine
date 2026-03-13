"""TVDB ID resolution helper (shared by matcher and API)."""

from __future__ import annotations

import asyncio
import logging

from arm.database import db
from arm.services import tvdb

log = logging.getLogger(__name__)


def resolve_and_cache_tvdb_id(job, imdb_id: str) -> int | None:
    """Resolve and cache TVDB series ID on the job. Returns tvdb_id or None."""
    tvdb_id = getattr(job, "tvdb_id", None)
    if tvdb_id:
        return tvdb_id
    tvdb_id = asyncio.run(tvdb.resolve_tvdb_id(imdb_id))
    if not tvdb_id:
        log.info("TVDB: no series found for %s", imdb_id)
        return None
    job.tvdb_id = tvdb_id
    db.session.commit()
    return tvdb_id
