"""
Devtools service - testing metadata provider lookups from inside the ARM app
context.

Ported from the v2 metadata_service and adapted to v3's metadata modules
(arm/ui/jobs/metadata.py), which serve both OMDB and TMDB. The provider tested
is whichever METADATA_PROVIDER the app is configured for.
"""
from __future__ import annotations

from typing import Any


def _api_key_prefix(key_name: str) -> str | None:
    from config import config as cfg

    key = str(cfg.arm_config.get(key_name, "") or "")
    if not key:
        return None
    return key[:8] + "..." if len(key) > 8 else key


def test_metadata_lookup(imdb_id: str) -> dict[str, Any]:
    """
    Run the configured metadata provider against one IMDb id and report the
    raw result plus diagnostics. Read-only.

    Args:
        imdb_id: IMDb id to look up, e.g. "tt0088559"

    Returns:
        dict: provider, has_api_key, result summary and any error
    """
    from config import config as cfg
    from ui.jobs.metadata import call_omdb_api, tmdb_find

    provider = str(cfg.arm_config.get("METADATA_PROVIDER", "omdb")).lower()
    result: dict[str, Any] = {
        "imdb_id": imdb_id,
        "provider": provider,
    }
    try:
        if provider == "omdb":
            result["has_api_key"] = bool(cfg.arm_config.get("OMDB_API_KEY"))
            result["api_key_prefix"] = _api_key_prefix("OMDB_API_KEY")
            lookup = call_omdb_api(imdb_id=imdb_id)
        else:
            result["has_api_key"] = bool(cfg.arm_config.get("TMDB_API_KEY"))
            result["api_key_prefix"] = _api_key_prefix("TMDB_API_KEY")
            lookup = tmdb_find(imdb_id)
        result["lookup"] = lookup if isinstance(lookup, dict) else {"raw": str(lookup)[:500]}
        result["title"] = (lookup or {}).get("Title") if isinstance(lookup, dict) else None
        result["year"] = (lookup or {}).get("Year") if isinstance(lookup, dict) else None
    except Exception as error:  # noqa: BLE001 - network/API failures are the point of the test
        result["error"] = str(error)[:500]
    return result
