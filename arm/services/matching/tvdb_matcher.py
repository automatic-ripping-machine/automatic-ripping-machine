"""TVDB runtime-based track-to-episode matcher.

Matches disc tracks to real TV episodes by comparing track durations
against TVDB episode runtimes.  Supports:

- Single-season matching (when season is known from label/metadata)
- Multi-season auto-detection (scans seasons, picks best fit)
- Disc-number position bias (later discs prefer later episodes)
- Cross-disc exclusion (skips episodes already matched on sibling discs)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import arm.config.config as cfg
from arm.services.matching.base import MatchResult, MatchStrategy, TrackMatch
from arm.services.matching.cross_disc import get_excluded_episodes

log = logging.getLogger(__name__)


class TvdbMatcher(MatchStrategy):
    """Match tracks to TVDB episodes by runtime similarity."""

    @property
    def name(self) -> str:
        return "tvdb"

    def can_handle(self, job) -> bool:
        """Requires: video_type is 'series', TVDB_API_KEY configured, IMDb ID present."""
        if getattr(job, "video_type", None) != "series":
            return False
        if not cfg.arm_config.get("TVDB_API_KEY"):
            return False
        imdb_id = getattr(job, "imdb_id", None) or getattr(job, "imdb_id_auto", None)
        return bool(imdb_id)

    def match(self, job, tracks: list[dict], **kwargs) -> MatchResult:
        """Run TVDB matching.

        Keyword args:
            season: explicit season override (None = auto-detect)
            tolerance: max runtime delta in seconds (default from config)
            exclude_episodes: set of episode numbers to skip (default: DB lookup)
        """
        from arm.services.matching._tvdb_resolve import resolve_tvdb_id

        tolerance = kwargs.get("tolerance")
        if tolerance is None:
            tolerance = int(cfg.arm_config.get("TVDB_MATCH_TOLERANCE", 300))
        max_season = int(cfg.arm_config.get("TVDB_MAX_SEASON_SCAN", 10))

        imdb_id = getattr(job, "imdb_id", None) or getattr(job, "imdb_id_auto", None)
        if not imdb_id:
            return MatchResult(matcher=self.name, error="No IMDb ID")

        tvdb_id = resolve_tvdb_id(job, imdb_id)
        if not tvdb_id:
            return MatchResult(matcher=self.name, error=f"No TVDB series for {imdb_id}")

        disc_number = getattr(job, "disc_number", None)
        disc_total = getattr(job, "disc_total", None)
        if disc_number:
            log.info("TVDB matcher: disc %d of %s", disc_number, disc_total or "?")

        season = kwargs.get("season")
        if season is None:
            season = _get_known_season(job)

        # Cross-disc exclusion: find episodes already matched on sibling discs
        exclude = kwargs.get("exclude_episodes")
        if exclude is None:
            exclude = get_excluded_episodes(job, season=season)

        if season is not None:
            return self._match_single_season(
                tvdb_id, tracks, season, tolerance,
                disc_number, disc_total, exclude,
            )
        else:
            return self._match_best_season(
                tvdb_id, tracks, tolerance, max_season,
                disc_number, disc_total, exclude,
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _match_single_season(
        self, tvdb_id, tracks, season, tolerance,
        disc_number, disc_total, exclude,
    ) -> MatchResult:
        from arm.services import tvdb

        episodes = asyncio.run(tvdb.get_season_episodes(tvdb_id, season))
        if not episodes:
            log.info("TVDB: no episodes for series %d season %d", tvdb_id, season)
            return MatchResult(matcher=self.name, season=season, tvdb_id=tvdb_id)

        raw = match_tracks_to_episodes(
            tracks, episodes, tolerance,
            disc_number=disc_number, disc_total=disc_total,
            exclude_episodes=exclude,
        )
        return MatchResult(
            matcher=self.name,
            season=season,
            matches=[TrackMatch(**m) for m in raw],
            match_count=len(raw),
            tvdb_id=tvdb_id,
        )

    def _match_best_season(
        self, tvdb_id, tracks, tolerance, max_season,
        disc_number, disc_total, exclude,
    ) -> MatchResult:
        from arm.services import tvdb

        log.info("TVDB: no season from metadata, scanning seasons 1-%d", max_season)
        seasons_episodes = asyncio.run(
            tvdb.get_all_season_episodes(tvdb_id, max_season)
        )
        if not seasons_episodes:
            log.info("TVDB: no episodes found for series %d", tvdb_id)
            return MatchResult(matcher=self.name, tvdb_id=tvdb_id)

        best = match_tracks_best_season(
            tracks, seasons_episodes, tolerance,
            disc_number=disc_number, disc_total=disc_total,
            exclude_episodes=exclude,
        )

        season = best["season"]
        if season:
            log.info(
                "TVDB: best season = S%02d (%d tracks, avg delta %.0fs)",
                season, best["match_count"], best["score"],
            )
            for alt in best.get("alternatives", []):
                log.debug(
                    "TVDB: alternative S%02d (%d tracks, avg delta %.0fs)",
                    alt["season"], alt["match_count"], alt["score"],
                )

        return MatchResult(
            matcher=self.name,
            season=season if season else None,
            matches=[TrackMatch(**m) for m in best["matches"]],
            match_count=best["match_count"],
            score=best["score"],
            alternatives=best.get("alternatives", []),
            tvdb_id=tvdb_id,
        )


# ======================================================================
# Pure matching functions (no DB or API dependencies — easy to test)
# ======================================================================


def match_tracks_to_episodes(
    tracks: list[dict],
    episodes: list[dict],
    tolerance: int = 300,
    disc_number: int | None = None,
    disc_total: int | None = None,
    exclude_episodes: set[int] | None = None,
) -> list[dict]:
    """Match tracks to episodes by runtime similarity.

    Uses greedy nearest-neighbor: build all (track, episode) pairs ranked
    by runtime delta, assign smallest first, no reuse.

    When disc_number is provided, adds a position bias so that later discs
    prefer later episodes (prevents all discs matching early episodes when
    runtimes are identical).

    When exclude_episodes is provided, those episode numbers are skipped
    entirely (used for cross-disc deduplication).

    Args:
        tracks: [{"track_number": "0", "length": 3407}, ...]
        episodes: [{"number": 1, "name": "Pilot", "runtime": 3300}, ...]
        tolerance: max seconds difference for a valid match
        disc_number: 1-based disc number (None = no position bias)
        disc_total: total discs in set (None = estimate from disc_number)
        exclude_episodes: episode numbers to skip (already matched elsewhere)

    Returns:
        [{"track_number": "0", "episode_number": 1, "episode_name": "Pilot"}, ...]
    """
    if not tracks or not episodes:
        return []

    # Filter out excluded episodes
    if exclude_episodes:
        episodes = [ep for ep in episodes if ep["number"] not in exclude_episodes]
        if not episodes:
            log.info("All episodes excluded by cross-disc filter")
            return []

    # Calculate expected episode position for this disc (for tiebreaking).
    # Computed after exclusion filtering so the bias is relative to the
    # remaining candidates, not the full season — this is intentional.
    use_position_bias = disc_number is not None and disc_number > 0
    if use_position_bias:
        disc_count = disc_total or disc_number
        expected_center = (disc_number - 0.5) / disc_count * len(episodes)
    else:
        expected_center = 0.0

    # Build cost matrix
    pairs = []
    for ti, track in enumerate(tracks):
        t_len = track.get("length") or 0
        if t_len < 120:  # skip very short tracks (menus, intros)
            continue
        for ei, ep in enumerate(episodes):
            delta = abs(t_len - ep.get("runtime", 0))
            if delta <= tolerance:
                pos_bias = abs(ei - expected_center) if use_position_bias else 0.0
                pairs.append((delta, pos_bias, ti, ei))

    # Greedy assignment: smallest delta first, position bias breaks ties
    pairs.sort()
    used_tracks: set[int] = set()
    used_episodes: set[int] = set()
    matches = []

    for delta, _pos_bias, ti, ei in pairs:
        if ti in used_tracks or ei in used_episodes:
            continue
        used_tracks.add(ti)
        used_episodes.add(ei)
        matches.append({
            "track_number": tracks[ti]["track_number"],
            "episode_number": episodes[ei]["number"],
            "episode_name": episodes[ei]["name"],
            "episode_runtime": episodes[ei].get("runtime", 0),
        })

    return matches


def match_tracks_best_season(
    tracks: list[dict],
    seasons_episodes: dict[int, list[dict[str, Any]]],
    tolerance: int = 300,
    disc_number: int | None = None,
    disc_total: int | None = None,
    exclude_episodes: set[int] | None = None,
) -> dict[str, Any]:
    """Try each season independently, pick the best match.

    Scores: primary = match count (higher better),
    secondary = average runtime delta (lower better).
    Never mixes episodes across seasons.
    """
    empty = {"season": 0, "matches": [], "score": 0.0, "match_count": 0, "alternatives": []}
    if not tracks or not seasons_episodes:
        return empty

    scored: list[tuple[int, list[dict], float, int]] = []
    for season, episodes in sorted(seasons_episodes.items()):
        matches = match_tracks_to_episodes(
            tracks, episodes, tolerance,
            disc_number=disc_number, disc_total=disc_total,
            exclude_episodes=exclude_episodes,
        )
        if not matches:
            scored.append((season, [], 0.0, 0))
            continue

        track_len_map = {str(t["track_number"]): t.get("length", 0) for t in tracks}
        ep_runtime_map = {ep["number"]: ep.get("runtime", 0) for ep in episodes}
        total_delta = sum(
            abs(track_len_map.get(m["track_number"], 0) - ep_runtime_map.get(m["episode_number"], 0))
            for m in matches
        )
        avg_delta = total_delta / len(matches)
        scored.append((season, matches, avg_delta, len(matches)))

    if not scored:
        return empty

    scored.sort(key=lambda x: (-x[3], x[2]))
    best_season, best_matches, best_delta, best_count = scored[0]

    alternatives = [
        {"season": s, "score": round(d, 1), "match_count": c}
        for s, _, d, c in scored[1:]
        if c > 0
    ]

    return {
        "season": best_season,
        "matches": best_matches,
        "score": round(best_delta, 1),
        "match_count": best_count,
        "alternatives": alternatives,
    }


# ======================================================================
# Helpers
# ======================================================================


def _get_known_season(job) -> int | None:
    """Return season number from job metadata, or None if unknown."""
    for field in ("season", "season_auto"):
        val = getattr(job, field, None)
        if val is not None:
            try:
                return int(val)
            except (ValueError, TypeError):
                pass
    return None
