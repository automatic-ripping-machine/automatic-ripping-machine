"""Tests for arm/api/v1/metadata.py — FastAPI router endpoints.

Covers all 6 endpoints: /search, /{imdb_id}, /music/search,
/music/{release_id}, /crc/{crc64}, /test-key.
"""

import unittest.mock

import httpx
import pytest


@pytest.fixture
def client():
    """Create a test client for just the metadata router."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from arm.api.v1.metadata import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /api/v1/metadata/search
# ---------------------------------------------------------------------------


class TestSearchEndpoint:
    def test_success(self, client):
        results = [{"title": "Matrix", "year": "1999", "imdb_id": "tt0133093",
                     "media_type": "movie", "poster_url": None}]
        with unittest.mock.patch('arm.api.v1.metadata.search', return_value=results):
            resp = client.get("/api/v1/metadata/search?q=Matrix")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "Matrix"

    def test_with_year(self, client):
        with unittest.mock.patch('arm.api.v1.metadata.search', return_value=[]) as mock_fn:
            resp = client.get("/api/v1/metadata/search?q=Matrix&year=1999")
        assert resp.status_code == 200
        mock_fn.assert_called_once_with("Matrix", "1999")

    def test_missing_query(self, client):
        resp = client.get("/api/v1/metadata/search")
        assert resp.status_code == 422  # FastAPI validation error

    def test_config_error_returns_503(self, client):
        from arm.services.metadata import MetadataConfigError
        with unittest.mock.patch('arm.api.v1.metadata.search',
                                 side_effect=MetadataConfigError("no key")):
            resp = client.get("/api/v1/metadata/search?q=Matrix")
        assert resp.status_code == 503


# ---------------------------------------------------------------------------
# GET /api/v1/metadata/{imdb_id}
# ---------------------------------------------------------------------------


class TestDetailEndpoint:
    def test_success(self, client):
        detail = {"title": "Matrix", "year": "1999", "imdb_id": "tt0133093",
                  "media_type": "movie", "poster_url": None, "plot": "A hacker...",
                  "background_url": None}
        with unittest.mock.patch('arm.api.v1.metadata.get_details', return_value=detail):
            resp = client.get("/api/v1/metadata/tt0133093")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Matrix"

    def test_not_found(self, client):
        with unittest.mock.patch('arm.api.v1.metadata.get_details', return_value=None):
            resp = client.get("/api/v1/metadata/tt9999999")
        assert resp.status_code == 404

    def test_config_error_returns_503(self, client):
        from arm.services.metadata import MetadataConfigError
        with unittest.mock.patch('arm.api.v1.metadata.get_details',
                                 side_effect=MetadataConfigError("no key")):
            resp = client.get("/api/v1/metadata/tt0133093")
        assert resp.status_code == 503


# ---------------------------------------------------------------------------
# GET /api/v1/metadata/test-key
# ---------------------------------------------------------------------------


class TestKeyEndpoint:
    def test_valid_key(self, client):
        result = {"success": True, "message": "OMDb key valid", "provider": "omdb"}
        with unittest.mock.patch('arm.api.v1.metadata.test_configured_key', return_value=result):
            resp = client.get("/api/v1/metadata/test-key")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_invalid_key(self, client):
        result = {"success": False, "message": "Invalid key", "provider": "omdb"}
        with unittest.mock.patch('arm.api.v1.metadata.test_configured_key', return_value=result):
            resp = client.get("/api/v1/metadata/test-key")
        assert resp.status_code == 200
        assert resp.json()["success"] is False


# ---------------------------------------------------------------------------
# GET /api/v1/metadata/crc/{crc64}
# ---------------------------------------------------------------------------


class TestCrcEndpoint:
    @unittest.mock.patch.dict('arm.config.config.arm_config', {'ARM_API_KEY': 'key123'})
    def test_found(self, client):
        crc_result = {"found": True, "results": [{"title": "Matrix"}]}
        with unittest.mock.patch('arm.api.v1.metadata.lookup_crc', return_value=crc_result), \
             unittest.mock.patch('arm.api.v1.metadata.has_api_key', return_value=True):
            resp = client.get("/api/v1/metadata/crc/abc123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["found"] is True
        assert data["has_api_key"] is True

    @unittest.mock.patch.dict('arm.config.config.arm_config', {})
    def test_not_found(self, client):
        crc_result = {"found": False, "results": []}
        with unittest.mock.patch('arm.api.v1.metadata.lookup_crc', return_value=crc_result), \
             unittest.mock.patch('arm.api.v1.metadata.has_api_key', return_value=False):
            resp = client.get("/api/v1/metadata/crc/unknown")
        assert resp.status_code == 200
        data = resp.json()
        assert data["found"] is False
        assert data["has_api_key"] is False


# ---------------------------------------------------------------------------
# GET /api/v1/metadata/music/search
# ---------------------------------------------------------------------------


class TestMusicSearchEndpoint:
    def test_success(self, client):
        result = {"results": [{"title": "Master of Puppets", "artist": "Metallica"}], "total": 1}
        with unittest.mock.patch('arm.api.v1.metadata.search_music', return_value=result):
            resp = client.get("/api/v1/metadata/music/search?q=Metallica")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_with_filters(self, client):
        result = {"results": [], "total": 0}
        with unittest.mock.patch('arm.api.v1.metadata.search_music',
                                 return_value=result) as mock_fn:
            resp = client.get(
                "/api/v1/metadata/music/search?q=Metallica&artist=Metallica&format=CD&country=US"
            )
        assert resp.status_code == 200
        # Verify filters were passed through
        call_kwargs = mock_fn.call_args
        assert call_kwargs[1]["format"] == "CD"
        assert call_kwargs[1]["country"] == "US"

    def test_missing_query(self, client):
        resp = client.get("/api/v1/metadata/music/search")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/metadata/music/{release_id}
# ---------------------------------------------------------------------------


class TestMusicDetailEndpoint:
    def test_success(self, client):
        detail = {"title": "Master of Puppets", "artist": "Metallica", "tracks": []}
        with unittest.mock.patch('arm.api.v1.metadata.get_music_details', return_value=detail):
            resp = client.get("/api/v1/metadata/music/mbid-123")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Master of Puppets"

    def test_not_found(self, client):
        with unittest.mock.patch('arm.api.v1.metadata.get_music_details', return_value=None):
            resp = client.get("/api/v1/metadata/music/bad-mbid")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Route ordering: music/* must not be captured by {imdb_id} catch-all
# ---------------------------------------------------------------------------


class TestRouteOrdering:
    def test_music_search_not_caught_by_imdb(self, client):
        """GET /music/search should NOT match /{imdb_id} catch-all."""
        result = {"results": [], "total": 0}
        with unittest.mock.patch('arm.api.v1.metadata.search_music', return_value=result):
            resp = client.get("/api/v1/metadata/music/search?q=test")
        # Should be 200 from music search, not 503/404 from imdb handler
        assert resp.status_code == 200

    def test_test_key_not_caught_by_imdb(self, client):
        """GET /test-key should NOT match /{imdb_id} catch-all."""
        result = {"success": True, "message": "OK", "provider": "omdb"}
        with unittest.mock.patch('arm.api.v1.metadata.test_configured_key', return_value=result):
            resp = client.get("/api/v1/metadata/test-key")
        assert resp.status_code == 200
        assert resp.json()["success"] is True
