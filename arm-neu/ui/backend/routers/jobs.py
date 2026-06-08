import logging
import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from backend.dependencies import require_transcoder_enabled
from pydantic import BaseModel

from backend.models.schemas import (
    JobDetailSchema,
    JobListResponse,
    JobSchema,
    JobTranscodeOverridesUpdate,
    MediaDetailSchema,
    MusicDetailSchema,
    MusicSearchResponse,
    MusicSearchResultSchema,
    OperationResult,
    SearchResultSchema,
    TrackSchema,
    TrackTitleUpdateRequest,
)
import httpx

from backend.services import arm_client, transcoder_client

log = logging.getLogger(__name__)

_JOB_NOT_FOUND = "Job not found"
_ARM_UNREACHABLE = "ARM service unreachable"

_404_JOB = {404: {"description": _JOB_NOT_FOUND}}
_502_ARM = {502: {"description": _ARM_UNREACHABLE}}
_404_502_ARM = {404: {"description": _JOB_NOT_FOUND}, 502: {"description": _ARM_UNREACHABLE}}

router = APIRouter(prefix="/api", tags=["jobs"])


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    status: str | None = None,
    search: str | None = None,
    video_type: str | None = None,
    disctype: str | None = None,
    days: int | None = Query(None, ge=1),
    sort_by: str | None = None,
    sort_dir: str | None = Query(None, pattern="^(asc|desc)$"),
):
    data = await arm_client.get_jobs_paginated(
        page=page, per_page=per_page, status=status, search=search,
        video_type=video_type, disctype=disctype, days=days,
        sort_by=sort_by, sort_dir=sort_dir,
    )
    if data is None:
        raise HTTPException(status_code=502, detail=_ARM_UNREACHABLE)
    return JobListResponse(
        jobs=[JobSchema.model_validate(j) for j in data.get("jobs") or []],
        total=data.get("total", 0),
        page=data.get("page", page),
        per_page=data.get("per_page", per_page),
        pages=data.get("pages", 1),
    )


@router.get("/jobs/stats")
async def get_job_stats(
    search: str | None = None,
    video_type: str | None = None,
    disctype: str | None = None,
    days: int | None = Query(None, ge=1),
):
    data = await arm_client.get_jobs_stats(
        search=search, video_type=video_type, disctype=disctype, days=days,
    )
    if data is None:
        return {"total": 0, "active": 0, "success": 0, "fail": 0, "waiting": 0}
    return data


class BulkJobRequest(BaseModel):
    job_ids: list[int] | None = None
    status: str | None = None


@router.post("/jobs/bulk-delete")
async def bulk_delete_jobs(req: BulkJobRequest):
    """Delete multiple jobs by ID list or by status."""
    job_ids = await _resolve_job_ids(req)
    deleted = 0
    errors: list[str] = []

    for job_id in job_ids:
        result = await arm_client.delete_job(job_id)
        if result is None:
            errors.append(f"ARM unreachable for job {job_id}")
        elif result.get("success") is False:
            errors.append(f"Job {job_id}: {result.get('error', 'delete failed')}")
        else:
            deleted += 1

    return {"deleted": deleted, "errors": errors}


@router.post("/jobs/bulk-purge")
async def bulk_purge_jobs(req: BulkJobRequest):
    """Purge multiple jobs - delete record + all associated files.

    Cleans up: log file, raw MKV output, transcoded intermediates,
    and final completed media folder.
    """
    job_ids = await _resolve_job_ids(req)
    purged = 0
    errors: list[str] = []

    for job_id in job_ids:
        # Read job (via the detail endpoint) to get all file paths before deleting the record.
        detail = await arm_client.get_job_detail(job_id)
        job = (detail or {}).get("job") or {}
        logfile = job.get("logfile")
        raw_path = job.get("raw_path")
        transcode_path = job.get("transcode_path")
        completed_path = job.get("path")

        # Delete job record via ARM
        result = await arm_client.delete_job(job_id)
        if result is None:
            errors.append(f"ARM unreachable for job {job_id}")
            continue
        if result.get("success") is False:
            errors.append(f"Job {job_id}: {result.get('error', 'delete failed')}")
            continue

        # Best-effort: delete all associated files
        if logfile:
            await arm_client.delete_orphan_log(logfile)
        for folder in (raw_path, transcode_path, completed_path):
            if folder:
                await arm_client.delete_orphan_folder(folder)

        purged += 1

    return {"purged": purged, "errors": errors}


async def _resolve_job_ids(req: BulkJobRequest) -> list[int]:
    """Resolve a bulk request to a list of job IDs (explicit IDs or by-status query).

    Pages through ARM at the per_page=100 cap (Query(le=100) on /jobs/paginated)
    so a `Purge All Failed` on a deployment with hundreds of failed jobs still
    catches everything, instead of getting 422'd into a silent zero.
    """
    if req.job_ids:
        return req.job_ids
    if not req.status:
        return []

    page_size = 100
    ids: list[int] = []
    page = 1
    while True:
        data = await arm_client.get_jobs_paginated(
            page=page, per_page=page_size, status=req.status,
        )
        if not data:
            return ids
        if data.get("success") is False:
            safe_status = str(req.status).replace("\n", "").replace("\r", "")
            safe_err = str(data.get("error")).replace("\n", "").replace("\r", "")
            log.warning("ARM rejected paginated lookup for status=%s: %s",
                        safe_status, safe_err)
            return ids
        page_jobs = data.get("jobs") or []
        ids.extend(j["job_id"] for j in page_jobs if "job_id" in j)
        if len(page_jobs) < page_size or page >= (data.get("pages") or page):
            return ids
        page += 1


@router.get("/jobs/{job_id}", response_model=JobDetailSchema, responses=_404_JOB)
async def get_job(job_id: int):
    detail = await arm_client.get_job_detail(job_id)
    if detail is None:
        raise HTTPException(status_code=502, detail=_ARM_UNREACHABLE)
    if detail.get("success") is False:
        raise HTTPException(status_code=404, detail=_JOB_NOT_FOUND)

    job = detail.get("job") or {}
    if not job:
        raise HTTPException(status_code=404, detail=_JOB_NOT_FOUND)

    tracks = [TrackSchema.model_validate(t) for t in (detail.get("tracks") or [])]
    job_data = JobSchema.model_validate(job).model_dump()
    return JobDetailSchema(**job_data, tracks=tracks, config=detail.get("config"))


# Tiny TTL cache for upstream progress-state to absorb dashboard polling.
# The dashboard polls every 2s per active job; multiple browser tabs
# multiply that load against arm-neu. A 1s cache caps it at one upstream
# call per job per second regardless of how many tabs poll.
_PROGRESS_CACHE: dict[int, tuple[float, dict | None]] = {}
_PROGRESS_TTL = 1.0


async def _cached_progress_state(job_id: int) -> dict | None:
    now = time.monotonic()
    cached = _PROGRESS_CACHE.get(job_id)
    if cached is not None and now - cached[0] < _PROGRESS_TTL:
        return cached[1]
    state = await arm_client.get_job_progress_state(job_id)
    _PROGRESS_CACHE[job_id] = (now, state)
    return state


@router.get("/jobs/{job_id}/progress", responses=_404_JOB)
async def get_job_progress(job_id: int):
    state = await _cached_progress_state(job_id)
    if state is None:
        raise HTTPException(status_code=502, detail=_ARM_UNREACHABLE)
    if state.get("success") is False:
        raise HTTPException(status_code=404, detail=_JOB_NOT_FOUND)

    counts_raw = state.get("track_counts") or {}
    # Ripper returns {total, ripped}; UI's progress shape uses tracks_total/tracks_ripped.
    counts = {
        "tracks_total": counts_raw.get("total", 0),
        "tracks_ripped": counts_raw.get("ripped", 0),
    }
    if state.get("disctype") == "music":
        progress_value = state.get("music_progress")
        stage_value = state.get("music_stage")
        realtime_ripped = state.get("tracks_ripped_realtime")
    else:
        progress_value = state.get("rip_progress")
        stage_value = state.get("rip_stage")
        realtime_ripped = state.get("tracks_ripped_realtime")

    # Merge DB counts with the real-time ripped count from PRGC/encoding
    # messages. During ripping the realtime count leads; after
    # completion the DB count is authoritative, so take the max.
    db_ripped = counts["tracks_ripped"] or 0
    realtime = realtime_ripped or 0
    return {
        "progress": progress_value,
        "stage": stage_value,
        "tracks_total": counts["tracks_total"],
        "tracks_ripped": max(realtime, db_ripped),
        "no_of_titles": state.get("no_of_titles"),
        "copy_progress": state.get("copy_progress"),
        "copy_stage": state.get("copy_stage"),
    }


@router.get("/jobs/{job_id}/metadata", responses=_404_502_ARM)
async def get_job_metadata(job_id: int):
    """Pass-through to ARM's merged MediaMetadata for a job."""
    data = await arm_client.get_job_metadata(job_id)
    if data is None:
        raise HTTPException(status_code=502, detail=_ARM_UNREACHABLE)
    if isinstance(data, dict) and data.get("detail") == "Job not found":
        raise HTTPException(status_code=404, detail=_JOB_NOT_FOUND)
    return data


@router.get("/jobs/{job_id}/crc-lookup", responses=_404_502_ARM)
async def crc_lookup_endpoint(job_id: int):
    """Look up a job's CRC64 hash in the community database."""
    detail = await arm_client.get_job_detail(job_id)
    if detail is None:
        raise HTTPException(status_code=502, detail=_ARM_UNREACHABLE)
    if detail.get("success") is False:
        raise HTTPException(status_code=404, detail=_JOB_NOT_FOUND)
    job = detail.get("job") or {}
    crc_id = job.get("crc_id")
    if not crc_id:
        return {"no_crc": True, "found": False, "results": [], "has_api_key": False}
    try:
        return await arm_client.lookup_crc(crc_id)
    except httpx.HTTPStatusError as exc:
        log.warning("CRC lookup for job %d failed: %d", job_id, exc.response.status_code)
        raise HTTPException(status_code=exc.response.status_code, detail="CRC lookup failed")
    except (httpx.HTTPError, httpx.ConnectError, RuntimeError, OSError) as exc:
        log.error("CRC lookup for job %d unreachable: %s", job_id, exc)
        raise HTTPException(status_code=502, detail=_ARM_UNREACHABLE)


@router.get("/metadata/search", response_model=list[SearchResultSchema], responses=_502_ARM)
async def search_metadata(
    q: Annotated[str, Query(min_length=1)],
    year: Annotated[str | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
):
    """Search OMDb/TMDb for titles matching the query (proxied through ARM)."""
    try:
        return await arm_client.search_metadata(q, year, page=page)
    except httpx.HTTPStatusError as exc:
        log.warning("Metadata search failed for q=%r: %d", q, exc.response.status_code)
        # Pass through ARM's detail message (e.g. missing API key guidance)
        upstream_detail = "Metadata search failed"
        try:
            body = exc.response.json()
            if body.get("detail"):
                upstream_detail = body["detail"]
        except Exception:
            pass
        raise HTTPException(status_code=exc.response.status_code, detail=upstream_detail)
    except (httpx.HTTPError, httpx.ConnectError, RuntimeError, OSError) as exc:
        log.error("Metadata search unreachable for q=%r: %s", q, exc)
        raise HTTPException(status_code=502, detail=_ARM_UNREACHABLE)


@router.get("/metadata/{imdb_id}", response_model=MediaDetailSchema, responses={404: {"description": "Title not found"}, 502: {"description": _ARM_UNREACHABLE}})
async def get_media_detail(imdb_id: str):
    """Fetch full details for a title by IMDb ID (proxied through ARM)."""
    try:
        result = await arm_client.get_media_detail(imdb_id)
    except httpx.HTTPStatusError as exc:
        log.warning("Metadata detail failed: %d", exc.response.status_code)
        upstream_detail = "Metadata detail failed"
        try:
            body = exc.response.json()
            if body.get("detail"):
                upstream_detail = body["detail"]
        except Exception:
            pass
        raise HTTPException(status_code=exc.response.status_code, detail=upstream_detail)
    except (httpx.HTTPError, httpx.ConnectError, RuntimeError, OSError):
        log.error("Metadata detail unreachable")
        raise HTTPException(status_code=502, detail=_ARM_UNREACHABLE)
    if not result:
        raise HTTPException(status_code=404, detail="Title not found")
    return result


@router.get("/metadata/music/search", response_model=MusicSearchResponse, responses=_502_ARM)
async def search_music_metadata(
    q: str = Query(..., min_length=1),
    artist: str | None = None,
    release_type: str | None = None,
    format: str | None = None,
    country: str | None = None,
    status: str | None = None,
    tracks: int | None = None,
    offset: int = Query(0, ge=0),
):
    """Search MusicBrainz for releases (proxied through ARM)."""
    try:
        return await arm_client.search_music_metadata(
            q, artist=artist, release_type=release_type, format=format,
            country=country, status=status, tracks=tracks, offset=offset,
        )
    except httpx.HTTPStatusError as exc:
        log.warning("Music search failed: %d", exc.response.status_code)
        raise HTTPException(status_code=exc.response.status_code, detail="Music search failed")
    except (httpx.HTTPError, httpx.ConnectError, RuntimeError, OSError):
        log.error("Music search unreachable")
        raise HTTPException(status_code=502, detail=_ARM_UNREACHABLE)


@router.get("/metadata/music/{release_id}", response_model=MusicDetailSchema, responses={404: {"description": "Release not found"}, 502: {"description": _ARM_UNREACHABLE}})
async def get_music_detail(release_id: str):
    """Fetch full release details from MusicBrainz (proxied through ARM)."""
    try:
        result = await arm_client.get_music_detail(release_id)
    except httpx.HTTPStatusError as exc:
        log.warning("Music detail failed: %d", exc.response.status_code)
        raise HTTPException(status_code=exc.response.status_code, detail="Music detail failed")
    except (httpx.HTTPError, httpx.ConnectError, RuntimeError, OSError):
        log.error("Music detail unreachable")
        raise HTTPException(status_code=502, detail=_ARM_UNREACHABLE)
    if not result:
        raise HTTPException(status_code=404, detail="Release not found")
    return result


@router.post("/jobs/{job_id}/multi-title", responses=_404_502_ARM)
async def toggle_multi_title(job_id: int, request: Request):
    """Toggle the multi_title flag on a job."""
    body = await request.json()
    result = await arm_client.toggle_multi_title(job_id, body)
    if result is None:
        raise HTTPException(status_code=502, detail=_ARM_UNREACHABLE)
    if not result.get("success"):
        status = 404 if "not found" in result.get("error", "").lower() else 400
        raise HTTPException(status_code=status, detail=result.get("error", "Failed"))
    return result


@router.put(
    "/jobs/{job_id}/tracks/{track_id}/title",
    response_model=OperationResult,
    responses=_404_502_ARM,
)
async def update_track_title(job_id: int, track_id: int, body: TrackTitleUpdateRequest):
    """Set per-track title metadata for a multi-title disc."""
    payload = body.model_dump(exclude_none=True)
    result = await arm_client.update_track_title(job_id, track_id, payload)
    if result is None:
        raise HTTPException(status_code=502, detail=_ARM_UNREACHABLE)
    if not result.get("success"):
        status = 404 if "not found" in result.get("error", "").lower() else 400
        raise HTTPException(status_code=status, detail=result.get("error", "Failed"))
    return result


@router.delete(
    "/jobs/{job_id}/tracks/{track_id}/title",
    response_model=OperationResult,
    responses=_404_502_ARM,
)
async def clear_track_title(job_id: int, track_id: int):
    """Clear per-track title metadata (revert to job-level inheritance)."""
    result = await arm_client.clear_track_title(job_id, track_id)
    if result is None:
        raise HTTPException(status_code=502, detail=_ARM_UNREACHABLE)
    if not result.get("success"):
        status = 404 if "not found" in result.get("error", "").lower() else 400
        raise HTTPException(status_code=status, detail=result.get("error", "Failed"))
    return result


@router.post("/jobs/{job_id}/tvdb-match", responses=_404_502_ARM)
async def tvdb_match(job_id: int, request: Request):
    """Run TVDB episode matching for a job (proxied to ARM)."""
    body = await request.json()
    result = await arm_client.tvdb_match(job_id, body)
    if result is None:
        raise HTTPException(status_code=502, detail=_ARM_UNREACHABLE)
    if not result.get("success"):
        status = 404 if "not found" in result.get("error", "").lower() else 400
        raise HTTPException(status_code=status, detail=result.get("error", "Failed"))
    return result


@router.get("/jobs/{job_id}/tvdb-episodes", responses=_404_502_ARM)
async def tvdb_episodes(job_id: int, season: int = Query(1, ge=1)):
    """Fetch TVDB episodes for a job's series (proxied to ARM)."""
    result = await arm_client.tvdb_episodes(job_id, season)
    if result is None:
        raise HTTPException(status_code=502, detail=_ARM_UNREACHABLE)
    if not result.get("success", True):
        status = 404 if "not found" in result.get("error", "").lower() else 400
        raise HTTPException(status_code=status, detail=result.get("error", "Failed"))
    return result


@router.get("/jobs/{job_id}/naming-preview", responses=_404_502_ARM)
async def naming_preview_for_job(job_id: int):
    """Get rendered filenames for all tracks on a job (proxied to ARM)."""
    result = await arm_client.naming_preview_for_job(job_id)
    if result is None:
        raise HTTPException(status_code=502, detail=_ARM_UNREACHABLE)
    if not result.get("success", True):
        status = 404 if "not found" in result.get("error", "").lower() else 400
        raise HTTPException(status_code=status, detail=result.get("error", "Failed"))
    return result


@router.patch("/jobs/{job_id}/naming", responses={400: {"description": "Invalid pattern"}, 404: {"description": _JOB_NOT_FOUND}, 502: {}, 503: {}})
async def update_job_naming(job_id: int, request: Request):
    """Update per-job naming pattern overrides (proxied to ARM)."""
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Request body must be a JSON object")
    result = await arm_client.update_job_naming(job_id, body)
    if result is None:
        raise HTTPException(status_code=503, detail="ARM web UI is unreachable")
    if isinstance(result, dict) and result.get("success") is False:
        detail = result.get("error") or "Action failed"
        status = 400 if result.get("invalid_vars") else (404 if "not found" in detail.lower() else 502)
        raise HTTPException(status_code=status, detail=detail)
    return result


@router.post("/naming/validate")
async def validate_naming_pattern(request: Request):
    """Validate a naming pattern against known variables (proxied to ARM)."""
    body = await request.json()
    pattern = body.get("pattern", "")
    result = await arm_client.validate_naming_pattern(pattern)
    if result is None:
        raise HTTPException(status_code=503, detail="ARM web UI is unreachable")
    return result


@router.get("/naming/variables")
async def get_naming_variables():
    """Get the list of valid naming pattern variables (proxied to ARM)."""
    result = await arm_client.get_naming_variables()
    if result is None:
        raise HTTPException(status_code=503, detail="ARM web UI is unreachable")
    return result


@router.patch(
    "/jobs/{job_id}/transcode-config",
    response_model=OperationResult,
    responses={400: {"description": "Invalid request"}, 404: {"description": _JOB_NOT_FOUND}, 502: {}, 503: {}},
    dependencies=[Depends(require_transcoder_enabled)],
)
async def update_transcode_config(job_id: int, body: JobTranscodeOverridesUpdate):
    """Set per-job transcode override settings (proxied to ARM)."""
    result = await arm_client.update_transcode_overrides(job_id, body.model_dump(exclude_none=True))
    if result is None:
        raise HTTPException(status_code=503, detail="ARM web UI is unreachable")
    if isinstance(result, dict) and result.get("success") is False:
        detail = result.get("error") or result.get("detail") or "Action failed"
        status = 404 if "not found" in detail.lower() else 502
        raise HTTPException(status_code=status, detail=detail)
    return result


@router.patch("/jobs/{job_id}/tracks/{track_id}", responses={400: {"description": "Invalid request"}, 404: {"description": "Track not found"}, 502: {}, 503: {}})
async def update_track_fields(job_id: int, track_id: int, request: Request):
    """Update editable fields (enabled, filename, ripped) on a track (proxied to ARM)."""
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Request body must be a JSON object")
    result = await arm_client.update_track_fields(job_id, track_id, body)
    if result is None:
        raise HTTPException(status_code=503, detail="ARM web UI is unreachable")
    if isinstance(result, dict) and result.get("success") is False:
        detail = result.get("error") or result.get("detail") or "Action failed"
        status = 404 if "not found" in detail.lower() else 502
        raise HTTPException(status_code=status, detail=detail)
    return result


@router.post("/jobs/{job_id}/retranscode", responses={404: {"description": "Job not found or not a video disc"}, 503: {"description": "Transcoder unavailable"}},
             dependencies=[Depends(require_transcoder_enabled)])
async def retranscode_job(job_id: int):
    """Re-send a completed ARM job to the transcoder."""
    payload = await arm_client.get_job_retranscode_info(job_id)
    if payload is None:
        raise HTTPException(status_code=502, detail=_ARM_UNREACHABLE)
    if isinstance(payload, dict) and payload.get("success") is False:
        # Ripper returns 404 ({"success": False, "error": "Job not found"})
        # or 400 ("Only video disc jobs can be re-transcoded"); either way
        # the UI just needs "can't retranscode this job".
        raise HTTPException(status_code=404, detail="Job not found or not a video disc")
    result = await transcoder_client.send_webhook(payload)
    if not result.get("success"):
        raise HTTPException(status_code=503, detail=result.get("error", "Transcoder unavailable"))
    return {"status": "ok", "message": "Transcode job queued"}
