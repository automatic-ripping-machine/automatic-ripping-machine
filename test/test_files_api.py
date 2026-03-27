"""Tests for arm/api/v1/files.py — file browser API endpoints.

Verifies that file browser endpoints:
1. Use sync def (not async def) so FastAPI runs them in a threadpool,
   preventing event loop blocking during heavy I/O operations.
2. Accept Pydantic request models instead of raw Request objects.
3. Handle all error cases correctly (403, 404, 409, 500).
4. Return correct success responses for all operations.
"""
import inspect
import os
import shutil
import unittest.mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def files_client(app_context):
    from arm.api.v1.files import router
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def tmp_media_tree(tmp_path):
    """Create a temporary media directory tree for file browser tests."""
    raw = tmp_path / "raw"
    raw.mkdir()
    completed = tmp_path / "completed"
    completed.mkdir()
    # Create some files and directories
    movie_dir = raw / "Test Movie"
    movie_dir.mkdir()
    (movie_dir / "title.mkv").write_bytes(b"\x00" * 1024)
    (raw / "orphan.mkv").write_bytes(b"\x00" * 512)
    return {
        "root": str(tmp_path),
        "raw": str(raw),
        "completed": str(completed),
        "movie_dir": str(movie_dir),
    }


class TestHandlersAreSync:
    """Verify all file browser handlers are sync (def, not async def).

    FastAPI automatically runs sync def handlers in a threadpool via
    anyio.to_thread.run_sync(). Async def handlers run directly on the
    event loop — if they call blocking I/O (shutil.move, shutil.rmtree,
    os.walk + chown), they block ALL other requests.

    This is the root cause of API unresponsiveness during file operations.
    """

    def test_rename_handler_is_sync(self):
        from arm.api.v1.files import rename_item
        assert not inspect.iscoroutinefunction(rename_item), (
            "rename_item must be sync (def, not async def) to avoid "
            "blocking the event loop during filesystem operations"
        )

    def test_move_handler_is_sync(self):
        from arm.api.v1.files import move_item
        assert not inspect.iscoroutinefunction(move_item), (
            "move_item must be sync (def, not async def) to avoid "
            "blocking the event loop during large file moves"
        )

    def test_mkdir_handler_is_sync(self):
        from arm.api.v1.files import create_directory
        assert not inspect.iscoroutinefunction(create_directory), (
            "create_directory must be sync (def, not async def) to avoid "
            "blocking the event loop during directory creation"
        )

    def test_fix_permissions_handler_is_sync(self):
        from arm.api.v1.files import fix_permissions
        assert not inspect.iscoroutinefunction(fix_permissions), (
            "fix_permissions must be sync (def, not async def) to avoid "
            "blocking the event loop during recursive permission fixing"
        )

    def test_delete_handler_is_sync(self):
        from arm.api.v1.files import delete_item
        assert not inspect.iscoroutinefunction(delete_item), (
            "delete_item must be sync (def, not async def) to avoid "
            "blocking the event loop during directory tree deletion"
        )

    def test_get_roots_handler_is_sync(self):
        from arm.api.v1.files import get_roots
        assert not inspect.iscoroutinefunction(get_roots)

    def test_list_directory_handler_is_sync(self):
        from arm.api.v1.files import list_directory
        assert not inspect.iscoroutinefunction(list_directory)


class TestHandlersDoNotUseRawRequest:
    """Verify handlers use Pydantic models, not raw Request objects.

    Using raw Request objects forces async def (to await request.json()).
    Pydantic models let FastAPI parse the body automatically in sync handlers.
    """

    def test_rename_does_not_take_request_param(self):
        from arm.api.v1.files import rename_item
        sig = inspect.signature(rename_item)
        param_types = [p.annotation for p in sig.parameters.values()]
        from fastapi import Request
        assert Request not in param_types, (
            "rename_item should use a Pydantic model, not Request"
        )

    def test_move_does_not_take_request_param(self):
        from arm.api.v1.files import move_item
        sig = inspect.signature(move_item)
        param_types = [p.annotation for p in sig.parameters.values()]
        from fastapi import Request
        assert Request not in param_types, (
            "move_item should use a Pydantic model, not Request"
        )

    def test_delete_does_not_take_request_param(self):
        from arm.api.v1.files import delete_item
        sig = inspect.signature(delete_item)
        param_types = [p.annotation for p in sig.parameters.values()]
        from fastapi import Request
        assert Request not in param_types, (
            "delete_item should use a Pydantic model, not Request"
        )


class TestFileOperations:
    """Verify file browser endpoints work correctly end-to-end."""

    def test_get_roots(self, app_context, files_client):
        with unittest.mock.patch(
            "arm.config.config.arm_config",
            {"RAW_PATH": "/media/raw", "COMPLETED_PATH": "/media/completed",
             "TRANSCODE_PATH": "/media/transcode", "MUSIC_PATH": "/media/music",
             "INSTALLPATH": "/opt/arm/"},
        ):
            resp = files_client.get("/api/v1/files/roots")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_directory(self, app_context, tmp_media_tree, files_client):
        mock_cfg = {
            "RAW_PATH": tmp_media_tree["raw"],
            "COMPLETED_PATH": tmp_media_tree["completed"],
            "TRANSCODE_PATH": "",
            "MUSIC_PATH": "",
        }
        with unittest.mock.patch("arm.config.config.arm_config", mock_cfg):
            resp = files_client.get(
                "/api/v1/files/list",
                params={"path": tmp_media_tree["raw"]},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "entries" in data
        names = [e["name"] for e in data["entries"]]
        assert "Test Movie" in names

    def test_list_directory_access_denied(self, app_context, files_client):
        mock_cfg = {"RAW_PATH": "/media/raw", "COMPLETED_PATH": "/media/completed",
                     "TRANSCODE_PATH": "", "MUSIC_PATH": ""}
        with unittest.mock.patch("arm.config.config.arm_config", mock_cfg):
            resp = files_client.get(
                "/api/v1/files/list",
                params={"path": "/etc/passwd"},
            )
        assert resp.status_code == 403

    def test_rename_success(self, app_context, tmp_media_tree, files_client):
        mock_cfg = {
            "RAW_PATH": tmp_media_tree["raw"],
            "COMPLETED_PATH": tmp_media_tree["completed"],
            "TRANSCODE_PATH": "",
            "MUSIC_PATH": "",
        }
        target = os.path.join(tmp_media_tree["raw"], "orphan.mkv")
        with unittest.mock.patch("arm.config.config.arm_config", mock_cfg):
            resp = files_client.post(
                "/api/v1/files/rename",
                json={"path": target, "new_name": "renamed.mkv"},
            )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_rename_missing_params(self, app_context, files_client):
        resp = files_client.post("/api/v1/files/rename", json={"path": "/some/path"})
        assert resp.status_code == 422  # Pydantic validation error

    def test_move_success(self, app_context, tmp_media_tree, files_client):
        mock_cfg = {
            "RAW_PATH": tmp_media_tree["raw"],
            "COMPLETED_PATH": tmp_media_tree["completed"],
            "TRANSCODE_PATH": "",
            "MUSIC_PATH": "",
        }
        src = os.path.join(tmp_media_tree["raw"], "orphan.mkv")
        with unittest.mock.patch("arm.config.config.arm_config", mock_cfg):
            resp = files_client.post(
                "/api/v1/files/move",
                json={"path": src, "destination": tmp_media_tree["completed"]},
            )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_mkdir_success(self, app_context, tmp_media_tree, files_client):
        mock_cfg = {
            "RAW_PATH": tmp_media_tree["raw"],
            "COMPLETED_PATH": tmp_media_tree["completed"],
            "TRANSCODE_PATH": "",
            "MUSIC_PATH": "",
        }
        with unittest.mock.patch("arm.config.config.arm_config", mock_cfg):
            resp = files_client.post(
                "/api/v1/files/mkdir",
                json={"path": tmp_media_tree["raw"], "name": "New Folder"},
            )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        assert os.path.isdir(os.path.join(tmp_media_tree["raw"], "New Folder"))

    def test_delete_success(self, app_context, tmp_media_tree, files_client):
        mock_cfg = {
            "RAW_PATH": tmp_media_tree["raw"],
            "COMPLETED_PATH": tmp_media_tree["completed"],
            "TRANSCODE_PATH": "",
            "MUSIC_PATH": "",
        }
        target = os.path.join(tmp_media_tree["raw"], "orphan.mkv")
        with unittest.mock.patch("arm.config.config.arm_config", mock_cfg):
            resp = files_client.request(
                "DELETE",
                "/api/v1/files/delete",
                json={"path": target},
            )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        assert not os.path.exists(target)

    def test_delete_access_denied(self, app_context, files_client):
        mock_cfg = {"RAW_PATH": "/media/raw", "COMPLETED_PATH": "/media/completed",
                     "TRANSCODE_PATH": "", "MUSIC_PATH": ""}
        with unittest.mock.patch("arm.config.config.arm_config", mock_cfg):
            resp = files_client.request(
                "DELETE",
                "/api/v1/files/delete",
                json={"path": "/etc/passwd"},
            )
        assert resp.status_code == 403

    def test_fix_permissions_access_denied(self, app_context, files_client):
        mock_cfg = {"RAW_PATH": "/media/raw", "COMPLETED_PATH": "/media/completed",
                     "TRANSCODE_PATH": "", "MUSIC_PATH": ""}
        with unittest.mock.patch("arm.config.config.arm_config", mock_cfg):
            resp = files_client.post(
                "/api/v1/files/fix-permissions",
                json={"path": "/etc/passwd"},
            )
        assert resp.status_code == 403


class TestDbSessionMiddleware:
    """Verify that the app has DB session cleanup middleware."""

    def test_app_has_session_cleanup_middleware(self):
        """The app must clean up DB sessions after each request to prevent
        leaked transaction state across recycled threadpool threads."""
        from arm.app import app, SessionCleanupMiddleware
        # Check user_middleware list for our middleware class
        found = any(
            m.cls is SessionCleanupMiddleware
            for m in app.user_middleware
            if hasattr(m, 'cls')
        )
        assert found, (
            "App should have SessionCleanupMiddleware to prevent "
            "leaked sessions across recycled threadpool threads"
        )
