"""Tests for backend.routers.dashboard - orchestration, ripper-API-unavailable degradation."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from tests.factories import make_job_dict


def _drive_dict(**overrides) -> dict:
    """Return a ripper /api/v1/drives-shaped dict, matching arm/api/v1/drives.py:_drive_dict."""
    defaults = {
        "drive_id": 1,
        "name": "BD Drive 1",
        "description": "Primary Blu-ray drive",
        "mount": "/mnt/dev/sr0",
        "maker": "LG",
        "model": "WH16NS60",
        "serial": "ABC123",
        "firmware": "1.02",
        "connection": "SATA",
        "capabilities": {"cd": True, "dvd": True, "bd": True},
        "uhd_capable": False,
        "drive_mode": "auto",
        "rip_speed": None,
        "prescan_cache_mb": None,
        "prescan_timeout": None,
        "prescan_retries": None,
        "disc_enum_timeout": None,
        "stale": False,
        "job_id_current": None,
        "job_id_previous": None,
    }
    defaults.update(overrides)
    return defaults


def _active_job_dict(**overrides) -> dict:
    """Return a ripper /api/v1/jobs/active-shaped dict.

    Thin wrapper around make_job_dict() so call sites read as "an active job".
    """
    return make_job_dict(**overrides)


# --- GET /api/dashboard ---


async def test_dashboard_full(app_client):
    """Dashboard returns all fields when ripper API and services are available."""
    job = _active_job_dict(job_id=1, status="ripping")
    drive = _drive_dict()
    arm_hw = {"cpu": "AMD Ryzen 7", "memory_total_gb": 32.0}
    stats = {"cpu_percent": 45.0, "cpu_temp": 55.0, "memory": None, "storage": []}

    with (
        patch("backend.routers.dashboard.arm_client.get_active_jobs",
              new_callable=AsyncMock, return_value={"jobs": [job]}),
        patch("backend.routers.dashboard.arm_client.get_drives",
              new_callable=AsyncMock, return_value={"drives": [drive]}),
        patch("backend.routers.dashboard.arm_client.get_notification_count",
              new_callable=AsyncMock,
              return_value={"total": 5, "unseen": 3, "seen": 0, "cleared": 2}),
        patch("backend.routers.dashboard.arm_client.get_ripping_enabled",
              new_callable=AsyncMock, return_value={"ripping_enabled": True}),
        patch(
            "backend.routers.dashboard.transcoder_client.health",
            new_callable=AsyncMock, return_value={"status": "ok"},
        ),
        patch(
            "backend.routers.dashboard.transcoder_client.get_stats",
            new_callable=AsyncMock, return_value={"active": 1},
        ),
        patch(
            "backend.routers.dashboard.transcoder_client.get_jobs",
            new_callable=AsyncMock, return_value={"jobs": []},
        ),
        patch("backend.routers.dashboard.arm_client.get_system_stats",
              new_callable=AsyncMock, return_value=stats),
        patch("backend.routers.dashboard.system_cache.get_arm_info", return_value=arm_hw),
        patch("backend.routers.dashboard.system_cache.get_transcoder_info", return_value=None),
    ):
        resp = await app_client.get("/api/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert data["db_available"] is True
    assert data["drives_online"] == 1
    assert data["notification_count"] == 3
    assert data["ripping_enabled"] is True
    assert data["transcoder_online"] is True
    assert abs(data["system_stats"]["cpu_percent"] - 45.0) < 0.01
    assert data["system_info"]["cpu"] == "AMD Ryzen 7"
    assert len(data["active_jobs"]) == 1
    assert data["active_jobs"][0]["track_counts"] == {"total": 5, "ripped": 0}


async def test_dashboard_db_unavailable(app_client):
    """Dashboard degrades gracefully when ALL ripper endpoints fail.

    db_available flips False; sticky fields (active_jobs, drives_online,
    drive_names, notification_count, ripping_enabled) come back as None
    so the polling store keeps the prior value rather than overwriting
    with zero/empty (which flickered badges/counts to nothing).
    """
    with (
        patch("backend.routers.dashboard.arm_client.get_active_jobs",
              new_callable=AsyncMock, return_value=None),
        patch("backend.routers.dashboard.arm_client.get_drives",
              new_callable=AsyncMock, return_value=None),
        patch("backend.routers.dashboard.arm_client.get_notification_count",
              new_callable=AsyncMock, return_value=None),
        patch("backend.routers.dashboard.arm_client.get_ripping_enabled",
              new_callable=AsyncMock, return_value=None),
        patch("backend.routers.dashboard.transcoder_client.health",
              new_callable=AsyncMock, return_value=None),
        patch("backend.routers.dashboard.arm_client.get_system_stats",
              new_callable=AsyncMock, return_value=None),
        patch("backend.routers.dashboard.system_cache.get_arm_info", return_value=None),
        patch("backend.routers.dashboard.system_cache.get_transcoder_info", return_value=None),
    ):
        resp = await app_client.get("/api/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert data["db_available"] is False
    assert data["active_jobs"] is None
    assert data["drives_online"] is None
    assert data["drive_names"] is None
    assert data["notification_count"] is None
    assert data["ripping_enabled"] is None
    assert data["transcoder_online"] is False
    assert data["system_stats"] is None


async def test_dashboard_partial_arm_failure_keeps_other_fields(app_client):
    """When SOME ripper endpoints blip, only those specific fields come back
    None. Independent endpoints keep their fresh values, so notification
    count doesn't flicker to zero just because the drives endpoint timed out.
    """
    with (
        patch("backend.routers.dashboard.arm_client.get_active_jobs",
              new_callable=AsyncMock, return_value={"jobs": []}),
        patch("backend.routers.dashboard.arm_client.get_drives",
              new_callable=AsyncMock, return_value=None),  # this one blips
        patch("backend.routers.dashboard.arm_client.get_notification_count",
              new_callable=AsyncMock, return_value={"unseen": 7}),
        patch("backend.routers.dashboard.arm_client.get_ripping_enabled",
              new_callable=AsyncMock, return_value={"ripping_enabled": True}),
        patch("backend.routers.dashboard.transcoder_client.health",
              new_callable=AsyncMock, return_value=None),
        patch("backend.routers.dashboard.arm_client.get_system_stats",
              new_callable=AsyncMock, return_value=None),
        patch("backend.routers.dashboard.system_cache.get_arm_info", return_value=None),
        patch("backend.routers.dashboard.system_cache.get_transcoder_info", return_value=None),
    ):
        resp = await app_client.get("/api/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    # ARM partially up: db_available is True (at least one endpoint succeeded).
    assert data["db_available"] is True
    # The succeeding endpoints carry their fresh values through.
    assert data["active_jobs"] == []
    assert data["notification_count"] == 7
    assert data["ripping_enabled"] is True
    # Only the blipped endpoint's fields are None (frontend sticky-merges).
    assert data["drives_online"] is None
    assert data["drive_names"] is None


async def test_dashboard_transcoder_offline(app_client):
    """Dashboard shows transcoder_online=False when transcoder health returns None."""
    with (
        patch("backend.routers.dashboard.arm_client.get_active_jobs",
              new_callable=AsyncMock, return_value={"jobs": []}),
        patch("backend.routers.dashboard.arm_client.get_drives",
              new_callable=AsyncMock, return_value={"drives": []}),
        patch("backend.routers.dashboard.arm_client.get_notification_count",
              new_callable=AsyncMock,
              return_value={"total": 0, "unseen": 0, "seen": 0, "cleared": 0}),
        patch("backend.routers.dashboard.arm_client.get_ripping_enabled",
              new_callable=AsyncMock, return_value={"ripping_enabled": True}),
        patch("backend.routers.dashboard.transcoder_client.health",
              new_callable=AsyncMock, return_value=None),
        patch("backend.routers.dashboard.arm_client.get_system_stats",
              new_callable=AsyncMock, return_value=None),
        patch("backend.routers.dashboard.system_cache.get_arm_info", return_value=None),
        patch("backend.routers.dashboard.system_cache.get_transcoder_info", return_value=None),
    ):
        resp = await app_client.get("/api/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert data["transcoder_online"] is False
    assert data["transcoder_stats"] is None


async def test_dashboard_drive_names_normalize_mount_paths(app_client):
    """drive_names should include both /mnt/dev/srN and /dev/srN forms for job-mount lookup."""
    drive = _drive_dict(mount="/mnt/dev/sr0", name="BD Drive 1")
    with (
        patch("backend.routers.dashboard.arm_client.get_active_jobs",
              new_callable=AsyncMock, return_value={"jobs": []}),
        patch("backend.routers.dashboard.arm_client.get_drives",
              new_callable=AsyncMock, return_value={"drives": [drive]}),
        patch("backend.routers.dashboard.arm_client.get_notification_count",
              new_callable=AsyncMock,
              return_value={"total": 0, "unseen": 0, "seen": 0, "cleared": 0}),
        patch("backend.routers.dashboard.arm_client.get_ripping_enabled",
              new_callable=AsyncMock, return_value={"ripping_enabled": True}),
        patch("backend.routers.dashboard.transcoder_client.health",
              new_callable=AsyncMock, return_value=None),
        patch("backend.routers.dashboard.arm_client.get_system_stats",
              new_callable=AsyncMock, return_value=None),
        patch("backend.routers.dashboard.system_cache.get_arm_info", return_value=None),
        patch("backend.routers.dashboard.system_cache.get_transcoder_info", return_value=None),
    ):
        resp = await app_client.get("/api/dashboard")
    assert resp.status_code == 200
    drive_names = resp.json()["drive_names"]
    assert drive_names["/mnt/dev/sr0"] == "BD Drive 1"
    assert drive_names["/dev/sr0"] == "BD Drive 1"


async def test_dashboard_ripping_paused_when_disabled(app_client):
    """ripping_enabled=False from ripper -> dashboard reports ripping_enabled=False."""
    with (
        patch("backend.routers.dashboard.arm_client.get_active_jobs",
              new_callable=AsyncMock, return_value={"jobs": []}),
        patch("backend.routers.dashboard.arm_client.get_drives",
              new_callable=AsyncMock, return_value={"drives": []}),
        patch("backend.routers.dashboard.arm_client.get_notification_count",
              new_callable=AsyncMock,
              return_value={"total": 0, "unseen": 0, "seen": 0, "cleared": 0}),
        patch("backend.routers.dashboard.arm_client.get_ripping_enabled",
              new_callable=AsyncMock, return_value={"ripping_enabled": False}),
        patch("backend.routers.dashboard.transcoder_client.health",
              new_callable=AsyncMock, return_value=None),
        patch("backend.routers.dashboard.arm_client.get_system_stats",
              new_callable=AsyncMock, return_value=None),
        patch("backend.routers.dashboard.system_cache.get_arm_info", return_value=None),
        patch("backend.routers.dashboard.system_cache.get_transcoder_info", return_value=None),
    ):
        resp = await app_client.get("/api/dashboard")
    assert resp.status_code == 200
    assert resp.json()["ripping_enabled"] is False


# --- POST /api/dashboard/makemkv-key-check ---


async def test_makemkv_key_check_success(app_client):
    """POST /api/dashboard/makemkv-key-check returns key_valid and message from ARM."""
    result = {"success": True, "key_valid": True, "message": "MakeMKV key is valid"}
    with patch(
        "backend.routers.dashboard.arm_client.check_makemkv_key",
        new_callable=AsyncMock,
        return_value=result,
    ):
        resp = await app_client.post("/api/dashboard/makemkv-key-check")
    assert resp.status_code == 200
    data = resp.json()
    assert data["key_valid"] is True
    assert data["message"] == "MakeMKV key is valid"


async def test_makemkv_key_check_arm_unreachable(app_client):
    """POST /api/dashboard/makemkv-key-check returns 503 when ARM is unreachable."""
    with patch(
        "backend.routers.dashboard.arm_client.check_makemkv_key",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await app_client.post("/api/dashboard/makemkv-key-check")
    assert resp.status_code == 503
    assert "unreachable" in resp.json()["detail"].lower()


async def test_makemkv_key_check_arm_error(app_client):
    """POST /api/dashboard/makemkv-key-check returns 502 when ARM returns success=False."""
    with patch(
        "backend.routers.dashboard.arm_client.check_makemkv_key",
        new_callable=AsyncMock,
        return_value={"success": False, "error": "invalid key"},
    ):
        resp = await app_client.post("/api/dashboard/makemkv-key-check")
    assert resp.status_code == 502


# --- Ripper-only short-circuit ---

async def test_dashboard_skips_transcoder_when_disabled(ripper_only_app_client, monkeypatch):
    """Dashboard must return disabled transcoder payload without calling transcoder_client."""
    from backend.services import transcoder_client

    called = {"flag": False}

    async def _should_not_be_called(*args, **kwargs):
        called["flag"] = True
        return None

    monkeypatch.setattr(transcoder_client, "health", _should_not_be_called)
    monkeypatch.setattr(transcoder_client, "get_stats", _should_not_be_called)
    monkeypatch.setattr(transcoder_client, "get_jobs", _should_not_be_called)
    monkeypatch.setattr(transcoder_client, "get_system_stats", _should_not_be_called)

    with (
        patch("backend.routers.dashboard.arm_client.get_active_jobs",
              new_callable=AsyncMock, return_value=None),
        patch("backend.routers.dashboard.arm_client.get_drives",
              new_callable=AsyncMock, return_value=None),
        patch("backend.routers.dashboard.arm_client.get_notification_count",
              new_callable=AsyncMock, return_value=None),
        patch("backend.routers.dashboard.arm_client.get_ripping_enabled",
              new_callable=AsyncMock, return_value=None),
        patch("backend.routers.dashboard.arm_client.get_system_stats",
              new_callable=AsyncMock, return_value=None),
    ):
        resp = await ripper_only_app_client.get("/api/dashboard")

    assert resp.status_code == 200
    data = resp.json()
    assert data["transcoder_online"] is False
    assert data["transcoder_stats"] is None
    assert data["transcoder_system_stats"] is None
    assert data["active_transcodes"] == []
    assert data["transcoder_info"] is None
    assert called["flag"] is False, "transcoder_client was called despite flag being off"
