"""Tests for metadata proxy endpoints in jobs.py and settings.py.

Covers all metadata endpoints: search, detail, music search, music detail,
CRC lookup, test-metadata — including error handling for HTTPStatusError,
ConnectError, and other network failures.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from tests.factories import make_job_dict


# ---------------------------------------------------------------------------
# Helper: create an HTTPStatusError with a given status code
# ---------------------------------------------------------------------------

def _make_status_error(status_code: int, text: str = "error", detail: str = "") -> httpx.HTTPStatusError:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.text = text
    resp.json.return_value = {"detail": detail} if detail else {}
    return httpx.HTTPStatusError("error", request=MagicMock(), response=resp)


# ---------------------------------------------------------------------------
# GET /api/metadata/search
# ---------------------------------------------------------------------------


class TestMetadataSearch:
    async def test_success(self, app_client):
        results = [{"title": "Matrix", "year": "1999", "imdb_id": "tt0133093",
                     "media_type": "movie", "poster_url": None}]
        with patch("backend.routers.jobs.arm_client.search_metadata",
                   new_callable=AsyncMock, return_value=results):
            resp = await app_client.get("/api/metadata/search?q=matrix")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_with_year(self, app_client):
        with patch("backend.routers.jobs.arm_client.search_metadata",
                   new_callable=AsyncMock, return_value=[]) as mock_fn:
            resp = await app_client.get("/api/metadata/search?q=matrix&year=1999")
        assert resp.status_code == 200
        mock_fn.assert_called_once_with("matrix", "1999", page=1)

    async def test_http_status_error_passthrough(self, app_client):
        with patch("backend.routers.jobs.arm_client.search_metadata",
                   new_callable=AsyncMock, side_effect=_make_status_error(503)):
            resp = await app_client.get("/api/metadata/search?q=matrix")
        assert resp.status_code == 503

    async def test_http_status_error_with_detail(self, app_client):
        with patch("backend.routers.jobs.arm_client.search_metadata",
                   new_callable=AsyncMock,
                   side_effect=_make_status_error(503, detail="Missing API key")):
            resp = await app_client.get("/api/metadata/search?q=matrix")
        assert resp.status_code == 503
        assert resp.json()["detail"] == "Missing API key"

    async def test_connect_error_returns_502(self, app_client):
        with patch("backend.routers.jobs.arm_client.search_metadata",
                   new_callable=AsyncMock, side_effect=httpx.ConnectError("offline")):
            resp = await app_client.get("/api/metadata/search?q=matrix")
        assert resp.status_code == 502

    async def test_runtime_error_returns_502(self, app_client):
        with patch("backend.routers.jobs.arm_client.search_metadata",
                   new_callable=AsyncMock, side_effect=RuntimeError("client closed")):
            resp = await app_client.get("/api/metadata/search?q=matrix")
        assert resp.status_code == 502


# ---------------------------------------------------------------------------
# GET /api/metadata/{imdb_id}
# ---------------------------------------------------------------------------


class TestMediaDetail:
    async def test_success(self, app_client):
        detail = {"title": "Matrix", "year": "1999", "imdb_id": "tt0133093",
                  "media_type": "movie", "poster_url": None, "plot": "...",
                  "background_url": None}
        with patch("backend.routers.jobs.arm_client.get_media_detail",
                   new_callable=AsyncMock, return_value=detail):
            resp = await app_client.get("/api/metadata/tt0133093")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Matrix"

    async def test_not_found(self, app_client):
        with patch("backend.routers.jobs.arm_client.get_media_detail",
                   new_callable=AsyncMock, return_value=None):
            resp = await app_client.get("/api/metadata/tt9999999")
        assert resp.status_code == 404

    async def test_http_status_error_passthrough(self, app_client):
        with patch("backend.routers.jobs.arm_client.get_media_detail",
                   new_callable=AsyncMock, side_effect=_make_status_error(503)):
            resp = await app_client.get("/api/metadata/tt0133093")
        assert resp.status_code == 503

    async def test_http_status_error_with_detail(self, app_client):
        with patch("backend.routers.jobs.arm_client.get_media_detail",
                   new_callable=AsyncMock,
                   side_effect=_make_status_error(503, detail="Upstream error")):
            resp = await app_client.get("/api/metadata/tt0133093")
        assert resp.status_code == 503
        assert resp.json()["detail"] == "Upstream error"

    async def test_connect_error_returns_502(self, app_client):
        with patch("backend.routers.jobs.arm_client.get_media_detail",
                   new_callable=AsyncMock, side_effect=httpx.ConnectError("offline")):
            resp = await app_client.get("/api/metadata/tt0133093")
        assert resp.status_code == 502


# ---------------------------------------------------------------------------
# GET /api/metadata/music/search
# ---------------------------------------------------------------------------


class TestMusicSearch:
    async def test_success(self, app_client):
        result = {
            "results": [{
                "title": "Master of Puppets",
                "artist": "Metallica",
                "year": "1986",
                "release_id": "abc-123",
            }],
            "total": 1,
        }
        with patch("backend.routers.jobs.arm_client.search_music_metadata",
                   new_callable=AsyncMock, return_value=result):
            resp = await app_client.get("/api/metadata/music/search?q=Metallica")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert resp.json()["results"][0]["artist"] == "Metallica"

    async def test_with_filters(self, app_client):
        result = {"results": [], "total": 0}
        with patch("backend.routers.jobs.arm_client.search_music_metadata",
                   new_callable=AsyncMock, return_value=result) as mock_fn:
            resp = await app_client.get(
                "/api/metadata/music/search?q=Metallica&artist=Metallica&format=CD"
            )
        assert resp.status_code == 200
        # Verify kwargs passed through
        call_kwargs = mock_fn.call_args[1]
        assert call_kwargs["artist"] == "Metallica"
        assert call_kwargs["format"] == "CD"

    async def test_http_status_error_passthrough(self, app_client):
        with patch("backend.routers.jobs.arm_client.search_music_metadata",
                   new_callable=AsyncMock, side_effect=_make_status_error(500)):
            resp = await app_client.get("/api/metadata/music/search?q=test")
        assert resp.status_code == 500

    async def test_connect_error_returns_502(self, app_client):
        with patch("backend.routers.jobs.arm_client.search_music_metadata",
                   new_callable=AsyncMock, side_effect=httpx.ConnectError("offline")):
            resp = await app_client.get("/api/metadata/music/search?q=test")
        assert resp.status_code == 502


# ---------------------------------------------------------------------------
# GET /api/metadata/music/{release_id}
# ---------------------------------------------------------------------------


class TestMusicDetail:
    async def test_success(self, app_client):
        detail = {"title": "Master of Puppets", "artist": "Metallica",
                  "year": "1986", "release_id": "mbid-123", "media_type": "music",
                  "poster_url": None, "track_count": 8, "country": "US",
                  "release_type": "Album", "format": "CD", "label": "Elektra",
                  "catalog_number": "123", "barcode": "456", "status": "Official",
                  "tracks": []}
        with patch("backend.routers.jobs.arm_client.get_music_detail",
                   new_callable=AsyncMock, return_value=detail):
            resp = await app_client.get("/api/metadata/music/mbid-123")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Master of Puppets"

    async def test_not_found(self, app_client):
        with patch("backend.routers.jobs.arm_client.get_music_detail",
                   new_callable=AsyncMock, return_value=None):
            resp = await app_client.get("/api/metadata/music/bad-mbid")
        assert resp.status_code == 404

    async def test_http_status_error_passthrough(self, app_client):
        with patch("backend.routers.jobs.arm_client.get_music_detail",
                   new_callable=AsyncMock, side_effect=_make_status_error(500)):
            resp = await app_client.get("/api/metadata/music/mbid-123")
        assert resp.status_code == 500

    async def test_connect_error_returns_502(self, app_client):
        with patch("backend.routers.jobs.arm_client.get_music_detail",
                   new_callable=AsyncMock, side_effect=httpx.ConnectError("offline")):
            resp = await app_client.get("/api/metadata/music/mbid-123")
        assert resp.status_code == 502


# ---------------------------------------------------------------------------
# GET /api/jobs/{job_id}/crc-lookup
# ---------------------------------------------------------------------------


def _detail(crc_id: str | None) -> dict:
    """Build a /jobs/{id}/detail-shaped response with the given crc_id."""
    return {
        "job": make_job_dict(job_id=1, crc_id=crc_id),
        "config": None, "tracks": [], "track_counts": {"total": 0, "ripped": 0},
    }


class TestCrcLookup:
    async def test_success(self, app_client):
        crc_result = {"found": True, "results": [{"title": "Matrix"}], "has_api_key": True}
        with patch("backend.routers.jobs.arm_client.get_job_detail",
                   new_callable=AsyncMock, return_value=_detail("abc123")), \
             patch("backend.routers.jobs.arm_client.lookup_crc",
                   new_callable=AsyncMock, return_value=crc_result):
            resp = await app_client.get("/api/jobs/1/crc-lookup")
        assert resp.status_code == 200
        assert resp.json()["found"] is True

    async def test_job_not_found(self, app_client):
        with patch("backend.routers.jobs.arm_client.get_job_detail",
                   new_callable=AsyncMock,
                   return_value={"success": False, "error": "Job not found"}):
            resp = await app_client.get("/api/jobs/999/crc-lookup")
        assert resp.status_code == 404

    async def test_arm_unreachable(self, app_client):
        with patch("backend.routers.jobs.arm_client.get_job_detail",
                   new_callable=AsyncMock, return_value=None):
            resp = await app_client.get("/api/jobs/1/crc-lookup")
        assert resp.status_code == 502

    async def test_no_crc(self, app_client):
        with patch("backend.routers.jobs.arm_client.get_job_detail",
                   new_callable=AsyncMock, return_value=_detail("")):
            resp = await app_client.get("/api/jobs/1/crc-lookup")
        assert resp.status_code == 200
        data = resp.json()
        assert data["no_crc"] is True
        assert data["found"] is False

    async def test_http_status_error_passthrough(self, app_client):
        with patch("backend.routers.jobs.arm_client.get_job_detail",
                   new_callable=AsyncMock, return_value=_detail("abc123")), \
             patch("backend.routers.jobs.arm_client.lookup_crc",
                   new_callable=AsyncMock, side_effect=_make_status_error(503)):
            resp = await app_client.get("/api/jobs/1/crc-lookup")
        assert resp.status_code == 503

    async def test_connect_error_returns_502(self, app_client):
        with patch("backend.routers.jobs.arm_client.get_job_detail",
                   new_callable=AsyncMock, return_value=_detail("abc123")), \
             patch("backend.routers.jobs.arm_client.lookup_crc",
                   new_callable=AsyncMock, side_effect=httpx.ConnectError("offline")):
            resp = await app_client.get("/api/jobs/1/crc-lookup")
        assert resp.status_code == 502


# ---------------------------------------------------------------------------
# GET /api/settings/test-metadata
# ---------------------------------------------------------------------------


class TestSettingsTestMetadata:
    async def test_success(self, app_client):
        result = {"success": True, "message": "OMDb key valid", "provider": "omdb"}
        with patch("backend.routers.settings.arm_client.test_metadata_key",
                   new_callable=AsyncMock, return_value=result):
            resp = await app_client.get("/api/settings/test-metadata")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_invalid_key(self, app_client):
        result = {"success": False, "message": "Invalid key", "provider": "omdb"}
        with patch("backend.routers.settings.arm_client.test_metadata_key",
                   new_callable=AsyncMock, return_value=result):
            resp = await app_client.get("/api/settings/test-metadata")
        assert resp.status_code == 200
        assert resp.json()["success"] is False

    async def test_http_status_error(self, app_client):
        with patch("backend.routers.settings.arm_client.test_metadata_key",
                   new_callable=AsyncMock, side_effect=_make_status_error(500)):
            resp = await app_client.get("/api/settings/test-metadata")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "failed" in data["message"].lower()

    async def test_http_status_error_with_detail(self, app_client):
        with patch("backend.routers.settings.arm_client.test_metadata_key",
                   new_callable=AsyncMock,
                   side_effect=_make_status_error(500, detail="Invalid OMDb key")):
            resp = await app_client.get("/api/settings/test-metadata")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert data["message"] == "Invalid OMDb key"

    async def test_connect_error(self, app_client):
        with patch("backend.routers.settings.arm_client.test_metadata_key",
                   new_callable=AsyncMock, side_effect=httpx.ConnectError("offline")):
            resp = await app_client.get("/api/settings/test-metadata")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "unreachable" in data["message"].lower()


# ---------------------------------------------------------------------------
# GET /api/jobs/{job_id}/metadata - MediaMetadata pass-through
# ---------------------------------------------------------------------------


class TestJobMediaMetadata:
    async def test_passthrough(self, app_client):
        """ARM returns a merged MediaMetadata dict; BFF passes it through."""
        fake_metadata = {
            "title": "Annihilation",
            "year": "2018",
            "directors": ["Alex Garland"],
            "genres": ["Sci-Fi"],
        }
        with patch("backend.routers.jobs.arm_client.get_job_metadata",
                   new_callable=AsyncMock, return_value=fake_metadata):
            resp = await app_client.get("/api/jobs/42/metadata")
        assert resp.status_code == 200
        assert resp.json()["directors"] == ["Alex Garland"]

    async def test_job_not_found(self, app_client):
        with patch("backend.routers.jobs.arm_client.get_job_metadata",
                   new_callable=AsyncMock,
                   return_value={"detail": "Job not found"}):
            resp = await app_client.get("/api/jobs/999/metadata")
        assert resp.status_code == 404

    async def test_arm_unreachable(self, app_client):
        with patch("backend.routers.jobs.arm_client.get_job_metadata",
                   new_callable=AsyncMock, return_value=None):
            resp = await app_client.get("/api/jobs/42/metadata")
        assert resp.status_code == 502


# ---------------------------------------------------------------------------
# GET /api/patterns/tokens - PATTERN_TOKENS vocabulary
# ---------------------------------------------------------------------------


class TestPatternTokens:
    async def test_returns_full_vocabulary(self, app_client):
        """Lists every PATTERN_TOKENS alias with field_name + description."""
        resp = await app_client.get("/api/patterns/tokens")
        assert resp.status_code == 200
        data = resp.json()
        # Spot-check a few aliases the contract guarantees.
        for alias in ("title", "year", "director", "genre", "video_type"):
            assert alias in data, f"missing token: {alias}"
            assert data[alias]["description"]
        assert data["director"]["field_name"] == "directors"
        assert data["genre"]["field_name"] == "genres"

    async def test_returns_17_tokens(self, app_client):
        """v3.2.0 ships exactly 17 tokens; this guards regressions."""
        resp = await app_client.get("/api/patterns/tokens")
        assert resp.status_code == 200
        assert len(resp.json()) == 17
