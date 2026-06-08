"""Tests for DELETE /api/logs/{filename} and GET /api/logs/{filename}/download
pass-through to arm-neu."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch


# --- DELETE /api/logs/{filename} ---


async def test_delete_log_success(app_client):
    """DELETE /api/logs/{filename} returns 200 when upstream confirms."""
    upstream = {"success": True, "filename": "arm.log"}
    with patch(
        "backend.routers.logs.arm_client.delete_log", AsyncMock(return_value=upstream)
    ):
        resp = await app_client.delete("/api/logs/arm.log")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["filename"] == "arm.log"


async def test_delete_log_not_found(app_client):
    err = {"success": False, "error": "Log file not found"}
    with patch(
        "backend.routers.logs.arm_client.delete_log", AsyncMock(return_value=err)
    ):
        resp = await app_client.delete("/api/logs/missing.log")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


async def test_delete_log_502(app_client):
    with patch(
        "backend.routers.logs.arm_client.delete_log", AsyncMock(return_value=None)
    ):
        resp = await app_client.delete("/api/logs/arm.log")
    assert resp.status_code == 502


# --- GET /api/logs/{filename}/download ---


def _mock_streaming_response(*, status_code: int, body: bytes = b"", content_type: str = "text/plain"):
    """Build a fake httpx.Response that supports aiter_bytes + aclose."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = {"content-type": content_type}

    async def aiter_bytes():
        yield body

    resp.aiter_bytes = aiter_bytes
    resp.aclose = AsyncMock()
    return resp


async def test_download_log_success(app_client):
    upstream = _mock_streaming_response(status_code=200, body=b"log line 1\nlog line 2\n")
    with patch(
        "backend.routers.logs.arm_client.stream_log_download",
        AsyncMock(return_value=upstream),
    ):
        resp = await app_client.get("/api/logs/arm.log/download")
    assert resp.status_code == 200
    assert b"log line 1" in resp.content
    assert resp.headers["content-type"].startswith("text/plain")


async def test_download_log_forwards_content_disposition(app_client):
    """When upstream sets Content-Disposition, the BFF forwards it to the client."""
    upstream = _mock_streaming_response(status_code=200, body=b"x")
    upstream.headers = {
        "content-type": "text/plain",
        "content-disposition": 'attachment; filename="arm.log"',
    }
    with patch(
        "backend.routers.logs.arm_client.stream_log_download",
        AsyncMock(return_value=upstream),
    ):
        resp = await app_client.get("/api/logs/arm.log/download")
    assert resp.status_code == 200
    assert resp.headers["content-disposition"] == 'attachment; filename="arm.log"'


async def test_download_log_not_found(app_client):
    upstream = _mock_streaming_response(status_code=404)
    with patch(
        "backend.routers.logs.arm_client.stream_log_download",
        AsyncMock(return_value=upstream),
    ):
        resp = await app_client.get("/api/logs/nonexistent.log/download")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()
    upstream.aclose.assert_awaited()


async def test_download_log_502_when_unreachable(app_client):
    with patch(
        "backend.routers.logs.arm_client.stream_log_download",
        AsyncMock(return_value=None),
    ):
        resp = await app_client.get("/api/logs/arm.log/download")
    assert resp.status_code == 502


async def test_download_log_502_when_upstream_500(app_client):
    """Upstream non-200/non-404 (eg. 500) collapses to a BFF 502."""
    upstream = _mock_streaming_response(status_code=500)
    with patch(
        "backend.routers.logs.arm_client.stream_log_download",
        AsyncMock(return_value=upstream),
    ):
        resp = await app_client.get("/api/logs/arm.log/download")
    assert resp.status_code == 502
    upstream.aclose.assert_awaited()


async def test_list_logs_502_when_unreachable(app_client):
    with patch("backend.routers.logs.arm_client.list_logs", AsyncMock(return_value=None)):
        resp = await app_client.get("/api/logs")
    assert resp.status_code == 502
