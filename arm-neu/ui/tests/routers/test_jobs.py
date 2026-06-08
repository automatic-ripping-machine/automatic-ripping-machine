"""Tests for backend.routers.jobs - list/detail/metadata endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from tests.factories import make_job_dict


def _track_dict(**overrides) -> dict:
    """Ripper-shaped track dict (matches arm/api/v1/jobs.py:_track_to_dict)."""
    defaults = {
        "track_id": 1, "job_id": 1, "track_number": "1",
        "length": 5400, "aspect_ratio": "16:9", "fps": 23.976,
        "enabled": True, "basename": "title_t01", "filename": "title_t01.mkv",
        "orig_filename": "title_t01.mkv", "new_filename": "Test Movie (2024).mkv",
        "ripped": True, "status": "success", "error": None, "source": "/dev/sr0",
        "title": None, "year": None, "imdb_id": None, "poster_url": None, "video_type": None,
        "episode_number": None, "episode_name": None,
    }
    defaults.update(overrides)
    return defaults


# --- GET /api/jobs ---


async def test_list_jobs(app_client):
    """GET /api/jobs returns paginated job list."""
    paginated = {
        "jobs": [make_job_dict(job_id=1, title="Test Movie")],
        "total": 1,
        "page": 1,
        "per_page": 25,
        "pages": 1,
    }
    with patch(
        "backend.routers.jobs.arm_client.get_jobs_paginated",
        new_callable=AsyncMock, return_value=paginated,
    ):
        resp = await app_client.get("/api/jobs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["jobs"]) == 1
    assert data["jobs"][0]["title"] == "Test Movie"


async def test_list_jobs_with_pagination_params(app_client):
    """GET /api/jobs passes pagination params through to the ripper client."""
    paginated = {"jobs": [], "total": 0, "page": 3, "per_page": 10, "pages": 1}
    with patch(
        "backend.routers.jobs.arm_client.get_jobs_paginated",
        new_callable=AsyncMock, return_value=paginated,
    ) as mock_fn:
        resp = await app_client.get("/api/jobs?page=3&per_page=10&status=active")
    assert resp.status_code == 200
    mock_fn.assert_awaited_once_with(
        page=3, per_page=10, status="active", search=None,
        video_type=None, disctype=None, days=None,
        sort_by=None, sort_dir=None,
    )


async def test_list_jobs_arm_unreachable(app_client):
    """GET /api/jobs returns 502 when ARM is unreachable."""
    with patch(
        "backend.routers.jobs.arm_client.get_jobs_paginated",
        new_callable=AsyncMock, return_value=None,
    ):
        resp = await app_client.get("/api/jobs")
    assert resp.status_code == 502


# --- GET /api/jobs/{job_id} ---


async def test_get_job_detail(app_client):
    """GET /api/jobs/{id} returns job with tracks and config."""
    detail = {
        "job": make_job_dict(job_id=5, title="Detail Movie"),
        "config": {"RIPMETHOD": "mkv", "MINLENGTH": "600"},
        "tracks": [_track_dict(job_id=5)],
        "track_counts": {"total": 1, "ripped": 1},
    }
    with patch(
        "backend.routers.jobs.arm_client.get_job_detail",
        new_callable=AsyncMock, return_value=detail,
    ):
        resp = await app_client.get("/api/jobs/5")
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Detail Movie"
    assert len(data["tracks"]) == 1
    assert data["config"]["RIPMETHOD"] == "mkv"


async def test_get_job_404(app_client):
    """GET /api/jobs/{id} returns 404 when ARM returns success=False."""
    with patch(
        "backend.routers.jobs.arm_client.get_job_detail",
        new_callable=AsyncMock, return_value={"success": False, "error": "Job not found"},
    ):
        resp = await app_client.get("/api/jobs/999")
    assert resp.status_code == 404


async def test_get_job_arm_unreachable(app_client):
    """GET /api/jobs/{id} returns 502 when ARM is unreachable."""
    with patch(
        "backend.routers.jobs.arm_client.get_job_detail",
        new_callable=AsyncMock, return_value=None,
    ):
        resp = await app_client.get("/api/jobs/5")
    assert resp.status_code == 502


# --- GET /api/metadata/search ---


async def test_metadata_search(app_client):
    """GET /api/metadata/search returns search results (proxied through ARM)."""
    results = [{"title": "Matrix", "year": "1999", "imdb_id": "tt0133093", "media_type": "movie", "poster_url": None}]
    with patch("backend.routers.jobs.arm_client.search_metadata", new_callable=AsyncMock, return_value=results):
        resp = await app_client.get("/api/metadata/search?q=matrix")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Matrix"


async def test_metadata_search_502_on_arm_unreachable(app_client):
    """GET /api/metadata/search returns 502 when ARM is unreachable."""
    import httpx as _httpx
    with patch(
        "backend.routers.jobs.arm_client.search_metadata",
        new_callable=AsyncMock, side_effect=_httpx.ConnectError("offline"),
    ):
        resp = await app_client.get("/api/metadata/search?q=test")
    assert resp.status_code == 502


# --- GET /api/jobs/{job_id}/progress ---


async def test_get_job_progress_with_track_counts(app_client):
    """GET /api/jobs/{id}/progress returns rip progress enriched with track counts."""
    state = {
        "track_counts": {"total": 10, "ripped": 3},
        "disctype": "bluray", "logfile": "job_5.log", "no_of_titles": 10,
        "rip_progress": 45, "rip_stage": "rip",
        "music_progress": None, "music_stage": None,
        "tracks_ripped_realtime": None,
    }
    # Bypass the BFF's 1s TTL cache so each test sees a fresh upstream call.
    from backend.routers import jobs as jobs_router
    jobs_router._PROGRESS_CACHE.clear()
    with patch("backend.routers.jobs.arm_client.get_job_progress_state",
               new_callable=AsyncMock, return_value=state):
        resp = await app_client.get("/api/jobs/5/progress")
    assert resp.status_code == 200
    data = resp.json()
    assert data["progress"] == 45
    assert data["stage"] == "rip"
    assert data["tracks_total"] == 10
    assert data["tracks_ripped"] == 3


async def test_get_job_progress_404(app_client):
    """GET /api/jobs/{id}/progress returns 404 when ripper returns success=False."""
    from backend.routers import jobs as jobs_router
    jobs_router._PROGRESS_CACHE.clear()
    with patch("backend.routers.jobs.arm_client.get_job_progress_state",
               new_callable=AsyncMock,
               return_value={"success": False, "error": "Job not found"}):
        resp = await app_client.get("/api/jobs/999/progress")
    assert resp.status_code == 404


async def test_get_job_progress_arm_unreachable(app_client):
    """GET /api/jobs/{id}/progress returns 502 when ARM is unreachable."""
    from backend.routers import jobs as jobs_router
    jobs_router._PROGRESS_CACHE.clear()
    with patch("backend.routers.jobs.arm_client.get_job_progress_state",
               new_callable=AsyncMock, return_value=None):
        resp = await app_client.get("/api/jobs/5/progress")
    assert resp.status_code == 502


async def test_get_job_progress_music_branch(app_client):
    """GET /api/jobs/{id}/progress uses music_progress for disctype=music."""
    state = {
        "track_counts": {"total": 3, "ripped": 2},
        "disctype": "music", "logfile": "job_7.log", "no_of_titles": 3,
        "rip_progress": None, "rip_stage": None,
        "music_progress": 66.7, "music_stage": "2/3 - encoding track 3",
        "tracks_ripped_realtime": 2,
    }
    from backend.routers import jobs as jobs_router
    jobs_router._PROGRESS_CACHE.clear()
    with patch("backend.routers.jobs.arm_client.get_job_progress_state",
               new_callable=AsyncMock, return_value=state):
        resp = await app_client.get("/api/jobs/7/progress")
    assert resp.status_code == 200
    data = resp.json()
    assert data["progress"] == pytest.approx(66.7)
    assert "encoding" in data["stage"]


async def test_get_job_progress_includes_no_of_titles(app_client):
    """GET /api/jobs/{id}/progress includes no_of_titles from the job."""
    state = {
        "track_counts": {"total": 0, "ripped": 0},
        "disctype": "bluray", "logfile": "job_8.log", "no_of_titles": 12,
        "rip_progress": None, "rip_stage": None,
        "music_progress": None, "music_stage": None,
        "tracks_ripped_realtime": None,
    }
    from backend.routers import jobs as jobs_router
    jobs_router._PROGRESS_CACHE.clear()
    with patch("backend.routers.jobs.arm_client.get_job_progress_state",
               new_callable=AsyncMock, return_value=state):
        resp = await app_client.get("/api/jobs/8/progress")
    assert resp.status_code == 200
    data = resp.json()
    assert data["no_of_titles"] == 12


async def test_get_job_progress_realtime_overrides_db_count(app_client):
    """When realtime ripped > DB ripped, return the higher value."""
    state = {
        "track_counts": {"total": 10, "ripped": 2},
        "disctype": "bluray", "logfile": "job_9.log", "no_of_titles": 10,
        "rip_progress": 50, "rip_stage": "Title 5: Saving to MKV file",
        "music_progress": None, "music_stage": None,
        "tracks_ripped_realtime": 4,
    }
    from backend.routers import jobs as jobs_router
    jobs_router._PROGRESS_CACHE.clear()
    with patch("backend.routers.jobs.arm_client.get_job_progress_state",
               new_callable=AsyncMock, return_value=state):
        resp = await app_client.get("/api/jobs/9/progress")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tracks_ripped"] == 4  # realtime wins
    assert data["tracks_total"] == 10


async def test_get_job_progress_uses_ttl_cache(app_client):
    """Two rapid polls hit upstream once thanks to the 1s TTL cache."""
    state = {
        "track_counts": {"total": 10, "ripped": 3},
        "disctype": "bluray", "logfile": "job_42.log", "no_of_titles": 10,
        "rip_progress": 50, "rip_stage": None,
        "music_progress": None, "music_stage": None,
        "tracks_ripped_realtime": None,
    }
    from backend.routers import jobs as jobs_router
    jobs_router._PROGRESS_CACHE.clear()
    mock = AsyncMock(return_value=state)
    with patch("backend.routers.jobs.arm_client.get_job_progress_state", mock):
        await app_client.get("/api/jobs/42/progress")
        await app_client.get("/api/jobs/42/progress")
    assert mock.await_count == 1


# --- GET /api/jobs/{job_id}/naming-preview ---


async def test_naming_preview_success(app_client):
    """GET /api/jobs/{id}/naming-preview returns rendered filenames."""
    result = {
        "success": True,
        "job_title": "Show S01E01",
        "job_folder": "Show/Season 01",
        "tracks": [
            {"track_number": "0", "rendered_title": "Pilot S01E01", "rendered_folder": "Show/Season 01"},
        ],
    }
    with patch("backend.routers.jobs.arm_client.naming_preview_for_job", new_callable=AsyncMock, return_value=result):
        resp = await app_client.get("/api/jobs/1/naming-preview")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert len(data["tracks"]) == 1
    assert data["tracks"][0]["rendered_title"] == "Pilot S01E01"


async def test_naming_preview_job_not_found(app_client):
    """GET /api/jobs/{id}/naming-preview returns 404 for missing job."""
    result = {"success": False, "error": "Job not found"}
    with patch("backend.routers.jobs.arm_client.naming_preview_for_job", new_callable=AsyncMock, return_value=result):
        resp = await app_client.get("/api/jobs/999/naming-preview")
    assert resp.status_code == 404


async def test_naming_preview_arm_unreachable(app_client):
    """GET /api/jobs/{id}/naming-preview returns 502 when ARM is down."""
    with patch("backend.routers.jobs.arm_client.naming_preview_for_job", new_callable=AsyncMock, return_value=None):
        resp = await app_client.get("/api/jobs/1/naming-preview")
    assert resp.status_code == 502


# --- Per-job naming overrides ---


async def test_update_job_naming_success(app_client):
    """PATCH /api/jobs/{id}/naming saves pattern overrides."""
    result = {"success": True, "title_pattern_override": "{title} - E{episode}", "folder_pattern_override": None}
    with patch("backend.routers.jobs.arm_client.update_job_naming", new_callable=AsyncMock, return_value=result):
        resp = await app_client.patch("/api/jobs/1/naming", json={"title_pattern_override": "{title} - E{episode}"})
    assert resp.status_code == 200
    assert resp.json()["title_pattern_override"] == "{title} - E{episode}"


async def test_update_job_naming_invalid_pattern(app_client):
    """PATCH /api/jobs/{id}/naming returns 400 for invalid patterns."""
    result = {"success": False, "error": "Invalid variables in pattern: ['episde']", "invalid_vars": ["episde"], "suggestions": {"episde": "episode"}}
    with patch("backend.routers.jobs.arm_client.update_job_naming", new_callable=AsyncMock, return_value=result):
        resp = await app_client.patch("/api/jobs/1/naming", json={"title_pattern_override": "{title} S{episde}"})
    assert resp.status_code == 400


async def test_update_job_naming_arm_unreachable(app_client):
    """PATCH /api/jobs/{id}/naming returns 503 when ARM is down."""
    with patch("backend.routers.jobs.arm_client.update_job_naming", new_callable=AsyncMock, return_value=None):
        resp = await app_client.patch("/api/jobs/1/naming", json={"title_pattern_override": "{title}"})
    assert resp.status_code == 503


async def test_validate_naming_pattern(app_client):
    """POST /api/naming/validate returns validation result."""
    result = {"valid": False, "invalid_vars": ["episde"], "suggestions": {"episde": "episode"}}
    with patch("backend.routers.jobs.arm_client.validate_naming_pattern", new_callable=AsyncMock, return_value=result):
        resp = await app_client.post("/api/naming/validate", json={"pattern": "{title} {episde}"})
    assert resp.status_code == 200
    assert resp.json()["valid"] is False
    assert "episde" in resp.json()["invalid_vars"]


async def test_validate_naming_arm_unreachable(app_client):
    """POST /api/naming/validate returns 503 when ARM is down."""
    with patch("backend.routers.jobs.arm_client.validate_naming_pattern", new_callable=AsyncMock, return_value=None):
        resp = await app_client.post("/api/naming/validate", json={"pattern": "{title}"})
    assert resp.status_code == 503


async def test_get_naming_variables(app_client):
    """GET /api/naming/variables returns variable list."""
    result = {"variables": ["album", "artist", "episode", "label", "season", "title", "video_type", "year"], "descriptions": {}}
    with patch("backend.routers.jobs.arm_client.get_naming_variables", new_callable=AsyncMock, return_value=result):
        resp = await app_client.get("/api/naming/variables")
    assert resp.status_code == 200
    assert "title" in resp.json()["variables"]
    assert len(resp.json()["variables"]) == 8


async def test_get_naming_variables_arm_unreachable(app_client):
    """GET /api/naming/variables returns 503 when ARM is down."""
    with patch("backend.routers.jobs.arm_client.get_naming_variables", new_callable=AsyncMock, return_value=None):
        resp = await app_client.get("/api/naming/variables")
    assert resp.status_code == 503


# --- Ripper-only gating ---

async def test_transcode_config_gated_when_disabled(ripper_only_app_client):
    resp = await ripper_only_app_client.patch("/api/jobs/1/transcode-config", json={})
    assert resp.status_code == 503
    assert resp.json()["detail"] == "Transcoder disabled on this deployment"


async def test_retranscode_gated_when_disabled(ripper_only_app_client):
    resp = await ripper_only_app_client.post("/api/jobs/1/retranscode")
    assert resp.status_code == 503
    assert resp.json()["detail"] == "Transcoder disabled on this deployment"

