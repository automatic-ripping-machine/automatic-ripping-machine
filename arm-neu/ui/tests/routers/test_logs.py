"""Tests for backend.routers.logs - pass-through to arm-neu logs API."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch


# --- GET /api/logs ---


async def test_list_logs(app_client):
    """GET /api/logs proxies arm_client.list_logs."""
    logs = [
        {"filename": "arm.log", "size": 1024, "modified": datetime(2024, 1, 1, tzinfo=timezone.utc).isoformat()},
        {"filename": "job_1.log", "size": 512, "modified": datetime(2024, 1, 2, tzinfo=timezone.utc).isoformat()},
    ]
    with patch("backend.routers.logs.arm_client.list_logs", AsyncMock(return_value=logs)):
        resp = await app_client.get("/api/logs")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["filename"] == "arm.log"


async def test_list_logs_502_when_unreachable(app_client):
    """GET /api/logs returns 502 when arm-neu is unreachable."""
    with patch("backend.routers.logs.arm_client.list_logs", AsyncMock(return_value=None)):
        resp = await app_client.get("/api/logs")
    assert resp.status_code == 502


# --- GET /api/logs/{filename} ---


async def test_read_log(app_client):
    """GET /api/logs/{filename} proxies arm_client.read_log."""
    log_data = {"filename": "arm.log", "content": "line1\nline2\n", "lines": 2, "truncated": False}
    with patch(
        "backend.routers.logs.arm_client.read_log", AsyncMock(return_value=log_data)
    ) as mock:
        resp = await app_client.get("/api/logs/arm.log?mode=tail&lines=100")
    assert resp.status_code == 200
    data = resp.json()
    assert data["filename"] == "arm.log"
    assert data["lines"] == 2
    mock.assert_awaited_once_with("arm.log", mode="tail", lines=100)


async def test_read_log_404(app_client):
    """GET /api/logs/{filename} returns 404 when upstream signals missing file."""
    err = {"success": False, "error": "Log file not found"}
    with patch("backend.routers.logs.arm_client.read_log", AsyncMock(return_value=err)):
        resp = await app_client.get("/api/logs/nonexistent.log")
    assert resp.status_code == 404


async def test_read_log_502(app_client):
    """GET /api/logs/{filename} returns 502 when upstream is unreachable."""
    with patch("backend.routers.logs.arm_client.read_log", AsyncMock(return_value=None)):
        resp = await app_client.get("/api/logs/arm.log")
    assert resp.status_code == 502


# --- GET /api/logs/{filename}/structured ---


async def test_read_structured_log(app_client):
    """GET /api/logs/{filename}/structured proxies arm_client.read_log_structured."""
    structured_data = {
        "filename": "arm.log",
        "entries": [
            {
                "timestamp": "2026-02-28T10:15:30Z",
                "level": "info",
                "logger": "arm.ripper.makemkv",
                "event": "Ripping title 1",
                "job_id": 5,
                "label": "LOTR",
                "raw": '{"level":"info","event":"Ripping title 1"}',
            }
        ],
        "lines": 1,
    }
    with patch(
        "backend.routers.logs.arm_client.read_log_structured",
        AsyncMock(return_value=structured_data),
    ):
        resp = await app_client.get("/api/logs/arm.log/structured?mode=tail&lines=100")
    assert resp.status_code == 200
    data = resp.json()
    assert data["filename"] == "arm.log"
    assert data["lines"] == 1
    assert data["entries"][0]["event"] == "Ripping title 1"


async def test_read_structured_log_404(app_client):
    err = {"success": False, "error": "Log file not found"}
    with patch(
        "backend.routers.logs.arm_client.read_log_structured", AsyncMock(return_value=err)
    ):
        resp = await app_client.get("/api/logs/nonexistent.log/structured")
    assert resp.status_code == 404


async def test_read_structured_log_with_filters(app_client):
    """GET .../structured forwards level + search params to arm_client."""
    structured_data = {"filename": "job.log", "entries": [], "lines": 0}
    with patch(
        "backend.routers.logs.arm_client.read_log_structured",
        AsyncMock(return_value=structured_data),
    ) as mock:
        resp = await app_client.get(
            "/api/logs/job.log/structured?level=error&search=failed"
        )
    assert resp.status_code == 200
    mock.assert_awaited_once_with(
        "job.log", mode="tail", lines=100, level="error", search="failed"
    )
