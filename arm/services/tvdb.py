"""TVDB v4 API client for TV episode matching.

Resolves TVDB series IDs from IMDb IDs, fetches season episodes with
runtimes, and matches disc tracks to real episodes by duration similarity.

Prefers DVD episode ordering when available, falling back to aired order.
All functions are async (use tvdb_sync.py for the ripper's sync context).
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

import arm.config.config as cfg

log = logging.getLogger(__name__)

_BASE = "https://api4.thetvdb.com/v4"
_TOKEN: str | None = None
_TOKEN_EXPIRES: float = 0
_TOKEN_TTL = 23 * 3600  # refresh after 23 hours (tokens last 30 days)


async def _ensure_token() -> str:
    """Obtain or reuse a TVDB bearer token."""
    global _TOKEN, _TOKEN_EXPIRES
    if _TOKEN and time.time() < _TOKEN_EXPIRES:
        return _TOKEN

    api_key = cfg.arm_config.get("TVDB_API_KEY", "")
    if not api_key:
        raise ValueError("TVDB_API_KEY not configured")

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(f"{_BASE}/login", json={"apikey": api_key})
        resp.raise_for_status()
        data = resp.json()
        _TOKEN = data["data"]["token"]
        _TOKEN_EXPIRES = time.time() + _TOKEN_TTL
        log.info("TVDB token acquired")
        return _TOKEN


async def _get(path: str, params: dict | None = None) -> dict:
    """Authenticated GET request to TVDB v4 API."""
    token = await _ensure_token()
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{_BASE}{path}",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        return resp.json()


async def resolve_tvdb_id(imdb_id: str) -> int | None:
    """Look up TVDB series ID from an IMDb ID.

    Returns the first matching series ID, or None if not found.
    """
    try:
        data = await _get(f"/search/remoteid/{imdb_id}")
        # Response is a list of result objects, each with optional series/movie/etc
        results = data.get("data", [])
        for result in results:
            # Each result may have a "series" key with the series info
            series = result.get("series")
            if series:
                tvdb_id = series.get("id")
                if tvdb_id:
                    return int(tvdb_id)
            # Fallback: check top-level id field
            if result.get("id"):
                return int(result["id"])
    except (httpx.HTTPError, KeyError, ValueError) as e:
        log.warning("TVDB series lookup failed for %s: %s", imdb_id, e)
    return None


async def get_season_episodes(
    tvdb_id: int, season: int
) -> list[dict[str, Any]]:
    """Fetch all episodes for a season, trying DVD order first.

    Returns list of dicts with keys: number, name, runtime (seconds).
    """
    for season_type in ("dvd", "default"):
        episodes = await _fetch_episodes(tvdb_id, season, season_type)
        if episodes:
            log.info(
                "TVDB: %d episodes for season %d (%s order)",
                len(episodes), season, season_type,
            )
            return episodes
    return []


async def _fetch_episodes(
    tvdb_id: int, season: int, season_type: str
) -> list[dict[str, Any]]:
    """Fetch episodes with pagination for a given season type."""
    all_episodes: list[dict[str, Any]] = []
    page = 0
    max_pages = 10  # safety cap

    while page < max_pages:
        try:
            data = await _get(
                f"/series/{tvdb_id}/episodes/{season_type}",
                {"season": str(season), "page": str(page)},
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                break  # season type not available
            raise

        raw_episodes = data.get("data", {}).get("episodes", [])
        if not raw_episodes:
            break

        for ep in raw_episodes:
            runtime_min = ep.get("runtime") or 0
            all_episodes.append({
                "number": ep.get("number", 0),
                "name": ep.get("name") or f"Episode {ep.get('number', '?')}",
                "runtime": int(runtime_min) * 60,  # convert minutes → seconds
                "aired": ep.get("aired", ""),
            })

        page += 1

    return all_episodes


async def get_all_season_episodes(
    tvdb_id: int, max_season: int = 10,
) -> dict[int, list[dict[str, Any]]]:
    """Fetch episodes for seasons 1..max_season.

    Stops early when a season returns no episodes.
    Returns dict keyed by season number.
    """
    result: dict[int, list[dict[str, Any]]] = {}
    for s in range(1, max_season + 1):
        eps = await get_season_episodes(tvdb_id, s)
        if not eps:
            break
        result[s] = eps
    return result


def match_tracks_best_season(
    tracks: list[dict],
    seasons_episodes: dict[int, list[dict[str, Any]]],
    tolerance: int = 300,
) -> dict[str, Any]:
    """Try each season independently, pick the best match.

    Scores: primary = match count (higher better),
    secondary = average runtime delta (lower better).
    Never mixes episodes across seasons.

    Returns::

        {
            "season": int,
            "matches": [...],
            "score": float,
            "match_count": int,
            "alternatives": [{"season": int, "score": float, "match_count": int}, ...],
        }
    """
    if not tracks or not seasons_episodes:
        return {"season": 0, "matches": [], "score": 0.0, "match_count": 0, "alternatives": []}

    scored: list[tuple[int, list[dict], float, int]] = []  # (season, matches, avg_delta, count)
    for season, episodes in sorted(seasons_episodes.items()):
        matches = match_tracks_to_episodes(tracks, episodes, tolerance)
        if not matches:
            scored.append((season, [], 0.0, 0))
            continue
        # Calculate average delta for matched tracks
        track_len_map = {str(t["track_number"]): t.get("length", 0) for t in tracks}
        ep_runtime_map = {ep["number"]: ep.get("runtime", 0) for ep in episodes}
        total_delta = 0
        for m in matches:
            t_len = track_len_map.get(m["track_number"], 0)
            e_run = ep_runtime_map.get(m["episode_number"], 0)
            total_delta += abs(t_len - e_run)
        avg_delta = total_delta / len(matches)
        scored.append((season, matches, avg_delta, len(matches)))

    if not scored:
        return {"season": 0, "matches": [], "score": 0.0, "match_count": 0, "alternatives": []}

    # Sort: most matches first, then lowest avg_delta
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


def match_tracks_to_episodes(
    tracks: list[dict], episodes: list[dict], tolerance: int = 300,
) -> list[dict]:
    """Match tracks to episodes by runtime similarity.

    Uses greedy nearest-neighbor: build all (track, episode) pairs ranked
    by runtime delta, assign smallest first, no reuse. Tracks outside
    tolerance get no match.

    Args:
        tracks: [{"track_number": "0", "length": 3407}, ...]
        episodes: [{"number": 1, "name": "Pilot", "runtime": 3300}, ...]
        tolerance: max seconds difference for a valid match

    Returns:
        [{"track_number": "0", "episode_number": 1, "episode_name": "Pilot"}, ...]
    """
    if not tracks or not episodes:
        return []

    # Build cost matrix: all (track_idx, episode_idx, delta) triples
    pairs = []
    for ti, track in enumerate(tracks):
        t_len = track.get("length") or 0
        if t_len < 120:  # skip very short tracks (menus, intros)
            continue
        for ei, ep in enumerate(episodes):
            delta = abs(t_len - ep.get("runtime", 0))
            if delta <= tolerance:
                pairs.append((delta, ti, ei))

    # Greedy assignment: smallest delta first, no reuse
    pairs.sort()
    used_tracks: set[int] = set()
    used_episodes: set[int] = set()
    matches = []

    for delta, ti, ei in pairs:
        if ti in used_tracks or ei in used_episodes:
            continue
        used_tracks.add(ti)
        used_episodes.add(ei)
        matches.append({
            "track_number": tracks[ti]["track_number"],
            "episode_number": episodes[ei]["number"],
            "episode_name": episodes[ei]["name"],
        })

    return matches
