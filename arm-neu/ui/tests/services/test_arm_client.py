"""Tests for backend.services.arm_client — HTTP method patterns and error handling."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from backend.services import arm_client


def _mock_response(json_data, status_code: int = 200) -> MagicMock:
    """Create a mock httpx.Response."""
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


@pytest.fixture()
def mock_client():
    """Yield a patched AsyncMock httpx client and wire it into arm_client."""
    client = AsyncMock(spec=httpx.AsyncClient)
    with patch.object(arm_client, "get_client", return_value=client):
        yield client


def _set_request_response(client, json_data, status_code=200):
    """Configure the mock client.request to return a mock response."""
    client.request.return_value = _mock_response(json_data, status_code)


def _set_request_connect_error(client):
    """Configure the mock client.request to raise ConnectError."""
    client.request.side_effect = httpx.ConnectError("refused")


def _set_get_response(client, json_data, status_code=200):
    """Configure the mock client.get to return a mock response."""
    client.get.return_value = _mock_response(json_data, status_code)


def _set_get_connect_error(client):
    """Configure the mock client.get to raise ConnectError."""
    client.get.side_effect = httpx.ConnectError("refused")


# --- abandon_job (uses _request) ---


async def test_abandon_job_success(mock_client):
    """abandon_job returns JSON on success."""
    _set_request_response(mock_client, {"success": True})
    result = await arm_client.abandon_job(42)
    assert result == {"success": True}
    mock_client.request.assert_awaited_once_with("POST", "/api/v1/jobs/42/abandon")


async def test_abandon_job_connect_error(mock_client):
    """abandon_job returns None on ConnectError."""
    _set_request_connect_error(mock_client)
    assert await arm_client.abandon_job(42) is None


# --- _request empty-body handling (204 No Content) ---


async def test_request_handles_204_empty_body():
    """A 204 with an empty body returns {} (not None, no JSONDecodeError).

    arm-neu's DELETE /notifications/channels/{id} returns 204 No Content.
    Calling resp.json() on the empty body would raise JSONDecodeError and
    crash the BFF with HTTP 500. Returning {} keeps the None=unreachable
    sentinel intact while signalling success.
    """
    resp = MagicMock()
    resp.is_success = True
    resp.status_code = 204
    resp.content = b""
    fake_client = MagicMock()
    fake_client.request = AsyncMock(return_value=resp)
    with patch.object(arm_client, "get_client", return_value=fake_client):
        out = await arm_client._request(
            "DELETE", "/api/v1/notifications/channels/1"
        )
    assert out == {}


async def test_request_parses_json_on_200():
    """A normal 200 with a JSON body is still parsed and returned."""
    resp = MagicMock()
    resp.is_success = True
    resp.status_code = 200
    resp.content = b'{"ok": true}'
    resp.json = MagicMock(return_value={"ok": True})
    fake_client = MagicMock()
    fake_client.request = AsyncMock(return_value=resp)
    with patch.object(arm_client, "get_client", return_value=fake_client):
        out = await arm_client._request("GET", "/x")
    assert out == {"ok": True}


# --- skip_and_finalize ---


async def test_skip_and_finalize_success(mock_client):
    """skip_and_finalize returns JSON on success."""
    _set_request_response(mock_client, {"success": True, "message": "Job finalized"})
    result = await arm_client.skip_and_finalize(7)
    assert result == {"success": True, "message": "Job finalized"}
    mock_client.request.assert_awaited_once_with("POST", "/api/v1/jobs/7/skip-and-finalize")


async def test_skip_and_finalize_connect_error(mock_client):
    """skip_and_finalize returns None on ConnectError."""
    _set_request_connect_error(mock_client)
    assert await arm_client.skip_and_finalize(7) is None


# --- force_complete ---


async def test_force_complete_success(mock_client):
    """force_complete returns JSON on success."""
    _set_request_response(mock_client, {"success": True, "message": "Job marked as complete"})
    result = await arm_client.force_complete(7)
    assert result == {"success": True, "message": "Job marked as complete"}
    mock_client.request.assert_awaited_once_with("POST", "/api/v1/jobs/7/force-complete")


async def test_force_complete_connect_error(mock_client):
    """force_complete returns None on ConnectError."""
    _set_request_connect_error(mock_client)
    assert await arm_client.force_complete(7) is None


# --- get_config ---


async def test_get_config_success(mock_client):
    """get_config returns JSON on success."""
    _set_request_response(mock_client, {"RIPMETHOD": "mkv"})
    result = await arm_client.get_config()
    assert result == {"RIPMETHOD": "mkv"}


async def test_get_config_http_error(mock_client):
    """get_config returns error dict on HTTP 500 (not None)."""
    _set_request_response(mock_client, {"error": "Internal error"}, status_code=500)
    result = await arm_client.get_config()
    assert result is not None
    assert result["success"] is False
    assert "500" in result["error"]


# --- update_title ---


async def test_update_title_success(mock_client):
    """update_title sends PUT with JSON body."""
    _set_request_response(mock_client, {"success": True})
    data = {"title": "New Title", "year": "2024"}
    result = await arm_client.update_title(1, data)
    assert result == {"success": True}
    mock_client.request.assert_awaited_once_with(
        "PUT", "/api/v1/jobs/1/title", json=data
    )


async def test_update_title_connect_error(mock_client):
    """update_title returns None on ConnectError."""
    _set_request_connect_error(mock_client)
    assert await arm_client.update_title(1, {"title": "X"}) is None


# --- set_ripping_enabled ---


async def test_set_ripping_enabled_success(mock_client):
    """set_ripping_enabled sends POST with JSON body."""
    _set_request_response(mock_client, {"success": True})
    result = await arm_client.set_ripping_enabled(True)
    assert result == {"success": True}
    mock_client.request.assert_awaited_once_with(
        "POST", "/api/v1/system/ripping-enabled", json={"enabled": True}
    )


async def test_set_ripping_enabled_connect_error(mock_client):
    """set_ripping_enabled returns None on ConnectError."""
    _set_request_connect_error(mock_client)
    assert await arm_client.set_ripping_enabled(False) is None


# --- update_drive ---


async def test_update_drive_success(mock_client):
    """update_drive sends PATCH with JSON body."""
    _set_request_response(mock_client, {"success": True})
    result = await arm_client.update_drive(3, {"name": "Drive A"})
    assert result == {"success": True}
    mock_client.request.assert_awaited_once_with(
        "PATCH", "/api/v1/drives/3", json={"name": "Drive A"}
    )


async def test_update_drive_http_error(mock_client):
    """update_drive returns error dict on HTTP 404."""
    _set_request_response(mock_client, {"error": "Not found"}, status_code=404)
    result = await arm_client.update_drive(3, {"name": "X"})
    assert result is not None
    assert result["success"] is False


# --- pause_waiting_job ---


async def test_pause_waiting_job_success(mock_client):
    """pause_waiting_job returns JSON on success."""
    _set_request_response(mock_client, {"success": True, "paused": True})
    result = await arm_client.pause_waiting_job(42)
    assert result == {"success": True, "paused": True}
    mock_client.request.assert_awaited_once_with("POST", "/api/v1/jobs/42/pause")


async def test_pause_waiting_job_connect_error(mock_client):
    """pause_waiting_job returns None on ConnectError."""
    _set_request_connect_error(mock_client)
    assert await arm_client.pause_waiting_job(42) is None


# --- search_metadata (direct httpx, not _request) ---


async def test_search_metadata_success(mock_client):
    """search_metadata returns list of results."""
    _set_get_response(mock_client, [{"title": "Matrix", "year": "1999"}])
    result = await arm_client.search_metadata("Matrix")
    assert result == [{"title": "Matrix", "year": "1999"}]
    call_kwargs = mock_client.get.call_args
    assert "year" not in call_kwargs[1].get("params", {})


async def test_search_metadata_with_year(mock_client):
    """search_metadata includes year param when provided."""
    _set_get_response(mock_client, [])
    await arm_client.search_metadata("Matrix", year="1999")
    call_kwargs = mock_client.get.call_args
    assert call_kwargs[1]["params"]["year"] == "1999"


async def test_search_metadata_raises_on_error(mock_client):
    """search_metadata raises HTTPStatusError on 5xx."""
    _set_get_response(mock_client, {}, status_code=503)
    with pytest.raises(httpx.HTTPStatusError):
        await arm_client.search_metadata("Matrix")


# --- get_media_detail ---


async def test_get_media_detail_success(mock_client):
    """get_media_detail returns detail dict on 200."""
    _set_get_response(mock_client, {"title": "Matrix", "imdb_id": "tt0133093"})
    result = await arm_client.get_media_detail("tt0133093")
    assert result["title"] == "Matrix"


async def test_get_media_detail_404_returns_none(mock_client):
    """get_media_detail returns None on 404 (not found)."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 404
    resp.json.return_value = {}
    resp.raise_for_status = MagicMock()
    mock_client.get.return_value = resp
    result = await arm_client.get_media_detail("tt9999999")
    assert result is None


async def test_get_media_detail_raises_on_500(mock_client):
    """get_media_detail raises on 500 (not 404)."""
    _set_get_response(mock_client, {}, status_code=500)
    with pytest.raises(httpx.HTTPStatusError):
        await arm_client.get_media_detail("tt0133093")


# --- search_music_metadata ---


async def test_search_music_metadata_success(mock_client):
    """search_music_metadata returns results."""
    _set_get_response(mock_client, {"results": [{"title": "Master of Puppets"}], "total": 1})
    result = await arm_client.search_music_metadata("Metallica")
    assert result["total"] == 1


async def test_search_music_metadata_filters_none_kwargs(mock_client):
    """search_music_metadata excludes None kwargs from params."""
    _set_get_response(mock_client, {"results": [], "total": 0})
    await arm_client.search_music_metadata(
        "Metallica", artist="Metallica", format=None, country="US")
    call_kwargs = mock_client.get.call_args
    params = call_kwargs[1]["params"]
    assert params["artist"] == "Metallica"
    assert params["country"] == "US"
    assert "format" not in params


async def test_search_music_metadata_converts_to_str(mock_client):
    """search_music_metadata converts non-string kwargs to str."""
    _set_get_response(mock_client, {"results": [], "total": 0})
    await arm_client.search_music_metadata("test", offset=25)
    call_kwargs = mock_client.get.call_args
    params = call_kwargs[1]["params"]
    assert params["offset"] == "25"


# --- get_music_detail ---


async def test_get_music_detail_success(mock_client):
    """get_music_detail returns detail dict on 200."""
    _set_get_response(mock_client, {"title": "Master of Puppets", "artist": "Metallica"})
    result = await arm_client.get_music_detail("mbid-123")
    assert result["title"] == "Master of Puppets"


async def test_get_music_detail_404_returns_none(mock_client):
    """get_music_detail returns None on 404."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 404
    resp.json.return_value = {}
    resp.raise_for_status = MagicMock()
    mock_client.get.return_value = resp
    result = await arm_client.get_music_detail("bad-mbid")
    assert result is None


# --- lookup_crc ---


async def test_lookup_crc_success(mock_client):
    """lookup_crc returns CRC result dict."""
    _set_get_response(mock_client, {"found": True, "results": [{"title": "Matrix"}], "has_api_key": True})
    result = await arm_client.lookup_crc("abc123")
    assert result["found"] is True
    mock_client.get.assert_awaited_once_with("/api/v1/metadata/crc/abc123")


async def test_lookup_crc_raises_on_error(mock_client):
    """lookup_crc raises HTTPStatusError on failure."""
    _set_get_response(mock_client, {}, status_code=500)
    with pytest.raises(httpx.HTTPStatusError):
        await arm_client.lookup_crc("abc123")


# --- test_metadata_key ---


async def test_metadata_key_success(mock_client):
    """test_metadata_key returns result dict."""
    _set_get_response(mock_client, {"success": True, "message": "OMDb key valid", "provider": "omdb"})
    result = await arm_client.test_metadata_key()
    assert result["success"] is True
    mock_client.get.assert_awaited_once_with("/api/v1/metadata/test-key", params={}, timeout=30.0)


async def test_metadata_key_with_key_and_provider(mock_client):
    """test_metadata_key includes key and provider in params when provided."""
    _set_get_response(mock_client, {"success": True, "message": "Key valid", "provider": "tmdb"})
    result = await arm_client.test_metadata_key(key="abc123", provider="tmdb")
    assert result["success"] is True
    mock_client.get.assert_awaited_once_with(
        "/api/v1/metadata/test-key",
        params={"key": "abc123", "provider": "tmdb"},
        timeout=30.0,
    )


async def test_metadata_key_uses_30s_timeout(mock_client):
    """test_metadata_key uses 30s timeout: makemkv prep_mkv() can take 15-30s
    on a cold check (fetches a fresh beta key from forum.makemkv.com)."""
    _set_get_response(mock_client, {"success": True, "message": "ok", "provider": "makemkv"})
    await arm_client.test_metadata_key(provider="makemkv")
    args, kwargs = mock_client.get.await_args
    assert kwargs["timeout"] == pytest.approx(30.0)


async def test_metadata_key_raises_on_error(mock_client):
    """test_metadata_key raises HTTPStatusError on failure."""
    _set_get_response(mock_client, {}, status_code=502)
    with pytest.raises(httpx.HTTPStatusError):
        await arm_client.test_metadata_key()


# --- get_setup_status ---


async def test_get_setup_status_success(mock_client):
    """get_setup_status returns JSON on success."""
    data = {"first_run": True, "db_initialized": True}
    _set_request_response(mock_client, data)
    result = await arm_client.get_setup_status()
    assert result == data
    mock_client.request.assert_awaited_once_with("GET", "/api/v1/setup/status")


async def test_get_setup_status_unreachable(mock_client):
    """get_setup_status returns None on ConnectError."""
    _set_request_connect_error(mock_client)
    assert await arm_client.get_setup_status() is None


# --- complete_setup ---


async def test_complete_setup_success(mock_client):
    """complete_setup returns JSON on success."""
    _set_request_response(mock_client, {"success": True})
    result = await arm_client.complete_setup()
    assert result == {"success": True}
    mock_client.request.assert_awaited_once_with("POST", "/api/v1/setup/complete")


async def test_complete_setup_unreachable(mock_client):
    """complete_setup returns None on ConnectError."""
    _set_request_connect_error(mock_client)
    assert await arm_client.complete_setup() is None


# --- eject_drive ---


async def test_eject_drive_success(mock_client):
    _set_request_response(mock_client, {"success": True, "method": "eject"})
    result = await arm_client.eject_drive(1, "eject")
    assert result["success"] is True
    mock_client.request.assert_awaited_once()


async def test_eject_drive_unreachable(mock_client):
    _set_request_connect_error(mock_client)
    assert await arm_client.eject_drive(1) is None


# --- get_job_stats ---


async def test_get_job_stats_success(mock_client):
    data = {"by_status": {"success": 5}, "by_type": {"movie": 3}, "total": 5}
    _set_request_response(mock_client, data)
    result = await arm_client.get_job_stats()
    assert result["total"] == 5


async def test_get_job_stats_unreachable(mock_client):
    _set_request_connect_error(mock_client)
    assert await arm_client.get_job_stats() is None


# --- restart_arm ---


async def test_restart_arm_success(mock_client):
    _set_request_response(mock_client, {"success": True})
    result = await arm_client.restart_arm()
    assert result["success"] is True


async def test_restart_arm_unreachable(mock_client):
    _set_request_connect_error(mock_client)
    assert await arm_client.restart_arm() is None


# --- run_preflight / fix_preflight ---


async def test_run_preflight_uses_60s_timeout(mock_client):
    """run_preflight uses a 60s timeout to absorb slow ARM preflight responses."""
    _set_request_response(mock_client, {"checks": [], "paths": []})
    result = await arm_client.run_preflight()
    assert result == {"checks": [], "paths": []}
    mock_client.request.assert_awaited_once_with("POST", "/api/v1/system/preflight", timeout=60.0)


async def test_run_preflight_unreachable(mock_client):
    _set_request_connect_error(mock_client)
    assert await arm_client.run_preflight() is None


async def test_fix_preflight_uses_60s_timeout(mock_client):
    """fix_preflight uses a 60s timeout since it re-runs preflight after applying fixes."""
    _set_request_response(mock_client, {"checks": [], "paths": []})
    result = await arm_client.fix_preflight(["RAW_PATH", "LOGPATH"])
    assert result == {"checks": [], "paths": []}
    mock_client.request.assert_awaited_once_with(
        "POST",
        "/api/v1/system/preflight/fix",
        json={"fix": ["RAW_PATH", "LOGPATH"]},
        timeout=60.0,
    )


async def test_fix_preflight_unreachable(mock_client):
    _set_request_connect_error(mock_client)
    assert await arm_client.fix_preflight([]) is None


# --- Jobs (read-side, replaces direct DB access) ---


async def test_get_active_jobs(mock_client):
    _set_request_response(mock_client, {"jobs": [{"job_id": 1}]})
    result = await arm_client.get_active_jobs()
    assert result == {"jobs": [{"job_id": 1}]}
    mock_client.request.assert_awaited_once_with("GET", "/api/v1/jobs/active")


async def test_get_active_jobs_unreachable(mock_client):
    _set_request_connect_error(mock_client)
    assert await arm_client.get_active_jobs() is None


async def test_get_jobs_paginated_passes_filters(mock_client):
    _set_request_response(mock_client, {"jobs": [], "total": 0, "page": 2, "per_page": 10, "pages": 1})
    await arm_client.get_jobs_paginated(
        page=2, per_page=10, status="active", search="serial",
        video_type="movie", disctype="bluray", days=7,
        sort_by="title", sort_dir="asc",
    )
    mock_client.request.assert_awaited_once_with(
        "GET", "/api/v1/jobs/paginated",
        params={
            "page": 2, "per_page": 10, "status": "active", "search": "serial",
            "video_type": "movie", "disctype": "bluray", "days": 7,
            "sort_by": "title", "sort_dir": "asc",
        },
    )


async def test_get_jobs_paginated_drops_empty_filters(mock_client):
    """Empty/None filter values are not sent so the ripper sees defaults."""
    _set_request_response(mock_client, {"jobs": [], "total": 0, "page": 1, "per_page": 25, "pages": 1})
    await arm_client.get_jobs_paginated()
    mock_client.request.assert_awaited_once_with(
        "GET", "/api/v1/jobs/paginated",
        params={"page": 1, "per_page": 25},
    )


async def test_get_jobs_paginated_unreachable(mock_client):
    _set_request_connect_error(mock_client)
    assert await arm_client.get_jobs_paginated() is None


async def test_get_jobs_stats_passes_filters(mock_client):
    _set_request_response(mock_client, {"total": 5, "active": 1, "waiting": 0, "success": 3, "fail": 1})
    await arm_client.get_jobs_stats(search="x", video_type="movie", disctype="dvd", days=30)
    mock_client.request.assert_awaited_once_with(
        "GET", "/api/v1/jobs/stats",
        params={"search": "x", "video_type": "movie", "disctype": "dvd", "days": 30},
    )


async def test_get_jobs_stats_no_filters(mock_client):
    _set_request_response(mock_client, {"total": 0, "active": 0, "waiting": 0, "success": 0, "fail": 0})
    await arm_client.get_jobs_stats()
    mock_client.request.assert_awaited_once_with("GET", "/api/v1/jobs/stats", params={})


async def test_get_jobs_stats_unreachable(mock_client):
    _set_request_connect_error(mock_client)
    assert await arm_client.get_jobs_stats() is None


async def test_get_job_detail(mock_client):
    _set_request_response(mock_client, {"job": {"job_id": 5}, "config": None, "track_counts": {"total": 0, "ripped": 0}})
    result = await arm_client.get_job_detail(5)
    assert result["job"]["job_id"] == 5
    mock_client.request.assert_awaited_once_with("GET", "/api/v1/jobs/5/detail")


async def test_get_job_detail_unreachable(mock_client):
    _set_request_connect_error(mock_client)
    assert await arm_client.get_job_detail(5) is None


async def test_get_job_track_counts(mock_client):
    _set_request_response(mock_client, {"total": 3, "ripped": 1})
    result = await arm_client.get_job_track_counts(7)
    assert result == {"total": 3, "ripped": 1}
    mock_client.request.assert_awaited_once_with("GET", "/api/v1/jobs/7/track-counts")


async def test_get_job_track_counts_unreachable(mock_client):
    _set_request_connect_error(mock_client)
    assert await arm_client.get_job_track_counts(7) is None


async def test_get_job_retranscode_info(mock_client):
    _set_request_response(mock_client, {"webhook_payload": {}, "preset_slug": "balanced"})
    result = await arm_client.get_job_retranscode_info(9)
    assert "preset_slug" in result
    mock_client.request.assert_awaited_once_with("GET", "/api/v1/jobs/9/retranscode-info")


async def test_get_job_retranscode_info_unreachable(mock_client):
    _set_request_connect_error(mock_client)
    assert await arm_client.get_job_retranscode_info(9) is None


# --- Drives (read-side) ---


async def test_get_drives_default_includes_stale(mock_client):
    """Default include_stale=True matches arm_db.get_drives() which returned all drives."""
    _set_request_response(mock_client, {"drives": [{"drive_id": 1}]})
    result = await arm_client.get_drives()
    assert result == {"drives": [{"drive_id": 1}]}
    mock_client.request.assert_awaited_once_with(
        "GET", "/api/v1/drives", params={"include_stale": "true"},
    )


async def test_get_drives_excludes_stale_when_requested(mock_client):
    _set_request_response(mock_client, {"drives": []})
    await arm_client.get_drives(include_stale=False)
    mock_client.request.assert_awaited_once_with("GET", "/api/v1/drives", params=None)


async def test_get_drives_unreachable(mock_client):
    _set_request_connect_error(mock_client)
    assert await arm_client.get_drives() is None


async def test_get_drives_with_jobs(mock_client):
    _set_request_response(mock_client, {"drives": []})
    result = await arm_client.get_drives_with_jobs()
    assert result == {"drives": []}
    mock_client.request.assert_awaited_once_with("GET", "/api/v1/drives/with-jobs")


async def test_get_drives_with_jobs_unreachable(mock_client):
    _set_request_connect_error(mock_client)
    assert await arm_client.get_drives_with_jobs() is None


# --- Notifications ---


async def test_get_notifications_default(mock_client):
    _set_request_response(mock_client, [])
    await arm_client.get_notifications()
    mock_client.request.assert_awaited_once_with("GET", "/api/v1/notifications", params=None)


async def test_get_notifications_include_cleared(mock_client):
    _set_request_response(mock_client, [])
    await arm_client.get_notifications(include_cleared=True)
    mock_client.request.assert_awaited_once_with(
        "GET", "/api/v1/notifications", params={"include_cleared": "true"},
    )


async def test_get_notifications_unreachable(mock_client):
    _set_request_connect_error(mock_client)
    assert await arm_client.get_notifications() is None


async def test_get_notification_count(mock_client):
    _set_request_response(mock_client, {"total": 5, "unseen": 2, "seen": 1, "cleared": 2})
    result = await arm_client.get_notification_count()
    assert result == {"total": 5, "unseen": 2, "seen": 1, "cleared": 2}
    mock_client.request.assert_awaited_once_with("GET", "/api/v1/notifications/count")


async def test_get_notification_count_unreachable(mock_client):
    _set_request_connect_error(mock_client)
    assert await arm_client.get_notification_count() is None


async def test_dismiss_all_notifications(mock_client):
    _set_request_response(mock_client, {"affected": 3})
    result = await arm_client.dismiss_all_notifications()
    assert result == {"affected": 3}
    mock_client.request.assert_awaited_once_with("POST", "/api/v1/notifications/dismiss-all")


async def test_dismiss_all_notifications_unreachable(mock_client):
    _set_request_connect_error(mock_client)
    assert await arm_client.dismiss_all_notifications() is None


async def test_purge_cleared_notifications(mock_client):
    _set_request_response(mock_client, {"deleted": 2})
    result = await arm_client.purge_cleared_notifications()
    assert result == {"deleted": 2}
    mock_client.request.assert_awaited_once_with("POST", "/api/v1/notifications/purge")


async def test_purge_cleared_notifications_unreachable(mock_client):
    _set_request_connect_error(mock_client)
    assert await arm_client.purge_cleared_notifications() is None


# --- Health ---


async def test_is_available_true_when_version_returns(mock_client):
    _set_request_response(mock_client, {"version": "16.3.1"})
    assert await arm_client.is_available() is True


async def test_is_available_false_when_unreachable(mock_client):
    _set_request_connect_error(mock_client)
    assert await arm_client.is_available() is False
