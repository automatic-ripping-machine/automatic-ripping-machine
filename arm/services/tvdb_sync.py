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


def _resolve_tvdb_id(job, imdb_id):
    """Resolve and cache TVDB series ID on the job. Returns tvdb_id or None."""
    tvdb_id = getattr(job, 'tvdb_id', None)
    if tvdb_id:
        return tvdb_id
    tvdb_id = asyncio.run(tvdb.resolve_tvdb_id(imdb_id))
    if not tvdb_id:
        log.info("TVDB: no series found for %s", imdb_id)
        return None
    job.tvdb_id = tvdb_id
    db.session.commit()
    return tvdb_id


def _get_known_season(job):
    """Return season number from job metadata, or None if unknown."""
    for field in ('season', 'season_auto'):
        val = getattr(job, field, None)
        if val is not None:
            try:
                return int(val)
            except (ValueError, TypeError):
                pass
    return None


def _build_track_data(job):
    """Build list of dicts for the matching algorithm."""
    return [
        {"track_number": str(t.track_number), "length": t.length or 0}
        for t in job.tracks
    ]


def _apply_matches(job, matches, season):
    """Write match results to Track rows. Returns count of matched tracks."""
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
    return matched_count


def match_episodes_sync(job) -> bool:
    """Match job tracks to TVDB episodes and update the database.

    When season is known (from label parsing), uses single-season matching.
    When season is unknown, scans all seasons and picks the best match.

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
        max_season = int(cfg.arm_config.get("TVDB_MAX_SEASON_SCAN", 10))

        tvdb_id = _resolve_tvdb_id(job, imdb_id)
        if not tvdb_id:
            return False

        track_data = _build_track_data(job)
        season = _get_known_season(job)

        if season:
            # Known season — single-season matching (existing behavior)
            episodes = asyncio.run(tvdb.get_season_episodes(tvdb_id, season))
            if not episodes:
                log.info("TVDB: no episodes found for series %d season %d", tvdb_id, season)
                return False
            matches = tvdb.match_tracks_to_episodes(track_data, episodes, tolerance)
        else:
            # Unknown season — scan all seasons, pick best
            log.info("TVDB: no season from metadata, scanning seasons 1-%d", max_season)
            seasons_episodes = asyncio.run(
                tvdb.get_all_season_episodes(tvdb_id, max_season)
            )
            if not seasons_episodes:
                log.info("TVDB: no episodes found for series %d", tvdb_id)
                return False
            result = tvdb.match_tracks_best_season(track_data, seasons_episodes, tolerance)
            season = result["season"]
            matches = result["matches"]
            if season:
                log.info(
                    "TVDB: best season match = S%02d (%d tracks, avg delta %.0fs)",
                    season, result["match_count"], result["score"],
                )
                if result["alternatives"]:
                    for alt in result["alternatives"]:
                        log.debug(
                            "TVDB: alternative S%02d (%d tracks, avg delta %.0fs)",
                            alt["season"], alt["match_count"], alt["score"],
                        )
                # Store detected season back on job
                job.season_auto = str(season)

        if not matches:
            log.info("TVDB: no runtime matches within %ds tolerance", tolerance)
            return False

        matched_count = _apply_matches(job, matches, season)

        if matched_count:
            db.session.commit()
            log.info("TVDB: matched %d/%d tracks to episodes", matched_count, len(track_data))
            return True
        return False

    except Exception as e:
        log.warning("TVDB episode matching failed (non-fatal): %s", e)
        return False


def match_episodes_for_api(job, season=None, tolerance=None, apply=False):
    """API-facing TVDB match with detailed results.

    Args:
        job: Job ORM instance
        season: explicit season override (None = auto-detect)
        tolerance: match tolerance in seconds (None = use config default)
        apply: if True, write matches to DB

    Returns dict with match results, scores, and alternatives.
    """
    import arm.config.config as cfg

    imdb_id = job.imdb_id or job.imdb_id_auto
    if not imdb_id:
        return {"success": False, "error": "No IMDb ID on this job"}

    if tolerance is None:
        tolerance = int(cfg.arm_config.get("TVDB_MATCH_TOLERANCE", 300))
    max_season = int(cfg.arm_config.get("TVDB_MAX_SEASON_SCAN", 10))

    tvdb_id = _resolve_tvdb_id(job, imdb_id)
    if not tvdb_id:
        return {"success": False, "error": f"No TVDB series found for {imdb_id}"}

    track_data = _build_track_data(job)

    if season is not None:
        # Explicit season
        episodes = asyncio.run(tvdb.get_season_episodes(tvdb_id, season))
        if not episodes:
            return {"success": True, "season": season, "matches": [], "alternatives": []}
        matches = tvdb.match_tracks_to_episodes(track_data, episodes, tolerance)
        result = {
            "success": True,
            "season": season,
            "matches": matches,
            "match_count": len(matches),
            "score": 0.0,
            "alternatives": [],
        }
    else:
        # Auto-detect best season
        seasons_episodes = asyncio.run(
            tvdb.get_all_season_episodes(tvdb_id, max_season)
        )
        if not seasons_episodes:
            return {"success": True, "season": 0, "matches": [], "alternatives": []}
        best = tvdb.match_tracks_best_season(track_data, seasons_episodes, tolerance)
        season = best["season"]
        matches = best["matches"]
        result = {
            "success": True,
            "season": season,
            "matches": matches,
            "match_count": best["match_count"],
            "score": best["score"],
            "alternatives": best["alternatives"],
        }

    if apply and matches and season:
        _apply_matches(job, matches, season)
        job.season_auto = str(season)
        db.session.commit()
        result["applied"] = True

    return result
