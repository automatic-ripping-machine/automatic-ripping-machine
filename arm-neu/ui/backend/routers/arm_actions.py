from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.models.files import OperationResult
from backend.models.metadata import NamingPreviewResponse
from backend.models.schemas import JobConfigUpdateRequest, NamingPreviewRequest, TitleUpdateRequest
from backend.models.system import RippingEnabledResponse
from backend.services import arm_client

_502_503_ARM = {502: {"description": "ARM action failed"}, 503: {"description": "ARM web UI is unreachable"}}

router = APIRouter(prefix="/api/jobs", tags=["arm-actions"])


def _check_result(result: dict[str, Any] | None) -> dict[str, Any]:
    """Raise HTTPException if the ARM proxy result is None or reports failure."""
    if result is None:
        raise HTTPException(status_code=503, detail="ARM web UI is unreachable")
    if isinstance(result, dict) and result.get("success") is False:
        detail = result.get("error") or result.get("Error") or "Action failed"
        raise HTTPException(status_code=502, detail=detail)
    return result


def _proxy_post(path: str, method_name: str, *, http_method: str = "post") -> None:
    """Register a simple ARM proxy endpoint that forwards only job_id."""

    async def _endpoint(job_id: int) -> dict[str, Any]:
        result = await getattr(arm_client, method_name)(job_id)
        return _check_result(result)

    _endpoint.__name__ = method_name
    _endpoint.__qualname__ = method_name
    route = f"/{{job_id}}/{path}" if path else "/{job_id}"
    getattr(router, http_method)(
        route,
        response_model=OperationResult,
        responses=_502_503_ARM,
    )(_endpoint)


# Simple proxies — just forward job_id to ARM
_proxy_post("abandon", "abandon_job")
_proxy_post("cancel", "cancel_waiting_job")
_proxy_post("fix-permissions", "fix_permissions")
_proxy_post("skip-and-finalize", "skip_and_finalize")
_proxy_post("force-complete", "force_complete")
_proxy_post("start", "start_waiting_job")
_proxy_post("crc-submit", "send_to_crc_db")
_proxy_post("", "delete_job", http_method="delete")


# --- Endpoints with extra parameters (kept as regular functions) ---


@router.put("/{job_id}/title", response_model=OperationResult, responses=_502_503_ARM)
async def update_title(job_id: int, body: TitleUpdateRequest) -> dict[str, Any]:
    """Update a job's title metadata (proxies to ARM)."""
    return _check_result(await arm_client.update_title(job_id, body.model_dump(exclude_none=True)))


@router.patch("/{job_id}/config", response_model=OperationResult, responses=_502_503_ARM)
async def update_job_config(job_id: int, body: JobConfigUpdateRequest) -> dict[str, Any]:
    """Update a job's rip parameters (proxies to ARM)."""
    return _check_result(await arm_client.update_job_config(job_id, body.model_dump(exclude_none=True)))


@router.post("/{job_id}/pause", response_model=OperationResult, responses=_502_503_ARM)
async def pause_waiting_job(job_id: int, body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Set or toggle per-job pause for a waiting job (proxies to ARM)."""
    paused = body.get("paused") if body else None
    return _check_result(await arm_client.pause_waiting_job(job_id, paused=paused))


@router.put("/{job_id}/tracks", response_model=OperationResult, responses=_502_503_ARM)
async def set_job_tracks(job_id: int, body: list[dict]) -> dict[str, Any]:
    """Replace a job's tracks with MusicBrainz data (proxies to ARM)."""
    return _check_result(await arm_client.set_job_tracks(job_id, body))


# --- Naming preview (separate prefix) ---

naming_router = APIRouter(prefix="/api", tags=["naming"])


@naming_router.post("/naming/preview", response_model=NamingPreviewResponse, responses=_502_503_ARM)
async def naming_preview(body: NamingPreviewRequest) -> dict[str, Any]:
    """Preview a naming pattern with given variables (proxies to ARM)."""
    return _check_result(await arm_client.naming_preview(body.pattern, body.variables))


# --- System-level actions (separate prefix) ---

class RippingEnabledRequest(BaseModel):
    enabled: bool


system_router = APIRouter(prefix="/api/system", tags=["arm-system-actions"])


@system_router.post("/ripping-enabled", response_model=RippingEnabledResponse, responses=_502_503_ARM)
async def set_ripping_enabled(body: RippingEnabledRequest) -> dict[str, Any]:
    """Toggle global ripping pause (proxies to ARM)."""
    return _check_result(await arm_client.set_ripping_enabled(body.enabled))
