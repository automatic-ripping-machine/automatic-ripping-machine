"""API v1 — Maintenance endpoints for orphan detection and cleanup."""
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from arm.services import maintenance as svc

router = APIRouter(prefix="/api/v1", tags=["maintenance"])


class PathRequest(BaseModel):
    path: str


class BulkPathRequest(BaseModel):
    paths: list[str]


@router.get("/maintenance/counts")
def get_counts():
    """Return orphan counts for summary display."""
    return svc.get_counts()


@router.get("/maintenance/orphan-logs")
def get_orphan_logs():
    """List log files not referenced by any job."""
    return svc.get_orphan_logs()


@router.get("/maintenance/orphan-folders")
def get_orphan_folders():
    """List folders in RAW_PATH/COMPLETED_PATH not matching any job."""
    return svc.get_orphan_folders()


@router.post("/maintenance/delete-log")
def delete_log(req: PathRequest):
    result = svc.delete_log(req.path)
    if not result["success"]:
        error = result.get("error", "")
        if "outside" in error:
            raise HTTPException(status_code=403, detail="Access denied")
        if "not found" in error.lower():
            raise HTTPException(status_code=404, detail="File not found")
    return result


@router.post("/maintenance/delete-folder")
def delete_folder(req: PathRequest):
    result = svc.delete_folder(req.path)
    if not result["success"]:
        error = result.get("error", "")
        if "outside" in error:
            raise HTTPException(status_code=403, detail="Access denied")
        if "not found" in error.lower():
            raise HTTPException(status_code=404, detail="Directory not found")
    return result


@router.post("/maintenance/bulk-delete-logs")
def bulk_delete_logs(req: BulkPathRequest):
    result = svc.bulk_delete_logs(req.paths)
    # Sanitize error messages — don't expose internal paths
    result["errors"] = [
        f"{Path(e.split(':')[0]).name}: operation failed" if ':' in e else e
        for e in result.get("errors", [])
    ]
    return result


@router.post("/maintenance/bulk-delete-folders")
def bulk_delete_folders(req: BulkPathRequest):
    result = svc.bulk_delete_folders(req.paths)
    result["errors"] = [
        f"{Path(e.split(':')[0]).name}: operation failed" if ':' in e else e
        for e in result.get("errors", [])
    ]
    return result
