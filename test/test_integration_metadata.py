"""Integration tests for metadata API — runs against live containers.

Requires:
  - arm-rippers on localhost:8080
  - arm-ui on localhost:8888

Run with: pytest test/test_integration_metadata.py -v -m integration
"""

from __future__ import annotations

import httpx
import pytest

ARM_BASE = "http://localhost:8080"
UI_BASE = "http://localhost:8888"

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _musicbrainz_rate_limit():
    """MusicBrainz rate-limits to 1 req/sec — pause between tests."""
    import time
    time.sleep(1.1)


@pytest.fixture(scope="module")
def arm():
    """Shared httpx client for ARM direct endpoints."""
    with httpx.Client(base_url=ARM_BASE, timeout=15.0) as client:
        yield client


@pytest.fixture(scope="module")
def ui():
    """Shared httpx client for UI proxy endpoints."""
    with httpx.Client(base_url=UI_BASE, timeout=15.0) as client:
        yield client


def _require_reachable(client: httpx.Client, label: str):
    try:
        client.get("/")
    except httpx.ConnectError:
        pytest.skip(f"{label} not reachable")


# ---------------------------------------------------------------------------
# ARM direct — /api/v1/metadata/search
# ---------------------------------------------------------------------------


class TestArmMetadataSearch:
    def test_search_returns_results(self, arm):
        _require_reachable(arm, "ARM")
        resp = arm.get("/api/v1/metadata/search", params={"q": "Matrix"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        first = data[0]
        assert "title" in first
        assert "imdb_id" in first
        assert "media_type" in first

    def test_search_with_year_narrows(self, arm):
        _require_reachable(arm, "ARM")
        resp = arm.get("/api/v1/metadata/search", params={"q": "Matrix", "year": "1999"})
        assert resp.status_code == 200
        data = resp.json()
        assert any(r["year"] == "1999" for r in data)

    def test_search_missing_q_returns_422(self, arm):
        _require_reachable(arm, "ARM")
        resp = arm.get("/api/v1/metadata/search")
        assert resp.status_code == 422

    def test_search_nonsense_returns_empty(self, arm):
        _require_reachable(arm, "ARM")
        resp = arm.get("/api/v1/metadata/search", params={"q": "zzxxyy99nonexistent"})
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# ARM direct — /api/v1/metadata/{imdb_id}
# ---------------------------------------------------------------------------


class TestArmMediaDetail:
    def test_detail_returns_full_info(self, arm):
        _require_reachable(arm, "ARM")
        resp = arm.get("/api/v1/metadata/tt0133093")
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "The Matrix"
        assert data["year"] == "1999"
        assert data["imdb_id"] == "tt0133093"
        assert "plot" in data

    def test_detail_not_found(self, arm):
        _require_reachable(arm, "ARM")
        resp = arm.get("/api/v1/metadata/tt0000000")
        # OMDb returns 200 with Response=False for non-existent IDs → our code returns 404
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# ARM direct — /api/v1/metadata/music/search
# ---------------------------------------------------------------------------


class TestArmMusicSearch:
    def test_music_search_returns_results(self, arm):
        _require_reachable(arm, "ARM")
        resp = arm.get("/api/v1/metadata/music/search", params={"q": "Abbey Road"})
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert "total" in data
        # MusicBrainz rate-limits aggressively; treat empty as soft failure
        if data["total"] == 0:
            pytest.skip("MusicBrainz returned 0 results (likely rate-limited)")

    def test_music_search_with_format_filter(self, arm):
        _require_reachable(arm, "ARM")
        resp = arm.get("/api/v1/metadata/music/search",
                       params={"q": "Abbey Road", "format": "CD"})
        assert resp.status_code == 200
        data = resp.json()
        if data["total"] == 0:
            pytest.skip("MusicBrainz returned 0 results (likely rate-limited)")
        assert data["total"] > 0

    def test_music_search_missing_q(self, arm):
        _require_reachable(arm, "ARM")
        resp = arm.get("/api/v1/metadata/music/search")
        assert resp.status_code == 422

    def test_music_search_result_schema(self, arm):
        _require_reachable(arm, "ARM")
        resp = arm.get("/api/v1/metadata/music/search", params={"q": "Abbey Road"})
        data = resp.json()
        if data["results"]:
            entry = data["results"][0]
            for key in ("title", "artist", "release_id", "media_type"):
                assert key in entry, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# ARM direct — /api/v1/metadata/music/{release_id}
# ---------------------------------------------------------------------------


class TestArmMusicDetail:
    def _get_release_id(self, arm):
        """Get a real release_id from a search to use in detail lookup."""
        import time
        resp = arm.get("/api/v1/metadata/music/search", params={"q": "Abbey Road"})
        data = resp.json()
        if not data.get("results"):
            pytest.skip("No MusicBrainz results to test detail with")
        time.sleep(1.1)  # respect MusicBrainz rate limit before detail call
        return data["results"][0]["release_id"]

    def test_music_detail_returns_tracks(self, arm):
        _require_reachable(arm, "ARM")
        release_id = self._get_release_id(arm)
        resp = arm.get(f"/api/v1/metadata/music/{release_id}")
        if resp.status_code == 503:
            pytest.skip("MusicBrainz rate-limited (503)")
        assert resp.status_code == 200
        data = resp.json()
        assert data["release_id"] == release_id
        assert "tracks" in data
        assert "title" in data

    def test_music_detail_not_found(self, arm):
        _require_reachable(arm, "ARM")
        resp = arm.get("/api/v1/metadata/music/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# ARM direct — /api/v1/metadata/crc/{crc64}
# ---------------------------------------------------------------------------


class TestArmCrcLookup:
    def test_crc_unknown_returns_not_found(self, arm):
        _require_reachable(arm, "ARM")
        resp = arm.get("/api/v1/metadata/crc/0000000000000000")
        assert resp.status_code == 200
        data = resp.json()
        assert data["found"] is False
        assert "has_api_key" in data

    def test_crc_response_schema(self, arm):
        _require_reachable(arm, "ARM")
        resp = arm.get("/api/v1/metadata/crc/abc123")
        assert resp.status_code == 200
        data = resp.json()
        assert "found" in data
        assert "results" in data
        assert isinstance(data["results"], list)


# ---------------------------------------------------------------------------
# ARM direct — /api/v1/metadata/test-key
# ---------------------------------------------------------------------------


class TestArmTestKey:
    def test_key_returns_status(self, arm):
        _require_reachable(arm, "ARM")
        resp = arm.get("/api/v1/metadata/test-key")
        assert resp.status_code == 200
        data = resp.json()
        assert "success" in data
        assert "message" in data
        assert "provider" in data

    def test_key_valid_omdb(self, arm):
        _require_reachable(arm, "ARM")
        resp = arm.get("/api/v1/metadata/test-key")
        data = resp.json()
        # If OMDB_API_KEY is configured, should be valid
        if data["provider"] == "omdb" and data["success"]:
            assert "valid" in data["message"].lower() or "found" in data["message"].lower()


# ===========================================================================
# UI Proxy — all metadata requests proxied through ARM
# ===========================================================================


class TestUiProxySearch:
    def test_search_proxied(self, ui):
        _require_reachable(ui, "UI")
        resp = ui.get("/api/metadata/search", params={"q": "Matrix"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["title"] == "The Matrix"

    def test_search_with_year(self, ui):
        _require_reachable(ui, "UI")
        resp = ui.get("/api/metadata/search", params={"q": "Matrix", "year": "1999"})
        assert resp.status_code == 200
        data = resp.json()
        assert any(r["year"] == "1999" for r in data)


class TestUiProxyDetail:
    def test_detail_proxied(self, ui):
        _require_reachable(ui, "UI")
        resp = ui.get("/api/metadata/tt0133093")
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "The Matrix"
        assert "plot" in data

    def test_detail_not_found(self, ui):
        _require_reachable(ui, "UI")
        resp = ui.get("/api/metadata/tt0000000")
        assert resp.status_code == 404


class TestUiProxyMusicSearch:
    def test_music_search_proxied(self, ui):
        _require_reachable(ui, "UI")
        resp = ui.get("/api/metadata/music/search", params={"q": "Abbey Road"})
        assert resp.status_code == 200
        data = resp.json()
        if data["total"] == 0:
            pytest.skip("MusicBrainz returned 0 results (likely rate-limited)")
        assert data["total"] > 0

    def test_music_search_with_filters(self, ui):
        _require_reachable(ui, "UI")
        resp = ui.get("/api/metadata/music/search",
                       params={"q": "Abbey Road", "format": "CD", "country": "US"})
        assert resp.status_code == 200
        data = resp.json()
        if data["total"] == 0:
            pytest.skip("MusicBrainz returned 0 results (likely rate-limited)")
        assert data["total"] > 0


class TestUiProxyMusicDetail:
    def test_music_detail_proxied(self, ui):
        import time
        _require_reachable(ui, "UI")
        # First get a release_id
        search = ui.get("/api/metadata/music/search", params={"q": "Abbey Road"})
        results = search.json().get("results", [])
        if not results:
            pytest.skip("No MusicBrainz results")
        time.sleep(1.1)  # respect MusicBrainz rate limit before detail call
        release_id = results[0]["release_id"]
        resp = ui.get(f"/api/metadata/music/{release_id}")
        if resp.status_code == 503:
            pytest.skip("MusicBrainz rate-limited (503)")
        assert resp.status_code == 200
        data = resp.json()
        assert "tracks" in data
        assert "title" in data

    def test_music_detail_not_found(self, ui):
        _require_reachable(ui, "UI")
        resp = ui.get("/api/metadata/music/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404


class TestUiProxyTestKey:
    def test_test_metadata_proxied(self, ui):
        _require_reachable(ui, "UI")
        resp = ui.get("/api/settings/test-metadata")
        assert resp.status_code == 200
        data = resp.json()
        assert "success" in data
        assert "provider" in data


# ---------------------------------------------------------------------------
# Cross-validation: ARM and UI return same data
# ---------------------------------------------------------------------------


class TestCrossValidation:
    def test_search_results_match(self, arm, ui):
        _require_reachable(arm, "ARM")
        _require_reachable(ui, "UI")
        arm_resp = arm.get("/api/v1/metadata/search", params={"q": "Inception", "year": "2010"})
        ui_resp = ui.get("/api/metadata/search", params={"q": "Inception", "year": "2010"})
        assert arm_resp.status_code == 200
        assert ui_resp.status_code == 200
        arm_data = arm_resp.json()
        ui_data = ui_resp.json()
        assert len(arm_data) == len(ui_data)
        if arm_data:
            assert arm_data[0]["imdb_id"] == ui_data[0]["imdb_id"]

    def test_detail_results_match(self, arm, ui):
        _require_reachable(arm, "ARM")
        _require_reachable(ui, "UI")
        arm_resp = arm.get("/api/v1/metadata/tt0133093")
        ui_resp = ui.get("/api/metadata/tt0133093")
        assert arm_resp.json()["title"] == ui_resp.json()["title"]
        assert arm_resp.json()["plot"] == ui_resp.json()["plot"]

    def test_key_test_results_match(self, arm, ui):
        _require_reachable(arm, "ARM")
        _require_reachable(ui, "UI")
        arm_resp = arm.get("/api/v1/metadata/test-key")
        ui_resp = ui.get("/api/settings/test-metadata")
        assert arm_resp.json()["success"] == ui_resp.json()["success"]
        assert arm_resp.json()["provider"] == ui_resp.json()["provider"]
