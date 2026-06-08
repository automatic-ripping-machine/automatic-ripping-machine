"""Tests for enhanced job listing - sort, disc type filter, time range."""
from __future__ import annotations
from unittest.mock import AsyncMock, patch

_EMPTY = {"jobs": [], "total": 0, "page": 1, "per_page": 25, "pages": 1}


async def test_sort_by_title_asc(app_client):
    with patch(
        "backend.routers.jobs.arm_client.get_jobs_paginated",
        new_callable=AsyncMock, return_value=_EMPTY,
    ) as mock_fn:
        resp = await app_client.get("/api/jobs?sort_by=title&sort_dir=asc")
    assert resp.status_code == 200
    mock_fn.assert_awaited_once_with(
        page=1, per_page=25, status=None, search=None,
        video_type=None, disctype=None, days=None,
        sort_by="title", sort_dir="asc",
    )


async def test_sort_by_start_time_desc_is_default(app_client):
    with patch(
        "backend.routers.jobs.arm_client.get_jobs_paginated",
        new_callable=AsyncMock, return_value=_EMPTY,
    ) as mock_fn:
        resp = await app_client.get("/api/jobs")
    assert resp.status_code == 200
    mock_fn.assert_awaited_once_with(
        page=1, per_page=25, status=None, search=None,
        video_type=None, disctype=None, days=None,
        sort_by=None, sort_dir=None,
    )


async def test_filter_by_disctype(app_client):
    with patch(
        "backend.routers.jobs.arm_client.get_jobs_paginated",
        new_callable=AsyncMock, return_value=_EMPTY,
    ) as mock_fn:
        resp = await app_client.get("/api/jobs?disctype=dvd")
    assert resp.status_code == 200
    mock_fn.assert_awaited_once_with(
        page=1, per_page=25, status=None, search=None,
        video_type=None, disctype="dvd", days=None,
        sort_by=None, sort_dir=None,
    )


async def test_filter_by_days(app_client):
    with patch(
        "backend.routers.jobs.arm_client.get_jobs_paginated",
        new_callable=AsyncMock, return_value=_EMPTY,
    ) as mock_fn:
        resp = await app_client.get("/api/jobs?days=7")
    assert resp.status_code == 200
    mock_fn.assert_awaited_once_with(
        page=1, per_page=25, status=None, search=None,
        video_type=None, disctype=None, days=7,
        sort_by=None, sort_dir=None,
    )


async def test_invalid_sort_dir_rejected(app_client):
    resp = await app_client.get("/api/jobs?sort_dir=invalid")
    assert resp.status_code == 422
