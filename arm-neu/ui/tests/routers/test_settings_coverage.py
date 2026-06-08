"""Additional tests for backend.routers.settings - uncovered lines."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx


# --- GET /api/settings ---


async def test_get_settings_all_sources(app_client):
    """get_settings with all data sources available."""
    arm_resp = {
        "config": {"RIPMETHOD": "mkv"},
        "comments": {"RIPMETHOD": "Rip method"},
        "naming_variables": {"title": "Movie title"},
    }
    tc_config = {"config": {"video_encoder": "x265"}, "updatable_keys": ["video_encoder"]}
    health = {
        "status": "healthy",
        "gpu_support": {"nvenc": True},
        "require_api_auth": False,
        "webhook_secret_configured": False,
    }
    with (
        patch("backend.routers.settings.arm_client.get_config", new_callable=AsyncMock, return_value=arm_resp),
        patch("backend.routers.settings.transcoder_client.get_config", new_callable=AsyncMock, return_value=tc_config),
        patch("backend.routers.settings.transcoder_client.health", new_callable=AsyncMock, return_value=health),
    ):
        resp = await app_client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["arm_config"] == {"RIPMETHOD": "mkv"}
    assert data["arm_metadata"] == {"RIPMETHOD": "Rip method"}
    assert data["naming_variables"] == {"title": "Movie title"}
    # transcoder_config is now typed (TranscoderConfig); compare meaningful
    # fields rather than full equality, since the typed model surfaces all
    # optional fields with default None.
    assert data["transcoder_config"]["config"] == tc_config["config"]
    assert data["transcoder_config"]["updatable_keys"] == tc_config["updatable_keys"]
    assert data["gpu_support"] == {"nvenc": True}


async def test_get_settings_arm_offline_returns_none_config(app_client):
    """When the ripper API is unreachable, arm_config is None (no DB fallback)."""
    with (
        patch("backend.routers.settings.arm_client.get_config", new_callable=AsyncMock, return_value=None),
        patch("backend.routers.settings.transcoder_client.get_config", new_callable=AsyncMock, return_value=None),
        patch("backend.routers.settings.transcoder_client.health", new_callable=AsyncMock, return_value=None),
    ):
        resp = await app_client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["arm_config"] is None
    assert data["transcoder_config"] is None
    assert data["gpu_support"] is None


async def test_get_settings_transcoder_config_fallback_from_health(app_client):
    """When /config fails but /health succeeds, config is extracted from health."""
    health = {
        "status": "healthy",
        "gpu_support": None,
        "config": {"video_encoder": "x265"},
        "require_api_auth": False,
        "webhook_secret_configured": False,
    }
    with (
        patch("backend.routers.settings.arm_client.get_config", new_callable=AsyncMock, return_value=None),
        patch("backend.routers.settings.transcoder_client.get_config", new_callable=AsyncMock, return_value=None),
        patch("backend.routers.settings.transcoder_client.health", new_callable=AsyncMock, return_value=health),
    ):
        resp = await app_client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["transcoder_config"]["config"] == {"video_encoder": "x265"}


# --- PUT /api/settings/arm ---


async def test_update_arm_config_success(app_client):
    with patch(
        "backend.routers.settings.arm_client.update_config",
        new_callable=AsyncMock,
        return_value={"success": True},
    ):
        resp = await app_client.put(
            "/api/settings/arm", json={"config": {"RIPMETHOD": "backup"}}
        )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


async def test_update_arm_config_unreachable(app_client):
    with patch(
        "backend.routers.settings.arm_client.update_config",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await app_client.put(
            "/api/settings/arm", json={"config": {"RIPMETHOD": "backup"}}
        )
    assert resp.status_code == 502
    assert "unreachable" in resp.json()["detail"].lower()


async def test_update_arm_config_failure(app_client):
    with patch(
        "backend.routers.settings.arm_client.update_config",
        new_callable=AsyncMock,
        return_value={"success": False, "error": "Invalid key"},
    ):
        resp = await app_client.put(
            "/api/settings/arm", json={"config": {"BAD_KEY": "value"}}
        )
    assert resp.status_code == 400
    assert "Invalid key" in resp.json()["detail"]


# --- PATCH /api/settings/transcoder ---


async def test_update_transcoder_config_success(app_client):
    with patch(
        "backend.routers.settings.transcoder_client.update_config",
        new_callable=AsyncMock,
        return_value={"success": True},
    ):
        resp = await app_client.patch(
            "/api/settings/transcoder", json={"video_encoder": "nvenc_h265"}
        )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


async def test_update_transcoder_config_unreachable(app_client):
    with patch(
        "backend.routers.settings.transcoder_client.update_config",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await app_client.patch(
            "/api/settings/transcoder", json={"video_encoder": "x265"}
        )
    assert resp.status_code == 502
    assert "unreachable" in resp.json()["detail"].lower()


async def test_update_transcoder_config_failure(app_client):
    with patch(
        "backend.routers.settings.transcoder_client.update_config",
        new_callable=AsyncMock,
        return_value={"success": False, "detail": "Invalid encoder"},
    ):
        resp = await app_client.patch(
            "/api/settings/transcoder", json={"video_encoder": "bad"}
        )
    assert resp.status_code == 400
    assert "Invalid encoder" in resp.json()["detail"]


async def test_update_transcoder_config_forwards_422(app_client):
    """422 validation errors from transcoder should surface (not swallowed as 502)."""
    err_resp = httpx.Response(422, json={"detail": "global_overrides must be a string"})
    err = httpx.HTTPStatusError("unprocessable", request=None, response=err_resp)
    with patch(
        "backend.routers.settings.transcoder_client.update_config",
        new_callable=AsyncMock,
        side_effect=err,
    ):
        resp = await app_client.patch(
            "/api/settings/transcoder",
            json={"global_overrides": {"shared": {}, "tiers": {}}},
        )
    assert resp.status_code == 422
    assert "global_overrides" in resp.json()["detail"]


# --- GET /api/settings/test-metadata ---


async def test_test_metadata_key_success(app_client):
    with patch(
        "backend.routers.settings.arm_client.test_metadata_key",
        new_callable=AsyncMock,
        return_value={"success": True, "message": "OMDb key valid", "provider": "omdb"},
    ):
        resp = await app_client.get("/api/settings/test-metadata")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


async def test_test_metadata_key_http_error(app_client):
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 502
    mock_resp.json.return_value = {"detail": "Upstream error"}
    with patch(
        "backend.routers.settings.arm_client.test_metadata_key",
        new_callable=AsyncMock,
        side_effect=httpx.HTTPStatusError("error", request=MagicMock(), response=mock_resp),
    ):
        resp = await app_client.get("/api/settings/test-metadata")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["message"] == "Upstream error"


async def test_test_metadata_key_connect_error(app_client):
    with patch(
        "backend.routers.settings.arm_client.test_metadata_key",
        new_callable=AsyncMock,
        side_effect=httpx.ConnectError("refused"),
    ):
        resp = await app_client.get("/api/settings/test-metadata")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "unreachable" in data["message"].lower()


# --- GET /api/settings/transcoder/scheme ---


async def test_get_transcoder_scheme_success(app_client):
    data = {"slug": "default", "name": "Default Scheme", "presets": []}
    with patch(
        "backend.routers.settings.transcoder_client.get_scheme",
        new_callable=AsyncMock,
        return_value=data,
    ):
        resp = await app_client.get("/api/settings/transcoder/scheme")
    assert resp.status_code == 200
    assert resp.json()["slug"] == "default"


async def test_get_transcoder_scheme_unreachable(app_client):
    with patch(
        "backend.routers.settings.transcoder_client.get_scheme",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await app_client.get("/api/settings/transcoder/scheme")
    assert resp.status_code == 502
    assert "unreachable" in resp.json()["detail"].lower()


# --- GET /api/settings/transcoder/presets ---


async def test_get_transcoder_presets_success(app_client):
    data = {"presets": [{"slug": "hq-1080p", "name": "HQ 1080p", "scheme": "matroska"}]}
    with patch(
        "backend.routers.settings.transcoder_client.get_presets",
        new_callable=AsyncMock,
        return_value=data,
    ):
        resp = await app_client.get("/api/settings/transcoder/presets")
    assert resp.status_code == 200
    assert resp.json()["presets"][0]["slug"] == "hq-1080p"
    assert resp.json()["presets"][0]["scheme"] == "matroska"


async def test_get_transcoder_presets_unreachable(app_client):
    with patch(
        "backend.routers.settings.transcoder_client.get_presets",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await app_client.get("/api/settings/transcoder/presets")
    assert resp.status_code == 502
    assert "unreachable" in resp.json()["detail"].lower()


# --- PUT /api/settings/abcde failure ---


async def test_put_abcde_config_failure(app_client):
    with patch(
        "backend.routers.settings.arm_client.update_abcde_config",
        new_callable=AsyncMock,
        return_value={"success": False, "error": "Parse error"},
    ):
        resp = await app_client.put(
            "/api/settings/abcde", json={"content": "invalid\x00content"}
        )
    assert resp.status_code == 400
    assert "Parse error" in resp.json()["detail"]


# --- POST /api/settings/transcoder/presets ---


async def test_create_preset_proxy_success(app_client):
    with patch(
        "backend.routers.settings.transcoder_client.create_preset",
        new_callable=AsyncMock,
        return_value={"slug": "x", "name": "X", "scheme": "matroska"},
    ):
        resp = await app_client.post(
            "/api/settings/transcoder/presets",
            json={
                "name": "X",
                "parent_slug": "y",
                "overrides": {"shared": {}, "tiers": {}},
            },
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["slug"] == "x"
    assert body["scheme"] == "matroska"


async def test_create_preset_proxy_offline(app_client):
    with patch(
        "backend.routers.settings.transcoder_client.create_preset",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await app_client.post(
            "/api/settings/transcoder/presets",
            json={"name": "X", "parent_slug": "y"},
        )
    assert resp.status_code == 502


async def test_create_preset_proxy_forwards_4xx_detail(app_client):
    err_resp = httpx.Response(409, json={"detail": "Slug exists"})
    err = httpx.HTTPStatusError("conflict", request=None, response=err_resp)
    with patch(
        "backend.routers.settings.transcoder_client.create_preset",
        new_callable=AsyncMock,
        side_effect=err,
    ):
        resp = await app_client.post(
            "/api/settings/transcoder/presets",
            json={"name": "X", "parent_slug": "y"},
        )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "Slug exists"


# --- PATCH /api/settings/transcoder/presets/{slug} ---


async def test_update_preset_proxy_success(app_client):
    with patch(
        "backend.routers.settings.transcoder_client.update_preset",
        new_callable=AsyncMock,
        return_value={"slug": "x", "name": "Y", "scheme": "matroska"},
    ):
        resp = await app_client.patch(
            "/api/settings/transcoder/presets/x", json={"name": "Y"}
        )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Y"
    assert resp.json()["scheme"] == "matroska"


async def test_update_preset_proxy_offline(app_client):
    with patch(
        "backend.routers.settings.transcoder_client.update_preset",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await app_client.patch(
            "/api/settings/transcoder/presets/x", json={}
        )
    assert resp.status_code == 502


async def test_update_preset_proxy_forwards_404(app_client):
    err_resp = httpx.Response(404, json={"detail": "Cannot update built-in"})
    err = httpx.HTTPStatusError("not found", request=None, response=err_resp)
    with patch(
        "backend.routers.settings.transcoder_client.update_preset",
        new_callable=AsyncMock,
        side_effect=err,
    ):
        resp = await app_client.patch(
            "/api/settings/transcoder/presets/x", json={}
        )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Cannot update built-in"


async def test_update_preset_proxy_handles_non_json_error_body(app_client):
    """When transcoder error body isn't JSON, fall back to generic detail."""
    err_resp = httpx.Response(500, content=b"<html>Internal Error</html>")
    err = httpx.HTTPStatusError("boom", request=None, response=err_resp)
    with patch(
        "backend.routers.settings.transcoder_client.update_preset",
        new_callable=AsyncMock,
        side_effect=err,
    ):
        resp = await app_client.patch(
            "/api/settings/transcoder/presets/x", json={}
        )
    assert resp.status_code == 500
    assert resp.json()["detail"] == "Preset operation failed"


# --- DELETE /api/settings/transcoder/presets/{slug} ---


async def test_delete_preset_proxy_success(app_client):
    with patch(
        "backend.routers.settings.transcoder_client.delete_preset",
        new_callable=AsyncMock,
        return_value={"success": True, "deleted": "x"},
    ):
        resp = await app_client.delete("/api/settings/transcoder/presets/x")
    assert resp.status_code == 200
    assert resp.json()["deleted"] == "x"


async def test_delete_preset_proxy_offline(app_client):
    with patch(
        "backend.routers.settings.transcoder_client.delete_preset",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await app_client.delete("/api/settings/transcoder/presets/x")
    assert resp.status_code == 502


async def test_delete_preset_proxy_forwards_404(app_client):
    err_resp = httpx.Response(404, json={"detail": "Preset not found"})
    err = httpx.HTTPStatusError("not found", request=None, response=err_resp)
    with patch(
        "backend.routers.settings.transcoder_client.delete_preset",
        new_callable=AsyncMock,
        side_effect=err,
    ):
        resp = await app_client.delete("/api/settings/transcoder/presets/x")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Preset not found"


# --- slug validation at router boundary (SSRF defense-in-depth) ---


async def test_update_preset_proxy_returns_400_on_invalid_slug(app_client):
    with patch(
        "backend.routers.settings.transcoder_client.update_preset",
        new_callable=AsyncMock,
        side_effect=ValueError("Invalid preset slug: 'bad'"),
    ):
        resp = await app_client.patch(
            "/api/settings/transcoder/presets/bad", json={}
        )
    assert resp.status_code == 400
    assert "Invalid preset slug" in resp.json()["detail"]


async def test_delete_preset_proxy_returns_400_on_invalid_slug(app_client):
    with patch(
        "backend.routers.settings.transcoder_client.delete_preset",
        new_callable=AsyncMock,
        side_effect=ValueError("Invalid preset slug: 'bad'"),
    ):
        resp = await app_client.delete("/api/settings/transcoder/presets/bad")
    assert resp.status_code == 400
    assert "Invalid preset slug" in resp.json()["detail"]
