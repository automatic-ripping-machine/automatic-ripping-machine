import asyncio
import logging
import os
from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException
import httpx
from pydantic import BaseModel

from backend.config import settings as app_settings
from backend.dependencies import require_transcoder_enabled
from backend.models.schemas import OperationResult, Preset, PresetCreateRequest, PresetListResponse, PresetUpdateRequest, Scheme, SettingsResponse
from backend.services import arm_client, transcoder_client

router = APIRouter(prefix="/api", tags=["settings"])
log = logging.getLogger(__name__)

_TRANSCODER_UNREACHABLE = "Transcoder service unreachable"
_TRANSCODER_UNREACHABLE_RESPONSE = {502: {"description": _TRANSCODER_UNREACHABLE}}


@router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    arm_config = None
    arm_metadata = None
    naming_variables = None
    arm_resp = await arm_client.get_config()
    if arm_resp:
        arm_config = arm_resp.get("config")
        raw_comments = arm_resp.get("comments")
        if isinstance(raw_comments, dict):
            arm_metadata = {k: v for k, v in raw_comments.items() if isinstance(v, str)}
        naming_variables = arm_resp.get("naming_variables")

    # Transcoder config + GPU support
    transcoder_config = None
    transcoder_gpu_support = None
    transcoder_auth_status = None

    if app_settings.transcoder_enabled:
        tc_config_resp = await transcoder_client.get_config()
        if tc_config_resp:
            transcoder_config = tc_config_resp

        health = await transcoder_client.health()
        if health:
            transcoder_gpu_support = health.get("gpu_support")
            transcoder_auth_status = {
                "require_api_auth": health.get("require_api_auth", False),
                "webhook_secret_configured": health.get("webhook_secret_configured", False),
            }
            # If the dedicated /config endpoint was offline, use health fallback
            if not transcoder_config:
                transcoder_config = {
                    "config": health.get("config"),
                    "updatable_keys": list(health.get("config", {}).keys()),
                }

    return SettingsResponse(
        arm_config=arm_config,
        arm_metadata=arm_metadata,
        naming_variables=naming_variables,
        transcoder_config=transcoder_config,
        transcoder_gpu_support=transcoder_gpu_support,
        transcoder_auth_status=transcoder_auth_status,
        arm_ui_webhook_secret_configured=bool(app_settings.transcoder_webhook_secret),
        gpu_support=transcoder_gpu_support,
    )


class ArmConfigUpdate(BaseModel):
    config: dict


@router.put("/settings/arm", responses={400: {"description": "Invalid config"}, 502: {"description": "ARM service unreachable"}})
async def update_arm_config(body: ArmConfigUpdate):
    result = await arm_client.update_config(body.config)
    if result is None:
        raise HTTPException(status_code=502, detail="ARM service unreachable")
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Unknown error"))
    return result


class AbcdeConfigUpdate(BaseModel):
    content: str


@router.get("/settings/abcde")
async def get_abcde_config():
    result = await arm_client.get_abcde_config()
    if result is None:
        raise HTTPException(status_code=502, detail="ARM service unreachable")
    return result


@router.put("/settings/abcde", responses={400: {"description": "Invalid request"}, 502: {"description": "ARM service unreachable"}})
async def update_abcde_config(body: AbcdeConfigUpdate):
    result = await arm_client.update_abcde_config(body.content)
    if result is None:
        raise HTTPException(status_code=502, detail="ARM service unreachable")
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Unknown error"))
    return result


@router.get("/settings/test-metadata")
async def test_metadata_key(key: str | None = None, provider: str | None = None):
    """Test a metadata API key (proxied through ARM). Tests the field value if provided, else saved config."""
    try:
        return await arm_client.test_metadata_key(key=key, provider=provider)
    except httpx.HTTPStatusError as exc:
        log.warning("Metadata key test failed: %d", exc.response.status_code)
        upstream_msg = "Metadata key test failed"
        try:
            body = exc.response.json()
            if body.get("detail"):
                upstream_msg = body["detail"]
        except Exception:
            pass
        return {"success": False, "message": upstream_msg, "provider": "unknown"}
    except (httpx.HTTPError, httpx.ConnectError, RuntimeError, OSError) as exc:
        log.error("Metadata key test unreachable: %s", exc)
        return {"success": False, "message": "ARM service unreachable", "provider": "unknown"}


@router.get("/settings/transcoder/scheme", response_model=Scheme,
            responses=_TRANSCODER_UNREACHABLE_RESPONSE,
            dependencies=[Depends(require_transcoder_enabled)])
async def get_transcoder_scheme():
    result = await transcoder_client.get_scheme()
    if result is None:
        raise HTTPException(status_code=502, detail=_TRANSCODER_UNREACHABLE)
    return result


@router.get("/settings/transcoder/presets", response_model=PresetListResponse,
            responses=_TRANSCODER_UNREACHABLE_RESPONSE,
            dependencies=[Depends(require_transcoder_enabled)])
async def get_transcoder_presets():
    result = await transcoder_client.get_presets()
    if result is None:
        raise HTTPException(status_code=502, detail=_TRANSCODER_UNREACHABLE)
    return result


def _raise_from_http_status_error(exc: httpx.HTTPStatusError) -> NoReturn:
    """Re-raise an httpx HTTPStatusError as a FastAPI HTTPException, forwarding detail."""
    detail = "Preset operation failed"
    try:
        detail = exc.response.json().get("detail", detail)
    except Exception:
        pass
    raise HTTPException(status_code=exc.response.status_code, detail=detail)


@router.post("/settings/transcoder/presets", status_code=201,
             response_model=Preset,
             responses={409: {"description": "Slug conflict"}, 502: {"description": "Transcoder unreachable"}},
             dependencies=[Depends(require_transcoder_enabled)])
async def create_transcoder_preset(body: PresetCreateRequest):
    try:
        result = await transcoder_client.create_preset(body.model_dump())
    except httpx.HTTPStatusError as exc:
        _raise_from_http_status_error(exc)
    if result is None:
        raise HTTPException(status_code=502, detail=_TRANSCODER_UNREACHABLE)
    return result


@router.patch("/settings/transcoder/presets/{slug}",
              response_model=Preset,
              responses={400: {"description": "Invalid slug"}, 404: {"description": "Preset not found"}, 502: {"description": "Transcoder unreachable"}},
              dependencies=[Depends(require_transcoder_enabled)])
async def update_transcoder_preset(slug: str, body: PresetUpdateRequest):
    try:
        result = await transcoder_client.update_preset(slug, body.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except httpx.HTTPStatusError as exc:
        _raise_from_http_status_error(exc)
    if result is None:
        raise HTTPException(status_code=502, detail=_TRANSCODER_UNREACHABLE)
    return result


@router.delete("/settings/transcoder/presets/{slug}",
               response_model=OperationResult,
               responses={400: {"description": "Invalid slug"}, 404: {"description": "Preset not found"}, 502: {"description": "Transcoder unreachable"}},
               dependencies=[Depends(require_transcoder_enabled)])
async def delete_transcoder_preset(slug: str):
    try:
        result = await transcoder_client.delete_preset(slug)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except httpx.HTTPStatusError as exc:
        _raise_from_http_status_error(exc)
    if result is None:
        raise HTTPException(status_code=502, detail=_TRANSCODER_UNREACHABLE)
    return result


@router.patch("/settings/transcoder", responses={400: {"description": "Invalid config"}, **_TRANSCODER_UNREACHABLE_RESPONSE},
              dependencies=[Depends(require_transcoder_enabled)])
async def update_transcoder_config(body: dict):
    try:
        result = await transcoder_client.update_config(body)
    except httpx.HTTPStatusError as exc:
        _raise_from_http_status_error(exc)
    if result is None:
        raise HTTPException(status_code=502, detail=_TRANSCODER_UNREACHABLE)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("detail", "Unknown error"))
    return result


@router.post("/settings/transcoder/test-connection",
             dependencies=[Depends(require_transcoder_enabled)])
async def test_transcoder_connection():
    return await transcoder_client.test_connection()


class WebhookTestRequest(BaseModel):
    webhook_secret: str = ""


@router.post("/settings/transcoder/test-webhook",
             responses={400: {"description": "webhook_secret is required"}},
             dependencies=[Depends(require_transcoder_enabled)])
async def test_transcoder_webhook(body: WebhookTestRequest):
    if not body.webhook_secret:
        raise HTTPException(status_code=400, detail="webhook_secret is required")
    return await transcoder_client.test_webhook(body.webhook_secret)


@router.get("/settings/system-info")
async def get_system_info():
    """Gather system info: versions, paths, database migration state, drives."""
    arm_versions, tc_health, drives_resp, paths = await asyncio.gather(
        arm_client.get_version(),
        transcoder_client.health(),
        arm_client.get_drives(),
        arm_client.get_paths(),
    )

    ui_version_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "VERSION")

    def _read_version() -> str:
        try:
            with open(ui_version_file) as f:
                return f.read().strip()
        except OSError:
            return "unknown"

    ui_version = await asyncio.to_thread(_read_version)
    tc_version = tc_health.get("version") if tc_health else None

    db_version = arm_versions.get("db_version", "unknown") if arm_versions else "offline"
    db_head = arm_versions.get("db_head", "unknown") if arm_versions else "offline"
    db_up_to_date = db_version == db_head if (db_version not in ("unknown", "offline") and db_head not in ("unknown", "offline")) else None

    versions = {
        "arm": arm_versions.get("arm_version", "unknown") if arm_versions else "offline",
        "makemkv": arm_versions.get("makemkv_version", "unknown") if arm_versions else "offline",
        "transcoder": tc_version or ("offline" if not tc_health else "unknown"),
        "ui": ui_version,
    }

    drives = (drives_resp or {}).get("drives") or []
    drive_list = [
        {
            "name": d.get("name"), "mount": d.get("mount"), "maker": d.get("maker"),
            "model": d.get("model"), "capabilities": d.get("capabilities") or [],
            "firmware": d.get("firmware"),
        }
        for d in drives
    ]

    return {
        "versions": versions,
        "endpoints": {
            "arm": {"url": app_settings.arm_url, "reachable": arm_versions is not None},
            "transcoder": {"url": app_settings.transcoder_url, "reachable": tc_health is not None},
        },
        "paths": paths or [],
        "database": {
            "path": arm_versions.get("db_path") if arm_versions else None,
            "size_bytes": arm_versions.get("db_size_bytes") if arm_versions else None,
            "available": arm_versions is not None,
            "migration_current": db_version,
            "migration_head": db_head,
            "up_to_date": db_up_to_date,
        },
        "drives": drive_list,
    }
