"""API v1 - Folder import endpoints."""
import logging
import threading
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import arm.config.config as cfg
from arm.api.v1._import_helpers import apply_request_metadata_to_job
from arm.database import db
from arm.models.config import Config
from arm.models.job import Job, JobState
from arm.ripper.folder_scan import scan_folder, validate_ingress_path
from arm.ripper.import_prescan import (
    auto_disable_short_tracks,
    prescan_and_wait as _prescan_and_wait,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["folder"])

# Re-exported for backward compatibility with existing tests that patch
# `arm.api.v1.folder.auto_disable_short_tracks` and import
# `arm.api.v1.folder._prescan_and_wait`. The canonical home for both is
# `arm.ripper.import_prescan`.
__all__ = [
    "auto_disable_short_tracks",
    "FolderScanRequest",
    "FolderCreateRequest",
    "FolderScanResult",
    "FolderJobCreated",
    "scan_folder_endpoint",
    "create_folder_job",
]


class FolderScanRequest(BaseModel):
    path: str


class FolderCreateRequest(BaseModel):
    source_path: str
    title: str
    year: Optional[str] = None
    video_type: str
    disctype: str
    imdb_id: Optional[str] = None
    poster_url: Optional[str] = None
    multi_title: bool = False
    season: Optional[int] = None
    disc_number: Optional[int] = None
    disc_total: Optional[int] = None


class FolderScanResult(BaseModel):
    """Folder scan response.

    Mirrors the maintenance + jobs endpoints' invariant: HTTP status
    carries the success/failure signal, the body carries the data.
    Callers reading legacy `success`/`error` keys: failure paths now
    return a FastAPI error envelope (`{"detail": "..."}`) with the
    appropriate 4xx status code.
    """
    disc_type: str
    label: Optional[str] = None
    title_suggestion: Optional[str] = None
    year_suggestion: Optional[str] = None
    folder_size_bytes: int = 0
    stream_count: int = 0
    disc_number: Optional[int] = None
    disc_total: Optional[int] = None
    season: Optional[int] = None


class FolderJobCreated(BaseModel):
    """Folder import job creation response."""
    job_id: int
    status: str
    source_type: str
    source_path: str


@router.post("/jobs/folder/scan", response_model=FolderScanResult)
def scan_folder_endpoint(req: FolderScanRequest):
    """Scan a folder and return disc type and metadata. No job created."""
    ingress_path = cfg.arm_config.get("INGRESS_PATH", "")
    if not ingress_path:
        raise HTTPException(status_code=400, detail="INGRESS_PATH not configured")
    try:
        return scan_folder(req.path, ingress_path)
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="Folder not found or path is not accessible")
    except ValueError:
        raise HTTPException(status_code=422, detail="Not a valid disc folder (no BDMV or VIDEO_TS structure found)")


@router.post("/jobs/folder", status_code=201, response_model=FolderJobCreated)
def create_folder_job(req: FolderCreateRequest):
    """Create a folder import job in review state."""
    ingress_path = cfg.arm_config.get("INGRESS_PATH", "")
    if not ingress_path:
        raise HTTPException(status_code=400, detail="INGRESS_PATH not configured")

    # Validate path is under ingress root
    try:
        safe_source_path = validate_ingress_path(req.source_path, ingress_path)
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="Source folder not found")
    except ValueError:
        raise HTTPException(status_code=400, detail="Path is outside the configured ingress directory")

    # Check for duplicate active job with same source_path
    existing = Job.query.filter(
        Job.source_path == safe_source_path,
        ~Job.finished,
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Active job already exists for this path (job_id={existing.job_id})",
        )

    # Create job
    job = Job.from_folder(safe_source_path, req.disctype)
    apply_request_metadata_to_job(job, req)
    job.status = JobState.IDENTIFYING.value

    db.session.add(job)
    db.session.flush()  # assigns job_id

    # Create Config (copies current arm.yaml settings for this job)
    config = Config(cfg.arm_config, job_id=job.job_id)
    db.session.add(config)
    db.session.commit()

    log.info("Created folder import job %s for %s (prescanning)", job.job_id, safe_source_path)

    # Run prescan in background - populates tracks, then moves to MANUAL_PAUSED
    thread = threading.Thread(
        target=_prescan_and_wait, args=(job.job_id,), daemon=True
    )
    thread.start()

    return {
        "job_id": job.job_id,
        "status": job.status,
        "source_type": job.source_type,
        "source_path": job.source_path,
    }
