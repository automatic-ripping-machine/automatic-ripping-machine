"""Worker pool status endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from auth import get_current_user
from config import settings

router = APIRouter()


@router.get("/workers")
async def get_workers(request: Request, _role: Annotated[str, Depends(get_current_user)]):
    """Return per-worker status for dashboard display."""
    worker = request.app.state.worker
    return {
        "max_concurrent": settings.max_concurrent,
        "active_count": worker.active_count if worker else 0,
        "workers": worker.active_jobs if worker else [],
    }
