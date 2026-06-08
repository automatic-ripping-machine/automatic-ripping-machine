"""BFF pass-through tests for copy_progress / copy_stage on /api/jobs/{id}/progress."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


async def test_progress_endpoint_includes_copy_fields(app_client):
    """When arm-neu reports copy_progress / copy_stage, the BFF passes them
    through on /api/jobs/{id}/progress."""
    state = {
        "track_counts": {"total": 2, "ripped": 1},
        "disctype": "bluray",
        "logfile": None,
        "no_of_titles": 2,
        "rip_progress": None,
        "rip_stage": None,
        "tracks_ripped_realtime": None,
        "music_progress": None,
        "music_stage": None,
        "copy_progress": 47.5,
        "copy_stage": "scratch-to-media",
    }
    from backend.routers import jobs as jobs_router
    jobs_router._PROGRESS_CACHE.clear()
    with patch(
        "backend.routers.jobs.arm_client.get_job_progress_state",
        new_callable=AsyncMock,
        return_value=state,
    ):
        response = await app_client.get("/api/jobs/42/progress")
    assert response.status_code == 200
    data = response.json()
    assert data["copy_progress"] == pytest.approx(47.5)
    assert data["copy_stage"] == "scratch-to-media"


async def test_progress_endpoint_copy_fields_default_to_none(app_client):
    """No copy in flight - copy_progress and copy_stage are None on the wire."""
    state = {
        "track_counts": {"total": 0, "ripped": 0},
        "disctype": "dvd",
        "logfile": None,
        "no_of_titles": None,
        "rip_progress": 50.0,
        "rip_stage": "Title 1: Saving to MKV file",
        "tracks_ripped_realtime": 0,
        "music_progress": None,
        "music_stage": None,
        "copy_progress": None,
        "copy_stage": None,
    }
    from backend.routers import jobs as jobs_router
    jobs_router._PROGRESS_CACHE.clear()
    with patch(
        "backend.routers.jobs.arm_client.get_job_progress_state",
        new_callable=AsyncMock,
        return_value=state,
    ):
        response = await app_client.get("/api/jobs/42/progress")
    assert response.status_code == 200
    data = response.json()
    assert data["copy_progress"] is None
    assert data["copy_stage"] is None
