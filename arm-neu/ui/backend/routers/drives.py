from fastapi import APIRouter, HTTPException

from backend.models.schemas import DriveEjectResult, DriveSchema, DriveUpdateRequest, OperationResult
from backend.services import arm_client

router = APIRouter(prefix="/api", tags=["drives"])


@router.get("/drives", response_model=list[DriveSchema])
async def list_drives():
    """Return non-stale drives with their current job attached.

    Returns an empty list if the ripper API is unreachable so the dashboard
    can still render (the offline state is signaled separately by the
    /api/dashboard endpoint).
    """
    resp = await arm_client.get_drives_with_jobs()
    if resp is None:
        return []
    return resp.get("drives") or []


@router.post("/drives/rescan", response_model=OperationResult, responses={502: {"description": "ARM unreachable"}})
async def rescan_drives(force: bool = False):
    """Re-detect optical drives and update the database.

    With force=true, deletes all non-processing drive records before rescanning.
    """
    result = await arm_client.rescan_drives(force=force)
    if result is None:
        raise HTTPException(status_code=502, detail="ARM unreachable")
    return result


@router.get("/drives/diagnostic", responses={502: {"description": "ARM unreachable"}})
async def drive_diagnostic():
    result = await arm_client.drive_diagnostic()
    if result is None:
        raise HTTPException(status_code=502, detail="ARM unreachable")
    return result


@router.delete("/drives/{drive_id}", response_model=OperationResult, responses={404: {"description": "Drive not found"}, 409: {"description": "Drive has active job"}, 502: {"description": "ARM unreachable"}})
async def delete_drive(drive_id: int):
    result = await arm_client.delete_drive(drive_id)
    if result is None:
        raise HTTPException(status_code=502, detail="ARM unreachable")
    if not result.get("success"):
        error = result.get("error", "Delete failed")
        status = 409 if "active" in error.lower() else 404
        raise HTTPException(status_code=status, detail=error)
    return result


@router.post("/drives/{drive_id}/scan", response_model=OperationResult, responses={404: {"description": "Drive not found"}, 502: {"description": "ARM unreachable"}})
async def scan_drive(drive_id: int):
    result = await arm_client.scan_drive(drive_id)
    if result is None:
        raise HTTPException(status_code=502, detail="ARM unreachable")
    if not result.get("success"):
        status = 404 if "not found" in result.get("error", "").lower() else 400
        raise HTTPException(status_code=status, detail=result.get("error", "Scan failed"))
    return result


@router.post("/drives/{drive_id}/eject", response_model=DriveEjectResult, responses={404: {"description": "Drive not found"}, 502: {"description": "ARM unreachable"}})
async def eject_drive(drive_id: int, method: str = "toggle"):
    """Eject, close, or toggle the drive tray."""
    result = await arm_client.eject_drive(drive_id, method)
    if result is None:
        raise HTTPException(status_code=502, detail="ARM unreachable")
    if not result.get("success"):
        status = 404 if "not found" in result.get("error", "").lower() else 500
        raise HTTPException(status_code=status, detail=result.get("error", "Eject failed"))
    return result


@router.patch("/drives/{drive_id}", response_model=OperationResult, responses={400: {"description": "No fields to update"}, 404: {"description": "Update failed"}, 502: {"description": "ARM unreachable"}})
async def update_drive(drive_id: int, body: DriveUpdateRequest):
    data = body.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = await arm_client.update_drive(drive_id, data)
    if result is None:
        raise HTTPException(status_code=502, detail="ARM unreachable")
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Update failed"))
    return result
