"""Tests for backend.routers.arm_actions — _check_result + proxy endpoints."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from backend.routers.arm_actions import _check_result


# --- _check_result unit tests ---


@pytest.mark.parametrize(
    "result, expected_status, expected_detail_substr",
    [
        (None, 503, "unreachable"),
        ({"success": False, "error": "Job not found"}, 502, "Job not found"),
        ({"success": False, "Error": "Something broke"}, 502, "Something broke"),
        ({"success": False}, 502, "Action failed"),
    ],
    ids=["none-503", "error-key", "Error-key-capital", "fallback-message"],
)
def test_check_result_raises(result, expected_status, expected_detail_substr):
    """_check_result raises HTTPException for None or success=False results."""
    with pytest.raises(HTTPException) as exc_info:
        _check_result(result)
    assert exc_info.value.status_code == expected_status
    assert expected_detail_substr.lower() in exc_info.value.detail.lower()


@pytest.mark.parametrize(
    "result",
    [
        {"success": True, "data": "ok"},
        {"job_id": 1, "status": "abandoned"},
    ],
    ids=["success-true", "no-success-key"],
)
def test_check_result_passthrough(result):
    """Successful or keyless results pass through unchanged."""
    assert _check_result(result) == result


# --- Endpoint test helpers ---


def _patch_arm_client(method_name: str, return_value):
    """Patch an arm_client method for endpoint tests."""
    return patch(
        f"backend.routers.arm_actions.arm_client.{method_name}",
        new_callable=AsyncMock,
        return_value=return_value,
    )


# --- Endpoint tests via app_client ---


async def test_abandon_job_endpoint(app_client):
    """POST /api/jobs/{id}/abandon proxies to arm_client."""
    with _patch_arm_client("abandon_job", {"success": True}):
        resp = await app_client.post("/api/jobs/1/abandon")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


async def test_abandon_job_503_when_unreachable(app_client):
    """POST /api/jobs/{id}/abandon returns 503 when ARM is down."""
    with _patch_arm_client("abandon_job", None):
        resp = await app_client.post("/api/jobs/1/abandon")
    assert resp.status_code == 503


async def test_delete_job_endpoint(app_client):
    """DELETE /api/jobs/{id} proxies to arm_client."""
    with _patch_arm_client("delete_job", {"success": True}):
        resp = await app_client.delete("/api/jobs/1")
    assert resp.status_code == 200


async def test_set_ripping_enabled_endpoint(app_client):
    """POST /api/system/ripping-enabled toggles ripping."""
    with _patch_arm_client("set_ripping_enabled", {"success": True}):
        resp = await app_client.post(
            "/api/system/ripping-enabled", json={"enabled": True},
        )
    assert resp.status_code == 200


async def test_start_waiting_job_endpoint(app_client):
    """POST /api/jobs/{id}/start proxies to arm_client."""
    with _patch_arm_client("start_waiting_job", {"success": True}):
        resp = await app_client.post("/api/jobs/1/start")
    assert resp.status_code == 200


async def test_pause_waiting_job_endpoint(app_client):
    """POST /api/jobs/{id}/pause proxies to arm_client."""
    with _patch_arm_client("pause_waiting_job", {"success": True, "paused": True}):
        resp = await app_client.post("/api/jobs/1/pause")
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    assert resp.json()["paused"] is True


async def test_pause_waiting_job_503_when_unreachable(app_client):
    """POST /api/jobs/{id}/pause returns 503 when ARM is down."""
    with _patch_arm_client("pause_waiting_job", None):
        resp = await app_client.post("/api/jobs/1/pause")
    assert resp.status_code == 503


async def test_pause_waiting_job_explicit_true(app_client):
    """POST /api/jobs/{id}/pause with {paused: true} forwards paused=True."""
    with _patch_arm_client("pause_waiting_job", {"success": True, "paused": True}) as mock_pause:
        resp = await app_client.post("/api/jobs/1/pause", json={"paused": True})
    assert resp.status_code == 200
    assert resp.json()["paused"] is True
    mock_pause.assert_called_once_with(1, paused=True)


async def test_pause_waiting_job_explicit_false(app_client):
    """POST /api/jobs/{id}/pause with {paused: false} forwards paused=False."""
    with _patch_arm_client("pause_waiting_job", {"success": True, "paused": False}) as mock_pause:
        resp = await app_client.post("/api/jobs/1/pause", json={"paused": False})
    assert resp.status_code == 200
    assert resp.json()["paused"] is False
    mock_pause.assert_called_once_with(1, paused=False)


# --- skip_and_finalize endpoint ---


async def test_skip_and_finalize_endpoint(app_client):
    """POST /api/jobs/{id}/skip-and-finalize proxies to arm_client."""
    with _patch_arm_client("skip_and_finalize", {"success": True, "message": "Job finalized"}):
        resp = await app_client.post("/api/jobs/5/skip-and-finalize")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


async def test_skip_and_finalize_502_on_arm_error(app_client):
    """POST /api/jobs/{id}/skip-and-finalize returns 502 when ARM reports failure."""
    with _patch_arm_client("skip_and_finalize", {"success": False, "error": "Job not in transcoding state"}):
        resp = await app_client.post("/api/jobs/5/skip-and-finalize")
    assert resp.status_code == 502
    assert "Job not in transcoding state" in resp.json()["detail"]


async def test_skip_and_finalize_503_when_unreachable(app_client):
    """POST /api/jobs/{id}/skip-and-finalize returns 503 when ARM is down."""
    with _patch_arm_client("skip_and_finalize", None):
        resp = await app_client.post("/api/jobs/5/skip-and-finalize")
    assert resp.status_code == 503


# --- force_complete endpoint ---


async def test_force_complete_endpoint(app_client):
    """POST /api/jobs/{id}/force-complete proxies to arm_client."""
    with _patch_arm_client("force_complete", {"success": True, "message": "Job marked as complete"}):
        resp = await app_client.post("/api/jobs/5/force-complete")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


async def test_force_complete_502_on_arm_error(app_client):
    """POST /api/jobs/{id}/force-complete returns 502 when ARM reports failure."""
    with _patch_arm_client("force_complete", {"success": False, "error": "Job not in valid state"}):
        resp = await app_client.post("/api/jobs/5/force-complete")
    assert resp.status_code == 502
    assert "Job not in valid state" in resp.json()["detail"]


async def test_force_complete_503_when_unreachable(app_client):
    """POST /api/jobs/{id}/force-complete returns 503 when ARM is down."""
    with _patch_arm_client("force_complete", None):
        resp = await app_client.post("/api/jobs/5/force-complete")
    assert resp.status_code == 503
