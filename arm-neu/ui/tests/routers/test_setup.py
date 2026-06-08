"""Tests for backend.routers.setup — setup wizard proxy endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch


# --- GET /api/setup/status ---


async def test_setup_status_success(app_client):
    """setup/status proxies ARM response."""
    result = {
        "db_exists": True,
        "db_initialized": True,
        "db_current": True,
        "first_run": True,
        "arm_version": "13.3.0",
        "setup_steps": {"database": "complete", "drives": "0 detected", "settings_reviewed": "pending"},
    }
    with patch(
        "backend.routers.setup.arm_client.get_setup_status",
        new_callable=AsyncMock,
        return_value=result,
    ):
        resp = await app_client.get("/api/setup/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["first_run"] is True
    assert data["setup_steps"]["database"] == "complete"


async def test_setup_status_arm_unreachable(app_client):
    """setup/status returns 503 when ARM is unreachable."""
    with patch(
        "backend.routers.setup.arm_client.get_setup_status",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await app_client.get("/api/setup/status")
    assert resp.status_code == 503


# --- POST /api/setup/complete ---


async def test_setup_complete_success(app_client):
    """setup/complete proxies ARM success response."""
    with patch(
        "backend.routers.setup.arm_client.complete_setup",
        new_callable=AsyncMock,
        return_value={"success": True},
    ):
        resp = await app_client.post("/api/setup/complete")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


async def test_setup_complete_arm_unreachable(app_client):
    """setup/complete returns 503 when ARM is unreachable."""
    with patch(
        "backend.routers.setup.arm_client.complete_setup",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await app_client.post("/api/setup/complete")
    assert resp.status_code == 503


async def test_setup_complete_arm_error(app_client):
    """setup/complete returns 502 when ARM reports failure."""
    with patch(
        "backend.routers.setup.arm_client.complete_setup",
        new_callable=AsyncMock,
        return_value={"success": False, "error": "DB error"},
    ):
        resp = await app_client.post("/api/setup/complete")
    assert resp.status_code == 502
