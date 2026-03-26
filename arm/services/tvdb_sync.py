"""Synchronous entry points for track matching in the ripper process.

Delegates to the matching system (``arm.services.matching``) which selects
the appropriate strategy.  All exceptions are caught — matching failures
never block ripping.

The ``match_episodes_for_api`` function is kept for the REST API layer,
providing detailed results with optional DB writes.
"""

from __future__ import annotations

import logging

from arm.database import db

log = logging.getLogger(__name__)


def _apply_matches(job, result) -> int:
    """Write match results to Track rows.  Returns count of matched tracks."""
    track_map = {str(t.track_number): t for t in job.tracks}
    matched_count = 0
    for m in result.matches:
        track = track_map.get(m.track_number)
        if track:
            track.title = m.episode_name
            track.episode_number = str(m.episode_number)
            track.episode_name = m.episode_name
            matched_count += 1
            log.info(
                "Match: track %s → S%02dE%02d %s",
                m.track_number, result.season, m.episode_number, m.episode_name,
            )
    return matched_count


def match_episodes_sync(job) -> bool:
    """Match job tracks to episodes and update the database.

    Selects the appropriate matcher via the registry, runs it, and
    persists results.  Returns True if any tracks were matched.
    """
    try:
        from arm.services.matching import match_job

        result = match_job(job)

        if not result.success:
            if result.error:
                log.info("Matching: %s", result.error)
            return False

        # Persist tvdb_id if the matcher resolved one
        if result.tvdb_id and not getattr(job, "tvdb_id", None):
            job.tvdb_id = result.tvdb_id

        # Store detected season if the matcher found one
        if result.season is not None and not getattr(job, "season", None):
            job.season_auto = str(result.season)

        matched_count = _apply_matches(job, result)

        if matched_count:
            db.session.commit()
            log.info(
                "%s matcher: %d/%d tracks matched",
                result.matcher, matched_count, len(list(job.tracks)),
            )
            return True
        return False

    except Exception as e:
        log.warning("Episode matching failed (non-fatal): %s", e)
        return False


def match_episodes_for_api(job, season=None, tolerance=None, apply=False):
    """API-facing match with detailed results.

    Args:
        job: Job ORM instance
        season: explicit season override (None = auto-detect)
        tolerance: match tolerance in seconds (None = use config default)
        apply: if True, write matches to DB

    Returns dict with match results, scores, and alternatives.
    """
    from arm.services.matching import match_job

    kwargs = {}
    if season is not None:
        kwargs["season"] = season
    if tolerance is not None:
        kwargs["tolerance"] = tolerance

    result = match_job(job, **kwargs)

    out = {
        "success": result.success,
        "matcher": result.matcher,
        "season": result.season,
        "matches": [
            {
                "track_number": m.track_number,
                "episode_number": m.episode_number,
                "episode_name": m.episode_name,
                "episode_runtime": m.episode_runtime,
            }
            for m in result.matches
        ],
        "match_count": result.match_count,
        "score": result.score,
        "alternatives": result.alternatives,
    }

    if result.error:
        out["error"] = result.error

    # Always persist tvdb_id so fetchTvdbEpisodes can load full season dropdown
    if result.tvdb_id and not getattr(job, "tvdb_id", None):
        job.tvdb_id = result.tvdb_id
        db.session.commit()

    if apply and result.success:
        matched_count = _apply_matches(job, result)
        if result.season is not None:
            job.season_auto = str(result.season)
        if matched_count:
            db.session.commit()
        out["applied"] = True

    return out
