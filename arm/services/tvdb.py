"""TVDB v4 API client.

Resolves TVDB series IDs from IMDb IDs and fetches season episodes with
runtimes.  Prefers DVD episode ordering when available, falling back to
aired order.

All functions are async (use tvdb_sync.py for the ripper's sync context).

Note: matching algorithms have moved to arm.services.matching.tvdb_matcher.
The old names are re-exported here for backward compatibility.
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
        results = data.get("data", [])
        for result in results:
            series = result.get("series")
            if series:
                tvdb_id = series.get("id")
                if tvdb_id:
                    return int(tvdb_id)
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


# ------------------------------------------------------------------
# Backward compatibility: matching functions moved to
# arm.services.matching.tvdb_matcher but re-exported here so
# existing imports and tests continue to work.
# ------------------------------------------------------------------
from arm.services.matching.tvdb_matcher import (  # noqa: E402, F401
    match_tracks_to_episodes,
    match_tracks_best_season,
)
