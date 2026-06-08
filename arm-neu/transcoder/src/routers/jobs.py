"""Job management and webhook endpoints."""

import json
import logging
import os
import re
from pathlib import Path
from typing import Annotated, Optional

from arm_contracts import TranscodeJobConfig, WebhookPayload
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy import select, delete, func

from auth import get_current_user, require_admin, verify_webhook_secret
from config import settings
from constants import MAX_WEBHOOK_PAYLOAD_SIZE
from database import get_db
from models import JobStatus, TranscodeJobDB
from version import (
    ACCEPT_MISSING_VERSION_HEADER,
    ACCEPTED_VERSIONS,
    API_VERSION,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def require_api_version(
    x_api_version: Optional[str] = Header(default=None, alias="X-Api-Version"),
) -> str:
    """Validate the X-Api-Version header on cross-service webhook calls.

    Returns the version string (or the current API_VERSION if header is
    missing-and-accepted) so endpoints can branch on it if needed later.

    Rejects with 400:
      - Any explicit version not in ACCEPTED_VERSIONS (e.g. v1).
      - Missing header, only if ACCEPT_MISSING_VERSION_HEADER is False.
    """
    if x_api_version is None:
        if ACCEPT_MISSING_VERSION_HEADER:
            return API_VERSION
        raise HTTPException(
            status_code=400,
            detail=(
                f"X-Api-Version header is required. "
                f"Supported versions: {sorted(ACCEPTED_VERSIONS)}. "
                f"Upgrade arm-neu to a version that sends the handshake header."
            ),
        )
    if x_api_version not in ACCEPTED_VERSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported X-Api-Version: {x_api_version!r}. "
                f"This transcoder supports: {sorted(ACCEPTED_VERSIONS)}. "
                f"Upgrade arm-neu to a version that supports API v2."
            ),
        )
    return x_api_version


def _extract_media_title(body: str | None) -> str | None:
    """Extract media title from ARM notification body text."""
    if not body:
        return None
    for pattern in [
        r"^(.+?)\s+rip complete",           # ARM rip notification
        r"^(.+?)\s+processing complete",     # ARM transcode notification
        r"Rip of (.+?) complete",            # legacy format
    ]:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    # No notification pattern matched — use body directly, stripping trailing year
    cleaned = re.sub(r"\s*\(\d{4}\)\s*$", "", body).strip()
    return cleaned or None


@router.post("/webhook/arm", responses={400: {"description": "Invalid payload"}, 413: {"description": "Payload too large"}, 503: {"description": "Transcoder not ready"}})
async def arm_webhook(
    request: Request,
    _verified: Annotated[bool, Depends(verify_webhook_secret)],
    api_version: Annotated[str, Depends(require_api_version)],
):
    """
    Receive webhook from ARM's JSON_URL or BASH_SCRIPT curl.

    Expected payload formats:

    1. Apprise JSON format:
    {
        "title": "ARM notification",
        "body": "Rip of Movie Title (2024) complete",
        "type": "info"
    }

    2. Custom format from BASH_SCRIPT:
    {
        "title": "Movie Title",
        "path": "/home/arm/media/raw/Movie Title (2024)",
        "job_id": "123",
        "status": "success"
    }
    """
    worker = request.app.state.worker

    # Validate request size; cap is a sanity guard, not a gate on legitimate
    # payloads (a 4K Blu-ray with 70+ titles ships ~12KB of typed tracks[]).
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_WEBHOOK_PAYLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"Payload too large (max {MAX_WEBHOOK_PAYLOAD_SIZE // 1024}KB)",
        )

    try:
        payload_dict = await request.json()
        payload = WebhookPayload(**payload_dict)
    except ValidationError as exc:
        # Structured 422 with field-level errors - matches the prior shape
        # used for config_overrides validation, now applied to the whole
        # payload since WebhookPayload is fully typed end-to-end.
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Invalid webhook payload",
                "errors": [
                    {"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]}
                    for e in exc.errors()
                ],
            },
        )
    except Exception as e:
        logger.warning(f"Invalid webhook payload: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid payload: {e}")

    body = payload.effective_body
    logger.info(f"Received webhook: {payload.title} (body={'present' if body else 'empty'})")

    # Check if this is a completion notification
    is_complete = (
        "complete" in payload.title.lower() or
        (body and "complete" in body.lower()) or
        payload.status == "success"
    )
    if not is_complete:
        logger.debug(f"Ignoring non-completion webhook: {payload.title}")
        return {"status": "ignored", "reason": "not a completion event"}

    if not payload.input_path:
        logger.warning(f"Webhook missing input_path: {payload.title}")
        return {"status": "error", "reason": "input_path required"}

    # Contracts validator already rejected absolute paths and `..`
    # segments, so we trust the value and join straight to the share root.
    full_path = str(Path(settings.raw_path) / payload.input_path)
    media_title = _extract_media_title(body)

    # config_overrides is already typed by WebhookPayload.
    typed_overrides: TranscodeJobConfig | None = payload.config_overrides

    if worker is None or not worker.is_running:
        raise HTTPException(status_code=503, detail="Transcoder not ready")

    job_title = media_title or payload.title
    job_id, created = await worker.queue_job(
        job_id=payload.job_id,
        source_path=full_path,
        title=job_title,
        video_type=payload.video_type,
        year=payload.year,
        disctype=payload.disctype,
        poster_url=payload.poster_url,
        # model_dump() (no exclusions) preserves the full validated shape, including
        # explicit null fields and the default-expanded tier keys. This matches the
        # pre-typed behavior most closely - the only observable change is that missing
        # tiers now default to empty dicts in the persisted JSON, which downstream
        # merge code treats as a no-op.
        config_overrides=typed_overrides.model_dump() if typed_overrides else None,
        multi_title=bool(payload.multi_title),
        # Worker persists tracks as JSON dicts; dump the typed models.
        tracks=[t.model_dump() for t in payload.tracks] if payload.tracks else None,
        output_path=payload.output_path,
        title_name=payload.title_name,
    )

    return {
        "status": "queued" if created else "already_queued",
        "job_id": job_id,
        "input_path": payload.input_path,
        "queue_size": worker.queue_size,
    }


@router.get("/jobs")
async def list_jobs(
    _role: Annotated[str, Depends(get_current_user)],
    status: JobStatus | None = None,
    job_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """List all transcode jobs, optionally filtered by status."""
    # Validate pagination
    if limit > 500:
        limit = 500
    if limit < 1:
        limit = 1
    if offset < 0:
        offset = 0

    async with get_db() as db:
        query = select(TranscodeJobDB)
        if status:
            query = query.where(TranscodeJobDB.status == status)
        if job_id is not None:
            query = query.where(TranscodeJobDB.id == job_id)
        query = query.order_by(TranscodeJobDB.created_at.desc())

        # Get total count
        count_query = select(func.count()).select_from(TranscodeJobDB)
        if status:
            count_query = count_query.where(TranscodeJobDB.status == status)
        if job_id is not None:
            count_query = count_query.where(TranscodeJobDB.id == job_id)
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # Apply pagination
        query = query.limit(limit).offset(offset)

        result = await db.execute(query)
        jobs = result.scalars().all()

        return {
            "jobs": [
                {
                    "id": job.id,
                    "title": job.title,
                    "source_path": job.source_path,
                    "status": job.status,
                    "phase": job.phase,
                    "progress": job.progress,
                    "current_fps": job.current_fps,
                    "created_at": job.created_at.isoformat() if job.created_at else None,
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                    "error": job.error,
                    "logfile": job.logfile,
                    "video_type": job.video_type,
                    "year": job.year,
                    "disctype": job.disctype,
                    "output_path": job.output_path,
                    "total_tracks": job.total_tracks,
                    "poster_url": job.poster_url,
                    "config_overrides": json.loads(job.config_overrides) if job.config_overrides else None,
                }
                for job in jobs
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }


@router.post("/jobs/{job_id}/retry", responses={400: {"description": "Job not in failed state or retry limit reached"}, 404: {"description": "Job not found"}, 503: {"description": "Transcoder not ready"}})
async def retry_job(
    job_id: int,
    request: Request,
    _role: Annotated[str, Depends(require_admin)],
):
    """Retry a failed job (admin only)."""
    worker = request.app.state.worker
    if worker is None or not worker.is_running:
        raise HTTPException(status_code=503, detail="Transcoder not ready")

    async with get_db() as db:
        result = await db.execute(
            select(TranscodeJobDB).where(TranscodeJobDB.id == job_id)
        )
        job = result.scalar_one_or_none()

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if job.status != JobStatus.FAILED:
            raise HTTPException(status_code=400, detail="Job is not in failed state")

        # Check retry limit
        if job.retry_count >= settings.max_retry_count:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum retry limit reached ({settings.max_retry_count})"
            )

        # Re-queue via queue_job (handles status reset internally)
        await worker.queue_job(
            job_id=job.id,
            source_path=job.source_path,
            title=job.title,
        )

        return {"status": "queued", "job_id": job.id, "retry_count": job.retry_count + 1}


@router.delete("/jobs/{job_id}", responses={400: {"description": "Cannot delete job in progress"}, 404: {"description": "Job not found"}})
async def delete_job(
    job_id: int,
    _role: Annotated[str, Depends(require_admin)],
):
    """Delete a job from the database (admin only)."""
    async with get_db() as db:
        result = await db.execute(
            select(TranscodeJobDB).where(TranscodeJobDB.id == job_id)
        )
        job = result.scalar_one_or_none()

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if job.status == JobStatus.PROCESSING:
            raise HTTPException(status_code=400, detail="Cannot delete job in progress")

        await db.execute(delete(TranscodeJobDB).where(TranscodeJobDB.id == job_id))
        await db.commit()

        return {"status": "deleted", "job_id": job_id}
