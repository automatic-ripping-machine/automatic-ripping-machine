"""Metadata services — async OMDb/TMDb/MusicBrainz/CRC64.

Ported from the UI's clean httpx implementations. ARM is the single source
of truth for all external metadata API calls. Reads keys from the in-memory
``cfg.arm_config`` dict (loaded at startup).
"""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

import arm.config.config as cfg

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


def _extract_year(raw: str) -> str:
    """Extract a 4-digit year from a date/range string."""
    m = re.search(r"\d{4}", str(raw))
    return m.group(0) if m else raw


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
    """Test a metadata API key. Uses overrides if given, else the saved config."""
    keys = _get_keys()
    provider = override_provider or keys["provider"]
    key = override_key or (keys["tmdb_key"] if provider == "tmdb" else keys["omdb_key"])
    if not key or not key.strip():
        return {"success": False, "message": f"No API key configured for {provider.upper()}", "provider": provider}
    try:
        result = await (_test_tmdb_key(key.strip()) if provider == "tmdb" else _test_omdb_key(key.strip()))
        result["provider"] = provider
        return result
    except httpx.TimeoutException:
        return {"success": False, "message": "Request timed out \u2014 check network connectivity", "provider": provider}
    except httpx.ConnectError:
        return {"success": False, "message": "Cannot connect to API \u2014 check network/DNS", "provider": provider}
    except Exception as exc:
        log.warning("Metadata key test failed: %s", exc)
        return {"success": False, "message": f"Test failed: {type(exc).__name__}", "provider": provider}


async def search(query: str, year: str | None = None) -> list[dict[str, Any]]:
    """Search for titles. Returns normalized list of SearchResult dicts."""
    log.debug("Metadata search: query=%r year=%s", query, year)
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
        return await _omdb_search(query, year, keys["omdb_key"])
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
        for track in medium.get("tracks", []):
            recording = track.get("recording", {})
            length_ms = track.get("length") or recording.get("length")
            tracks_list.append({
                "number": track.get("number", ""),
                "title": recording.get("title", track.get("title", "")),
                "length_ms": length_ms,
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
            "poster_url": entry.get("poster_img", ""),
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


async def _omdb_search(query: str, year: str | None, api_key: str) -> list[dict[str, Any]]:
    params: dict[str, str] = {"s": query, "r": "json", "apikey": api_key}
    if year:
        params["y"] = year
    async with _http_client() as client:
        resp = await client.get(_OMDB_URL, params=params)
        if resp.status_code in (401, 403):
            raise MetadataConfigError(_OMDB_KEY_ERROR)
        data = resp.json()

    results = []
    if data.get("Response") == "True" and "Search" in data:
        for item in data["Search"]:
            results.append(_normalize_omdb(item))
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
        results.append(_normalize_omdb(data))
    log.info("OMDb search for %r returned %d results (via ?t= fallback)", query, len(results))
    return results


def _normalize_omdb(item: dict) -> dict[str, Any]:
    media_type = (item.get("Type") or "movie").lower()
    if media_type != "series":
        media_type = "movie"
    poster = item.get("Poster")
    if poster == "N/A":
        poster = None
    year_raw = item.get("Year", "")
    return {
        "title": item.get("Title", ""),
        "year": _extract_year(year_raw) if year_raw else "",
        "imdb_id": item.get("imdbID"),
        "media_type": media_type,
        "poster_url": poster,
    }


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
    result = _normalize_omdb(data)
    plot = data.get("Plot")
    result["plot"] = plot if plot != "N/A" else None
    result["background_url"] = None  # OMDb has no background images
    return result


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
            results.append(await _normalize_tmdb(item, "movie", api_key))
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
            results.append(await _normalize_tmdb(item, "series", api_key))
    log.info("TMDb TV search for %r returned %d results", query, len(results))
    return results


async def _normalize_tmdb(
    item: dict, media_type: str, api_key: str
) -> dict[str, Any]:
    title = item.get("title") or item.get("name", "")
    release = item.get("release_date") or item.get("first_air_date") or ""
    year = _extract_year(release) if release else ""
    poster_path = item.get("poster_path")
    poster_url = f"{TMDB_POSTER_BASE}{poster_path}" if poster_path else None
    imdb_id = await _tmdb_get_imdb(item["id"], media_type, api_key)
    return {
        "title": title,
        "year": year,
        "imdb_id": imdb_id,
        "media_type": media_type,
        "poster_url": poster_url,
    }


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
    year = _extract_year(release) if release else ""
    poster_path = item.get("poster_path")
    backdrop_path = item.get("backdrop_path")

    log.info("TMDb detail for %s: %s (%s) [%s]", imdb_id, title, year, media_type)
    return {
        "title": title,
        "year": year,
        "imdb_id": imdb_id,
        "media_type": media_type,
        "poster_url": f"{TMDB_POSTER_BASE}{poster_path}" if poster_path else None,
        "plot": item.get("overview") or None,
        "background_url": f"{TMDB_POSTER_BASE}{backdrop_path}" if backdrop_path else None,
    }
