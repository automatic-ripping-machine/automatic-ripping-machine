"""Tests for backend.routers.files — file browser proxy endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch


# --- GET /api/files/roots ---


async def test_get_roots_success(app_client):
    roots = [{"path": "/media/raw", "label": "Raw"}, {"path": "/media/completed", "label": "Completed"}]
    with patch("backend.routers.files.arm_client.get_file_roots", new_callable=AsyncMock, return_value=roots):
        resp = await app_client.get("/api/files/roots")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["path"] == "/media/raw"


async def test_get_roots_arm_unreachable(app_client):
    with patch("backend.routers.files.arm_client.get_file_roots", new_callable=AsyncMock, return_value=None):
        resp = await app_client.get("/api/files/roots")
    assert resp.status_code == 503
    assert "unreachable" in resp.json()["detail"].lower()


# --- GET /api/files/list ---


async def test_list_directory_success(app_client):
    result = {
        "path": "/media/raw",
        "parent": "/media",
        "entries": [{"name": "movie.mkv", "type": "file", "size": 1024}],
    }
    with patch("backend.routers.files.arm_client.list_files", new_callable=AsyncMock, return_value=result):
        resp = await app_client.get("/api/files/list", params={"path": "/media/raw"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["entries"][0]["name"] == "movie.mkv"
    assert body["path"] == "/media/raw"
    assert body["parent"] == "/media"


async def test_list_directory_arm_unreachable(app_client):
    with patch("backend.routers.files.arm_client.list_files", new_callable=AsyncMock, return_value=None):
        resp = await app_client.get("/api/files/list", params={"path": "/media/raw"})
    assert resp.status_code == 503


async def test_list_directory_arm_error(app_client):
    result = {"success": False, "error": "ARM error (403): Path not allowed"}
    with patch("backend.routers.files.arm_client.list_files", new_callable=AsyncMock, return_value=result):
        resp = await app_client.get("/api/files/list", params={"path": "/etc/shadow"})
    assert resp.status_code == 502
    assert "Path not allowed" in resp.json()["detail"]


# --- POST /api/files/rename ---


async def test_rename_file_success(app_client):
    result = {"success": True, "new_path": "/media/raw/new_name.mkv"}
    with patch("backend.routers.files.arm_client.rename_file", new_callable=AsyncMock, return_value=result):
        resp = await app_client.post(
            "/api/files/rename",
            json={"path": "/media/raw/old.mkv", "new_name": "new_name.mkv"},
        )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


async def test_rename_file_arm_unreachable(app_client):
    with patch("backend.routers.files.arm_client.rename_file", new_callable=AsyncMock, return_value=None):
        resp = await app_client.post(
            "/api/files/rename",
            json={"path": "/media/raw/old.mkv", "new_name": "new.mkv"},
        )
    assert resp.status_code == 503


# --- POST /api/files/move ---


async def test_move_file_success(app_client):
    result = {"success": True}
    with patch("backend.routers.files.arm_client.move_file", new_callable=AsyncMock, return_value=result):
        resp = await app_client.post(
            "/api/files/move",
            json={"path": "/media/raw/file.mkv", "destination": "/media/completed/"},
        )
    assert resp.status_code == 200


async def test_move_file_arm_unreachable(app_client):
    with patch("backend.routers.files.arm_client.move_file", new_callable=AsyncMock, return_value=None):
        resp = await app_client.post(
            "/api/files/move",
            json={"path": "/media/raw/file.mkv", "destination": "/media/completed/"},
        )
    assert resp.status_code == 503


# --- POST /api/files/mkdir ---


async def test_mkdir_success(app_client):
    result = {"success": True}
    with patch("backend.routers.files.arm_client.create_directory", new_callable=AsyncMock, return_value=result):
        resp = await app_client.post(
            "/api/files/mkdir",
            json={"path": "/media/raw", "name": "new_folder"},
        )
    assert resp.status_code == 200


async def test_mkdir_arm_unreachable(app_client):
    with patch("backend.routers.files.arm_client.create_directory", new_callable=AsyncMock, return_value=None):
        resp = await app_client.post(
            "/api/files/mkdir",
            json={"path": "/media/raw", "name": "new_folder"},
        )
    assert resp.status_code == 503


# --- POST /api/files/fix-permissions ---


async def test_fix_permissions_success(app_client):
    result = {"success": True}
    with patch("backend.routers.files.arm_client.fix_file_permissions", new_callable=AsyncMock, return_value=result):
        resp = await app_client.post(
            "/api/files/fix-permissions",
            json={"path": "/media/raw/file.mkv"},
        )
    assert resp.status_code == 200


async def test_fix_permissions_arm_unreachable(app_client):
    with patch("backend.routers.files.arm_client.fix_file_permissions", new_callable=AsyncMock, return_value=None):
        resp = await app_client.post(
            "/api/files/fix-permissions",
            json={"path": "/media/raw/file.mkv"},
        )
    assert resp.status_code == 503


# --- DELETE /api/files/delete ---


async def test_delete_file_success(app_client):
    result = {"success": True}
    with patch("backend.routers.files.arm_client.delete_file", new_callable=AsyncMock, return_value=result):
        resp = await app_client.request(
            "DELETE",
            "/api/files/delete",
            json={"path": "/media/raw/file.mkv"},
        )
    assert resp.status_code == 200


async def test_delete_file_arm_unreachable(app_client):
    with patch("backend.routers.files.arm_client.delete_file", new_callable=AsyncMock, return_value=None):
        resp = await app_client.request(
            "DELETE",
            "/api/files/delete",
            json={"path": "/media/raw/file.mkv"},
        )
    assert resp.status_code == 503


async def test_delete_file_arm_error(app_client):
    result = {"success": False, "error": "Permission denied"}
    with patch("backend.routers.files.arm_client.delete_file", new_callable=AsyncMock, return_value=result):
        resp = await app_client.request(
            "DELETE",
            "/api/files/delete",
            json={"path": "/media/raw/file.mkv"},
        )
    assert resp.status_code == 502
    assert "Permission denied" in resp.json()["detail"]
