"""TVDB ID resolution helper (shared by matcher and API)."""

from __future__ import annotations

import logging

from arm.services import tvdb
from arm.services.matching.tvdb_matcher import _run_async

log = logging.getLogger(__name__)


def resolve_tvdb_id(job, imdb_id: str) -> int | None:
    """Resolve TVDB series ID, using cached value if available.

    Checks ``job.tvdb_id`` first.  If not set, queries the TVDB API.
    Does NOT mutate the job or commit to the database — the caller
    is responsible for persisting ``tvdb_id`` if desired.

    Returns tvdb_id or None.
    """
    tvdb_id = getattr(job, "tvdb_id", None)
    if tvdb_id:
        return tvdb_id
    tvdb_id = _run_async(tvdb.resolve_tvdb_id(imdb_id))
    if not tvdb_id:
        log.info("TVDB: no series found for %s", imdb_id)
        return None
    return tvdb_id
