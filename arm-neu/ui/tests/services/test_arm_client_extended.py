"""Tests for arm_client: multi-title, track title, set_job_tracks, abcde config."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx

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


# --- toggle_multi_title ---


async def test_toggle_multi_title_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({"success": True, "multi_title": True})
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.toggle_multi_title(1, {"enabled": True})
    assert result == {"success": True, "multi_title": True}
    mock_client.request.assert_awaited_once_with(
        "POST", "/api/v1/jobs/1/multi-title", json={"enabled": True}
    )


async def test_toggle_multi_title_connect_error():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.side_effect = httpx.ConnectError("refused")
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.toggle_multi_title(1, {"enabled": True})
    assert result is None


# --- update_track_title ---


async def test_update_track_title_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({"success": True, "updated": {"title": "X"}})
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.update_track_title(1, 5, {"title": "X"})
    assert result["success"] is True
    mock_client.request.assert_awaited_once_with(
        "PUT", "/api/v1/jobs/1/tracks/5/title", json={"title": "X"}
    )


async def test_update_track_title_connect_error():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.side_effect = httpx.ConnectError("refused")
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.update_track_title(1, 5, {"title": "X"})
    assert result is None


# --- clear_track_title ---


async def test_clear_track_title_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({"success": True})
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.clear_track_title(1, 5)
    assert result == {"success": True}
    mock_client.request.assert_awaited_once_with(
        "DELETE", "/api/v1/jobs/1/tracks/5/title"
    )


async def test_clear_track_title_connect_error():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.side_effect = httpx.ConnectError("refused")
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.clear_track_title(1, 5)
    assert result is None


# --- set_job_tracks ---


async def test_set_job_tracks_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({"success": True})
    tracks = [{"track_number": "1", "title": "Track 1"}]
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.set_job_tracks(1, tracks)
    assert result == {"success": True}
    mock_client.request.assert_awaited_once_with(
        "PUT", "/api/v1/jobs/1/tracks", json={"tracks": tracks}
    )


async def test_set_job_tracks_connect_error():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.side_effect = httpx.ConnectError("refused")
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.set_job_tracks(1, [])
    assert result is None


# --- update_abcde_config ---


async def test_update_abcde_config_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({"success": True})
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.update_abcde_config("OUTPUTTYPE=flac\n")
    assert result == {"success": True}
    mock_client.request.assert_awaited_once_with(
        "PUT", "/api/v1/settings/abcde", json={"content": "OUTPUTTYPE=flac\n"}
    )


async def test_update_abcde_config_connect_error():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.side_effect = httpx.ConnectError("refused")
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.update_abcde_config("content")
    assert result is None


# --- get_abcde_config ---


async def test_get_abcde_config_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response(
        {"content": "# abcde.conf", "path": "/etc/abcde.conf", "exists": True}
    )
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.get_abcde_config()
    assert result["exists"] is True
    assert result["content"] == "# abcde.conf"


# --- naming_preview ---


async def test_naming_preview_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({"result": "Movie (2024)"})
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.naming_preview("{title} ({year})", {"title": "Movie", "year": "2024"})
    assert result["result"] == "Movie (2024)"
    mock_client.request.assert_awaited_once_with(
        "POST", "/api/v1/naming/preview",
        json={"pattern": "{title} ({year})", "variables": {"title": "Movie", "year": "2024"}},
    )


# --- update_job_naming ---


async def test_update_job_naming_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({
        "success": True, "title_pattern_override": "{title} - E{episode}", "folder_pattern_override": None
    })
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.update_job_naming(1, {"title_pattern_override": "{title} - E{episode}"})
    assert result["success"] is True
    assert result["title_pattern_override"] == "{title} - E{episode}"
    mock_client.request.assert_awaited_once_with(
        "PATCH", "/api/v1/jobs/1/naming",
        json={"title_pattern_override": "{title} - E{episode}"},
    )


# --- validate_naming_pattern ---


async def test_validate_naming_pattern_invalid():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({
        "valid": False, "invalid_vars": ["episde"], "suggestions": {"episde": "episode"}
    })
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.validate_naming_pattern("{title} {episde}")
    assert result["valid"] is False
    assert "episde" in result["invalid_vars"]


# --- get_naming_variables ---


async def test_get_naming_variables():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({
        "variables": ["album", "artist", "episode", "label", "season", "title", "video_type", "year"],
        "descriptions": {"title": "Disc title"}
    })
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.get_naming_variables()
    assert len(result["variables"]) == 8
    assert "title" in result["variables"]


# --- Logs API client wrappers ---


async def test_list_logs_proxies_to_api():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response([{"filename": "a.log", "size": 1, "modified": "x"}])
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.list_logs()
    assert result[0]["filename"] == "a.log"
    mock_client.request.assert_called_once_with("GET", "/api/v1/logs")


async def test_read_log_proxies_with_params():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({"filename": "a.log", "content": "x", "lines": 1})
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.read_log("a.log", mode="full", lines=42)
    assert result["lines"] == 1
    args, kwargs = mock_client.request.call_args
    assert args == ("GET", "/api/v1/logs/a.log")
    assert kwargs["params"] == {"mode": "full", "lines": "42"}


async def test_read_log_structured_omits_unset_filters():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({"filename": "a.log", "entries": [], "lines": 0})
    with patch.object(arm_client, "get_client", return_value=mock_client):
        await arm_client.read_log_structured("a.log")
    _, kwargs = mock_client.request.call_args
    assert "level" not in kwargs["params"]
    assert "search" not in kwargs["params"]


async def test_read_log_structured_includes_filters():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({"filename": "a.log", "entries": [], "lines": 0})
    with patch.object(arm_client, "get_client", return_value=mock_client):
        await arm_client.read_log_structured("a.log", level="error", search="boom")
    _, kwargs = mock_client.request.call_args
    assert kwargs["params"]["level"] == "error"
    assert kwargs["params"]["search"] == "boom"


async def test_delete_log_proxies():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({"success": True, "filename": "a.log"})
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.delete_log("a.log")
    assert result["success"] is True
    mock_client.request.assert_called_once_with("DELETE", "/api/v1/logs/a.log")


async def test_log_filename_is_url_encoded():
    """Defence in depth: a malicious filename can't escape the /logs/ subtree."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({"filename": "x", "content": "", "lines": 0})
    with patch.object(arm_client, "get_client", return_value=mock_client):
        await arm_client.read_log("../etc/passwd")
    args, _ = mock_client.request.call_args
    # `/` and `.` percent-encoded; result is contained under /api/v1/logs/
    assert args[1] == "/api/v1/logs/..%2Fetc%2Fpasswd"


async def test_stream_log_download_returns_response():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    fake_resp = MagicMock(spec=httpx.Response)
    fake_resp.status_code = 200
    mock_client.build_request = MagicMock(return_value=MagicMock())
    mock_client.send = AsyncMock(return_value=fake_resp)
    with patch.object(arm_client, "get_client", return_value=mock_client):
        resp = await arm_client.stream_log_download("a.log")
    assert resp.status_code == 200
    args, kwargs = mock_client.build_request.call_args
    assert args == ("GET", "/api/v1/logs/a.log/download")


async def test_stream_log_download_handles_unreachable():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.build_request = MagicMock(return_value=MagicMock())
    mock_client.send = AsyncMock(side_effect=httpx.ConnectError("nope"))
    with patch.object(arm_client, "get_client", return_value=mock_client):
        resp = await arm_client.stream_log_download("a.log")
    assert resp is None


# --- scan_iso ---


async def test_scan_iso_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({
        "success": True,
        "disc_type": "dvd",
        "label": "MOVIE_DISC",
        "title_suggestion": "Movie",
        "year_suggestion": "2024",
        "iso_size": 4700000000,
        "stream_count": 1,
    })
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.scan_iso("/ingress/movie.iso")
    assert result["success"] is True
    assert result["disc_type"] == "dvd"
    mock_client.request.assert_awaited_once_with(
        "POST", "/api/v1/jobs/iso/scan", json={"path": "/ingress/movie.iso"}
    )


async def test_scan_iso_connect_error():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.side_effect = httpx.ConnectError("refused")
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.scan_iso("/ingress/movie.iso")
    assert result is None


# --- create_iso_job ---


async def test_create_iso_job_success():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.return_value = _mock_response({
        "success": True,
        "job_id": 42,
        "status": "identifying",
        "source_type": "iso",
        "source_path": "/ingress/movie.iso",
    })
    payload = {
        "source_path": "/ingress/movie.iso",
        "title": "Movie",
        "year": "2024",
        "video_type": "movie",
        "disctype": "dvd",
    }
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.create_iso_job(payload)
    assert result["job_id"] == 42
    assert result["source_type"] == "iso"
    mock_client.request.assert_awaited_once_with(
        "POST", "/api/v1/jobs/iso", json=payload
    )


async def test_create_iso_job_connect_error():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request.side_effect = httpx.ConnectError("refused")
    with patch.object(arm_client, "get_client", return_value=mock_client):
        result = await arm_client.create_iso_job({"source_path": "/x.iso"})
    assert result is None
