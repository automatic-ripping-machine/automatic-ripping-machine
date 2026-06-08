"""Tests for arm_client: uncovered functions — file operations, system, notifications."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from backend.services import arm_client


def _mock_response(json_data, status_code: int = 200) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.is_success = 200 <= status_code < 300
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    return resp


# --- close_client ---


async def test_close_client():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.is_closed = False
    arm_client._client = mock_client
    await arm_client.close_client()
    mock_client.aclose.assert_awaited_once()
    assert arm_client._client is None


async def test_close_client_already_none():
    arm_client._client = None
    await arm_client.close_client()  # should not raise


# --- _parse_error_response ---


def test_parse_error_response_with_detail():
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 400
    resp.json.return_value = {"detail": "Bad request data"}
    result = arm_client._parse_error_response(resp)
    assert result["success"] is False
    assert "Bad request data" in result["error"]


def test_parse_error_response_with_error_key():
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 404
    resp.json.return_value = {"error": "Not found"}
    result = arm_client._parse_error_response(resp)
    assert "Not found" in result["error"]


def test_parse_error_response_with_Error_key():
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 500
    resp.json.return_value = {"Error": "Internal failure"}
    result = arm_client._parse_error_response(resp)
    assert "Internal failure" in result["error"]


def test_parse_error_response_no_known_keys():
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 422
    resp.json.return_value = {"foo": "bar"}
    result = arm_client._parse_error_response(resp)
    assert "422" in result["error"]


def test_parse_error_response_non_json():
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 503
    resp.json.side_effect = Exception("not json")
    result = arm_client._parse_error_response(resp)
    assert "503" in result["error"]


# --- cancel_waiting_job ---


async def test_cancel_waiting_job_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({"success": True})
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.cancel_waiting_job(5)
    assert result == {"success": True}
    mock_client.request.assert_awaited_once_with("POST", "/api/v1/jobs/5/cancel")


async def test_cancel_waiting_job_offline():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.side_effect = httpx.ConnectError("refused")
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.cancel_waiting_job(5)
    assert result is None


# --- delete_job ---


async def test_delete_job_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({"success": True})
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.delete_job(10)
    assert result == {"success": True}
    mock_client.request.assert_awaited_once_with("DELETE", "/api/v1/jobs/10")


# --- fix_permissions ---


async def test_fix_permissions_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({"success": True})
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.fix_permissions(1)
    assert result == {"success": True}
    mock_client.request.assert_awaited_once_with("POST", "/api/v1/jobs/1/fix-permissions")


# --- update_job_config ---


async def test_update_job_config_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({"success": True})
    data = {"RIPMETHOD": "backup"}
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.update_job_config(1, data)
    assert result == {"success": True}
    mock_client.request.assert_awaited_once_with("PATCH", "/api/v1/jobs/1/config", json=data)


# --- start_waiting_job ---


async def test_start_waiting_job_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({"success": True})
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.start_waiting_job(7)
    assert result == {"success": True}
    mock_client.request.assert_awaited_once_with("POST", "/api/v1/jobs/7/start")


# --- get_system_info ---


async def test_get_system_info_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({"cpu": "Intel"})
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.get_system_info()
    assert result == {"cpu": "Intel"}


async def test_get_system_info_offline():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.side_effect = httpx.ConnectError("refused")
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.get_system_info()
    assert result is None


# --- get_system_stats ---


async def test_get_system_stats_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({"cpu_percent": 50})
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.get_system_stats()
    assert result == {"cpu_percent": 50}


# --- get_version ---


async def test_get_version_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({"arm_version": "10.2.0"})
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.get_version()
    assert result == {"arm_version": "10.2.0"}


async def test_get_version_offline():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.side_effect = httpx.TimeoutException("timed out")
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.get_version()
    assert result is None


# --- get_paths ---


async def test_get_paths_success():
    data = [{"path": "/media/raw", "exists": True}]
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response(data)
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.get_paths()
    assert result == data


async def test_get_paths_offline():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.ConnectError("refused")
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.get_paths()
    assert result is None


async def test_get_paths_http_error():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response({}, status_code=500)
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.get_paths()
    assert result is None


# --- send_to_crc_db ---


async def test_send_to_crc_db_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({"success": True})
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.send_to_crc_db(1)
    assert result == {"success": True}
    mock_client.request.assert_awaited_once_with("POST", "/api/v1/jobs/1/send")


# --- tvdb_match ---


async def test_tvdb_match_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({"matched": 5})
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.tvdb_match(1, {"series_id": 123})
    assert result == {"matched": 5}
    mock_client.request.assert_awaited_once_with(
        "POST", "/api/v1/jobs/1/tvdb-match", json={"series_id": 123}
    )


# --- tvdb_episodes ---


async def test_tvdb_episodes_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({"episodes": []})
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.tvdb_episodes(1, season=2)
    assert result == {"episodes": []}
    mock_client.request.assert_awaited_once_with(
        "GET", "/api/v1/jobs/1/tvdb-episodes", params={"season": "2"}
    )


# --- File browser functions ---


async def test_get_file_roots_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response([{"path": "/media"}])
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.get_file_roots()
    assert result == [{"path": "/media"}]


async def test_get_file_roots_offline():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.side_effect = httpx.ConnectError("refused")
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.get_file_roots()
    assert result is None


async def test_list_files_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({"entries": [{"name": "movie.mkv"}]})
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.list_files("/media/raw")
    assert result == {"entries": [{"name": "movie.mkv"}]}
    mock_client.request.assert_awaited_once_with(
        "GET", "/api/v1/files/list", params={"path": "/media/raw"}
    )


async def test_rename_file_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({"success": True})
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.rename_file("/media/old.mkv", "new.mkv")
    assert result == {"success": True}


async def test_move_file_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({"success": True})
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.move_file("/media/file.mkv", "/completed/")
    assert result == {"success": True}


async def test_create_directory_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({"success": True})
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.create_directory("/media", "new_folder")
    assert result == {"success": True}


async def test_fix_file_permissions_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({"success": True})
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.fix_file_permissions("/media/file.mkv")
    assert result == {"success": True}


async def test_delete_file_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({"success": True})
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.delete_file("/media/file.mkv")
    assert result == {"success": True}


# --- dismiss_notification ---


async def test_dismiss_notification_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({"success": True})
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.dismiss_notification(42)
    assert result == {"success": True}
    mock_client.request.assert_awaited_once_with("PATCH", "/api/v1/notifications/42")


async def test_dismiss_notification_offline():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.side_effect = httpx.ConnectError("refused")
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.dismiss_notification(42)
    assert result is None


# --- scan_drive ---


async def test_scan_drive_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({"success": True})
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.scan_drive(1)
    assert result == {"success": True}


# --- drive_diagnostic ---


async def test_drive_diagnostic_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({"drives": []})
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.drive_diagnostic()
    assert result == {"drives": []}


# --- delete_drive ---


async def test_delete_drive_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({"success": True})
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.delete_drive(1)
    assert result == {"success": True}


# --- update_config ---


async def test_update_config_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({"success": True})
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.update_config({"RIPMETHOD": "backup"})
    assert result == {"success": True}
    mock_client.request.assert_awaited_once_with(
        "PUT", "/api/v1/settings/config", json={"config": {"RIPMETHOD": "backup"}}
    )
