"""Tests for transcoder_client: health, get_job, jobs, stats, logs, config, etc."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from backend.services import transcoder_client


def _mock_response(json_data: dict | list, status_code: int = 200) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    return resp


# --- get_client ---


def test_get_client_creates_new_client():
    """get_client creates a new AsyncClient when none exists."""
    transcoder_client._client = None
    client = transcoder_client.get_client()
    assert isinstance(client, httpx.AsyncClient)


def test_get_client_reuses_existing():
    """get_client returns the same client on subsequent calls."""
    transcoder_client._client = None
    c1 = transcoder_client.get_client()
    c2 = transcoder_client.get_client()
    assert c1 is c2


def test_get_client_recreates_if_closed():
    """get_client creates new client if existing one is closed."""
    mock_closed = MagicMock(spec=httpx.AsyncClient)
    mock_closed.is_closed = True
    transcoder_client._client = mock_closed
    client = transcoder_client.get_client()
    assert client is not mock_closed


# --- close_client ---


async def test_close_client():
    """close_client closes the client and sets it to None."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.is_closed = False
    transcoder_client._client = mock_client
    await transcoder_client.close_client()
    mock_client.aclose.assert_awaited_once()
    assert transcoder_client._client is None


async def test_close_client_already_closed():
    """close_client does nothing if client is already closed."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.is_closed = True
    transcoder_client._client = mock_client
    await transcoder_client.close_client()
    mock_client.aclose.assert_not_awaited()


async def test_close_client_none():
    """close_client does nothing if no client exists."""
    transcoder_client._client = None
    await transcoder_client.close_client()  # should not raise


# --- health ---


async def test_health_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response({"status": "healthy"})
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.health()
    assert result == {"status": "healthy"}


async def test_health_connect_error():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.ConnectError("refused")
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.health()
    assert result is None


async def test_health_http_error():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response({}, status_code=500)
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.health()
    assert result is None


async def test_health_runtime_error():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = RuntimeError("event loop closed")
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.health()
    assert result is None


# --- get_job ---


async def test_get_job_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response({"jobs": [{"id": 42, "status": "completed"}], "total": 1})
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.get_job(42)
    assert result == {"id": 42, "status": "completed"}
    mock_client.get.assert_awaited_once_with("/jobs", params={"job_id": 42, "limit": 1})


async def test_get_job_not_found():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response({"jobs": [], "total": 0})
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.get_job(999)
    assert result is None


async def test_get_job_connect_error():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.ConnectError("refused")
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.get_job(42)
    assert result is None


# --- get_system_info ---


async def test_get_system_info_success():
    data = {"cpu": "Intel i7", "ram": "16GB"}
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response(data)
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.get_system_info()
    assert result == data
    mock_client.get.assert_awaited_once_with("/system/info")


async def test_get_system_info_offline():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.ConnectError("refused")
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.get_system_info()
    assert result is None


# --- get_system_stats ---


async def test_get_system_stats_success():
    data = {"cpu_percent": 45.2, "temperature": 72}
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response(data)
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.get_system_stats()
    assert result == data
    mock_client.get.assert_awaited_once_with("/system/stats")


async def test_get_system_stats_offline():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = OSError("network down")
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.get_system_stats()
    assert result is None


# --- get_scheme ---


async def test_get_scheme_success():
    data = {"slug": "default", "name": "Default Scheme", "presets": []}
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response(data)
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.get_scheme()
    assert result == data
    mock_client.get.assert_awaited_once_with("/api/v1/scheme")


async def test_get_scheme_offline():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.ConnectError("refused")
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.get_scheme()
    assert result is None


# --- get_presets ---


async def test_get_presets_success():
    data = {"presets": [{"slug": "hq-1080p", "name": "HQ 1080p"}]}
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response(data)
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.get_presets()
    assert result == data
    mock_client.get.assert_awaited_once_with("/api/v1/presets")


async def test_get_presets_offline():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.ConnectError("refused")
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.get_presets()
    assert result is None


# --- get_config ---


async def test_get_config_success():
    data = {"config": {"video_encoder": "x265"}, "updatable_keys": ["video_encoder"]}
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response(data)
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.get_config()
    assert result == data


async def test_get_config_offline():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.ConnectError("refused")
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.get_config()
    assert result is None


# --- update_config ---


async def test_update_config_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.patch.return_value = _mock_response({"success": True})
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.update_config({"video_encoder": "nvenc_h265"})
    assert result == {"success": True}
    mock_client.patch.assert_awaited_once_with(
        "/config", json={"video_encoder": "nvenc_h265"}
    )


async def test_update_config_offline():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.patch.side_effect = httpx.ConnectError("refused")
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.update_config({"video_encoder": "x265"})
    assert result is None


async def test_update_config_raises_on_4xx():
    """4xx/5xx responses should raise HTTPStatusError (not swallowed to None)."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.patch.return_value = _mock_response(
        {"detail": "global_overrides must be a string"}, status_code=422
    )
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        with pytest.raises(httpx.HTTPStatusError):
            await transcoder_client.update_config(
                {"global_overrides": {"shared": {}, "tiers": {}}}
            )


# --- get_jobs ---


async def test_get_jobs_success():
    data = {"jobs": [{"id": 1}], "total": 1}
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response(data)
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.get_jobs()
    assert result == data


async def test_get_jobs_with_filters():
    data = {"jobs": [], "total": 0}
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response(data)
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.get_jobs(
            status="completed", limit=10, offset=5, job_id=42
        )
    assert result == data
    call_kwargs = mock_client.get.call_args
    params = call_kwargs[1]["params"]
    assert params["status"] == "completed"
    assert params["limit"] == 10
    assert params["offset"] == 5
    assert params["job_id"] == 42


async def test_get_jobs_no_status_or_job_id():
    """get_jobs excludes status and job_id when not provided."""
    data = {"jobs": [], "total": 0}
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response(data)
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.get_jobs(limit=25, offset=0)
    call_kwargs = mock_client.get.call_args
    params = call_kwargs[1]["params"]
    assert "status" not in params
    assert "job_id" not in params


async def test_get_jobs_offline():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.ConnectError("refused")
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.get_jobs()
    assert result is None


# --- get_stats ---


async def test_get_stats_success():
    data = {"total": 100, "completed": 80}
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response(data)
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.get_stats()
    assert result == data
    mock_client.get.assert_awaited_once_with("/stats")


async def test_get_stats_offline():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.ConnectError("refused")
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.get_stats()
    assert result is None


# --- retry_job ---


async def test_retry_job_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = _mock_response({"success": True, "id": 42})
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.retry_job(42)
    assert result == {"success": True, "id": 42}
    mock_client.post.assert_awaited_once_with("/jobs/42/retry")


async def test_retry_job_offline():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.side_effect = httpx.ConnectError("refused")
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.retry_job(42)
    assert result is None


async def test_retry_job_http_error():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = _mock_response({}, status_code=404)
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.retry_job(999)
    assert result is None


# --- delete_job ---


async def test_delete_job_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.delete.return_value = _mock_response({})
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.delete_job(42)
    assert result is True
    mock_client.delete.assert_awaited_once_with("/jobs/42")


async def test_delete_job_offline():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.delete.side_effect = httpx.ConnectError("refused")
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.delete_job(42)
    assert result is False


async def test_delete_job_http_error():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.delete.return_value = _mock_response({}, status_code=404)
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.delete_job(999)
    assert result is False


# --- list_logs ---


async def test_list_logs_success():
    data = [{"filename": "transcoder.log", "size": 1024}]
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response(data)
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.list_logs()
    assert result == data
    mock_client.get.assert_awaited_once_with("/logs")


async def test_list_logs_offline():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.ConnectError("refused")
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.list_logs()
    assert result is None


# --- read_log ---


async def test_read_log_success():
    data = {"content": "log line 1\nlog line 2", "filename": "transcoder.log"}
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response(data)
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.read_log("transcoder.log")
    assert result == data
    mock_client.get.assert_awaited_once_with(
        "/logs/transcoder.log", params={"mode": "tail", "lines": 100}
    )


async def test_read_log_custom_params():
    data = {"content": "full log", "filename": "transcoder.log"}
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response(data)
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.read_log("transcoder.log", mode="full", lines=500)
    mock_client.get.assert_awaited_once_with(
        "/logs/transcoder.log", params={"mode": "full", "lines": 500}
    )


async def test_read_log_offline():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.ConnectError("refused")
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.read_log("transcoder.log")
    assert result is None


# --- read_structured_log ---


async def test_read_structured_log_success():
    data = {"entries": [{"level": "INFO", "message": "Started"}]}
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response(data)
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.read_structured_log("transcoder.log")
    assert result == data
    mock_client.get.assert_awaited_once_with(
        "/logs/transcoder.log/structured", params={"mode": "tail", "lines": 100}
    )


async def test_read_structured_log_with_filters():
    data = {"entries": []}
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response(data)
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.read_structured_log(
            "transcoder.log", mode="full", lines=200, level="ERROR", search="failed"
        )
    call_kwargs = mock_client.get.call_args
    params = call_kwargs[1]["params"]
    assert params["mode"] == "full"
    assert params["lines"] == 200
    assert params["level"] == "ERROR"
    assert params["search"] == "failed"


async def test_read_structured_log_no_optional_filters():
    """level and search are excluded when not provided."""
    data = {"entries": []}
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response(data)
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        await transcoder_client.read_structured_log("transcoder.log")
    call_kwargs = mock_client.get.call_args
    params = call_kwargs[1]["params"]
    assert "level" not in params
    assert "search" not in params


async def test_read_structured_log_offline():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.ConnectError("refused")
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.read_structured_log("transcoder.log")
    assert result is None


# --- test_connection edge cases ---


async def test_test_connection_health_timeout():
    """test_connection handles TimeoutException."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.TimeoutException("timed out")
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.test_connection()
    assert result["reachable"] is False
    assert "failed" in result["error"].lower()


async def test_test_connection_health_http_error():
    """test_connection handles non-connect HTTP errors at health step."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response({}, status_code=500)
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.test_connection()
    assert result["reachable"] is False
    assert "failed" in result["error"].lower()


async def test_test_connection_config_non_auth_error():
    """test_connection handles non-401/403 config errors."""
    health_data = {"status": "healthy", "worker_running": True, "queue_size": 0, "gpu_support": {}, "require_api_auth": False}
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    health_resp = _mock_response(health_data)
    config_resp = _mock_response({}, status_code=500)
    mock_client.get.side_effect = [health_resp, config_resp]

    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.test_connection()
    assert result["reachable"] is True
    assert "Config check failed" in result["error"]


async def test_test_connection_config_lost_connection():
    """test_connection handles ConnectError during config check."""
    health_data = {"status": "healthy", "worker_running": True, "queue_size": 0, "gpu_support": {}, "require_api_auth": False}
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    health_resp = _mock_response(health_data)
    mock_client.get.side_effect = [health_resp, httpx.ConnectError("lost")]

    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.test_connection()
    assert result["reachable"] is True
    assert "Lost connection" in result["error"]


# --- test_webhook edge cases ---


async def test_test_webhook_http_error():
    """test_webhook handles generic HTTP errors."""
    with patch("backend.services.transcoder_client.httpx.AsyncClient") as MockClient:
        ctx = AsyncMock()
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = httpx.HTTPError("server error")
        ctx.post.side_effect = httpx.HTTPError("server error")
        MockClient.return_value.__aenter__ = AsyncMock(return_value=ctx)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await transcoder_client.test_webhook("secret")

    assert result["reachable"] is True
    assert "failed" in result["error"].lower()


# --- restart_transcoder ---


async def test_restart_transcoder_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    resp = MagicMock(spec=httpx.Response)
    resp.is_success = True
    resp.json.return_value = {"success": True, "message": "Transcoder is restarting"}
    mock_client.post.return_value = resp
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.restart_transcoder()
    assert result["success"] is True
    mock_client.post.assert_awaited_once_with("/system/restart")


async def test_restart_transcoder_http_error():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    resp = MagicMock(spec=httpx.Response)
    resp.is_success = False
    resp.status_code = 500
    mock_client.post.return_value = resp
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.restart_transcoder()
    assert result["success"] is False


async def test_restart_transcoder_unreachable():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.side_effect = httpx.ConnectError("refused")
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.restart_transcoder()
    assert result is None


# --- create_preset ---


async def test_create_preset_returns_response_on_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = _mock_response({"slug": "my-preset", "name": "My Preset"})
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.create_preset({"name": "My Preset", "parent_slug": "x"})
    assert result == {"slug": "my-preset", "name": "My Preset"}
    mock_client.post.assert_awaited_once_with(
        "/api/v1/presets", json={"name": "My Preset", "parent_slug": "x"}
    )


async def test_create_preset_returns_none_on_offline():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.side_effect = httpx.ConnectError("connection refused")
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.create_preset({"name": "x", "parent_slug": "y"})
    assert result is None


async def test_create_preset_raises_on_4xx():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post.return_value = _mock_response({"detail": "Slug exists"}, status_code=409)
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        with pytest.raises(httpx.HTTPStatusError):
            await transcoder_client.create_preset({"name": "x", "parent_slug": "y"})


# --- update_preset ---


async def test_update_preset_returns_response_on_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.patch.return_value = _mock_response({"slug": "my-preset", "name": "Updated"})
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.update_preset("my-preset", {"name": "Updated"})
    assert result == {"slug": "my-preset", "name": "Updated"}
    mock_client.patch.assert_awaited_once_with(
        "/api/v1/presets/my-preset", json={"name": "Updated"}
    )


async def test_update_preset_returns_none_on_offline():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.patch.side_effect = httpx.ConnectError("nope")
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.update_preset("x", {})
    assert result is None


async def test_update_preset_raises_on_4xx():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.patch.return_value = _mock_response({"detail": "Preset not found"}, status_code=404)
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        with pytest.raises(httpx.HTTPStatusError):
            await transcoder_client.update_preset("missing-slug", {"name": "x"})


# --- delete_preset ---


async def test_delete_preset_returns_response_on_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.delete.return_value = _mock_response({"success": True, "deleted": "my-preset"})
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.delete_preset("my-preset")
    assert result == {"success": True, "deleted": "my-preset"}
    mock_client.delete.assert_awaited_once_with("/api/v1/presets/my-preset")


async def test_delete_preset_returns_none_on_offline():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.delete.side_effect = httpx.ConnectError("nope")
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.delete_preset("x")
    assert result is None


async def test_delete_preset_raises_on_4xx():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.delete.return_value = _mock_response({"detail": "Preset not found"}, status_code=404)
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        with pytest.raises(httpx.HTTPStatusError):
            await transcoder_client.delete_preset("missing-slug")


# --- slug validation (SSRF protection) ---


@pytest.mark.parametrize("bad_slug", [
    "../admin",
    "preset/../other",
    "preset?query=1",
    "preset with spaces",
    "Preset-Uppercase",
    "-leading-dash",
    "trailing-dash-",
    "double--dash",
    "",
    "a" * 101,
    "preset#fragment",
    "preset%2e%2e",
])
async def test_update_preset_rejects_malicious_slug(bad_slug):
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        with pytest.raises(ValueError, match="Invalid preset slug"):
            await transcoder_client.update_preset(bad_slug, {"name": "x"})
    mock_client.patch.assert_not_called()


@pytest.mark.parametrize("bad_slug", [
    "../admin",
    "preset/../other",
    "preset?query=1",
    "Preset-Uppercase",
    "",
])
async def test_delete_preset_rejects_malicious_slug(bad_slug):
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        with pytest.raises(ValueError, match="Invalid preset slug"):
            await transcoder_client.delete_preset(bad_slug)
    mock_client.delete.assert_not_called()


@pytest.mark.parametrize("good_slug", [
    "nvidia-balanced",
    "my-anime-preset",
    "a",
    "preset123",
    "slug-with-9-digits",
])
async def test_update_preset_accepts_valid_slug(good_slug):
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.patch.return_value = _mock_response({"slug": good_slug})
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.update_preset(good_slug, {"name": "x"})
    assert result == {"slug": good_slug}
    mock_client.patch.assert_awaited_once_with(
        f"/api/v1/presets/{good_slug}", json={"name": "x"}
    )
