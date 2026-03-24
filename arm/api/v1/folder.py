"""API v1 — Folder import endpoints."""
import logging
import threading
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import arm.config.config as cfg
from arm.database import db
from arm.models.config import Config
from arm.models.job import Job, JobState
from arm.ripper.folder_scan import scan_folder, validate_ingress_path

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["folder"])


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


@router.post("/jobs/folder/scan")
def scan_folder_endpoint(req: FolderScanRequest):
    """Scan a folder and return disc type and metadata. No job created."""
    ingress_path = cfg.arm_config.get("INGRESS_PATH", "")
    if not ingress_path:
        return JSONResponse(
            {"success": False, "error": "INGRESS_PATH not configured"},
            status_code=400,
        )
    try:
        result = scan_folder(req.path, ingress_path)
    except FileNotFoundError:
        return JSONResponse(
            {"success": False, "error": "Folder not found or path is not accessible"},
            status_code=400,
        )
    except ValueError:
        return JSONResponse(
            {"success": False, "error": "Not a valid disc folder (no BDMV or VIDEO_TS structure found)"},
            status_code=422,
        )
    return {"success": True, **result}


@router.post("/jobs/folder", status_code=201)
def create_folder_job(req: FolderCreateRequest):
    """Create a folder import job in review state."""
    ingress_path = cfg.arm_config.get("INGRESS_PATH", "")
    if not ingress_path:
        return JSONResponse(
            {"success": False, "error": "INGRESS_PATH not configured"},
            status_code=400,
        )

    # Validate path is under ingress root
    try:
        validate_ingress_path(req.source_path, ingress_path)
    except FileNotFoundError:
        return JSONResponse(
            {"success": False, "error": "Source folder not found"},
            status_code=400,
        )
    except ValueError:
        return JSONResponse(
            {"success": False, "error": "Path is outside the configured ingress directory"},
            status_code=400,
        )

    # Check for duplicate active job with same source_path
    existing = Job.query.filter(
        Job.source_path == req.source_path,
        ~Job.finished,
    ).first()
    if existing:
        return JSONResponse(
            {
                "success": False,
                "error": f"Active job already exists for this path (job_id={existing.job_id})",
            },
            status_code=409,
        )

    # Create job
    job = Job.from_folder(req.source_path, req.disctype)
    job.title = req.title
    job.title_auto = req.title
    if req.year:
        job.year = req.year
        job.year_auto = req.year
    job.video_type = req.video_type
    if req.imdb_id:
        job.imdb_id = req.imdb_id
    if req.poster_url:
        job.poster_url = req.poster_url
    job.multi_title = req.multi_title
    job.status = JobState.IDENTIFYING.value

    db.session.add(job)
    db.session.flush()  # assigns job_id

    # Create Config (copies current arm.yaml settings for this job)
    config = Config(cfg.arm_config, job_id=job.job_id)
    db.session.add(config)
    db.session.commit()

    log.info("Created folder import job %s for %s (prescanning)", job.job_id, req.source_path)

    # Run prescan in background — populates tracks, then moves to MANUAL_WAIT
    thread = threading.Thread(
        target=_prescan_and_wait, args=(job.job_id,), daemon=True
    )
    thread.start()

    return {
        "success": True,
        "job_id": job.job_id,
        "status": job.status,
        "source_type": job.source_type,
        "source_path": job.source_path,
    }


def _prescan_and_wait(job_id: int):
    """Background: prescan tracks with MakeMKV, then move job to MANUAL_WAIT."""
    from arm.ripper.makemkv import prep_mkv, prescan_track_info

    job = Job.query.get(job_id)
    if not job:
        log.error("Prescan: job %s not found", job_id)
        return

    try:
        prep_mkv()
        prescan_track_info(job)
        job.status = JobState.MANUAL_WAIT_STARTED.value
        db.session.commit()
        log.info("Prescan complete for job %s — %d tracks found, waiting for review",
                 job_id, len(list(job.tracks)))
    except Exception as exc:
        log.error("Prescan failed for job %s: %s", job_id, exc)
        job.status = JobState.MANUAL_WAIT_STARTED.value
        job.errors = f"Prescan failed: {exc}"
        db.session.commit()
