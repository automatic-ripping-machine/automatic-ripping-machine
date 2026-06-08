"""Metadata services - async OMDb/TMDb/MusicBrainz/CRC64.

Ported from the UI's clean httpx implementations. ARM is the single source
of truth for all external metadata API calls. Reads keys from the in-memory
``cfg.arm_config`` dict (loaded at startup).
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
from typing import Any, Optional

import httpx

import arm.config.config as cfg
from arm.services.runtime_parsing import parse_runtime
from arm_contracts import MediaMetadata
from arm_contracts.enums import VideoType

log = logging.getLogger(__name__)

TMDB_POSTER_BASE = "https://image.tmdb.org/t/p/original"
MUSICBRAINZ_BASE = "https://musicbrainz.org/ws/2"
COVERART_BASE = "https://coverartarchive.org/release"
CRC_DB_URL = "https://1337server.pythonanywhere.com/api/v1/"
USER_AGENT = "ARM/1.0 (https://github.com/uprightbass360/automatic-ripping-machine-neu)"
_OMDB_URL = "https://www.omdbapi.com/"
_OMDB_KEY_ERROR = "OMDb API key is invalid or expired. Check OMDB_API_KEY in arm.yaml."
_TMDB_KEY_ERROR = "TMDb API key is invalid or expired. Check TMDB_API_KEY in arm.yaml."


class MetadataConfigError(Exception):
    """Raised when metadata provider is not configured or returns an auth error."""


def _get_keys() -> dict[str, str | None]:
    """Read provider and API keys from live ARM config."""
    provider = str(cfg.arm_config.get("METADATA_PROVIDER", "omdb")).lower()
    return {
        "provider": provider,
        "omdb_key": cfg.arm_config.get("OMDB_API_KEY"),
        "tmdb_key": cfg.arm_config.get("TMDB_API_KEY"),
    }


def has_api_key() -> bool:
    """Check whether ARM_API_KEY is configured."""
    return bool(cfg.arm_config.get("ARM_API_KEY"))


def _http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=15.0)


def _mb_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=15.0,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )


# ---------------------------------------------------------------------------
# Public API — Video metadata (OMDb / TMDb)
# ---------------------------------------------------------------------------


async def _test_tmdb_key(key: str) -> dict[str, str]:
    """Test a TMDb API key. Returns {success, message}."""
    async with _http_client() as client:
        resp = await client.get(
            "https://api.themoviedb.org/3/configuration",
            params={"api_key": key},
        )
    if resp.status_code in (401, 403):
        return {"success": False, "message": "Invalid TMDb API key"}
    if resp.status_code == 200:
        return {"success": True, "message": "TMDb API key is valid"}
    return {"success": False, "message": f"Unexpected response ({resp.status_code})"}


async def _test_omdb_key(key: str) -> dict[str, str]:
    """Test an OMDb API key. Returns {success, message}."""
    async with _http_client() as client:
        resp = await client.get(
            _OMDB_URL,
            params={"apikey": key, "t": "The Matrix", "r": "json"},
        )
    if resp.status_code in (401, 403):
        return {"success": False, "message": "Invalid OMDb API key"}
    try:
        data = resp.json()
    except ValueError:
        text = resp.text[:200] if resp.text else "(empty)"
        log.warning("OMDb returned non-JSON (%s): %s", resp.status_code, text)
        if resp.status_code == 200:
            return {"success": False, "message": "OMDb returned an invalid response"}
        return {"success": False, "message": f"OMDb returned HTTP {resp.status_code}"}
    if data.get("Response") == "True":
        return {"success": True, "message": "OMDb API key is valid"}
    error_msg = data.get("Error", "")
    if "Invalid API key" in error_msg:
        return {"success": False, "message": "Invalid OMDb API key"}
    if error_msg:
        return {"success": False, "message": f"OMDb: {error_msg}"}
    return {"success": True, "message": "OMDb API key accepted"}


async def test_configured_key(override_key: str | None = None, override_provider: str | None = None) -> dict[str, Any]:
    """Test a metadata / external-service API key.

    Supports four providers via the unified
    ``{success, message, provider, checked_at}`` shape:

    - ``omdb`` / ``tmdb`` - hits the upstream search API once
    - ``tvdb`` - delegates to ``arm.services.tvdb.validate_tvdb_key`` (login round-trip)
    - ``makemkv`` - runs ``prep_mkv()`` synchronously via the executor

    ``checked_at`` is ``None`` for the metadata providers (no caching);
    for ``makemkv`` it carries the AppState timestamp, mirroring the
    legacy ``/system/makemkv-key-check`` shape so the Settings panel can
    surface "last validated at" without an extra round-trip.
    """
    keys = _get_keys()
    provider = (override_provider or keys["provider"]).lower()

    if provider == "tvdb":
        return await _test_tvdb_provider(override_key)
    if provider == "makemkv":
        return await _test_makemkv_provider()

    # OMDB / TMDB path
    key = override_key or (keys["tmdb_key"] if provider == "tmdb" else keys["omdb_key"])
    if not key or not key.strip():
        return {
            "success": False,
            "message": f"No API key configured for {provider.upper()}",
            "provider": provider,
            "checked_at": None,
        }
    try:
        result = await (_test_tmdb_key(key.strip()) if provider == "tmdb" else _test_omdb_key(key.strip()))
        result["provider"] = provider
        result["checked_at"] = None
        return result
    except httpx.TimeoutException:
        return {"success": False, "message": "Request timed out - check network connectivity", "provider": provider, "checked_at": None}
    except httpx.ConnectError:
        return {"success": False, "message": "Cannot connect to API - check network/DNS", "provider": provider, "checked_at": None}
    except Exception as exc:
        log.warning("Metadata key test failed: %s", exc)
        return {"success": False, "message": f"Test failed: {type(exc).__name__}", "provider": provider, "checked_at": None}


async def _test_tvdb_provider(override_key: str | None) -> dict[str, Any]:
    """Validate TVDB key via login round-trip; reuses arm.services.tvdb."""
    from arm.services.tvdb import validate_tvdb_key
    key = override_key or cfg.arm_config.get("TVDB_API_KEY") or ""
    result = await validate_tvdb_key(key)
    result["provider"] = "tvdb"
    result["checked_at"] = None
    return result


async def _test_makemkv_provider() -> dict[str, Any]:
    """Run prep_mkv() in the default executor; mirrors /system/makemkv-key-check.

    Same translation table for UpdateKeyErrorCodes as the legacy
    /system/makemkv-key-check route, plus the AppState ``checked_at``
    timestamp so the consolidated endpoint can replace the old one.
    """
    import asyncio
    from arm.models.app_state import AppState
    from arm.ripper.makemkv import UpdateKeyErrorCodes, UpdateKeyRunTimeError, prep_mkv

    message = "MakeMKV key is valid"
    try:
        # prep_mkv() is sync + can fork; run via executor to avoid
        # blocking the event loop (per feedback_preflight_event_loop_blocking).
        await asyncio.get_running_loop().run_in_executor(None, prep_mkv)
    except UpdateKeyRunTimeError as exc:
        code = UpdateKeyErrorCodes(exc.returncode)
        messages = {
            UpdateKeyErrorCodes.URL_ERROR: (
                "Could not reach forum.makemkv.com - set MAKEMKV_PERMA_KEY "
                "in arm.yaml to use a purchased key"
            ),
            UpdateKeyErrorCodes.PARSE_ERROR: "MakeMKV settings file is corrupt",
            UpdateKeyErrorCodes.INTERNAL_ERROR: "Key update script produced invalid output",
            UpdateKeyErrorCodes.INVALID_MAKEMKV_SERIAL: (
                "Invalid MakeMKV serial key format - should match M-XXXX-..."
            ),
        }
        message = messages.get(code, f"Key update failed (error {code.name})")

    # AppState.makemkv_key_valid is the canonical truth - prep_mkv()
    # writes to it on success/failure regardless of whether it raised.
    state = AppState.get()
    return {
        "success": bool(state.makemkv_key_valid),
        "message": message,
        "provider": "makemkv",
        "checked_at": state.makemkv_key_checked_at.isoformat() if state.makemkv_key_checked_at else None,
    }


async def search(query: str, year: str | None = None, page: int = 1) -> list[dict[str, Any]]:
    """Search for titles. Returns normalized list of SearchResult dicts."""
    log.debug("Metadata search: query=%r year=%s page=%d", query, year, page)
    keys = _get_keys()
    if keys["provider"] == "tmdb" and keys["tmdb_key"]:
        return await _tmdb_search(query, year, keys["tmdb_key"])
    if keys["provider"] == "tmdb" and not keys["tmdb_key"]:
        if keys["omdb_key"]:
            log.warning("METADATA_PROVIDER is 'tmdb' but TMDB_API_KEY is empty; falling back to OMDb")
        else:
            raise MetadataConfigError(
                "METADATA_PROVIDER is 'tmdb' but TMDB_API_KEY is not set and no OMDB_API_KEY fallback."
            )
    if keys["omdb_key"]:
        return await _omdb_search(query, year, keys["omdb_key"], page=page)
    raise MetadataConfigError(
        f"No API key configured for metadata provider '{keys['provider']}'. "
        "Set OMDB_API_KEY or TMDB_API_KEY in arm.yaml."
    )


async def get_details(imdb_id: str) -> dict[str, Any] | None:
    """Fetch full details for a single title by IMDb ID."""
    log.debug("Metadata detail lookup: imdb_id=%s", imdb_id)
    keys = _get_keys()
    if keys["provider"] == "tmdb" and keys["tmdb_key"]:
        return await _tmdb_find(imdb_id, keys["tmdb_key"])
    if keys["provider"] == "tmdb" and not keys["tmdb_key"]:
        if keys["omdb_key"]:
            log.warning("METADATA_PROVIDER is 'tmdb' but TMDB_API_KEY is empty; falling back to OMDb")
        else:
            raise MetadataConfigError(
                "METADATA_PROVIDER is 'tmdb' but TMDB_API_KEY is not set and no OMDB_API_KEY fallback."
            )
    if keys["omdb_key"]:
        return await _omdb_details(imdb_id, keys["omdb_key"])
    raise MetadataConfigError(
        f"No API key configured for metadata provider '{keys['provider']}'. "
        "Set OMDB_API_KEY or TMDB_API_KEY in arm.yaml."
    )


# ---------------------------------------------------------------------------
# Public API — MusicBrainz
# ---------------------------------------------------------------------------


# Lucene special characters that must be escaped in user-provided search terms.
_LUCENE_SPECIAL = re.compile(r'([+\-&|!(){}\[\]^"~*?:\\/<>])')


def _escape_lucene(text: str) -> str:
    """Escape Lucene special characters in user input."""
    return _LUCENE_SPECIAL.sub(r"\\\1", text)


async def search_music(
    query: str,
    artist: str | None = None,
    release_type: str | None = None,
    format: str | None = None,
    country: str | None = None,
    status: str | None = None,
    tracks: int | None = None,
    offset: int = 0,
) -> dict[str, Any]:
    """Search MusicBrainz for releases matching query text and optional filters."""
    log.debug("MusicBrainz search: query=%r artist=%s", query, artist)
    safe_query = _escape_lucene(query)
    parts: list[str] = []
    if artist:
        safe_artist = _escape_lucene(artist)
        parts.append(f'release:"{safe_query}" AND artist:"{safe_artist}"')
    else:
        parts.append(safe_query)
    if release_type:
        parts.append(f"AND type:{release_type}")
    if format:
        parts.append(f'AND format:"{format}"')
    if country:
        parts.append(f"AND country:{country}")
    if status:
        parts.append(f"AND status:{status}")
    if tracks is not None:
        parts.append(f"AND tracks:{tracks}")
    lucene_query = " ".join(parts)

    params: dict[str, str] = {"query": lucene_query, "fmt": "json", "limit": "15"}
    if offset > 0:
        params["offset"] = str(offset)

    try:
        async with _mb_client() as client:
            resp = await client.get(f"{MUSICBRAINZ_BASE}/release", params=params)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.ConnectError, httpx.HTTPError) as exc:
        log.warning("MusicBrainz search failed: %s", exc)
        return {"results": [], "total": 0}

    total = data.get("count", 0)
    log.info("MusicBrainz search for %r returned %d total results", query, total)
    results: list[dict[str, Any]] = []
    for release in data.get("releases", []):
        mbid = release.get("id", "")
        artist_credit = release.get("artist-credit", [])
        artist_name = _build_artist_credit(artist_credit)
        date = release.get("date", "")
        year = date[:4] if date else ""
        track_count = release.get("track-count")
        media = release.get("media", [])
        label_info = release.get("label-info", [])
        release_group = release.get("release-group", {})

        results.append({
            "title": release.get("title", ""),
            "artist": artist_name,
            "year": year,
            "release_id": mbid,
            "media_type": "music",
            "poster_url": f"{COVERART_BASE}/{mbid}/front-250" if mbid else None,
            "track_count": track_count,
            "country": release.get("country"),
            "release_type": release_group.get("primary-type"),
            "format": _extract_format(media),
            "label": _extract_label(label_info),
        })
    return {"results": results, "total": total}


async def get_music_details(release_id: str) -> dict[str, Any] | None:
    """Fetch full release details from MusicBrainz by release MBID."""
    log.debug("MusicBrainz detail lookup: release_id=%s", release_id)
    params = {
        "inc": "artist-credits+recordings+release-groups+labels",
        "fmt": "json",
    }

    try:
        async with _mb_client() as client:
            resp = await client.get(
                f"{MUSICBRAINZ_BASE}/release/{release_id}", params=params
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            data = resp.json()
    except (httpx.ConnectError, httpx.HTTPError) as exc:
        log.warning("MusicBrainz detail fetch failed for %s: %s", release_id, exc)
        return None

    mbid = data.get("id", release_id)
    artist_credit = data.get("artist-credit", [])
    artist_name = _build_artist_credit(artist_credit)
    date = data.get("date", "")
    year = date[:4] if date else ""
    label_info = data.get("label-info", [])
    media = data.get("media", [])
    release_group = data.get("release-group", {})

    tracks_list: list[dict[str, Any]] = []
    track_count = 0
    for medium in media:
        disc_num = medium.get("position")
        for track in medium.get("tracks", []):
            recording = track.get("recording", {})
            length_ms = track.get("length") or recording.get("length")
            tracks_list.append({
                "number": track.get("number", ""),
                "title": recording.get("title", track.get("title", "")),
                "length_ms": length_ms,
                "disc_number": disc_num,
            })
        track_count += medium.get("track-count", 0)

    return {
        "title": data.get("title", ""),
        "artist": artist_name,
        "year": year,
        "release_id": mbid,
        "media_type": "music",
        "poster_url": f"{COVERART_BASE}/{mbid}/front-250",
        "track_count": track_count or len(tracks_list),
        "country": data.get("country"),
        "release_type": release_group.get("primary-type"),
        "format": _extract_format(media),
        "label": _extract_label(label_info),
        "catalog_number": _extract_catalog_number(label_info),
        "barcode": data.get("barcode") or None,
        "status": data.get("status"),
        "disc_count": len(media),
        "tracks": tracks_list,
    }


# ---------------------------------------------------------------------------
# Public API — CRC64 lookup
# ---------------------------------------------------------------------------


async def lookup_crc(crc64: str) -> dict[str, Any]:
    """Search the CRC64 database for a disc hash.

    Returns {"found": bool, "results": [...]} on success,
    or {"found": false, "results": [], "error": "..."} on failure.
    """
    log.debug("CRC64 lookup: %s", crc64)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(CRC_DB_URL, params={"mode": "s", "crc64": crc64})
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, httpx.ConnectError) as exc:
        log.warning("CRC database unreachable for %s: %s", crc64, exc)
        return {"found": False, "results": [], "error": "The community CRC database (1337server.pythonanywhere.com) appears to be offline. This is an external service not maintained by ARM."}

    if not data.get("success"):
        log.debug("CRC64 %s not found in database", crc64)
        return {"found": False, "results": []}

    raw = data.get("results", {})
    results = []
    for entry in raw.values():
        results.append({
            "title": entry.get("title", ""),
            "year": entry.get("year", ""),
            "imdb_id": entry.get("imdb_id", ""),
            "tmdb_id": entry.get("tmdb_id", ""),
            "video_type": entry.get("video_type", ""),
            "disctype": entry.get("disctype", ""),
            "label": entry.get("label", ""),
            "poster_url": "" if entry.get("poster_img") in (None, "None", "N/A") else entry.get("poster_img", ""),
            "hasnicetitle": entry.get("hasnicetitle", ""),
            "validated": entry.get("validated", ""),
            "date_added": entry.get("date_added", ""),
        })

    found = len(results) > 0
    if found:
        log.info("CRC64 %s matched %d result(s): %s", crc64, len(results), results[0].get("title", "?"))
    return {"found": found, "results": results}


# ---------------------------------------------------------------------------
# MusicBrainz helpers
# ---------------------------------------------------------------------------


def _build_artist_credit(credits: list[dict]) -> str:
    """Join all artist-credit entries with their joinphrases."""
    parts: list[str] = []
    for entry in credits:
        parts.append(entry.get("name", ""))
        jp = entry.get("joinphrase", "")
        if jp:
            parts.append(jp)
    return "".join(parts)


def _extract_label(label_info: list[dict]) -> str | None:
    if label_info and label_info[0].get("label"):
        return label_info[0]["label"].get("name")
    return None


def _extract_catalog_number(label_info: list[dict]) -> str | None:
    if label_info:
        return label_info[0].get("catalog-number")
    return None


def _extract_format(media: list[dict]) -> str | None:
    if media:
        return media[0].get("format")
    return None


# ---------------------------------------------------------------------------
# OMDb helpers
# ---------------------------------------------------------------------------


async def _omdb_search(query: str, year: str | None, api_key: str, page: int = 1) -> list[dict[str, Any]]:
    params: dict[str, str] = {"s": query, "r": "json", "apikey": api_key}
    if year:
        params["y"] = year
    if page > 1:
        params["page"] = str(page)
    async with _http_client() as client:
        resp = await client.get(_OMDB_URL, params=params)
        if resp.status_code in (401, 403):
            raise MetadataConfigError(_OMDB_KEY_ERROR)
        data = resp.json()

    results = []
    if data.get("Response") == "True" and "Search" in data:
        for item in data["Search"]:
            results.append(_omdb_to_legacy_dict(item))
        log.info("OMDb search for %r returned %d results", query, len(results))
        return results

    # Fallback: ?t= exact match for short/numeric titles
    log.debug("OMDb ?s= search for %r returned no results, trying ?t= exact match", query)
    params_t: dict[str, str] = {"t": query, "r": "json", "apikey": api_key}
    if year:
        params_t["y"] = year
    async with _http_client() as client:
        resp = await client.get(_OMDB_URL, params=params_t)
        if resp.status_code in (401, 403):
            raise MetadataConfigError(_OMDB_KEY_ERROR)
        data = resp.json()
    if data.get("Response") == "True":
        results.append(_omdb_to_legacy_dict(data))
    log.info("OMDb search for %r returned %d results (via ?t= fallback)", query, len(results))
    return results


# ---------------------------------------------------------------------------
# OMDb -> MediaMetadata adapter (single source of truth for OMDb shape)
# ---------------------------------------------------------------------------

_OMDB_NA = "N/A"


def _csv_to_list(value: Optional[str]) -> list[str]:
    """Parse a CSV-formatted string into a list of trimmed entries.

    Handles OMDb's 'N/A' sentinel and missing values.
    """
    if not value or value == _OMDB_NA:
        return []
    return [s.strip() for s in value.split(",") if s.strip()]


def _none_if_na(value: Optional[str]) -> Optional[str]:
    """Convert OMDb's 'N/A' sentinel to None."""
    if not value or value == _OMDB_NA:
        return None
    return value


def _parse_omdb_released(value: Optional[str]) -> Optional[date]:
    """OMDb 'Released' format is '23 Feb 2018' or 'N/A'."""
    cleaned = _none_if_na(value)
    if not cleaned:
        return None
    try:
        return datetime.strptime(cleaned, "%d %b %Y").date()
    except ValueError:
        return None


def _parse_omdb_rating(value: Optional[str]) -> Optional[float]:
    """OMDb 'imdbRating' is a numeric string or 'N/A'."""
    cleaned = _none_if_na(value)
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_omdb_year(value: Optional[str]) -> Optional[str]:
    """OMDb 'Year' is '2018' for movies, '2008-2013' or '2008-' for series.

    Returns the first 4-digit year, or None if unparseable.
    """
    cleaned = _none_if_na(value)
    if not cleaned:
        return None
    # Year ranges use '-' (hyphen) or '–' (en-dash)
    head = re.split(r"[-–]", cleaned, maxsplit=1)[0].strip()
    if len(head) == 4 and head.isdigit():
        return head
    return None


def _parse_omdb_type(value: Optional[str]) -> Optional[VideoType]:
    """OMDb 'Type' is 'movie', 'series', or 'episode'. Map to our enum."""
    cleaned = (value or "").lower()
    if cleaned == "series":
        return VideoType.series
    if cleaned == "movie":
        return VideoType.movie
    return None


def _normalize_omdb_to_metadata(omdb: dict) -> MediaMetadata:
    """Convert an OMDb response dict into a MediaMetadata instance.

    All provider quirks (CSV lists, '120 min' runtime, '23 Feb 2018'
    released, 'N/A' sentinels, year ranges) are normalized here. The
    pydantic validator then enforces the canonical types.
    """
    return MediaMetadata(
        title=_none_if_na(omdb.get("Title")),
        year=_parse_omdb_year(omdb.get("Year")),
        video_type=_parse_omdb_type(omdb.get("Type")),
        imdb_id=_none_if_na(omdb.get("imdbID")),
        poster_url=_none_if_na(omdb.get("Poster")),
        runtime_seconds=parse_runtime(omdb.get("Runtime")),
        plot=_none_if_na(omdb.get("Plot")),
        genres=_csv_to_list(omdb.get("Genre")),
        directors=_csv_to_list(omdb.get("Director")),
        writers=_csv_to_list(omdb.get("Writer")),
        actors=_csv_to_list(omdb.get("Actors")),
        mpaa_rating=_none_if_na(omdb.get("Rated")),
        released_date=_parse_omdb_released(omdb.get("Released")),
        language=(_csv_to_list(omdb.get("Language")) or [None])[0],
        country=_none_if_na(omdb.get("Country")),
        production_company=_none_if_na(omdb.get("Production")),
        imdb_rating=_parse_omdb_rating(omdb.get("imdbRating")),
    )


def _omdb_to_legacy_dict(omdb: dict, *, include_details: bool = False) -> dict[str, Any]:
    """Wire-shape projection of an OMDb response for the /api/v1/metadata HTTP API.

    The HTTP wire shape is `media_type` (movie/series), not `video_type`
    (enum), so we project from MediaMetadata back to the legacy field set
    that arm-ui currently consumes. When `include_details` is True, also
    emits `plot` + `background_url` (used by /metadata/{imdb_id}).
    """
    m = _normalize_omdb_to_metadata(omdb)
    media_type = (
        m.video_type.value if m.video_type is not None
        else "movie"
    )
    out: dict[str, Any] = {
        "title": m.title or "",
        "year": m.year or "",
        "imdb_id": m.imdb_id,
        "media_type": media_type,
        "poster_url": m.poster_url,
        "runtime_seconds": m.runtime_seconds,
    }
    if include_details:
        out["plot"] = m.plot
        out["background_url"] = None  # OMDb has no background images
    return out


async def _omdb_details(imdb_id: str, api_key: str) -> dict[str, Any] | None:
    params = {"i": imdb_id, "plot": "short", "r": "json", "apikey": api_key}
    async with _http_client() as client:
        resp = await client.get(_OMDB_URL, params=params)
        if resp.status_code in (401, 403):
            raise MetadataConfigError(_OMDB_KEY_ERROR)
        data = resp.json()
    if data.get("Response") != "True":
        log.debug("OMDb detail lookup for %s returned no result: %s", imdb_id, data.get("Error", "unknown"))
        return None
    return _omdb_to_legacy_dict(data, include_details=True)


# ---------------------------------------------------------------------------
# TMDb helpers
# ---------------------------------------------------------------------------


async def _tmdb_search(query: str, year: str | None, api_key: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    # Try movies first
    params: dict[str, str] = {"api_key": api_key, "query": query}
    if year:
        params["year"] = year
    async with _http_client() as client:
        resp = await client.get(
            "https://api.themoviedb.org/3/search/movie", params=params
        )
        if resp.status_code in (401, 403):
            raise MetadataConfigError(_TMDB_KEY_ERROR)
        data = resp.json()

    movie_count = data.get("total_results", 0)
    if movie_count > 0:
        for item in data["results"]:
            results.append(await _tmdb_search_item_to_legacy_dict(item, "movie", api_key))
        log.info("TMDb movie search for %r returned %d results", query, len(results))
        return results

    # Fallback to TV
    log.debug("TMDb movie search for %r returned 0 results, trying TV", query)
    params_tv: dict[str, str] = {"api_key": api_key, "query": query}
    if year:
        params_tv["first_air_date_year"] = year
    async with _http_client() as client:
        resp = await client.get(
            "https://api.themoviedb.org/3/search/tv", params=params_tv
        )
        if resp.status_code in (401, 403):
            raise MetadataConfigError(_TMDB_KEY_ERROR)
        data = resp.json()

    if data.get("total_results", 0) > 0:
        for item in data["results"]:
            results.append(await _tmdb_search_item_to_legacy_dict(item, "series", api_key))
    log.info("TMDb TV search for %r returned %d results", query, len(results))
    return results


async def _tmdb_search_item_to_legacy_dict(
    item: dict, media_type: str, api_key: str
) -> dict[str, Any]:
    """Wire-shape projection of a TMDb search result for /api/v1/metadata.

    TMDb search responses don't include imdb_id, so we fetch it via the
    external_ids endpoint. TV results use `name` / `first_air_date` where
    movies use `title` / `release_date`.
    """
    title = item.get("title") or item.get("name", "")
    release = item.get("release_date") or item.get("first_air_date") or ""
    imdb_id = await _tmdb_get_imdb(item["id"], media_type, api_key)
    return {
        "title": title or "",
        "year": _tmdb_year_from_date(release) or "",
        "imdb_id": imdb_id,
        "media_type": media_type,
        "poster_url": _tmdb_poster_url(item.get("poster_path")),
        "runtime_seconds": parse_runtime(item.get("runtime")),
    }


# ---------------------------------------------------------------------------
# TMDb -> MediaMetadata adapter (post-MediaMetadata-contract migration)
# ---------------------------------------------------------------------------


def _tmdb_poster_url(poster_path: Optional[str]) -> Optional[str]:
    if not poster_path:
        return None
    return f"{TMDB_POSTER_BASE}{poster_path}"


def _tmdb_year_from_date(release_date: Optional[str]) -> Optional[str]:
    if not release_date or len(release_date) < 4:
        return None
    head = release_date[:4]
    return head if head.isdigit() else None


def _tmdb_release_date(release_date: Optional[str]) -> Optional[date]:
    if not release_date:
        return None
    try:
        return datetime.strptime(release_date, "%Y-%m-%d").date()
    except ValueError:
        return None


def _tmdb_us_certification(release_dates: Optional[dict]) -> Optional[str]:
    """Find the US certification in TMDb's nested release_dates structure."""
    if not release_dates:
        return None
    for entry in release_dates.get("results", []) or []:
        if entry.get("iso_3166_1") == "US":
            for rd in entry.get("release_dates") or []:
                cert = rd.get("certification")
                if cert:
                    return cert
    return None


def _tmdb_extract_credits(credits: Optional[dict], role: str) -> list[str]:
    """Extract crew names matching a job (e.g. 'Director', 'Writer')."""
    if not credits:
        return []
    return [
        c.get("name", "")
        for c in (credits.get("crew") or [])
        if c.get("job") == role and c.get("name")
    ]


def _tmdb_extract_cast(credits: Optional[dict], top_n: int = 5) -> list[str]:
    if not credits:
        return []
    cast_sorted = sorted(
        credits.get("cast") or [],
        key=lambda c: c.get("order", 999),
    )
    return [c.get("name", "") for c in cast_sorted[:top_n] if c.get("name")]


def _normalize_tmdb_movie_to_metadata(tmdb: dict) -> MediaMetadata:
    """Convert a TMDb /movie/{id} response into MediaMetadata.

    Assumes the response was fetched with
    `?append_to_response=credits,release_dates` so credits + certification
    are inline.
    """
    runtime_min = tmdb.get("runtime")
    return MediaMetadata(
        title=tmdb.get("title") or None,
        year=_tmdb_year_from_date(tmdb.get("release_date")),
        video_type=VideoType.movie,
        imdb_id=tmdb.get("imdb_id") or None,
        poster_url=_tmdb_poster_url(tmdb.get("poster_path")),
        runtime_seconds=runtime_min * 60 if runtime_min else None,
        plot=tmdb.get("overview") or None,
        tagline=tmdb.get("tagline") or None,
        released_date=_tmdb_release_date(tmdb.get("release_date")),
        language=tmdb.get("original_language") or None,
        country=(tmdb.get("origin_country") or [None])[0],
        production_company=(
            tmdb.get("production_companies") or [{}]
        )[0].get("name") or None,
        imdb_rating=tmdb.get("vote_average"),
        genres=[g["name"] for g in tmdb.get("genres") or [] if g.get("name")],
        directors=_tmdb_extract_credits(tmdb.get("credits"), "Director"),
        writers=_tmdb_extract_credits(tmdb.get("credits"), "Writer"),
        actors=_tmdb_extract_cast(tmdb.get("credits"), top_n=5),
        mpaa_rating=_tmdb_us_certification(tmdb.get("release_dates")),
    )


# ---------------------------------------------------------------------------
# TVDB -> MediaMetadata adapter (post-MediaMetadata-contract migration)
# ---------------------------------------------------------------------------


def _tvdb_extract_network(network: Any) -> Optional[str]:
    """TVDB returns network as either {'name': ...} or a plain string."""
    if isinstance(network, dict):
        return network.get("name") or None
    if isinstance(network, str):
        return network or None
    return None


def _tvdb_extract_genres(genres: Any) -> list[str]:
    """TVDB returns genres as either [{'name': ...}, ...] or [str, ...]."""
    if not genres:
        return []
    out: list[str] = []
    for g in genres:
        if isinstance(g, dict):
            name = g.get("name")
            if name:
                out.append(name)
        elif isinstance(g, str) and g:
            out.append(g)
    return out


def _normalize_tvdb_to_metadata(
    tvdb: dict, *, video_type: VideoType
) -> MediaMetadata:
    """Convert a TVDB series/movie response into MediaMetadata.

    Caller passes the canonical `video_type` because TVDB uses separate
    endpoints (`/series/{id}` vs `/movies/{id}`) with the same payload
    shape.
    """
    return MediaMetadata(
        title=tvdb.get("name") or None,
        year=tvdb.get("year") or _tmdb_year_from_date(tvdb.get("firstAired")),
        video_type=video_type,
        poster_url=tvdb.get("image") or None,
        plot=tvdb.get("overview") or None,
        released_date=_tmdb_release_date(tvdb.get("firstAired")),
        language=tvdb.get("originalLanguage") or None,
        country=tvdb.get("country") or None,
        network=_tvdb_extract_network(tvdb.get("network")),
        genres=_tvdb_extract_genres(tvdb.get("genres")),
        imdb_rating=tvdb.get("score"),
    )


# ---------------------------------------------------------------------------
# MusicBrainz -> MediaMetadata adapter (post-MediaMetadata-contract migration)
# ---------------------------------------------------------------------------


def _mb_release_date(value: Optional[str]) -> Optional[date]:
    """MusicBrainz 'date' field may be 'YYYY', 'YYYY-MM', or 'YYYY-MM-DD'."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _normalize_musicbrainz_to_metadata(mb: dict) -> MediaMetadata:
    """Convert a MusicBrainz /release/{id} response into MediaMetadata.

    Sets video_type=VideoType.music, with album in `album`, artist in
    `artist` + `album_artist` (same field on a release), and the cover
    art URL composed from the release MBID.
    """
    mbid = mb.get("id") or ""
    raw_date = mb.get("date") or ""
    artist = _build_artist_credit(mb.get("artist-credit") or [])
    return MediaMetadata(
        video_type=VideoType.music,
        album=mb.get("title") or None,
        artist=artist or None,
        album_artist=artist or None,
        year=raw_date[:4] if raw_date and len(raw_date) >= 4 else None,
        released_date=_mb_release_date(raw_date),
        country=mb.get("country") or None,
        poster_url=f"{COVERART_BASE}/{mbid}/front-250" if mbid else None,
    )


async def _tmdb_get_imdb(
    tmdb_id: int, media_type: str, api_key: str
) -> str | None:
    """Get the IMDb ID for a TMDb entry."""
    try:
        async with _http_client() as client:
            if media_type == "series":
                resp = await client.get(
                    f"https://api.themoviedb.org/3/tv/{tmdb_id}/external_ids",
                    params={"api_key": api_key},
                )
                data = resp.json()
                if "status_code" not in data:
                    return data.get("imdb_id")
                log.debug("TMDb TV external_ids failed for %s, trying movie endpoint", tmdb_id)
                resp = await client.get(
                    f"https://api.themoviedb.org/3/movie/{tmdb_id}",
                    params={"api_key": api_key, "append_to_response": "external_ids"},
                )
                data = resp.json()
                if "status_code" not in data:
                    return data.get("external_ids", {}).get("imdb_id")
            else:
                resp = await client.get(
                    f"https://api.themoviedb.org/3/movie/{tmdb_id}",
                    params={"api_key": api_key, "append_to_response": "external_ids"},
                )
                data = resp.json()
                if "status_code" not in data:
                    return data.get("external_ids", {}).get("imdb_id")
                log.debug("TMDb movie endpoint failed for %s, trying TV external_ids", tmdb_id)
                resp = await client.get(
                    f"https://api.themoviedb.org/3/tv/{tmdb_id}/external_ids",
                    params={"api_key": api_key},
                )
                data = resp.json()
                if "status_code" not in data:
                    return data.get("imdb_id")
    except Exception as e:
        log.warning("Failed to resolve IMDb ID for TMDb %s %s: %s", media_type, tmdb_id, e)
    return None


async def _tmdb_find(imdb_id: str, api_key: str) -> dict[str, Any] | None:
    """Lookup full details by IMDb ID via TMDb /find endpoint."""
    async with _http_client() as client:
        resp = await client.get(
            f"https://api.themoviedb.org/3/find/{imdb_id}",
            params={"api_key": api_key, "external_source": "imdb_id"},
        )
        if resp.status_code in (401, 403):
            raise MetadataConfigError(_TMDB_KEY_ERROR)
        data = resp.json()

    item = None
    media_type = "movie"
    if data.get("movie_results"):
        item = data["movie_results"][0]
    elif data.get("tv_results"):
        item = data["tv_results"][0]
        media_type = "series"

    if not item:
        log.debug("TMDb /find returned no results for %s", imdb_id)
        return None

    title = item.get("title") or item.get("name", "")
    release = item.get("release_date") or item.get("first_air_date") or ""
    year = _tmdb_year_from_date(release) or ""
    backdrop_path = item.get("backdrop_path")

    log.info("TMDb detail for %s: %s (%s) [%s]", imdb_id, title, year, media_type)
    return {
        "title": title,
        "year": year,
        "imdb_id": imdb_id,
        "media_type": media_type,
        "poster_url": _tmdb_poster_url(item.get("poster_path")),
        "plot": item.get("overview") or None,
        "background_url": f"{TMDB_POSTER_BASE}{backdrop_path}" if backdrop_path else None,
    }
