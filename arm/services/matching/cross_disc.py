"""Cross-disc state: find episodes already matched on sibling discs.

Queries the database for other jobs that share the same TVDB series ID
and have tracks with assigned episode numbers.  These episodes are
excluded from matching on the current disc to prevent duplicates.
"""

from __future__ import annotations

import logging

from arm.database import db

log = logging.getLogger(__name__)


def get_excluded_episodes(job) -> set[int]:
    """Return episode numbers already matched on sibling discs.

    Looks for other jobs with the same ``tvdb_id`` (and optionally the
    same season) whose tracks have non-null ``episode_number`` values.

    Returns an empty set when there are no siblings or no matches.
    """
    tvdb_id = getattr(job, "tvdb_id", None)
    if not tvdb_id:
        return set()

    from arm.models.job import Job
    from arm.models.track import Track

    try:
        rows = (
            db.session.query(Track.episode_number)
            .join(Job, Track.job_id == Job.job_id)
            .filter(
                Job.tvdb_id == tvdb_id,
                Job.job_id != job.job_id,
                Track.episode_number.isnot(None),
            )
            .all()
        )
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
