"""API v1 - ISO file import endpoints.

Mirrors `arm.api.v1.folder` but for `.iso` files. The ISO is identified via
MakeMKV's info pass on `iso:{path}`, persisted as a Job with
`source_type=iso`, and prescan runs in a background thread that leaves the
job in MANUAL_PAUSED for review.
"""
import logging
import threading
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import arm.config.config as cfg
from arm.api.v1._import_helpers import apply_request_metadata_to_job
from arm.database import db
from arm.models.config import Config
from arm.models.job import Job, JobState
from arm.ripper.import_prescan import (
    auto_disable_short_tracks,
    prescan_and_wait as _prescan_and_wait,
)
from arm.ripper.iso_scan import extract_metadata, validate_iso_path
from arm.ripper.makemkv import prescan_iso_disc_type

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["iso"])

# Re-exported for parity with arm.api.v1.folder. Tests may patch
# `arm.api.v1.iso.auto_disable_short_tracks` or import
# `arm.api.v1.iso._prescan_and_wait` even though both now live in
# `arm.ripper.import_prescan`.
__all__ = [
    "auto_disable_short_tracks",
    "IsoScanRequest",
    "IsoCreateRequest",
    "scan_iso_endpoint",
    "create_iso_job",
]


class IsoScanRequest(BaseModel):
    path: str


class IsoCreateRequest(BaseModel):
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


@router.post("/jobs/iso/scan")
def scan_iso_endpoint(req: IsoScanRequest):
    """Scan an ISO file: validate, extract metadata, detect disc type. No job created."""
    ingress_path = cfg.arm_config.get("INGRESS_PATH", "")
    if not ingress_path:
        return JSONResponse(
            {"success": False, "error": "INGRESS_PATH not configured"},
            status_code=400,
        )
    try:
        safe_path = validate_iso_path(req.path, ingress_path)
    except FileNotFoundError:
        return JSONResponse(
            {"success": False, "error": "ISO file not found"},
            status_code=400,
        )
    except ValueError:
        return JSONResponse(
            {"success": False, "error": "Invalid ISO path or extension"},
            status_code=422,
        )

    meta = extract_metadata(safe_path)
    info = prescan_iso_disc_type(safe_path)
    return {
        "success": True,
        "disc_type": info["disc_type"],
        "label": meta["label"],
        "title_suggestion": meta["title_suggestion"],
        "year_suggestion": meta["year_suggestion"],
        "iso_size": meta["iso_size"],
        "stream_count": info["stream_count"],
        "volume_id": info.get("volume_id"),
    }


@router.post("/jobs/iso", status_code=201)
def create_iso_job(req: IsoCreateRequest):
    """Create an ISO import job in review state."""
    ingress_path = cfg.arm_config.get("INGRESS_PATH", "")
    if not ingress_path:
        return JSONResponse(
            {"success": False, "error": "INGRESS_PATH not configured"},
            status_code=400,
        )

    try:
        safe_source_path = validate_iso_path(req.source_path, ingress_path)
    except FileNotFoundError:
        return JSONResponse(
            {"success": False, "error": "Source ISO not found"},
            status_code=400,
        )
    except ValueError:
        return JSONResponse(
            {"success": False, "error": "Path is outside the configured ingress directory or has invalid extension"},
            status_code=400,
        )

    existing = Job.query.filter(
        Job.source_path == safe_source_path,
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

    job = Job.from_iso(safe_source_path, req.disctype)
    apply_request_metadata_to_job(job, req)
    job.status = JobState.IDENTIFYING.value

    db.session.add(job)
    db.session.flush()

    config = Config(cfg.arm_config, job_id=job.job_id)
    db.session.add(config)
    db.session.commit()

    log.info("Created ISO import job %s for %s (prescanning)", job.job_id, safe_source_path)

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
