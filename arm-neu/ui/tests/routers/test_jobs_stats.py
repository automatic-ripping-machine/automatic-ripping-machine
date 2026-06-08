"""Tests for GET /api/jobs/stats endpoint."""
from __future__ import annotations
from unittest.mock import AsyncMock, patch

_STATS = {"total": 10, "active": 2, "success": 5, "fail": 2, "waiting": 1}


async def test_stats_returns_all_fields(app_client):
    with patch(
        "backend.routers.jobs.arm_client.get_jobs_stats",
        new_callable=AsyncMock, return_value=_STATS,
    ):
        resp = await app_client.get("/api/jobs/stats")
    assert resp.status_code == 200
    data = resp.json()
    for key in ("total", "active", "success", "fail", "waiting"):
        assert key in data


async def test_stats_passes_filters(app_client):
    with patch(
        "backend.routers.jobs.arm_client.get_jobs_stats",
        new_callable=AsyncMock, return_value=_STATS,
    ) as mock_fn:
        resp = await app_client.get("/api/jobs/stats?disctype=dvd&video_type=movie&days=7")
    assert resp.status_code == 200
    mock_fn.assert_awaited_once_with(
        search=None, video_type="movie", disctype="dvd", days=7,
    )


async def test_stats_no_filters(app_client):
    with patch(
        "backend.routers.jobs.arm_client.get_jobs_stats",
        new_callable=AsyncMock, return_value=_STATS,
    ) as mock_fn:
        resp = await app_client.get("/api/jobs/stats")
    assert resp.status_code == 200
    mock_fn.assert_awaited_once_with(
        search=None, video_type=None, disctype=None, days=None,
    )


async def test_stats_arm_unreachable_returns_zeros(app_client):
    """When ARM is unreachable, /api/jobs/stats returns zero buckets."""
    with patch(
        "backend.routers.jobs.arm_client.get_jobs_stats",
        new_callable=AsyncMock, return_value=None,
    ):
        resp = await app_client.get("/api/jobs/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data == {"total": 0, "active": 0, "success": 0, "fail": 0, "waiting": 0}
