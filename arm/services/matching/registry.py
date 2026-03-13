"""Matcher registry: select and run the right strategy for a job.

Matchers are tried in priority order.  The first one whose
``can_handle(job)`` returns True is used.  Additional matchers can be
registered at import time or via ``register()``.
"""

from __future__ import annotations

import logging
from typing import Sequence

from arm.services.matching.base import MatchResult, MatchStrategy

log = logging.getLogger(__name__)

# Ordered list — first match wins.
_MATCHERS: list[MatchStrategy] = []


def register(matcher: MatchStrategy) -> None:
    """Add a matcher to the registry (appended at the end)."""
    _MATCHERS.append(matcher)
    log.debug("Registered matcher: %s", matcher.name)


def get_matchers() -> Sequence[MatchStrategy]:
    """Return all registered matchers (read-only view)."""
    return list(_MATCHERS)


def select_matcher(job) -> MatchStrategy | None:
    """Return the first matcher that can handle *job*, or None."""
    for matcher in _MATCHERS:
        if matcher.can_handle(job):
            log.debug("Selected matcher '%s' for job %s", matcher.name, getattr(job, "job_id", "?"))
            return matcher
    return None


def match_job(job, tracks: list[dict] | None = None, **kwargs) -> MatchResult:
    """Select a matcher and run it.

    Builds track data from job.tracks if *tracks* is not provided.
    Returns a MatchResult (possibly with error or zero matches).
    """
    matcher = select_matcher(job)
    if matcher is None:
        return MatchResult(
            matcher="none",
            error=f"No matcher available for job {getattr(job, 'job_id', '?')} "
                  f"(type={getattr(job, 'video_type', None)})",
        )

    if tracks is None:
        tracks = _build_track_data(job)

    log.info(
        "Running '%s' matcher on job %s (%d tracks)",
        matcher.name, getattr(job, "job_id", "?"), len(tracks),
    )

    try:
        return matcher.match(job, tracks, **kwargs)
    except Exception as e:
        log.warning("Matcher '%s' failed: %s", matcher.name, e)
        return MatchResult(matcher=matcher.name, error=str(e))


def _build_track_data(job) -> list[dict]:
    """Build list of dicts for matching algorithms from job.tracks."""
    return [
        {"track_number": str(t.track_number), "length": t.length or 0}
        for t in job.tracks
    ]
