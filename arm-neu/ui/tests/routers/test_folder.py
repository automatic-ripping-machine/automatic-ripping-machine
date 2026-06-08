"""Tests for backend.routers.folder — folder import proxy and poster proxy."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


# --- Scan endpoint ---

async def test_scan_success(app_client):
    result = {"success": True, "disc_type": "bluray", "label": "TEST"}
    with patch("backend.routers.folder.arm_client.scan_folder", new_callable=AsyncMock, return_value=result):
        resp = await app_client.post("/api/jobs/folder/scan", json={"path": "/ingress/movie"})
    assert resp.status_code == 200
    assert resp.json()["disc_type"] == "bluray"


async def test_scan_unreachable(app_client):
    with patch("backend.routers.folder.arm_client.scan_folder", new_callable=AsyncMock, return_value=None):
        resp = await app_client.post("/api/jobs/folder/scan", json={"path": "/ingress/movie"})
    assert resp.status_code == 503


async def test_scan_backend_error(app_client):
    result = {"success": False, "error": "Not a valid disc folder"}
    with patch("backend.routers.folder.arm_client.scan_folder", new_callable=AsyncMock, return_value=result):
        resp = await app_client.post("/api/jobs/folder/scan", json={"path": "/ingress/bad"})
    assert resp.status_code == 502
    assert "Not a valid disc folder" in resp.json()["detail"]


async def test_scan_backend_error_no_message(app_client):
    result = {"success": False}
    with patch("backend.routers.folder.arm_client.scan_folder", new_callable=AsyncMock, return_value=result):
        resp = await app_client.post("/api/jobs/folder/scan", json={"path": "/ingress/bad"})
    assert resp.status_code == 502


# --- Create endpoint ---

async def test_create_success(app_client):
    result = {"success": True, "job_id": 1, "status": "ripping", "source_type": "folder"}
    with patch("backend.routers.folder.arm_client.create_folder_job", new_callable=AsyncMock, return_value=result):
        resp = await app_client.post("/api/jobs/folder", json={
            "source_path": "/ingress/movie",
            "title": "Test Movie",
            "video_type": "movie",
            "disctype": "bluray",
        })
    assert resp.status_code == 201
    assert resp.json()["job_id"] == 1


async def test_create_with_disc_season_fields(app_client):
    """Season, disc_number, disc_total are passed through to ARM backend."""
    result = {"success": True, "job_id": 2, "status": "identifying", "source_type": "folder"}
    with patch("backend.routers.folder.arm_client.create_folder_job", new_callable=AsyncMock, return_value=result) as mock_create:
        resp = await app_client.post("/api/jobs/folder", json={
            "source_path": "/ingress/tv_show",
            "title": "Test Show",
            "video_type": "series",
            "disctype": "bluray",
            "season": 1,
            "disc_number": 3,
            "disc_total": 4,
        })
    assert resp.status_code == 201
    # Verify the fields were passed through to the ARM client
    call_args = mock_create.call_args[0][0]
    assert call_args["season"] == 1
    assert call_args["disc_number"] == 3
    assert call_args["disc_total"] == 4


async def test_create_without_disc_fields(app_client):
    """Disc fields default to None when not provided."""
    result = {"success": True, "job_id": 3, "status": "identifying", "source_type": "folder"}
    with patch("backend.routers.folder.arm_client.create_folder_job", new_callable=AsyncMock, return_value=result) as mock_create:
        resp = await app_client.post("/api/jobs/folder", json={
            "source_path": "/ingress/movie",
            "title": "Test Movie",
            "video_type": "movie",
            "disctype": "bluray",
        })
    assert resp.status_code == 201
    call_args = mock_create.call_args[0][0]
    assert call_args["season"] is None
    assert call_args["disc_number"] is None
    assert call_args["disc_total"] is None


async def test_create_unreachable(app_client):
    with patch("backend.routers.folder.arm_client.create_folder_job", new_callable=AsyncMock, return_value=None):
        resp = await app_client.post("/api/jobs/folder", json={
            "source_path": "/ingress/movie",
            "title": "Test Movie",
            "video_type": "movie",
            "disctype": "bluray",
        })
    assert resp.status_code == 503


async def test_create_backend_error(app_client):
    result = {"success": False, "error": "Active job already exists"}
    with patch("backend.routers.folder.arm_client.create_folder_job", new_callable=AsyncMock, return_value=result):
        resp = await app_client.post("/api/jobs/folder", json={
            "source_path": "/ingress/movie",
            "title": "Test Movie",
            "video_type": "movie",
            "disctype": "bluray",
        })
    assert resp.status_code == 502


# --- Poster proxy redirect (backward compat) ---

async def test_poster_proxy_redirects(app_client):
    """Old poster-proxy URL redirects to /api/images/proxy."""
    resp = await app_client.get(
        "/api/jobs/folder/poster-proxy?url=https://m.media-amazon.com/test.jpg",
        follow_redirects=False,
    )
    assert resp.status_code == 301
    assert "/api/images/proxy" in resp.headers["location"]
