"""API v1 — Metadata endpoints.

Provides OMDb/TMDb search & details, MusicBrainz search & details,
CRC64 lookup, and API key testing. ARM is the single source of truth
for all external metadata calls.
"""

import logging

from fastapi import APIRouter, HTTPException, Query

from arm.services.metadata import (
    MetadataConfigError,
    get_details,
    get_music_details,
    has_api_key,
    lookup_crc,
    search,
    search_music,
    test_configured_key,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/metadata", tags=["metadata"])


# --- Music routes MUST come before the {imdb_id} catch-all ---


@router.get("/music/search")
async def search_music_metadata(
    q: str = Query(..., min_length=1),
    artist: str | None = None,
    release_type: str | None = None,
    format: str | None = None,
    country: str | None = None,
    status: str | None = None,
    tracks: int | None = None,
    offset: int = Query(0, ge=0),
):
    """Search MusicBrainz for releases matching the query with optional filters."""
    log.debug("GET /metadata/music/search q=%r artist=%s", q, artist)
    return await search_music(
        q, artist, release_type=release_type, format=format,
        country=country, status=status, tracks=tracks, offset=offset,
    )


@router.get("/music/{release_id}")
async def get_music_detail(release_id: str):
    """Fetch full release details from MusicBrainz by release MBID."""
    log.debug("GET /metadata/music/%s", release_id)
    result = await get_music_details(release_id)
    if not result:
        log.debug("MusicBrainz release %s not found", release_id)
        raise HTTPException(status_code=404, detail="Release not found")
    return result


# --- Test key route before {imdb_id} catch-all ---


@router.get("/test-key")
async def test_metadata_key():
    """Test the currently configured metadata API key by making a real API call."""
    return await test_configured_key()


# --- CRC route before {imdb_id} catch-all ---


@router.get("/crc/{crc64}")
async def crc_lookup_endpoint(crc64: str):
    """Look up a CRC64 hash in the community database."""
    log.debug("GET /metadata/crc/%s", crc64)
    result = await lookup_crc(crc64)
    result["has_api_key"] = has_api_key()
    return result


# --- Search (no path param conflict) ---


@router.get("/search")
async def search_metadata(
    q: str = Query(..., min_length=1),
    year: str | None = None,
):
    """Search OMDb/TMDb for titles matching the query."""
    log.debug("GET /metadata/search q=%r year=%s", q, year)
    try:
        return await search(q, year)
    except MetadataConfigError as exc:
        log.warning("Metadata search failed (config): %s", exc)
        raise HTTPException(status_code=503, detail=str(exc))


# --- IMDb detail catch-all (LAST) ---


@router.get("/{imdb_id}")
async def get_media_detail(imdb_id: str):
    """Fetch full details for a title by IMDb ID."""
    log.debug("GET /metadata/%s", imdb_id)
    try:
        result = await get_details(imdb_id)
    except MetadataConfigError as exc:
        log.warning("Metadata detail failed (config): %s", exc)
        raise HTTPException(status_code=503, detail=str(exc))
    if not result:
        log.debug("No metadata found for %s", imdb_id)
        raise HTTPException(status_code=404, detail="Title not found")
    return result
