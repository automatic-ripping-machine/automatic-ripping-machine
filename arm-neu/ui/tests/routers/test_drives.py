"""Tests for backend.routers.drives - delegation to the ripper API."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch


# --- GET /api/drives ---


async def test_list_drives(app_client):
    """GET /api/drives returns drives with current_job (proxied from ripper)."""
    drives_payload = {"drives": [
        {
            "drive_id": 1,
            "name": "BD Drive",
            "mount": "/mnt/dev/sr0",
            "job_id_current": None,
            "job_id_previous": None,
            "description": "Primary",
            "drive_mode": "auto",
            "maker": "LG",
            "model": "WH16NS60",
            "serial": "ABC",
            "connection": "SATA",
            "read_cd": True,
            "read_dvd": True,
            "read_bd": True,
            "firmware": "1.0",
            "location": "0:0:0:0",
            "stale": False,
            "mdisc": 0,
            "serial_id": "lg-abc",
            "current_job": None,
        }
    ]}
    with patch(
        "backend.routers.drives.arm_client.get_drives_with_jobs",
        new_callable=AsyncMock, return_value=drives_payload,
    ):
        resp = await app_client.get("/api/drives")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "BD Drive"


async def test_list_drives_arm_unreachable(app_client):
    """GET /api/drives returns [] when ARM is unreachable (dashboard tolerates this)."""
    with patch(
        "backend.routers.drives.arm_client.get_drives_with_jobs",
        new_callable=AsyncMock, return_value=None,
    ):
        resp = await app_client.get("/api/drives")
    assert resp.status_code == 200
    assert resp.json() == []


# --- PATCH /api/drives/{drive_id} ---


async def test_update_drive_success(app_client):
    """PATCH /api/drives/{id} returns result from ARM."""
    with patch(
        "backend.routers.drives.arm_client.update_drive",
        new_callable=AsyncMock, return_value={"success": True},
    ):
        resp = await app_client.patch("/api/drives/1", json={"name": "New Name"})
    assert resp.status_code == 200
    assert resp.json()["success"] is True


async def test_update_drive_arm_unreachable(app_client):
    """PATCH /api/drives/{id} returns 502 when ARM is down."""
    with patch("backend.routers.drives.arm_client.update_drive", new_callable=AsyncMock, return_value=None):
        resp = await app_client.patch("/api/drives/1", json={"name": "X"})
    assert resp.status_code == 502


async def test_update_drive_no_fields(app_client):
    """PATCH /api/drives/{id} with empty body returns 400."""
    resp = await app_client.patch("/api/drives/1", json={})
    assert resp.status_code == 400
    assert "No fields" in resp.json()["detail"]


async def test_update_drive_failure(app_client):
    """PATCH /api/drives/{id} returns 404 when ARM reports failure."""
    with patch(
        "backend.routers.drives.arm_client.update_drive",
        new_callable=AsyncMock,
        return_value={"success": False, "error": "Drive not found"},
    ):
        resp = await app_client.patch("/api/drives/1", json={"name": "X"})
    assert resp.status_code == 404


# --- GET /api/drives/diagnostic ---


async def test_drive_diagnostic_success(app_client):
    """GET /api/drives/diagnostic returns diagnostic data."""
    diag = {"drives": [{"device": "/dev/sr0", "status": "idle"}]}
    with patch(
        "backend.routers.drives.arm_client.drive_diagnostic",
        new_callable=AsyncMock,
        return_value=diag,
    ):
        resp = await app_client.get("/api/drives/diagnostic")
    assert resp.status_code == 200
    assert resp.json()["drives"][0]["device"] == "/dev/sr0"


async def test_drive_diagnostic_arm_unreachable(app_client):
    """GET /api/drives/diagnostic returns 502 when ARM is down."""
    with patch(
        "backend.routers.drives.arm_client.drive_diagnostic",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await app_client.get("/api/drives/diagnostic")
    assert resp.status_code == 502


# --- DELETE /api/drives/{drive_id} ---


async def test_delete_drive_success(app_client):
    """DELETE /api/drives/{id} returns success."""
    with patch(
        "backend.routers.drives.arm_client.delete_drive",
        new_callable=AsyncMock,
        return_value={"success": True},
    ):
        resp = await app_client.delete("/api/drives/1")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


async def test_delete_drive_arm_unreachable(app_client):
    """DELETE /api/drives/{id} returns 502 when ARM is down."""
    with patch(
        "backend.routers.drives.arm_client.delete_drive",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await app_client.delete("/api/drives/1")
    assert resp.status_code == 502


async def test_delete_drive_active_job(app_client):
    """DELETE /api/drives/{id} returns 409 when drive has active job."""
    with patch(
        "backend.routers.drives.arm_client.delete_drive",
        new_callable=AsyncMock,
        return_value={"success": False, "error": "Drive has active job"},
    ):
        resp = await app_client.delete("/api/drives/1")
    assert resp.status_code == 409


async def test_delete_drive_not_found(app_client):
    """DELETE /api/drives/{id} returns 404 when drive doesn't exist."""
    with patch(
        "backend.routers.drives.arm_client.delete_drive",
        new_callable=AsyncMock,
        return_value={"success": False, "error": "Drive not found"},
    ):
        resp = await app_client.delete("/api/drives/1")
    assert resp.status_code == 404


# --- POST /api/drives/{drive_id}/scan ---


async def test_scan_drive_success(app_client):
    """POST /api/drives/{id}/scan returns success."""
    with patch(
        "backend.routers.drives.arm_client.scan_drive",
        new_callable=AsyncMock,
        return_value={"success": True, "disc": {"label": "MY_DISC"}},
    ):
        resp = await app_client.post("/api/drives/1/scan")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


async def test_scan_drive_arm_unreachable(app_client):
    """POST /api/drives/{id}/scan returns 502 when ARM is down."""
    with patch(
        "backend.routers.drives.arm_client.scan_drive",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await app_client.post("/api/drives/1/scan")
    assert resp.status_code == 502


async def test_scan_drive_not_found(app_client):
    """POST /api/drives/{id}/scan returns 404 when drive not found."""
    with patch(
        "backend.routers.drives.arm_client.scan_drive",
        new_callable=AsyncMock,
        return_value={"success": False, "error": "Drive not found"},
    ):
        resp = await app_client.post("/api/drives/1/scan")
    assert resp.status_code == 404


async def test_scan_drive_generic_error(app_client):
    """POST /api/drives/{id}/scan returns 400 for non-404 errors."""
    with patch(
        "backend.routers.drives.arm_client.scan_drive",
        new_callable=AsyncMock,
        return_value={"success": False, "error": "Scan timed out"},
    ):
        resp = await app_client.post("/api/drives/1/scan")
    assert resp.status_code == 400


# --- POST /api/drives/rescan ---


async def test_rescan_drives_success(app_client):
    """POST /api/drives/rescan returns success from ARM."""
    with patch(
        "backend.routers.drives.arm_client.rescan_drives",
        new_callable=AsyncMock,
        return_value={"success": True, "before": 1, "after": 1, "removed": 0},
    ):
        resp = await app_client.post("/api/drives/rescan")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


async def test_rescan_drives_arm_unreachable(app_client):
    """POST /api/drives/rescan returns 502 when ARM is down."""
    with patch(
        "backend.routers.drives.arm_client.rescan_drives",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await app_client.post("/api/drives/rescan")
    assert resp.status_code == 502
