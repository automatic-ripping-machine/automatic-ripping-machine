"""Tests for backend.routers.system — job stats and restart proxy."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch


async def test_job_stats_success(app_client):
    result = {"by_status": {"success": 5}, "by_type": {"movie": 3}, "total": 5}
    with patch("backend.routers.system.arm_client.get_job_stats", new_callable=AsyncMock, return_value=result):
        resp = await app_client.get("/api/system/job-stats")
    assert resp.status_code == 200
    assert resp.json()["total"] == 5


async def test_job_stats_unreachable(app_client):
    with patch("backend.routers.system.arm_client.get_job_stats", new_callable=AsyncMock, return_value=None):
        resp = await app_client.get("/api/system/job-stats")
    assert resp.status_code == 503


async def test_restart_success(app_client):
    with patch("backend.routers.system.arm_client.restart_arm", new_callable=AsyncMock, return_value={"success": True}):
        resp = await app_client.post("/api/system/restart")
    assert resp.status_code == 200


async def test_restart_unreachable(app_client):
    with patch("backend.routers.system.arm_client.restart_arm", new_callable=AsyncMock, return_value=None):
        resp = await app_client.post("/api/system/restart")
    assert resp.status_code == 503


async def test_restart_transcoder_success(app_client):
    with patch("backend.routers.system.transcoder_client.restart_transcoder", new_callable=AsyncMock, return_value={"success": True, "message": "Transcoder is restarting"}):
        resp = await app_client.post("/api/system/restart-transcoder")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


async def test_restart_transcoder_unreachable(app_client):
    with patch("backend.routers.system.transcoder_client.restart_transcoder", new_callable=AsyncMock, return_value=None):
        resp = await app_client.post("/api/system/restart-transcoder")
    assert resp.status_code == 503


async def test_eject_drive_success(app_client):
    result = {"success": True, "drive_id": 1, "method": "eject"}
    with patch("backend.routers.drives.arm_client.eject_drive", new_callable=AsyncMock, return_value=result):
        resp = await app_client.post("/api/drives/1/eject?method=eject")
    assert resp.status_code == 200
    assert resp.json()["method"] == "eject"


async def test_eject_drive_unreachable(app_client):
    with patch("backend.routers.drives.arm_client.eject_drive", new_callable=AsyncMock, return_value=None):
        resp = await app_client.post("/api/drives/1/eject?method=toggle")
    assert resp.status_code == 502
