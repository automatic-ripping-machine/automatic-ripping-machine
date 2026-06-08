"""Tests for backend.routers.iso - ISO import proxy."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch


# --- Scan endpoint ---

async def test_scan_success(app_client):
    result = {
        "success": True,
        "disc_type": "bluray",
        "label": "TEST",
        "title_suggestion": "Test Movie",
        "year_suggestion": "2024",
        "iso_size": 25_000_000_000,
        "stream_count": 12,
        "volume_id": "TEST_DISC",
    }
    with patch("backend.routers.iso.arm_client.scan_iso", new_callable=AsyncMock, return_value=result):
        resp = await app_client.post("/api/jobs/iso/scan", json={"path": "/ingress/movie.iso"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["disc_type"] == "bluray"
    assert body["volume_id"] == "TEST_DISC"
    assert body["iso_size"] == 25_000_000_000
    assert body["stream_count"] == 12


async def test_scan_unreachable(app_client):
    with patch("backend.routers.iso.arm_client.scan_iso", new_callable=AsyncMock, return_value=None):
        resp = await app_client.post("/api/jobs/iso/scan", json={"path": "/ingress/movie.iso"})
    assert resp.status_code == 503


async def test_scan_backend_error(app_client):
    result = {"success": False, "error": "Not a valid ISO"}
    with patch("backend.routers.iso.arm_client.scan_iso", new_callable=AsyncMock, return_value=result):
        resp = await app_client.post("/api/jobs/iso/scan", json={"path": "/ingress/bad.iso"})
    assert resp.status_code == 502
    assert "Not a valid ISO" in resp.json()["detail"]


async def test_scan_backend_error_no_message(app_client):
    result = {"success": False}
    with patch("backend.routers.iso.arm_client.scan_iso", new_callable=AsyncMock, return_value=result):
        resp = await app_client.post("/api/jobs/iso/scan", json={"path": "/ingress/bad.iso"})
    assert resp.status_code == 502


# --- Create endpoint ---

async def test_create_success(app_client):
    result = {
        "success": True,
        "job_id": 7,
        "status": "ripping",
        "source_type": "iso",
        "source_path": "/ingress/movie.iso",
    }
    with patch("backend.routers.iso.arm_client.create_iso_job", new_callable=AsyncMock, return_value=result):
        resp = await app_client.post("/api/jobs/iso", json={
            "source_path": "/ingress/movie.iso",
            "title": "Test Movie",
            "video_type": "movie",
            "disctype": "bluray",
        })
    assert resp.status_code == 201
    body = resp.json()
    assert body["job_id"] == 7
    assert body["source_type"] == "iso"


async def test_create_with_disc_season_fields(app_client):
    """Season, disc_number, disc_total are passed through to ARM backend."""
    result = {"success": True, "job_id": 8, "status": "identifying", "source_type": "iso"}
    with patch("backend.routers.iso.arm_client.create_iso_job", new_callable=AsyncMock, return_value=result) as mock_create:
        resp = await app_client.post("/api/jobs/iso", json={
            "source_path": "/ingress/show.iso",
            "title": "Test Show",
            "video_type": "series",
            "disctype": "bluray",
            "season": 2,
            "disc_number": 1,
            "disc_total": 3,
        })
    assert resp.status_code == 201
    call_args = mock_create.call_args[0][0]
    assert call_args["season"] == 2
    assert call_args["disc_number"] == 1
    assert call_args["disc_total"] == 3


async def test_create_without_disc_fields(app_client):
    """Disc fields default to None when not provided."""
    result = {"success": True, "job_id": 9, "status": "identifying", "source_type": "iso"}
    with patch("backend.routers.iso.arm_client.create_iso_job", new_callable=AsyncMock, return_value=result) as mock_create:
        resp = await app_client.post("/api/jobs/iso", json={
            "source_path": "/ingress/movie.iso",
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
    with patch("backend.routers.iso.arm_client.create_iso_job", new_callable=AsyncMock, return_value=None):
        resp = await app_client.post("/api/jobs/iso", json={
            "source_path": "/ingress/movie.iso",
            "title": "Test Movie",
            "video_type": "movie",
            "disctype": "bluray",
        })
    assert resp.status_code == 503


async def test_create_backend_error(app_client):
    result = {"success": False, "error": "Active job already exists"}
    with patch("backend.routers.iso.arm_client.create_iso_job", new_callable=AsyncMock, return_value=result):
        resp = await app_client.post("/api/jobs/iso", json={
            "source_path": "/ingress/movie.iso",
            "title": "Test Movie",
            "video_type": "movie",
            "disctype": "bluray",
        })
    assert resp.status_code == 502
