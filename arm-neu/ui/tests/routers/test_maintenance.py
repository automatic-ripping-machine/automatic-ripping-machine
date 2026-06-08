"""Tests for backend.routers.maintenance — orchestration endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch


# --- GET /api/maintenance/summary ---


async def test_summary_success(app_client):
    """GET /api/maintenance/summary returns aggregate counts from all sources."""
    arm_counts = {"orphan_logs": 3, "orphan_folders": 2}
    notif_counts = {"total": 14, "unseen": 4, "seen": 0, "cleared": 10}
    completed_page = {"jobs": [], "total": 5}
    failed_page = {"jobs": [], "total": 2}

    def _tc_jobs(status=None, limit=1, offset=0):
        if status == "completed":
            return completed_page
        return failed_page

    with (
        patch(
            "backend.routers.maintenance.arm_client.get_maintenance_counts",
            new_callable=AsyncMock,
            return_value=arm_counts,
        ),
        patch(
            "backend.routers.maintenance.arm_client.get_notification_count",
            new_callable=AsyncMock,
            return_value=notif_counts,
        ),
        patch(
            "backend.routers.maintenance.transcoder_client.get_jobs",
            new_callable=AsyncMock,
            side_effect=_tc_jobs,
        ),
    ):
        resp = await app_client.get("/api/maintenance/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["orphan_logs"] == 3
    assert data["orphan_folders"] == 2
    assert data["unseen_notifications"] == 4
    assert data["cleared_notifications"] == 10
    assert data["stale_transcoder_jobs"] == 7


async def test_summary_arm_unavailable(app_client):
    """GET /api/maintenance/summary returns None fields when ARM is unreachable."""
    with (
        patch(
            "backend.routers.maintenance.arm_client.get_maintenance_counts",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "backend.routers.maintenance.arm_client.get_notification_count",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "backend.routers.maintenance.transcoder_client.get_jobs",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        resp = await app_client.get("/api/maintenance/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["orphan_logs"] is None
    assert data["orphan_folders"] is None
    assert data["unseen_notifications"] is None
    assert data["cleared_notifications"] is None
    assert data["stale_transcoder_jobs"] is None


# --- GET /api/maintenance/orphan-logs ---


async def test_orphan_logs_success(app_client):
    """GET /api/maintenance/orphan-logs returns log list from ARM."""
    payload = {
        "root": "/var/log/arm",
        "total_size_bytes": 1024,
        "files": [{"path": "/var/log/arm/orphan.log", "relative_path": "orphan.log", "size_bytes": 1024}],
    }
    with patch(
        "backend.routers.maintenance.arm_client.get_orphan_logs",
        new_callable=AsyncMock,
        return_value=payload,
    ):
        resp = await app_client.get("/api/maintenance/orphan-logs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["root"] == "/var/log/arm"
    assert data["total_size_bytes"] == 1024
    assert data["files"][0]["relative_path"] == "orphan.log"


async def test_orphan_logs_arm_unreachable(app_client):
    """GET /api/maintenance/orphan-logs returns 503 when ARM is down."""
    with patch(
        "backend.routers.maintenance.arm_client.get_orphan_logs",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await app_client.get("/api/maintenance/orphan-logs")
    assert resp.status_code == 503
    assert "unreachable" in resp.json()["detail"].lower()


async def test_orphan_logs_arm_error(app_client):
    """GET /api/maintenance/orphan-logs returns 502 when ARM returns success=False."""
    with patch(
        "backend.routers.maintenance.arm_client.get_orphan_logs",
        new_callable=AsyncMock,
        return_value={"success": False, "error": "permission denied"},
    ):
        resp = await app_client.get("/api/maintenance/orphan-logs")
    assert resp.status_code == 502


# --- GET /api/maintenance/orphan-folders ---


async def test_orphan_folders_success(app_client):
    """GET /api/maintenance/orphan-folders returns folder list from ARM."""
    payload = {
        "roots": ["/mnt/media/raw", "/mnt/media/completed"],
        "total_size_bytes": 4096,
        "folders": [{
            "path": "/mnt/media/raw/orphan_dir",
            "name": "orphan_dir",
            "category": "raw",
            "size_bytes": 4096,
        }],
    }
    with patch(
        "backend.routers.maintenance.arm_client.get_orphan_folders",
        new_callable=AsyncMock,
        return_value=payload,
    ):
        resp = await app_client.get("/api/maintenance/orphan-folders")
    assert resp.status_code == 200
    data = resp.json()
    assert data["roots"] == ["/mnt/media/raw", "/mnt/media/completed"]
    assert data["folders"][0]["name"] == "orphan_dir"


async def test_orphan_folders_arm_unreachable(app_client):
    """GET /api/maintenance/orphan-folders returns 503 when ARM is down."""
    with patch(
        "backend.routers.maintenance.arm_client.get_orphan_folders",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await app_client.get("/api/maintenance/orphan-folders")
    assert resp.status_code == 503


# --- POST /api/maintenance/delete-log ---


async def test_delete_log_success(app_client):
    """POST /api/maintenance/delete-log proxies to ARM and returns result."""
    with patch(
        "backend.routers.maintenance.arm_client.delete_orphan_log",
        new_callable=AsyncMock,
        return_value={"success": True, "path": "orphan.log", "error": None},
    ):
        resp = await app_client.post(
            "/api/maintenance/delete-log",
            json={"path": "orphan.log"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["error"] is None
    assert body["path"] == "orphan.log"


async def test_delete_log_arm_unreachable(app_client):
    """POST /api/maintenance/delete-log returns 503 when ARM is down."""
    with patch(
        "backend.routers.maintenance.arm_client.delete_orphan_log",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await app_client.post(
            "/api/maintenance/delete-log",
            json={"path": "/var/log/arm/orphan.log"},
        )
    assert resp.status_code == 503


# --- POST /api/maintenance/delete-folder ---


async def test_delete_folder_success(app_client):
    """POST /api/maintenance/delete-folder proxies to ARM."""
    with patch(
        "backend.routers.maintenance.arm_client.delete_orphan_folder",
        new_callable=AsyncMock,
        return_value={"success": True, "path": "orphan_dir", "error": None},
    ):
        resp = await app_client.post(
            "/api/maintenance/delete-folder",
            json={"path": "orphan_dir"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["error"] is None


# --- POST /api/maintenance/bulk-delete-logs ---


async def test_bulk_delete_logs_success(app_client):
    """POST /api/maintenance/bulk-delete-logs returns ARM result."""
    with patch(
        "backend.routers.maintenance.arm_client.bulk_delete_logs",
        new_callable=AsyncMock,
        return_value={"success": True, "removed": ["a.log", "b.log"], "errors": []},
    ):
        resp = await app_client.post(
            "/api/maintenance/bulk-delete-logs",
            json={"paths": ["a.log", "b.log"]},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["removed"] == ["a.log", "b.log"]
    assert body["errors"] == []


async def test_bulk_delete_logs_arm_unreachable(app_client):
    """POST /api/maintenance/bulk-delete-logs returns 503 when ARM is down."""
    with patch(
        "backend.routers.maintenance.arm_client.bulk_delete_logs",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await app_client.post(
            "/api/maintenance/bulk-delete-logs",
            json={"paths": ["/var/log/arm/a.log"]},
        )
    assert resp.status_code == 503


# --- POST /api/maintenance/bulk-delete-folders ---


async def test_bulk_delete_folders_success(app_client):
    """POST /api/maintenance/bulk-delete-folders returns ARM result."""
    with patch(
        "backend.routers.maintenance.arm_client.bulk_delete_folders",
        new_callable=AsyncMock,
        return_value={"success": True, "removed": ["orphan_dir"], "errors": []},
    ):
        resp = await app_client.post(
            "/api/maintenance/bulk-delete-folders",
            json={"paths": ["orphan_dir"]},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["removed"] == ["orphan_dir"]


# --- POST /api/maintenance/dismiss-all-notifications ---


async def test_dismiss_all_notifications_success(app_client):
    """POST /api/maintenance/dismiss-all-notifications proxies to ARM."""
    with patch(
        "backend.routers.maintenance.arm_client.dismiss_all_notifications",
        new_callable=AsyncMock,
        return_value={"success": True, "count": 7},
    ):
        resp = await app_client.post("/api/maintenance/dismiss-all-notifications")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["count"] == 7


async def test_dismiss_all_notifications_arm_unreachable(app_client):
    """POST /api/maintenance/dismiss-all-notifications returns 503 when ARM is down."""
    with patch(
        "backend.routers.maintenance.arm_client.dismiss_all_notifications",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await app_client.post("/api/maintenance/dismiss-all-notifications")
    assert resp.status_code == 503


# --- POST /api/maintenance/purge-notifications ---


async def test_purge_notifications_success(app_client):
    """POST /api/maintenance/purge-notifications proxies to ARM."""
    with patch(
        "backend.routers.maintenance.arm_client.purge_cleared_notifications",
        new_callable=AsyncMock,
        return_value={"success": True, "count": 15},
    ):
        resp = await app_client.post("/api/maintenance/purge-notifications")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["count"] == 15


async def test_purge_notifications_arm_unreachable(app_client):
    """POST /api/maintenance/purge-notifications returns 503 when ARM is down."""
    with patch(
        "backend.routers.maintenance.arm_client.purge_cleared_notifications",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await app_client.post("/api/maintenance/purge-notifications")
    assert resp.status_code == 503


# --- POST /api/maintenance/cleanup-transcoder ---


async def test_cleanup_transcoder_success(app_client):
    """POST /api/maintenance/cleanup-transcoder deletes completed and failed jobs."""
    jobs_page = {
        "jobs": [{"id": "abc123"}, {"id": "def456"}],
        "total": 2,
    }
    empty_page = {"jobs": [], "total": 0}

    call_count = {"n": 0}

    async def _get_jobs(status=None, limit=50, offset=0):
        call_count["n"] += 1
        # First call per status returns jobs; second call returns empty
        if offset == 0:
            return jobs_page
        return empty_page

    with (
        patch(
            "backend.routers.maintenance.transcoder_client.get_jobs",
            new_callable=AsyncMock,
            side_effect=_get_jobs,
        ),
        patch(
            "backend.routers.maintenance.transcoder_client.delete_job",
            new_callable=AsyncMock,
            return_value=True,
        ),
    ):
        resp = await app_client.post("/api/maintenance/cleanup-transcoder")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["deleted"] == 4  # 2 completed + 2 failed
    assert data["errors"] == []


async def test_cleanup_transcoder_unreachable(app_client):
    """POST /api/maintenance/cleanup-transcoder reports errors when transcoder is down."""
    with patch(
        "backend.routers.maintenance.transcoder_client.get_jobs",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await app_client.post("/api/maintenance/cleanup-transcoder")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["deleted"] == 0
    assert len(data["errors"]) == 2  # one per status (completed, failed)


# --- Image cache endpoints ---


async def test_image_cache_stats(app_client):
    with patch("backend.routers.maintenance.image_cache.stats", return_value={
        "count": 5, "size_bytes": 250000, "size_mb": 0.2, "oldest": 1711234567.0, "path": "/data/cache/images"
    }):
        resp = await app_client.get("/api/maintenance/image-cache-stats")
    assert resp.status_code == 200
    assert resp.json()["count"] == 5


async def test_clear_image_cache(app_client):
    with patch("backend.routers.maintenance.image_cache.clear", return_value={
        "success": True, "cleared": 5, "freed_bytes": 250000
    }):
        resp = await app_client.post("/api/maintenance/clear-image-cache")
    assert resp.status_code == 200
    assert resp.json()["cleared"] == 5


# --- Clear raw directory ---


async def test_clear_raw_success(app_client):
    """POST /api/maintenance/clear-raw proxies to ARM and returns result."""
    with patch(
        "backend.routers.maintenance.arm_client.clear_raw",
        new_callable=AsyncMock,
        return_value={
            "success": True,
            "cleared": 3,
            "freed_bytes": 5000000,
            "errors": [],
            "path": "/home/arm/media/raw",
            "error": None,
        },
    ):
        resp = await app_client.post("/api/maintenance/clear-raw")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["cleared"] == 3
    assert data["freed_bytes"] == 5000000
    assert data["path"] == "/home/arm/media/raw"
    assert data["errors"] == []
    assert data["error"] is None


async def test_clear_raw_arm_unreachable(app_client):
    """POST /api/maintenance/clear-raw returns 503 when ARM is unreachable."""
    with patch(
        "backend.routers.maintenance.arm_client.clear_raw",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await app_client.post("/api/maintenance/clear-raw")
    assert resp.status_code == 503


async def test_clear_raw_arm_error(app_client):
    """POST /api/maintenance/clear-raw returns 502 when ARM returns error.

    With arm-neu PR #322, the failure path emits the full success-shape with
    zero defaults plus `error`; the BFF still maps `success=False` to 502.
    """
    with patch(
        "backend.routers.maintenance.arm_client.clear_raw",
        new_callable=AsyncMock,
        return_value={
            "success": False,
            "cleared": 0,
            "freed_bytes": 0,
            "errors": [],
            "path": "/nonexistent",
            "error": "RAW_PATH not configured",
        },
    ):
        resp = await app_client.post("/api/maintenance/clear-raw")
    assert resp.status_code == 502
