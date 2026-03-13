"""Synchronous TVDB wrapper for the ripper process.

Matches disc tracks to real TV episodes using the TVDB v4 API.
All exceptions are caught internally — TVDB failures never block ripping.
"""

from __future__ import annotations

import asyncio
import logging

import httpx

from arm.database import db
from arm.services import tvdb

log = logging.getLogger(__name__)


def match_episodes_sync(job) -> bool:
    """Match job tracks to TVDB episodes and update the database.

    1. Resolve TVDB series ID from job.imdb_id
    2. Determine season number
    3. Fetch episodes for that season
    4. Match tracks by runtime
    5. Update Track rows with episode metadata

    Returns True if any tracks were matched, False otherwise.
    All exceptions caught internally; returns False on any failure.
    """
    import arm.config.config as cfg

    try:
        imdb_id = job.imdb_id or job.imdb_id_auto
        if not imdb_id:
            log.debug("No IMDb ID — skipping TVDB matching")
            return False

        tolerance = int(cfg.arm_config.get("TVDB_MATCH_TOLERANCE", 300))

        # Resolve TVDB series ID (cached on job if already looked up)
        tvdb_id = getattr(job, 'tvdb_id', None)
        if not tvdb_id:
            tvdb_id = asyncio.run(tvdb.resolve_tvdb_id(imdb_id))
            if not tvdb_id:
                log.info("TVDB: no series found for %s", imdb_id)
                return False
            job.tvdb_id = tvdb_id
            db.session.commit()

        # Determine season: prefer job.season, fall back to disc_number, then 1
        season = None
        for field in ('season', 'season_auto', 'disc_number'):
            val = getattr(job, field, None)
            if val is not None:
                try:
                    season = int(val)
                    break
                except (ValueError, TypeError):
                    pass
        if not season:
            season = 1
            log.info("TVDB: no season number known, defaulting to season 1")

        # Fetch episodes
        episodes = asyncio.run(tvdb.get_season_episodes(tvdb_id, season))
        if not episodes:
            log.info("TVDB: no episodes found for series %d season %d", tvdb_id, season)
            return False

        # Build track list for matching
        track_data = [
            {"track_number": str(t.track_number), "length": t.length or 0}
            for t in job.tracks
        ]

        matches = tvdb.match_tracks_to_episodes(track_data, episodes, tolerance)
        if not matches:
            log.info("TVDB: no runtime matches within %ds tolerance", tolerance)
            return False

        # Apply matches to Track rows
        track_map = {str(t.track_number): t for t in job.tracks}
        matched_count = 0
        for m in matches:
            track = track_map.get(m["track_number"])
            if track:
                track.title = m["episode_name"]
                track.episode_number = str(m["episode_number"])
                track.episode_name = m["episode_name"]
                matched_count += 1
                log.info(
                    "TVDB: track %s → S%02dE%02d %s",
                    m["track_number"], season, m["episode_number"], m["episode_name"],
                )

        if matched_count:
            db.session.commit()
            log.info("TVDB: matched %d/%d tracks to episodes", matched_count, len(track_data))
            return True
        return False

    except Exception as e:
        log.warning("TVDB episode matching failed (non-fatal): %s", e)
        return False
