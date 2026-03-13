"""Base classes for the track matching system.

Every matcher implements MatchStrategy, producing a list of TrackMatch
results.  The registry selects which matcher(s) to run for a given job.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class TrackMatch:
    """A single track-to-episode assignment."""

    track_number: str
    episode_number: int
    episode_name: str


@dataclass
class MatchResult:
    """Complete result of a matching run."""

    matcher: str  # e.g. "tvdb", "sequential", "musicbrainz"
    season: int | None = None
    matches: list[TrackMatch] = field(default_factory=list)
    score: float = 0.0
    match_count: int = 0
    alternatives: list[dict[str, Any]] = field(default_factory=list)
    applied: bool = False
    error: str | None = None
    # Provider-specific IDs resolved during matching (for caching by caller)
    tvdb_id: int | None = None

    @property
    def success(self) -> bool:
        return self.error is None and self.match_count > 0


class MatchStrategy(ABC):
    """Abstract base for track-matching strategies.

    Subclasses implement ``can_handle`` (job eligibility) and ``match``
    (the actual algorithm).  The registry calls them in priority order.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier for this strategy (e.g. 'tvdb')."""

    @abstractmethod
    def can_handle(self, job) -> bool:
        """Return True if this strategy is applicable to *job*."""

    @abstractmethod
    def match(self, job, tracks: list[dict], **kwargs) -> MatchResult:
        """Run matching and return results.

        Args:
            job: ORM Job instance (read for metadata, NOT mutated).
            tracks: [{"track_number": "0", "length": 3407}, ...]
            **kwargs: Strategy-specific overrides (season, tolerance, …).

        Returns:
            MatchResult with matches (possibly empty) or an error.
        """
