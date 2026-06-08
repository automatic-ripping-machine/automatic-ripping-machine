"""ISO import proxy - routes ISO scan/create through the ARM backend."""
from typing import Any

from fastapi import APIRouter, HTTPException

from backend.models.iso import (
    IsoCreateRequest,
    IsoCreateResponse,
    IsoScanRequest,
    IsoScanResult,
)
from backend.services import arm_client

router = APIRouter(prefix="/api/jobs/iso", tags=["iso"])

_ARM_UI_UNREACHABLE = "ARM web UI is unreachable"


def _check_result(result: dict[str, Any] | None) -> dict[str, Any]:
    if result is None:
        raise HTTPException(status_code=503, detail=_ARM_UI_UNREACHABLE)
    if isinstance(result, dict) and result.get("success") is False:
        detail = result.get("error") or "Action failed"
        raise HTTPException(status_code=502, detail=detail)
    return result


@router.post("/scan", response_model=IsoScanResult)
async def scan_iso(req: IsoScanRequest) -> dict[str, Any]:
    """Scan an ISO file for disc structure and metadata."""
    return _check_result(await arm_client.scan_iso(req.path))


@router.post("", status_code=201, response_model=IsoCreateResponse)
async def create_iso_job(req: IsoCreateRequest) -> dict[str, Any]:
    """Create an ISO import job."""
    return _check_result(await arm_client.create_iso_job(req.model_dump()))
