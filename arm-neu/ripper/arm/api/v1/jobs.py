"""API v1 - Job endpoints.

Most handlers use sync def so FastAPI runs them in a threadpool.
Heavy I/O endpoints (fix-permissions, remote DB send) use async def
with asyncio.to_thread to avoid blocking the event loop.
"""
import asyncio
import json
import math
import threading
from datetime import datetime, timedelta
from typing import Annotated

from arm_contracts import (
    Job as JobContract,
    JobProgressState,
    JobStatus,
    Track as TrackContract,
    TrackCounts,
    TranscodeCallbackPayload,
)
from arm_contracts.enums import SkipReason, SourceType, TrackStatus
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy import func, or_

from arm.api.dependencies import require_api_version
import arm.config.config as cfg
from arm.constants import SINGLE_TRACK_VIDEO_TYPES
from arm.database import db
from arm.enums import AudioFormat, RipMethod, SpeedProfile
from arm_contracts.enums import Disctype
from arm.models.job import Job, JobState
from arm.models.track import Track
from arm.models.notifications import Notifications
from arm.ripper.folder_ripper import rip_folder
from arm.ripper.iso_ripper import rip_iso
from arm.services import jobs as svc_jobs
from arm.services import files as svc_files
from arm.services import progress_reader

_JOB_NOT_FOUND = "Job not found"
_NOT_WAITING = "Job is not in waiting state"


def _rip_folder_by_id(job_id: int):
    """Re-query job by ID in the thread's own session, then run rip_folder."""
    import logging
    # Daemon threads are tolerant of delays - use the higher timeout
    db.session.commit_timeout = 90
    try:
        job = Job.query.get(job_id)
        if not job:
            logging.error("rip_folder thread: job %s not found", job_id)
            return
        rip_folder(job)
    finally:
        db.session.remove()


def _rip_iso_by_id(job_id: int):
    """Re-query job by ID in the thread's own session, then run rip_iso."""
    import logging
    db.session.commit_timeout = 90
    try:
        job = Job.query.get(job_id)
        if not job:
            logging.error("rip_iso thread: job %s not found", job_id)
            return
        rip_iso(job)
    finally:
        db.session.remove()


def _auto_flag_tracks(job, mainfeature: bool):
    """Re-flag track enabled state based on MAINFEATURE + video type.

    When mainfeature is on AND the disc is a single-title type (not
    multi-title), only the best track is enabled.  Otherwise all tracks
    are enabled.
    """
    is_single = getattr(job, 'video_type', None) in SINGLE_TRACK_VIDEO_TYPES
    is_multi = getattr(job, 'multi_title', False)
    if mainfeature and is_single and not is_multi:
        for t in job.tracks:
            t.enabled = False
        best = Track.query.filter_by(job_id=job.job_id).order_by(
            Track.chapters.desc(),
            Track.length.desc(),
            Track.filesize.desc(),
            Track.track_number.asc(),
        ).first()
        if best:
            best.enabled = True
    else:
        for t in job.tracks:
            t.enabled = True
    db.session.flush()

router = APIRouter(prefix="/api/v1", tags=["jobs"])


_ACTIVE_STATUSES = {
    JobState.VIDEO_RIPPING.value,
    JobState.AUDIO_RIPPING.value,
    JobState.TRANSCODE_ACTIVE.value,
    JobState.MANUAL_PAUSED.value,
    JobState.MAKEMKV_THROTTLED.value,
}
_WAITING_STATUSES = {
    JobState.MANUAL_PAUSED.value,
    JobState.MAKEMKV_THROTTLED.value,
    JobState.TRANSCODE_WAITING.value,
}

_SORTABLE_COLUMNS = {
    "title": Job.title,
    "year": Job.year,
    "status": Job.status,
    "video_type": Job.video_type,
    "disctype": Job.disctype,
    "start_time": Job.start_time,
}

HIDDEN_CONFIG_FIELDS = {
    "EMBY_PASSWORD", "EMBY_API_KEY", "OMDB_API_KEY",
    "TMDB_API_KEY", "TVDB_API_KEY", "MAKEMKV_PERMA_KEY",
    "ARM_API_KEY", "EMBY_USERID", "EMBY_USERNAME",
}


def _job_to_dict(job):
    """Serialize a Job record to a wire dict via the shared JobContract.

    Builds via Pydantic (mode='json') so datetimes round-trip as ISO
    strings and any column not in the contract is silently dropped
    (extra='ignore'), keeping the wire shape stable as the ORM grows.

    transcode_overrides arrives from the DB as a JSON string; pre-parse
    it to a dict so the contract's `dict | None` type validates. Legacy-
    key stripping is consumer-side (arm-ui) and not the producer's job.

    expected_titles is a db.relationship (not a column), so it has to be
    added explicitly. Pydantic's from_attributes=True on ExpectedTitle
    handles the per-row validation.
    """
    data = {
        col.name: getattr(job, col.name)
        for col in Job.__table__.columns
    }
    raw_overrides = data.get("transcode_overrides")
    if isinstance(raw_overrides, str):
        try:
            data["transcode_overrides"] = json.loads(raw_overrides)
        except (json.JSONDecodeError, TypeError):
            data["transcode_overrides"] = None
    data["expected_titles"] = list(job.expected_titles or [])

    # Project MediaMetadata into the JobContract's legacy flat fields so the
    # wire shape stays back-compat after the columns moved into the blob.
    # Only the three dropped columns (poster_url/artist/album) need this -
    # year/imdb_id/video_type are still real columns and remain authoritative.
    meta = job.media_metadata
    if meta is not None:
        for legacy_field in ("poster_url", "artist", "album"):
            value = getattr(meta, legacy_field, None)
            if value not in (None, "", []):
                data[legacy_field] = value
    return JobContract.model_validate(data).model_dump(mode="json")


@router.get('/jobs')
def list_jobs(status: str = None, q: str = None):
    """List jobs, optionally filtered by status or search query."""
    if q:
        return svc_jobs.search(q)
    elif status == 'fail':
        return svc_jobs.get_x_jobs(JobState.FAILURE.value)
    elif status == 'success':
        return svc_jobs.get_x_jobs(JobState.SUCCESS.value)
    else:
        return svc_jobs.get_x_jobs('joblist')


@router.get('/jobs/active')
def get_active_jobs():
    """Return jobs with active statuses, including track counts.

    Used by the dashboard to show currently running/waiting jobs.
    Track counts reflect only rippable tracks (enabled and above
    MINLENGTH), matching the UI's progress semantics.
    """
    jobs = Job.query.filter(Job.status.in_(_ACTIVE_STATUSES)).all()
    result = []
    for job in jobs:
        job_data = _job_to_dict(job)
        job_data["track_counts"] = svc_jobs.track_counts(job)
        result.append(job_data)
    return {"jobs": result}


def _apply_job_filters(query, status, search, video_type, disctype, days):
    """Apply the shared filter set used by /jobs/paginated and /jobs/stats.

    Status accepts the grouped values 'active' and 'waiting' (which expand
    to multiple raw statuses) as well as any raw status value.
    """
    if status:
        s = status.lower()
        if s == "active":
            query = query.filter(func.lower(Job.status).in_(list(_ACTIVE_STATUSES - _WAITING_STATUSES)))
        elif s == "waiting":
            query = query.filter(func.lower(Job.status).in_(list(_WAITING_STATUSES)))
        else:
            query = query.filter(func.lower(Job.status) == s)
    if video_type:
        query = query.filter(func.lower(Job.video_type) == video_type.lower())
    if disctype:
        query = query.filter(func.lower(Job.disctype) == disctype.lower())
    if days:
        cutoff = datetime.now() - timedelta(days=days)
        query = query.filter(Job.start_time >= cutoff)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Job.title.ilike(pattern),
                Job.title_auto.ilike(pattern),
                Job.title_manual.ilike(pattern),
                Job.label.ilike(pattern),
            )
        )
    return query


@router.get('/jobs/paginated')
def get_jobs_paginated(
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 25,
    status: str | None = None,
    search: str | None = None,
    video_type: str | None = None,
    disctype: str | None = None,
    days: Annotated[int | None, Query(ge=1)] = None,
    sort_by: str | None = None,
    sort_dir: Annotated[str | None, Query(pattern="^(asc|desc)$")] = None,
):
    """Paginated job list with filtering and sorting.

    Supports status grouping (active = active+ripping+transcoding,
    waiting = waiting+waiting_transcode), text search across title fields,
    and sorting by title/year/status/video_type/disctype/start_time.
    """
    query = _apply_job_filters(
        db.session.query(Job), status, search, video_type, disctype, days,
    )
    total = query.count()

    # Sorting
    col = _SORTABLE_COLUMNS.get(sort_by, Job.start_time)
    if sort_dir == "asc":
        query = query.order_by(col.asc().nulls_last())
    else:
        query = query.order_by(col.desc().nulls_last())

    jobs = query.offset((page - 1) * per_page).limit(per_page).all()
    pages = max(1, math.ceil(total / per_page)) if total else 1

    job_dicts = []
    for j in jobs:
        d = _job_to_dict(j)
        # Surface rippable-subset counts so the list UI can render
        # "ripped/total" without a per-row roundtrip. Matches the shape
        # /jobs/active and /jobs/{id}/detail emit.
        d["track_counts"] = svc_jobs.track_counts(j)
        job_dicts.append(d)

    return {
        "jobs": job_dicts,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
    }


@router.get('/jobs/stats')
def get_jobs_stats(
    search: str | None = None,
    video_type: str | None = None,
    disctype: str | None = None,
    days: Annotated[int | None, Query(ge=1)] = None,
):
    """Job counts bucketed by status category, respecting the same filters
    as /jobs/paginated.

    Returned buckets:
      - total:   matching jobs across all statuses
      - active:  active + ripping + transcoding (in-flight, not waiting)
      - waiting: waiting + waiting_transcode
      - success: completed successfully
      - fail:    failed

    Used by the dashboard's filter-aware count tiles. Status filter is
    intentionally omitted - the endpoint exists to count by status.
    """
    base = _apply_job_filters(
        db.session.query(Job), None, search, video_type, disctype, days,
    )
    total = base.count()
    active_set = list(_ACTIVE_STATUSES - _WAITING_STATUSES)
    return {
        "total": total,
        "active": base.filter(func.lower(Job.status).in_(active_set)).count(),
        "waiting": base.filter(func.lower(Job.status).in_(list(_WAITING_STATUSES))).count(),
        "success": base.filter(func.lower(Job.status) == "success").count(),
        "fail": base.filter(func.lower(Job.status) == "fail").count(),
    }


@router.delete('/jobs/{job_id}')
def delete_job(job_id: int):
    """Delete a job by ID."""
    return svc_jobs.delete_job(str(job_id), 'delete')


@router.get('/jobs/{job_id}/metadata')
def get_job_metadata(job_id: int):
    """Return the merged MediaMetadata for a job (auto + manual overrides)."""
    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"detail": _JOB_NOT_FOUND}, status_code=404)
    return JSONResponse(job.media_metadata.model_dump(mode='json'), status_code=200)


@router.post('/jobs/{job_id}/abandon')
def abandon_job(job_id: int):
    """Abandon a running job."""
    return svc_jobs.abandon_job(str(job_id))


@router.post('/jobs/{job_id}/start')
def start_waiting_job(job_id: int):
    """Start a job that is in 'waiting' status."""
    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": _JOB_NOT_FOUND}, status_code=404)

    if job.status != JobState.MANUAL_PAUSED.value:
        return JSONResponse({"success": False, "error": _NOT_WAITING}, status_code=409)

    if job.source_type in (SourceType.folder.value, SourceType.iso.value):
        # Import jobs (folder + ISO) have no running ripper thread - the
        # prescan ran synchronously and parked the job in MANUAL_PAUSED.
        # Spawn a fresh thread to drive the rip phase. Pass job_id, not
        # the ORM object — the thread has its own session scope and the
        # original object would be detached.
        job.status = JobState.VIDEO_RIPPING.value
        db.session.commit()
        job_id = job.job_id
        target = (
            _rip_iso_by_id if job.source_type == SourceType.iso.value else _rip_folder_by_id
        )
        thread = threading.Thread(target=target, args=(job_id,), daemon=True)
        thread.start()
        return {"success": True, "job_id": job_id, "status": job.status}

    # Disc rip — existing behavior (signal running ripper thread to proceed)
    svc_files.database_updater({"manual_start": True}, job)
    return {"success": True, "job_id": job.job_id}


@router.post('/jobs/{job_id}/pause')
def pause_waiting_job(job_id: int, body: dict | None = None):
    """Set or toggle per-job pause for a job in 'waiting' status.

    If the request body contains {"paused": true/false}, use that value
    explicitly.  Otherwise toggle the current manual_pause flag.
    Explicit mode is needed when the UI wants to resume a job that is
    paused by the global flag (manual_pause is already false, so a
    blind toggle would set it to true instead of resuming).
    """
    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": _JOB_NOT_FOUND}, status_code=404)

    if job.status != JobState.MANUAL_PAUSED.value:
        return JSONResponse({"success": False, "error": _NOT_WAITING}, status_code=409)

    if body and "paused" in body:
        new_val = bool(body["paused"])
    else:
        new_val = not (getattr(job, 'manual_pause', False) or False)

    updates = {"manual_pause": new_val}
    if not new_val:
        # Resuming - reset wait_start_time so the UI countdown restarts from now
        from datetime import datetime
        updates["wait_start_time"] = datetime.now()
    svc_files.database_updater(updates, job)
    return {"success": True, "job_id": job.job_id, "paused": new_val}


@router.post('/jobs/{job_id}/cancel')
def cancel_waiting_job(job_id: int):
    """Cancel a job that is in 'waiting' status."""
    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": _JOB_NOT_FOUND}, status_code=404)

    if job.status != JobState.MANUAL_PAUSED.value:
        return JSONResponse({"success": False, "error": _NOT_WAITING}, status_code=409)

    notification = Notifications(
        f"Job: {job.job_id} was cancelled",
        f"'{job.title}' was cancelled by user during manual-wait"
    )
    db.session.add(notification)
    svc_files.database_updater({"status": JobState.FAILURE.value}, job)

    return {"success": True, "job_id": job.job_id}


@router.patch('/jobs/{job_id}/config')
def change_job_config(job_id: int, body: dict):
    """Update job rip parameters."""
    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": _JOB_NOT_FOUND}, status_code=404)
    if not body:
        return JSONResponse({"success": False, "error": "No fields to update"}, status_code=400)

    config = job.config
    job_args = {}
    changes = []
    config_updates = {}  # collected for atomic apply under lock

    valid_ripmethods = tuple(m.value for m in RipMethod)
    # Disctype enum has an 'unknown' member but the API rejects it as a
    # PATCH target - 'unknown' is the initial state for unidentified discs,
    # not something operators set deliberately.
    valid_disctypes = tuple(m.value for m in Disctype if m.value != 'unknown')
    valid_audio_formats = tuple(m.value for m in AudioFormat)
    valid_speed_profiles = tuple(m.value for m in SpeedProfile)

    if 'RIPMETHOD' in body:
        val = str(body['RIPMETHOD']).lower()
        if val not in valid_ripmethods:
            return JSONResponse(
                {"success": False, "error": f"RIPMETHOD must be one of {valid_ripmethods}"},
                status_code=400,
            )
        config.RIPMETHOD = val
        config_updates["RIPMETHOD"] = val
        changes.append(f"Rip Method={val}")

    if 'DISCTYPE' in body:
        val = str(body['DISCTYPE']).lower()
        if val not in valid_disctypes:
            return JSONResponse(
                {"success": False, "error": f"DISCTYPE must be one of {valid_disctypes}"},
                status_code=400,
            )
        job_args['disctype'] = val
        changes.append(f"Disctype={val}")

    if 'MAINFEATURE' in body:
        val = 1 if body['MAINFEATURE'] else 0
        config.MAINFEATURE = val
        config_updates["MAINFEATURE"] = val
        changes.append(f"Main Feature={bool(val)}")
        # Re-flag tracks based on the new setting
        _auto_flag_tracks(job, mainfeature=bool(val))

    if 'MINLENGTH' in body:
        val = str(int(body['MINLENGTH']))
        config.MINLENGTH = val
        config_updates["MINLENGTH"] = val
        changes.append(f"Min Length={val}")

    if 'MAXLENGTH' in body:
        val = str(int(body['MAXLENGTH']))
        config.MAXLENGTH = val
        config_updates["MAXLENGTH"] = val
        changes.append(f"Max Length={val}")

    if 'AUDIO_FORMAT' in body:
        val = str(body['AUDIO_FORMAT']).lower()
        if val not in valid_audio_formats:
            return JSONResponse(
                {"success": False, "error": f"AUDIO_FORMAT must be one of {valid_audio_formats}"},
                status_code=400,
            )
        config.AUDIO_FORMAT = val
        config_updates["AUDIO_FORMAT"] = val
        changes.append(f"Audio Format={val}")

    if 'RIP_SPEED_PROFILE' in body:
        val = str(body['RIP_SPEED_PROFILE']).lower()
        if val not in valid_speed_profiles:
            return JSONResponse(
                {"success": False, "error": f"RIP_SPEED_PROFILE must be one of {valid_speed_profiles}"},
                status_code=400,
            )
        config.RIP_SPEED_PROFILE = val
        config_updates["RIP_SPEED_PROFILE"] = val
        changes.append(f"Rip Speed={val}")

    if 'MUSIC_MULTI_DISC_SUBFOLDERS' in body:
        val = bool(body['MUSIC_MULTI_DISC_SUBFOLDERS'])
        config.MUSIC_MULTI_DISC_SUBFOLDERS = val
        config_updates["MUSIC_MULTI_DISC_SUBFOLDERS"] = val
        changes.append(f"Multi-Disc Subfolders={val}")

    if 'MUSIC_DISC_FOLDER_PATTERN' in body:
        val = str(body['MUSIC_DISC_FOLDER_PATTERN']).strip()
        if not val or '{num}' not in val:
            return JSONResponse(
                {"success": False, "error": "MUSIC_DISC_FOLDER_PATTERN must contain {num}"},
                status_code=400,
            )
        config.MUSIC_DISC_FOLDER_PATTERN = val
        config_updates["MUSIC_DISC_FOLDER_PATTERN"] = val
        changes.append(f"Disc Folder Pattern={val}")

    if not changes:
        return JSONResponse({"success": False, "error": "No valid fields provided"}, status_code=400)

    # Apply config updates atomically so concurrent readers never see partial state
    if config_updates:
        with cfg.arm_config_lock:
            cfg.arm_config.update(config_updates)

    message = f"Parameters changed: {', '.join(changes)}"
    notification = Notifications(f"Job: {job.job_id} Config updated!", message)
    db.session.add(notification)
    svc_files.database_updater(job_args, job)

    return {"success": True, "job_id": job.job_id}


def _with_session_cleanup(fn, *args):
    """Run *fn* and ensure the executor thread's scoped session is released.

    asyncio.to_thread runs callables on executor threads whose scoped
    sessions are NOT cleaned up by the per-endpoint wrapper installed in
    arm.app._install_session_cleanup (that wrapper targets the sync handler
    callable that FastAPI dispatches into the threadpool, not callables
    handed off to to_thread from inside an async handler). This wrapper
    prevents stale sessions from accumulating on reused executor threads.
    """
    try:
        return fn(*args)
    finally:
        db.session.remove()


@router.post('/jobs/{job_id}/fix-permissions')
async def fix_job_permissions(job_id: int):
    """Fix file permissions for a job."""
    return await asyncio.to_thread(_with_session_cleanup, svc_files.fix_permissions, str(job_id))


@router.post('/jobs/{job_id}/send')
async def send_job(job_id: int):
    """Send a job to a remote database."""
    return await asyncio.to_thread(_with_session_cleanup, svc_files.send_to_remote_db, str(job_id))


_FIELD_MAP = {
    'title': ('title', 'title_manual'),
    'year': ('year', 'year_manual'),
    'video_type': ('video_type', 'video_type_manual'),
    'imdb_id': ('imdb_id', 'imdb_id_manual'),
    'season': ('season', 'season_manual'),
    'episode': ('episode', 'episode_manual'),
}
# Fields that don't map to Job columns - they route into the
# media_metadata_manual MediaMetadata blob via set_metadata_manual().
_METADATA_FIELDS = frozenset(('artist', 'album', 'poster_url'))
_DIRECT_FIELDS = ('path', 'label', 'disctype', 'disc_number', 'disc_total')
_STRUCTURED_KEYS = frozenset(('artist', 'album', 'season', 'episode'))
_VALID_DISCTYPES = ('dvd', 'bluray', 'bluray4k', 'music', 'data')


def _process_mapped_fields(body):
    """Extract mapped fields from request body. Returns (args, updated, metadata_overrides, structured_changed).

    `args` are the Job-column writes (bundle for database_updater).
    `metadata_overrides` is a dict of {MediaMetadata field: value} that
    must be written via set_metadata_manual().
    `structured_changed` triggers a title re-render after the update.
    """
    args, updated, metadata_overrides = {}, {}, {}
    structured_changed = False
    for key, (eff, manual) in _FIELD_MAP.items():
        if key not in body or body[key] is None:
            continue
        value = str(body[key]).strip()
        args[eff] = value
        args[manual] = value
        updated[key] = value
        if key in _STRUCTURED_KEYS:
            structured_changed = True
    for key in _METADATA_FIELDS:
        if key not in body or body[key] is None:
            continue
        value = str(body[key]).strip()
        metadata_overrides[key] = value
        updated[key] = value
        if key in _STRUCTURED_KEYS:
            structured_changed = True
    return args, updated, metadata_overrides, structured_changed


def _process_direct_fields(body, args, updated):
    """Extract direct fields. Returns error JSONResponse or None."""
    for key in _DIRECT_FIELDS:
        if key not in body or body[key] is None:
            continue
        value = str(body[key]).strip()
        if key == 'disctype':
            value = value.lower()
            if value not in _VALID_DISCTYPES:
                return JSONResponse(
                    {"success": False, "error": f"disctype must be one of {_VALID_DISCTYPES}"},
                    status_code=400,
                )
        args[key] = value
        updated[key] = value
    return None


def _re_render_title(job, updated):
    """Re-render display title from pattern engine if structured fields changed."""
    try:
        from arm.ripper.naming import render_title
        db.session.flush()
        rendered = render_title(job, cfg.arm_config)
        if rendered:
            svc_files.database_updater({'title': rendered, 'title_manual': rendered}, job)
            updated['title'] = rendered
    except Exception:
        pass


@router.put('/jobs/{job_id}/title')
def update_job_title(job_id: int, body: dict):
    """Update a job's title metadata."""
    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": _JOB_NOT_FOUND}, status_code=404)
    old_title, old_year = job.title, job.year

    args, updated, metadata_overrides, structured_changed = _process_mapped_fields(body)
    error = _process_direct_fields(body, args, updated)
    if error:
        return error

    if not updated:
        return JSONResponse({"success": False, "error": "No fields to update"}, status_code=400)

    args['hasnicetitle'] = True
    # If the body included MediaMetadata fields (artist/album/poster_url),
    # merge them into the existing media_metadata_manual blob and bundle
    # the write into the same database_updater call as the column writes.
    if metadata_overrides:
        from arm_contracts import MediaMetadata
        existing_blob = job.media_metadata_manual
        if existing_blob:
            try:
                existing = MediaMetadata.model_validate_json(existing_blob)
                merged = existing.model_copy(update=metadata_overrides)
            except Exception:
                merged = MediaMetadata(**metadata_overrides)
        else:
            merged = MediaMetadata(**metadata_overrides)
        args['media_metadata_manual'] = merged.model_dump_json()
    svc_files.database_updater(args, job)

    if structured_changed and 'title' not in updated:
        _re_render_title(job, updated)

    # Create notification after the title update succeeds.
    # Wrapped in try/except so a DB lock on the notification insert
    # doesn't roll back the title update itself.
    try:
        notification = Notifications(
            f"Job: {job.job_id} was updated",
            f"Title: {old_title} ({old_year}) was updated to "
            f"{updated.get('title', old_title)} ({updated.get('year', old_year)})"
        )
        db.session.add(notification)
        db.session.commit()
    except Exception:
        db.session.rollback()

    return {"success": True, "job_id": job.job_id, "updated": updated}


@router.put('/jobs/{job_id}/tracks')
def set_job_tracks(job_id: int, body: dict):
    """Replace a job's tracks with MusicBrainz track data."""
    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": _JOB_NOT_FOUND}, status_code=404)
    tracks = body.get('tracks', [])
    if not isinstance(tracks, list):
        return JSONResponse({"success": False, "error": "tracks must be a list"}, status_code=400)

    # Delete existing tracks
    Track.query.filter_by(job_id=job_id).delete()

    # Create new tracks from provided data
    for t in tracks:
        track = Track(
            job_id=job_id,
            track_number=str(t.get('track_number', '')),
            length=int(t['length_ms'] / 1000) if t.get('length_ms') else 0,
            aspect_ratio='n/a',
            fps=0.1,
            main_feature=False,
            source='MusicBrainz',
            basename=job.title or '',
            filename=t.get('title', ''),
        )
        db.session.add(track)

    db.session.commit()

    return {"success": True, "job_id": job_id, "tracks_count": len(tracks)}


@router.post('/jobs/{job_id}/multi-title')
def toggle_multi_title(job_id: int, body: dict):
    """Toggle the multi_title flag on a job."""
    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": _JOB_NOT_FOUND}, status_code=404)
    enabled = bool(body.get('enabled', not getattr(job, 'multi_title', False)))
    svc_files.database_updater({"multi_title": enabled}, job)
    return {"success": True, "job_id": job.job_id, "multi_title": enabled}


@router.put('/jobs/{job_id}/tracks/{track_id}/title')
def update_track_title(job_id: int, track_id: int, body: dict):
    """Set per-track title metadata for a multi-title disc."""
    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": _JOB_NOT_FOUND}, status_code=404)

    track = Track.query.get(track_id)
    if not track or track.job_id != job_id:
        return JSONResponse({"success": False, "error": "Track not found"}, status_code=404)
    updated = {}
    track_fields = {
        'title': ('title', str, 256),
        'year': ('year', str, 4),
        'imdb_id': ('imdb_id', str, 15),
        'poster_url': ('poster_url', str, 256),
        'video_type': ('video_type', str, 20),
    }
    for key, (attr, typ, maxlen) in track_fields.items():
        if key in body and body[key] is not None:
            value = typ(body[key]).strip()[:maxlen]
            setattr(track, attr, value)
            updated[key] = value

    if not updated:
        return JSONResponse({"success": False, "error": "No fields to update"}, status_code=400)

    # Note: track.filename is NOT overwritten here — it stays as the MakeMKV
    # original (e.g. "B1_t00.mkv") so the transcoder can match output files
    # back to track metadata.  The custom title/year/video_type saved above
    # flow via the webhook and get applied when the transcoder moves files
    # to their final completed directory.

    db.session.commit()
    return {"success": True, "job_id": job_id, "track_id": track_id, "updated": updated}


@router.delete('/jobs/{job_id}/tracks/{track_id}/title')
def clear_track_title(job_id: int, track_id: int):
    """Clear per-track title metadata (revert to job-level inheritance)."""
    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": _JOB_NOT_FOUND}, status_code=404)

    track = Track.query.get(track_id)
    if not track or track.job_id != job_id:
        return JSONResponse({"success": False, "error": "Track not found"}, status_code=404)

    track.title = None
    track.year = None
    track.imdb_id = None
    track.poster_url = None
    track.video_type = None
    track.filename = track.basename
    db.session.commit()
    return {"success": True, "job_id": job_id, "track_id": track_id}


@router.post('/naming/preview')
def naming_preview(body: dict):
    """Preview a naming pattern with given variables."""
    from arm.ripper.naming import render_preview
    pattern = body.get('pattern', '')
    variables = body.get('variables', {})
    if not pattern:
        return JSONResponse({"success": False, "error": "pattern is required"}, status_code=400)
    rendered = render_preview(pattern, variables)
    return {"success": True, "rendered": rendered}


@router.get('/jobs/{job_id}/naming-preview')
def naming_preview_for_job(job_id: int):
    """Return rendered filenames for all tracks on a job using the naming engine."""
    from arm.ripper.naming import render_all_tracks, render_title, render_folder

    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": _JOB_NOT_FOUND}, status_code=404)

    config_dict = cfg.arm_config

    return {
        "success": True,
        "job_title": render_title(job, config_dict),
        "job_folder": render_folder(job, config_dict),
        "tracks": render_all_tracks(job, config_dict),
    }


@router.patch('/jobs/{job_id}/naming')
def update_job_naming(job_id: int, body: dict):
    """Update per-job naming pattern overrides."""
    from arm.ripper.naming import validate_pattern

    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": _JOB_NOT_FOUND}, status_code=404)

    for field in ('title_pattern_override', 'folder_pattern_override'):
        if field in body:
            value = body[field]
            if value is not None and value != '':
                if len(value) > 512:
                    return JSONResponse({
                        "success": False,
                        "error": "Pattern too long (max 512 characters)",
                    }, status_code=400)
                result = validate_pattern(value)
                if not result['valid']:
                    return JSONResponse({
                        "success": False,
                        "error": f"Invalid variables in pattern: {result['invalid_vars']}",
                        "invalid_vars": result['invalid_vars'],
                        "suggestions": result['suggestions'],
                    }, status_code=400)
                setattr(job, field, value)
            else:
                setattr(job, field, None)

    db.session.commit()
    return {
        "success": True,
        "title_pattern_override": job.title_pattern_override,
        "folder_pattern_override": job.folder_pattern_override,
    }


@router.post('/naming/validate')
def validate_naming_pattern(body: dict):
    """Validate a naming pattern against known variables."""
    from arm.ripper.naming import validate_pattern
    pattern = body.get('pattern', '')
    if not pattern:
        return {"valid": True, "invalid_vars": [], "suggestions": {}}
    return validate_pattern(pattern)


@router.get('/naming/variables')
def get_naming_variables():
    """Return the list of valid naming pattern variables."""
    from arm.ripper.naming import VALID_VARS, PATTERN_VARIABLES
    return {
        "variables": sorted(VALID_VARS),
        "descriptions": PATTERN_VARIABLES,
    }


TRANSCODE_OVERRIDE_KEYS = {
    'preset_slug',
    'overrides',
    'delete_source',
    'output_extension',
}


def _validate_transcode_overrides(body):
    """Validate a PATCH /transcode-config body against the shared contract.

    Returns (overrides_dict, errors). `overrides_dict` is the pydantic-dumped
    shape ready for json.dumps + DB persistence; empty keys are dropped to
    preserve the pre-contracts on-the-wire shape. `errors` is a list of
    human-readable strings; empty list on success.
    """
    from arm_contracts import TranscodeJobConfig
    from pydantic import ValidationError

    if not isinstance(body, dict):
        return {}, ["body must be a JSON object"]
    # Strip None / empty-string values up-front so the client-side pattern of
    # "include-to-clear" doesn't trip the regex validator.
    cleaned = {k: v for k, v in body.items() if v is not None and v != ''}
    if not cleaned:
        return {}, []
    try:
        typed = TranscodeJobConfig.model_validate(cleaned)
    except ValidationError as exc:
        errors = []
        for e in exc.errors():
            loc = '.'.join(str(p) for p in e['loc']) or '<root>'
            errors.append(f"{loc}: {e['msg']}")
        return {}, errors
    # Drop optional None/False defaults that the caller didn't send so we
    # don't pad the persisted JSON with noise.
    dumped = {
        k: v for k, v in typed.model_dump().items()
        if k in cleaned or v is not None
    }
    return dumped, []


@router.patch('/jobs/{job_id}/transcode-config')
def update_transcode_config(job_id: int, body: dict):
    """Set per-job transcode override settings."""
    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": _JOB_NOT_FOUND}, status_code=404)
    if not body or not isinstance(body, dict):
        return JSONResponse({"success": False, "error": "Request body must be a JSON object"}, status_code=400)

    overrides, errors = _validate_transcode_overrides(body)
    if errors:
        return JSONResponse({"success": False, "errors": errors}, status_code=400)

    job.transcode_overrides = json.dumps(overrides) if overrides else None
    db.session.commit()

    return {"success": True, "overrides": overrides}


def _track_to_dict(track):
    """Serialize a Track row to a wire dict via the shared TrackContract.

    main_feature -> enabled fallback preserves the legacy semantic where
    older tracks with no enabled flag default to main_feature. The fold
    happens here so the contract never carries main_feature.
    """
    enabled = track.enabled if track.enabled is not None else track.main_feature
    return TrackContract(
        track_id=track.track_id,
        job_id=track.job_id,
        track_number=track.track_number,
        length=track.length,
        aspect_ratio=track.aspect_ratio,
        fps=track.fps,
        enabled=enabled,
        process=track.process if track.process is not None else True,
        skip_reason=track.skip_reason,
        basename=track.basename,
        filename=track.filename,
        orig_filename=track.orig_filename,
        new_filename=track.new_filename,
        ripped=track.ripped,
        status=track.status,
        error=track.error,
        source=track.source,
        title=track.title,
        year=track.year,
        imdb_id=track.imdb_id,
        poster_url=track.poster_url,
        video_type=track.video_type,
        episode_number=track.episode_number,
        episode_name=track.episode_name,
        custom_filename=track.custom_filename,
    ).model_dump(mode="json")


def _job_config_masked(job_config):
    """Serialize a Job.config row to a dict, masking sensitive fields."""
    if not job_config:
        return None
    from arm.models.config import Config
    config_data = {}
    for col in Config.__table__.columns:
        name = col.name
        if name in ("CONFIG_ID", "job_id"):
            continue
        value = getattr(job_config, name, None)
        if name in HIDDEN_CONFIG_FIELDS:
            config_data[name] = "***" if value else None
        else:
            config_data[name] = value
    return config_data


@router.get('/jobs/{job_id}/detail')
def get_job_detail(job_id: int):
    """Return job with config (masked), tracks, and track counts."""
    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": _JOB_NOT_FOUND}, status_code=404)

    return {
        "job": _job_to_dict(job),
        "config": _job_config_masked(job.config),
        "tracks": [_track_to_dict(t) for t in (job.tracks or [])],
        "track_counts": svc_jobs.track_counts(job),
    }


@router.get('/jobs/{job_id}/track-counts')
def get_job_track_counts(job_id: int):
    """Lightweight track-counts endpoint for progress polling.

    Returns ``{total, ripped}`` for the rippable subset of a job's tracks
    (enabled and above MINLENGTH for video, all enabled for music).
    Cheaper than ``/jobs/{id}/detail`` when the caller only needs progress.
    """
    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": _JOB_NOT_FOUND}, status_code=404)
    return svc_jobs.track_counts(job)


@router.get('/jobs/{job_id}/progress-state')
def get_job_progress_state(job_id: int):
    """Return the small bundle of job fields the UI's progress endpoint needs:
    track counts plus disctype / logfile / no_of_titles, plus realtime
    MakeMKV PRGV progress, abcde music progress, and rsync copy progress
    parsed from the progress + log files. One round-trip instead of three.
    """
    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": _JOB_NOT_FOUND}, status_code=404)
    counts = svc_jobs.track_counts(job)

    rip = progress_reader.get_rip_progress(job_id)
    music = progress_reader.get_music_progress(job.logfile, job.no_of_titles or 0)
    copy = progress_reader.get_copy_progress(job_id)

    return JobProgressState(
        track_counts=TrackCounts(**counts),
        disctype=job.disctype,
        logfile=job.logfile,
        no_of_titles=job.no_of_titles,
        rip_progress=rip["progress"],
        rip_stage=rip["stage"],
        tracks_ripped_realtime=rip["tracks_ripped"],
        music_progress=music["progress"],
        music_stage=music["stage"],
        copy_progress=copy["progress"],
        copy_stage=copy["stage"],
    ).model_dump(mode="json")


def _parse_transcode_overrides(raw: str | None) -> dict | None:
    """Parse JSON transcode overrides and round-trip through TranscodeJobConfig.

    Returns None on any failure (unparseable JSON or shape mismatch). Corrupt
    rows are dropped with a WARN log so callers fall back to scheme defaults
    rather than propagating garbage to the webhook producer.

    Preserves the "only return keys the caller stored" shape: Pydantic's
    default dump adds None-valued defaults for every field; we restrict the
    output to keys that were present in the original JSON so consumers that
    do equality checks on the round-tripped dict don't see new noise.
    """
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    from arm_contracts import TranscodeJobConfig
    from pydantic import ValidationError
    try:
        validated = TranscodeJobConfig.model_validate(data).model_dump()
    except ValidationError:
        import logging
        logging.getLogger(__name__).warning(
            "transcode_overrides row failed contract validation; dropping"
        )
        return None
    # Return only the keys the caller persisted, matching pre-contracts shape.
    return {k: validated[k] for k in data if k in validated}


def _build_multi_title_tracks(job) -> list[dict]:
    """Extract per-track metadata for multi-title discs."""
    return [
        {
            "track_number": str(t.track_number or ''),
            "title": str(t.title),
            "year": str(getattr(t, 'year', '') or ''),
            "video_type": str(getattr(t, 'video_type', '') or ''),
            "filename": str(t.filename or ''),
        }
        for t in (job.tracks or [])
        if getattr(t, 'title', None)
    ]


_VIDEO_DISC_TYPES = {"dvd", "bluray", "bluray4k"}


@router.get('/jobs/{job_id}/retranscode-info')
def get_retranscode_info(job_id: int):
    """Build a webhook-shaped payload for re-transcoding a job."""
    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": _JOB_NOT_FOUND}, status_code=404)
    if job.disctype not in _VIDEO_DISC_TYPES:
        return JSONResponse(
            {"success": False, "error": "Only video disc jobs can be re-transcoded"},
            status_code=400,
        )

    title = job.title or job.title_auto or job.label or "Unknown"
    year = job.year or job.year_auto or ""

    payload = {
        "title": title,
        "body": f"{title} ({year})" if year else title,
        "path": job.raw_path or job.path or "",
        "job_id": job.job_id,
        "status": "success",
        "video_type": job.video_type or job.video_type_auto or "movie",
        "year": year,
        "disctype": job.disctype,
        "poster_url": job.media_metadata.poster_url or "",
        "config_overrides": _parse_transcode_overrides(job.transcode_overrides),
    }

    if job.multi_title:
        payload["multi_title"] = True
        tracks_meta = _build_multi_title_tracks(job)
        if tracks_meta:
            payload["tracks"] = tracks_meta

    return payload


@router.post('/jobs/{job_id}/transcode-callback', dependencies=[Depends(require_api_version)])
def transcode_callback(job_id: int, body: dict):
    """Receive status update from the external transcoder.

    The body is validated against arm_contracts.TranscodeCallbackPayload.
    The transcoder sends one of:
      - {"status": "transcoding"} (informational, fire-and-forget)
      - {"status": "completed"|"partial"|"failed", "error": "...",
         "track_results": [{"track_number": "1", "status": ..., ...}]}

    Schema mismatches (unknown status, malformed track_results) return 422
    with field-level errors instead of being silently dropped.
    """
    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": _JOB_NOT_FOUND}, status_code=404)

    try:
        payload = TranscodeCallbackPayload.model_validate(body)
    except ValidationError as exc:
        return JSONResponse(
            {
                "success": False,
                "error": "Invalid callback payload",
                "errors": [
                    {"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]}
                    for e in exc.errors()
                ],
            },
            status_code=422,
        )

    if payload.status == JobStatus.transcoding:
        job.status = JobState.TRANSCODE_ACTIVE.value
    elif payload.status == JobStatus.completed:
        job.status = JobState.SUCCESS.value
        notification = Notifications(
            f"Job: {job.job_id} transcode complete",
            f"'{job.title}' transcoding finished successfully"
        )
        db.session.add(notification)
    elif payload.status == JobStatus.partial:
        # Some tracks succeeded, some failed
        job.status = JobState.SUCCESS.value
        error_msg = payload.error or "Some tracks failed to transcode"
        job.errors = error_msg
        notification = Notifications(
            f"Job: {job.job_id} transcode partial",
            f"'{job.title}' transcoding completed with errors: {error_msg}"
        )
        db.session.add(notification)
    elif payload.status == JobStatus.failed:
        job.status = JobState.FAILURE.value
        error_msg = payload.error or "Transcode failed"
        job.errors = error_msg
        notification = Notifications(
            f"Job: {job.job_id} transcode failed",
            f"'{job.title}' transcoding failed: {error_msg}"
        )
        db.session.add(notification)
    else:
        # Other JobStatus members (pending/processing/cancelled) aren't
        # produced by the transcoder for this endpoint, but they validate
        # against the enum. Return 422 so observability catches the drift.
        return JSONResponse(
            {
                "success": False,
                "error": (
                    f"Status '{payload.status}' is not a valid callback "
                    "outcome for this endpoint"
                ),
            },
            status_code=422,
        )

    # Update per-track status from transcoder results
    if payload.track_results:
        track_map = {str(t.track_number): t for t in job.tracks}
        for tr in payload.track_results:
            track = track_map.get(str(tr.track_number))
            if track:
                if tr.status == JobStatus.completed:
                    track.status = TrackStatus.transcoded.value
                elif tr.status == JobStatus.failed:
                    track.status = TrackStatus.transcode_failed.value
                    if tr.error:
                        track.error = tr.error

    db.session.commit()
    return {"success": True, "job_id": job.job_id, "status": job.status}


@router.post('/jobs/{job_id}/skip-and-finalize')
def skip_and_finalize(job_id: int):
    """Skip transcoding and finalize a job's output directly.

    Only allowed when the job is in TRANSCODE_WAITING. Actively transcoding
    jobs must be abandoned first - running finalize_output against files the
    transcoder is still reading causes corrupt output.
    """
    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": _JOB_NOT_FOUND}, status_code=404)

    if job.status != JobState.TRANSCODE_WAITING.value:
        return JSONResponse(
            {
                "success": False,
                "error": (
                    f"Job is in '{job.status}' state, expected transcode_waiting. "
                    "Skip-and-finalize is only valid when the job is waiting for transcode. "
                    "To stop an active transcode, abandon the job first."
                ),
            },
            status_code=409,
        )

    try:
        from arm.ripper.naming import finalize_output
        finalize_output(job)
        job.status = JobState.SUCCESS.value
        notification = Notifications(
            f"Job: {job.job_id} finalized without transcoding",
            f"'{job.title}' skipped transcoding and finalized successfully",
        )
        db.session.add(notification)
        db.session.commit()
        return {"success": True, "message": "Job finalized without transcoding"}
    except Exception as exc:
        db.session.rollback()
        logging.error("skip-and-finalize failed for job %s: %s", job_id, exc)
        return JSONResponse(
            {"success": False, "error": "Finalization failed"},
            status_code=500,
        )


@router.post('/jobs/{job_id}/force-complete')
def force_complete(job_id: int):
    """Mark a job as complete without moving files.

    Use when the transcoder already processed the job but the callback
    to ARM failed — the files are already in the right place, we just
    need to update the status.
    """
    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": _JOB_NOT_FOUND}, status_code=404)

    if job.status == JobState.SUCCESS.value:
        return {"success": True, "message": "Job is already complete"}

    previous_status = job.status
    job.status = JobState.SUCCESS.value
    notification = Notifications(
        f"Job: {job.job_id} force-completed",
        f"'{job.title}' marked complete (was: {previous_status})",
    )
    db.session.add(notification)
    db.session.commit()
    return {"success": True, "message": f"Job marked complete (was: {previous_status})"}


@router.post('/jobs/{job_id}/tvdb-match')
def tvdb_match(job_id: int, body: dict):
    """Run TVDB episode matching for a job.

    Body: {"season": int|null, "tolerance": int|null, "apply": bool}
    season=null → auto-detect via multi-season scan
    """
    from arm.services.tvdb_sync import match_episodes_for_api

    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": _JOB_NOT_FOUND}, status_code=404)
    season = body.get("season")
    tolerance = body.get("tolerance")
    apply = bool(body.get("apply", False))
    disc_number = body.get("disc_number")
    disc_total = body.get("disc_total")

    if season is not None:
        season = int(season)
    if tolerance is not None:
        tolerance = int(tolerance)

    # Temporarily set disc overrides on the job for this match run
    saved_disc_number = job.disc_number
    saved_disc_total = job.disc_total
    if disc_number is not None:
        job.disc_number = int(disc_number)
    if disc_total is not None:
        job.disc_total = int(disc_total)

    result = match_episodes_for_api(job, season=season, tolerance=tolerance, apply=apply)

    # Restore originals if not applying (preview mode)
    if not apply:
        job.disc_number = saved_disc_number
        job.disc_total = saved_disc_total
    else:
        # Persist disc overrides and enable multi_title when applying
        # (matched episodes imply distinct per-track names for transcoder)
        job.multi_title = True
        db.session.commit()
    return result


@router.get('/jobs/{job_id}/tvdb-episodes')
def tvdb_episodes(job_id: int, season: int = 1):
    """Fetch TVDB episodes for a job's series.

    Query: ?season=2
    """
    from arm.services import tvdb
    from arm.services.matching._async_compat import run_async as _run_async

    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": _JOB_NOT_FOUND}, status_code=404)

    tvdb_id = getattr(job, 'tvdb_id', None)
    if not tvdb_id:
        return JSONResponse(
            {"success": False, "error": "No TVDB ID on this job. Run TVDB match first."},
            status_code=400,
        )

    episodes = _run_async(tvdb.get_season_episodes(tvdb_id, season))
    return {"episodes": episodes, "tvdb_id": tvdb_id, "season": season}


# --- Track field updates ---

_TRACK_EDITABLE_FIELDS: dict[str, type] = {"enabled": bool, "filename": str, "ripped": bool, "custom_filename": str, "episode_number": str, "episode_name": str}


@router.patch('/jobs/{job_id}/tracks/{track_id}')
def update_track_fields(job_id: int, track_id: int, body: dict):
    """Update editable fields (enabled, filename, ripped) on a track."""
    invalid = set(body.keys()) - _TRACK_EDITABLE_FIELDS.keys()
    if invalid:
        return JSONResponse(
            {"success": False, "error": f"Unknown fields: {', '.join(sorted(invalid))}"},
            status_code=400,
        )
    if not body:
        return JSONResponse(
            {"success": False, "error": "No fields to update"},
            status_code=400,
        )

    clean: dict = {}
    for key, value in body.items():
        expected = _TRACK_EDITABLE_FIELDS[key]
        if expected is bool:
            if isinstance(value, bool):
                clean[key] = value
            elif isinstance(value, str):
                clean[key] = value.lower() in ("true", "1", "yes")
            else:
                clean[key] = bool(value)
        else:
            clean[key] = str(value)

    track = Track.query.filter_by(track_id=track_id, job_id=job_id).first()
    if not track:
        return JSONResponse(
            {"success": False, "error": "Track not found"},
            status_code=404,
        )

    for key, value in clean.items():
        setattr(track, key, value)
    # Re-enabling clears any prior reason; prescan re-fires it next pass.
    if "enabled" in clean:
        track.skip_reason = None if clean["enabled"] else SkipReason.user_disabled.value
    # Keep track.title in sync — the webhook payload reads track.title for
    # the filename, so it must reflect the current episode_name when set.
    if "episode_name" in clean and clean["episode_name"]:
        track.title = clean["episode_name"]
    db.session.commit()
    return {"success": True, "job_id": job_id, "track_id": track_id, "updated": clean}


@router.post('/jobs/{job_id}/tracks/auto-number')
def auto_number_episodes(job_id: int, body: dict = None):
    """Assign sequential episode numbers to enabled tracks.

    Body (optional):
        start: int - starting episode number (default 1)

    Only enabled (non-skipped) tracks receive episode numbers, sorted by
    track_number. Disabled tracks are left unnumbered. Existing episode
    numbers are overwritten.
    """
    body = body or {}
    start = int(body.get('start', 1))

    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": "Job not found"}, status_code=404)

    tracks = Track.query.filter_by(job_id=job_id).order_by(Track.track_number.asc()).all()
    if not tracks:
        return JSONResponse({"success": False, "error": "No tracks"}, status_code=404)

    ep = start
    numbered = []
    for t in tracks:
        if not getattr(t, 'enabled', True):
            t.episode_number = None
            continue
        t.episode_number = str(ep)
        numbered.append({"track_id": t.track_id, "track_number": t.track_number, "episode": ep})
        ep += 1

    db.session.commit()
    return {"success": True, "job_id": job_id, "start": start, "count": len(numbered), "tracks": numbered}
