"""Track matching system.

Public API::

    from arm.services.matching import match_job, MatchResult, TrackMatch

    result = match_job(job)
    if result.success:
        for m in result.matches:
            print(f"Track {m.track_number} → E{m.episode_number} {m.episode_name}")

To add a custom matcher::

    from arm.services.matching.base import MatchStrategy
    from arm.services.matching.registry import register

    class MyMatcher(MatchStrategy):
        ...

    register(MyMatcher())
"""

from arm.services.matching.base import MatchResult, MatchStrategy, TrackMatch  # noqa: F401
from arm.services.matching.registry import match_job, select_matcher, register  # noqa: F401

# ------------------------------------------------------------------
# Register built-in matchers (order = priority)
# ------------------------------------------------------------------
from arm.services.matching.tvdb_matcher import TvdbMatcher  # noqa: F401

register(TvdbMatcher())
