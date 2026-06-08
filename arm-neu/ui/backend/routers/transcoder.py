from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.dependencies import require_transcoder_enabled
from backend.models.files import OperationResult
from backend.models.schemas import LogContentResponse, LogFileSchema, StructuredLogResponse, TranscoderJobListResponse, TranscoderStatsResponse
from backend.models.transcoder import (
    DeleteResult,
    RetranscodeResult,
    RetryResult,
    TranscoderJobForArmResponse,
    WorkersResponse,
)
from backend.services import transcoder_client

router = APIRouter(
    prefix="/api/transcoder",
    tags=["transcoder"],
    dependencies=[Depends(require_transcoder_enabled)],
)


@router.get("/workers", response_model=WorkersResponse)
async def get_workers() -> dict[str, Any]:
    """Per-worker status for dashboard display."""
    data = await transcoder_client.get_workers()
    if data is None:
        return {"max_concurrent": 0, "active_count": 0, "workers": []}
    return data


@router.get("/stats", response_model=TranscoderStatsResponse)
async def get_stats():
    stats = await transcoder_client.get_stats()
    return TranscoderStatsResponse(
        online=stats is not None,
        stats=stats,
    )


@router.get("/jobs", response_model=TranscoderJobListResponse)
async def list_jobs(
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    data = await transcoder_client.get_jobs(status=status, limit=limit, offset=offset)
    if data is None:
        return TranscoderJobListResponse(jobs=[], total=0)
    return TranscoderJobListResponse(
        jobs=data.get("jobs", []),
        total=data.get("total", 0),
    )


@router.post(
    "/jobs/{job_id}/retry",
    response_model=RetryResult,
    responses={503: {"description": "Transcoder offline"}},
)
async def retry_job(job_id: int) -> dict[str, Any]:
    result = await transcoder_client.retry_job(job_id)
    if result is None:
        raise HTTPException(status_code=503, detail="Transcoder offline")
    return result


@router.delete(
    "/jobs/{job_id}",
    response_model=DeleteResult,
    responses={503: {"description": "Transcoder offline or job not found"}},
)
async def delete_job(job_id: int) -> dict[str, str]:
    success = await transcoder_client.delete_job(job_id)
    if not success:
        raise HTTPException(status_code=503, detail="Transcoder offline or job not found")
    return {"status": "deleted"}


@router.get("/logs", response_model=list[LogFileSchema])
async def list_logs():
    data = await transcoder_client.list_logs()
    if data is None:
        return []
    return data


@router.get("/logs/{filename}/structured", response_model=StructuredLogResponse, responses={404: {"description": "Log not found or transcoder offline"}})
async def get_structured_log(
    filename: str,
    mode: str = Query("tail", pattern="^(tail|full)$"),
    lines: int = Query(100, ge=1, le=10000),
    level: str | None = Query(None),
    search: str | None = Query(None),
):
    data = await transcoder_client.read_structured_log(
        filename, mode=mode, lines=lines, level=level, search=search
    )
    if data is None:
        raise HTTPException(status_code=404, detail="Log not found or transcoder offline")
    return data


@router.get("/logs/{filename}", response_model=LogContentResponse, responses={404: {"description": "Log not found or transcoder offline"}})
async def get_log(
    filename: str,
    mode: str = Query("tail", pattern="^(tail|full)$"),
    lines: int = Query(100, ge=1, le=10000),
):
    data = await transcoder_client.read_log(filename, mode=mode, lines=lines)
    if data is None:
        raise HTTPException(status_code=404, detail="Log not found or transcoder offline")
    return data


@router.post(
    "/jobs/{job_id}/retranscode",
    response_model=RetranscodeResult,
    responses={
        400: {"description": "Invalid job status"},
        404: {"description": "Transcoder job not found"},
        503: {"description": "Transcoder unavailable"},
    },
)
async def retranscode_transcoder_job(job_id: int):
    """Re-queue a completed or failed transcoder job for re-transcoding."""
    job = await transcoder_client.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Transcoder job not found or transcoder offline")

    status = job.get("status", "")
    if status not in ("completed", "failed"):
        raise HTTPException(status_code=400, detail=f"Cannot re-transcode job with status '{status}'")

    payload = {
        "title": job.get("title", "Unknown"),
        "body": job.get("title", "Unknown"),
        "path": job.get("source_path", ""),
        "job_id": job.get("arm_job_id") or job.get("id"),
        "status": "success",
        "video_type": job.get("video_type", "movie"),
        "year": job.get("year", ""),
        "disctype": job.get("disctype", "bluray"),
    }
    result = await transcoder_client.send_webhook(payload)
    if not result.get("success"):
        raise HTTPException(status_code=503, detail=result.get("error", "Transcoder unavailable"))
    return {"status": "ok", "message": "Transcode job re-queued"}


@router.get("/job-for-arm/{arm_job_id}", response_model=TranscoderJobForArmResponse)
async def get_transcoder_job_for_arm(arm_job_id: int) -> dict[str, Any]:
    """Look up the transcoder job for a given ARM job ID.

    IDs are unified: the transcoder stores ARM's job_id as its own primary key,
    so filtering on job_id returns at most one record and never correlates with
    an unrelated earlier job when the current ARM job has not yet reached the
    transcoder.

    Returns `progress` so the job detail page can render a transcoder progress
    bar without an extra round-trip.
    """
    data = await transcoder_client.get_jobs(job_id=arm_job_id, limit=1)
    if not data or not data.get("jobs"):
        return {"found": False}
    job = data["jobs"][0]
    return {
        "found": True,
        "logfile": job.get("logfile"),
        "transcoder_job_id": job.get("id"),
        "status": job.get("status"),
        "phase": job.get("phase"),
        "progress": job.get("progress"),
        "current_fps": job.get("current_fps"),
    }


@router.get("/handbrake-presets", response_model=dict[str, list[str]])
async def get_handbrake_presets() -> dict[str, list[str]]:
    """List HandBrakeCLI built-in preset names from the transcoder.

    Empty dict when the transcoder is offline or running an older version
    that doesn't expose the endpoint - the UI falls through to free-text
    entry in that case.
    """
    result = await transcoder_client.list_handbrake_presets()
    return result or {}
