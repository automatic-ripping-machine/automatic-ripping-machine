"""Cross-disc state: find episodes already matched on sibling discs.

Queries the database for other jobs that share the same TVDB series ID
and season, with tracks that have assigned episode numbers.  These
episodes are excluded from matching on the current disc to prevent
duplicates.
"""

from __future__ import annotations

import logging

from arm.database import db

log = logging.getLogger(__name__)


def get_excluded_episodes(job, season: int | None = None) -> set[int]:
    """Return episode numbers already matched on sibling discs.

    Looks for other jobs with the same ``tvdb_id`` whose tracks have
    non-null ``episode_number`` values.  When *season* is provided,
    restricts to siblings in the same season (prevents excluding
    episodes from a different season that share the same numbering).

    Returns an empty set when there are no siblings or no matches.
    """
    tvdb_id = getattr(job, "tvdb_id", None)
    if not tvdb_id:
        return set()

    from arm.models.job import Job
    from arm.models.track import Track

    try:
        query = (
            db.session.query(Track.episode_number)
            .join(Job, Track.job_id == Job.job_id)
            .filter(
                Job.tvdb_id == tvdb_id,
                Job.job_id != job.job_id,
                Track.episode_number.isnot(None),
            )
        )
        # Filter by season when known — episode numbers restart each season
        if season is not None:
            query = query.filter(
                db.or_(
                    Job.season == str(season),
                    Job.season_auto == str(season),
                )
            )
        rows = query.all()
    except Exception as e:
        log.warning("Cross-disc lookup failed: %s", e)
        return set()

    excluded: set[int] = set()
    for (ep_num,) in rows:
        try:
            excluded.add(int(ep_num))
        except (ValueError, TypeError):
            continue

    if excluded:
        log.info(
            "Cross-disc: excluding episodes %s (matched on sibling discs)",
            sorted(excluded),
        )
    return excluded
