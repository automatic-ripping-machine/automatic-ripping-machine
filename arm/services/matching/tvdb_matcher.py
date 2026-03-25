"""TVDB runtime-based track-to-episode matcher.

Matches disc tracks to real TV episodes by comparing track durations
against TVDB episode runtimes.  Supports:

- Single-season matching (when season is known from label/metadata)
- Multi-season auto-detection (scans seasons, picks best fit)
- Disc-number position bias (later discs prefer later episodes)
- Cross-disc exclusion (skips episodes already matched on sibling discs)
"""

from __future__ import annotations

import logging
from typing import Any

import arm.config.config as cfg
from arm.services.matching._async_compat import run_async as _run_async
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

        episodes = _run_async(tvdb.get_season_episodes(tvdb_id, season))
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
        seasons_episodes = _run_async(
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
    """Match tracks to episodes using disc-windowed positional assignment.

    Strategy:
    1. When disc info is available, compute an episode window for this disc
       and assign tracks positionally (track 0 → first episode in window).
    2. Runtime is used as validation, not as the primary signal.
    3. Falls back to greedy runtime matching when no disc info is given.

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

    # Identify main tracks (>= 2 min), sorted by track number
    main_tracks = sorted(
        [t for t in tracks if (t.get("length") or 0) >= 120],
        key=lambda t: int(t.get("track_number") or 0),
    )
    if not main_tracks:
        return []

    # Sort episodes by number for positional assignment
    episodes = sorted(episodes, key=lambda ep: ep["number"])

    use_disc_window = disc_number is not None and disc_number > 0
    if use_disc_window:
        return _match_windowed(main_tracks, episodes, tolerance, disc_number, disc_total)
    else:
        return _match_greedy(main_tracks, episodes, tolerance)


def _match_windowed(
    main_tracks: list[dict],
    episodes: list[dict],
    tolerance: int,
    disc_number: int,
    disc_total: int | None,
) -> list[dict]:
    """Windowed positional matching: disc position determines episode range.

    1. Compute a generous window (1.5x expected disc share) centered on
       this disc's expected position in the season.
    2. Pair tracks to windowed episodes positionally (T0→first, T1→second).
    3. Validate each pair with runtime tolerance; flag but keep mismatches.
    4. If the window produces fewer matches than greedy would, fall back.
    """
    n_tracks = len(main_tracks)
    n_episodes = len(episodes)
    disc_count = disc_total or disc_number

    # Expected share per disc and center position
    share = n_episodes / disc_count
    center = (disc_number - 0.5) * share

    # Window: 1.5x the expected share, clamped to episode bounds
    half_window = max(share * 0.75, n_tracks * 0.75)
    win_start = max(0, int(center - half_window))
    win_end = min(n_episodes, int(center + half_window + 1))

    # Ensure window is at least as wide as the number of tracks
    if win_end - win_start < n_tracks:
        # Expand symmetrically, clamped
        deficit = n_tracks - (win_end - win_start)
        win_start = max(0, win_start - (deficit + 1) // 2)
        win_end = min(n_episodes, win_end + (deficit + 1) // 2)

    windowed = episodes[win_start:win_end]

    log.info(
        "Disc %d/%d: episode window E%d-E%d (%d candidates for %d tracks)",
        disc_number, disc_count,
        windowed[0]["number"] if windowed else 0,
        windowed[-1]["number"] if windowed else 0,
        len(windowed), n_tracks,
    )

    # Positional assignment: pair tracks with windowed episodes by position
    # When more episodes than tracks, pick the best-fitting slice
    if len(windowed) > n_tracks:
        # Find the contiguous slice of n_tracks episodes with minimum
        # total runtime delta against the tracks.
        # Bias the offset toward where the disc center falls within the window
        # so that disc 4/4 prefers the END of its window, disc 1/4 the START.
        expected_offset = center - win_start - n_tracks / 2
        expected_offset = max(0, min(len(windowed) - n_tracks, expected_offset))

        best_offset = 0
        best_cost = float("inf")
        for offset in range(len(windowed) - n_tracks + 1):
            cost = sum(
                abs((main_tracks[i].get("length") or 0) - (windowed[offset + i].get("runtime") or 0))
                for i in range(n_tracks)
            )
            cost += abs(offset - expected_offset) * 30  # bias toward expected position
            if cost < best_cost:
                best_cost = cost
                best_offset = offset
        selected = windowed[best_offset:best_offset + n_tracks]
    elif len(windowed) < n_tracks:
        # Fewer episodes than tracks — match what we can positionally,
        # remaining tracks get no match
        selected = windowed
    else:
        selected = windowed

    # Build positional matches
    matches = []
    for i, ep in enumerate(selected):
        if i >= len(main_tracks):
            break
        track = main_tracks[i]
        delta = abs((track.get("length") or 0) - (ep.get("runtime") or 0))
        if delta <= tolerance:
            matches.append({
                "track_number": track["track_number"],
                "episode_number": ep["number"],
                "episode_name": ep["name"],
                "episode_runtime": ep.get("runtime", 0),
            })

    # Fallback: if windowed matching got fewer results than greedy would,
    # use greedy instead (handles edge cases where disc info is wrong)
    greedy = _match_greedy(main_tracks, episodes, tolerance)
    if len(greedy) > len(matches):
        log.info(
            "Windowed matching (%d) worse than greedy (%d), using greedy",
            len(matches), len(greedy),
        )
        return greedy

    return matches


def _match_greedy(
    main_tracks: list[dict],
    episodes: list[dict],
    tolerance: int,
) -> list[dict]:
    """Greedy runtime matching: no disc info, pure runtime similarity.

    Builds all (track, episode) pairs within tolerance, assigns by
    smallest delta first, then re-orders so track sequence matches
    episode sequence.
    """
    pairs = []
    for ti, track in enumerate(main_tracks):
        t_len = track.get("length") or 0
        for ei, ep in enumerate(episodes):
            delta = abs(t_len - ep.get("runtime", 0))
            if delta <= tolerance:
                pairs.append((delta, ti, ei))

    pairs.sort()
    used_tracks: set[int] = set()
    used_episodes: set[int] = set()
    matches = []

    for _delta, ti, ei in pairs:
        if ti in used_tracks or ei in used_episodes:
            continue
        used_tracks.add(ti)
        used_episodes.add(ei)
        matches.append({
            "track_number": main_tracks[ti]["track_number"],
            "episode_number": episodes[ei]["number"],
            "episode_name": episodes[ei]["name"],
            "episode_runtime": episodes[ei].get("runtime", 0),
        })

    # Re-order: track sequence → episode sequence
    if len(matches) > 1:
        sorted_tracks = sorted(matches, key=lambda m: int(m["track_number"]))
        sorted_eps = sorted(matches, key=lambda m: m["episode_number"])
        matches = [
            {
                "track_number": t["track_number"],
                "episode_number": e["episode_number"],
                "episode_name": e["episode_name"],
                "episode_runtime": e["episode_runtime"],
            }
            for t, e in zip(sorted_tracks, sorted_eps)
        ]

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
