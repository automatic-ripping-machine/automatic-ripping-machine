"""Transcoding statistics endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, func

from auth import get_current_user
from config import settings
from database import get_db
from models import JobStatus, TranscodeJobDB

router = APIRouter()


@router.get("/stats")
async def get_stats(request: Request, _role: Annotated[str, Depends(get_current_user)]):
    """Get transcoding statistics."""
    worker = request.app.state.worker
    async with get_db() as db:
        result = await db.execute(
            select(TranscodeJobDB.status, func.count(TranscodeJobDB.id))
            .group_by(TranscodeJobDB.status)
        )
        status_counts = dict(result.all())

        return {
            "pending": status_counts.get(JobStatus.PENDING, 0),
            "processing": status_counts.get(JobStatus.PROCESSING, 0),
            "completed": status_counts.get(JobStatus.COMPLETED, 0),
            "failed": status_counts.get(JobStatus.FAILED, 0),
            "cancelled": status_counts.get(JobStatus.CANCELLED, 0),
            "worker_running": worker is not None and worker.is_running,
            "current_job": worker.current_job if worker else None,
            "active_count": worker.active_count if worker else 0,
            "max_concurrent": settings.max_concurrent,
        }
