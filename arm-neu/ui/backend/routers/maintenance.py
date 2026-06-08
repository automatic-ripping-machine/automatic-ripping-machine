"""Maintenance endpoints - orchestrates ARM proxy, notifications, and transcoder cleanup."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.models.files import OperationResult
from backend.models.maintenance import (
    CleanupTranscoderResult,
    ClearRawResult,
    ImageCacheStats,
    MaintenanceBulkDeleteResult,
    MaintenanceDeleteResult,
    MaintenanceSummary,
    OrphanFolderList,
    OrphanLogList,
)
from backend.services import arm_client, image_cache, transcoder_client

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["maintenance"])

_ARM_UNREACHABLE = "ARM web UI is unreachable"


class PathRequest(BaseModel):
    path: str


class BulkPathRequest(BaseModel):
    paths: list[str]


def _check_arm(result: dict[str, Any] | None) -> dict[str, Any]:
    if result is None:
        raise HTTPException(status_code=503, detail=_ARM_UNREACHABLE)
    if result.get("success") is False:
        raise HTTPException(status_code=502, detail=result.get("error", "ARM request failed"))
    return result


@router.get("/maintenance/summary", response_model=MaintenanceSummary)
async def get_summary():
    """Aggregate counts from ARM (orphans + notifications) and transcoder."""

    async def _transcoder_counts():
        completed = await transcoder_client.get_jobs(status="completed", limit=1)
        failed = await transcoder_client.get_jobs(status="failed", limit=1)
        if completed is None and failed is None:
            return None
        total = 0
        if completed and "total" in completed:
            total += completed["total"]
        if failed and "total" in failed:
            total += failed["total"]
        return total

    arm_counts, notif_counts, tc_count = await asyncio.gather(
        arm_client.get_maintenance_counts(),
        arm_client.get_notification_count(),
        _transcoder_counts(),
    )

    return {
        "orphan_logs": arm_counts.get("orphan_logs") if arm_counts else None,
        "orphan_folders": arm_counts.get("orphan_folders") if arm_counts else None,
        "unseen_notifications": notif_counts.get("unseen") if notif_counts else None,
        "cleared_notifications": notif_counts.get("cleared") if notif_counts else None,
        "stale_transcoder_jobs": tc_count,
    }


@router.get("/maintenance/orphan-logs", response_model=OrphanLogList)
async def get_orphan_logs():
    return _check_arm(await arm_client.get_orphan_logs())


@router.get("/maintenance/orphan-folders", response_model=OrphanFolderList)
async def get_orphan_folders():
    return _check_arm(await arm_client.get_orphan_folders())


@router.post("/maintenance/delete-log", response_model=MaintenanceDeleteResult)
async def delete_log(req: PathRequest):
    return _check_arm(await arm_client.delete_orphan_log(req.path))


@router.post("/maintenance/delete-folder", response_model=MaintenanceDeleteResult)
async def delete_folder(req: PathRequest):
    return _check_arm(await arm_client.delete_orphan_folder(req.path))


@router.post("/maintenance/bulk-delete-logs", response_model=MaintenanceBulkDeleteResult)
async def bulk_delete_logs(req: BulkPathRequest):
    return _check_arm(await arm_client.bulk_delete_logs(req.paths))


@router.post("/maintenance/bulk-delete-folders", response_model=MaintenanceBulkDeleteResult)
async def bulk_delete_folders(req: BulkPathRequest):
    return _check_arm(await arm_client.bulk_delete_folders(req.paths))


@router.post("/maintenance/dismiss-all-notifications", response_model=OperationResult)
async def dismiss_all_notifications():
    return _check_arm(await arm_client.dismiss_all_notifications())


@router.post("/maintenance/purge-notifications", response_model=OperationResult)
async def purge_notifications():
    return _check_arm(await arm_client.purge_cleared_notifications())


@router.post("/maintenance/cleanup-transcoder", response_model=CleanupTranscoderResult)
async def cleanup_transcoder():
    """Delete completed and failed transcoder jobs. Paginates through all results."""
    deleted = 0
    errors: list[str] = []

    for status in ("completed", "failed"):
        offset = 0
        while True:
            page = await transcoder_client.get_jobs(status=status, limit=50, offset=offset)
            if page is None:
                errors.append(f"Transcoder unreachable while fetching {status} jobs")
                break
            jobs = page.get("jobs", [])
            if not jobs:
                break
            for job in jobs:
                job_id = job.get("id") or job.get("job_id")
                if job_id and await transcoder_client.delete_job(job_id):
                    deleted += 1
                else:
                    errors.append(f"Failed to delete transcoder job {job_id}")
            offset += len(jobs)
            if offset >= page.get("total", 0):
                break

    return {"success": True, "deleted": deleted, "errors": errors}


@router.post("/maintenance/clear-raw", response_model=ClearRawResult)
async def clear_raw():
    """Clear all contents of the raw/scratch directory."""
    return _check_arm(await arm_client.clear_raw())


@router.get("/maintenance/image-cache-stats", response_model=ImageCacheStats)
def get_image_cache_stats():
    """Return image cache statistics."""
    return image_cache.stats()


@router.post("/maintenance/clear-image-cache", response_model=ImageCacheStats)
def clear_image_cache():
    """Clear all cached images."""
    return image_cache.clear()
