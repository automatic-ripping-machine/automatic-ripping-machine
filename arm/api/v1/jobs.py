"""API v1 — Job endpoints."""
import json
import re
import threading

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import arm.config.config as cfg
from arm.constants import SINGLE_TRACK_VIDEO_TYPES
from arm.database import db
from arm.models.job import Job, JobState
from arm.models.track import Track
from arm.models.notifications import Notifications
from arm.ripper.folder_ripper import rip_folder
from arm.services import jobs as svc_jobs
from arm.services import files as svc_files

_JOB_NOT_FOUND = "Job not found"
_NOT_WAITING = "Job is not in waiting state"


def _rip_folder_by_id(job_id: int):
    """Re-query job by ID in the thread's own session, then run rip_folder."""
    import logging
    job = Job.query.get(job_id)
    if not job:
        logging.error("rip_folder thread: job %s not found", job_id)
        return
    rip_folder(job)


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


@router.delete('/jobs/{job_id}')
def delete_job(job_id: int):
    """Delete a job by ID."""
    return svc_jobs.delete_job(str(job_id), 'delete')


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

    if job.status != JobState.MANUAL_WAIT_STARTED.value:
        return JSONResponse({"success": False, "error": _NOT_WAITING}, status_code=409)

    if job.source_type == "folder":
        # Folder jobs: launch rip_folder in a background thread.
        # Pass job_id, not the ORM object — the thread has its own session
        # scope and the original object would be detached.
        job.status = JobState.VIDEO_RIPPING.value
        db.session.commit()
        job_id = job.job_id
        thread = threading.Thread(target=_rip_folder_by_id, args=(job_id,), daemon=True)
        thread.start()
        return {"success": True, "job_id": job_id, "status": job.status}

    # Disc rip — existing behavior (signal running ripper thread to proceed)
    svc_files.database_updater({"manual_start": True}, job)
    return {"success": True, "job_id": job.job_id}


@router.post('/jobs/{job_id}/pause')
def pause_waiting_job(job_id: int):
    """Toggle per-job pause for a job in 'waiting' status."""
    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": _JOB_NOT_FOUND}, status_code=404)

    if job.status != JobState.MANUAL_WAIT_STARTED.value:
        return JSONResponse({"success": False, "error": _NOT_WAITING}, status_code=409)

    new_val = not (getattr(job, 'manual_pause', False) or False)
    svc_files.database_updater({"manual_pause": new_val}, job)
    return {"success": True, "job_id": job.job_id, "paused": new_val}


@router.post('/jobs/{job_id}/cancel')
def cancel_waiting_job(job_id: int):
    """Cancel a job that is in 'waiting' status."""
    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": _JOB_NOT_FOUND}, status_code=404)

    if job.status != JobState.MANUAL_WAIT_STARTED.value:
        return JSONResponse({"success": False, "error": _NOT_WAITING}, status_code=409)

    notification = Notifications(
        f"Job: {job.job_id} was cancelled",
        f"'{job.title}' was cancelled by user during manual-wait"
    )
    db.session.add(notification)
    svc_files.database_updater({"status": JobState.FAILURE.value}, job)

    return {"success": True, "job_id": job.job_id}


@router.patch('/jobs/{job_id}/config')
async def change_job_config(job_id: int, request: Request):
    """Update job rip parameters."""
    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": _JOB_NOT_FOUND}, status_code=404)

    body = await request.json()
    if not body:
        return JSONResponse({"success": False, "error": "No fields to update"}, status_code=400)

    config = job.config
    job_args = {}
    changes = []

    valid_ripmethods = ('mkv', 'backup')
    valid_disctypes = ('dvd', 'bluray', 'bluray4k', 'music', 'data')
    valid_audio_formats = (
        'flac', 'mp3', 'vorbis', 'opus', 'm4a', 'wav', 'mka',
        'wv', 'ape', 'mpc', 'spx', 'mp2', 'tta', 'aiff',
    )
    valid_speed_profiles = ('safe', 'fast', 'fastest')

    if 'RIPMETHOD' in body:
        val = str(body['RIPMETHOD']).lower()
        if val not in valid_ripmethods:
            return JSONResponse(
                {"success": False, "error": f"RIPMETHOD must be one of {valid_ripmethods}"},
                status_code=400,
            )
        config.RIPMETHOD = val
        cfg.arm_config["RIPMETHOD"] = val
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
        cfg.arm_config["MAINFEATURE"] = val
        changes.append(f"Main Feature={bool(val)}")
        # Re-flag tracks based on the new setting
        _auto_flag_tracks(job, mainfeature=bool(val))

    if 'MINLENGTH' in body:
        val = str(int(body['MINLENGTH']))
        config.MINLENGTH = val
        cfg.arm_config["MINLENGTH"] = val
        changes.append(f"Min Length={val}")

    if 'MAXLENGTH' in body:
        val = str(int(body['MAXLENGTH']))
        config.MAXLENGTH = val
        cfg.arm_config["MAXLENGTH"] = val
        changes.append(f"Max Length={val}")

    if 'AUDIO_FORMAT' in body:
        val = str(body['AUDIO_FORMAT']).lower()
        if val not in valid_audio_formats:
            return JSONResponse(
                {"success": False, "error": f"AUDIO_FORMAT must be one of {valid_audio_formats}"},
                status_code=400,
            )
        config.AUDIO_FORMAT = val
        cfg.arm_config["AUDIO_FORMAT"] = val
        changes.append(f"Audio Format={val}")

    if 'RIP_SPEED_PROFILE' in body:
        val = str(body['RIP_SPEED_PROFILE']).lower()
        if val not in valid_speed_profiles:
            return JSONResponse(
                {"success": False, "error": f"RIP_SPEED_PROFILE must be one of {valid_speed_profiles}"},
                status_code=400,
            )
        config.RIP_SPEED_PROFILE = val
        cfg.arm_config["RIP_SPEED_PROFILE"] = val
        changes.append(f"Rip Speed={val}")

    if 'MUSIC_MULTI_DISC_SUBFOLDERS' in body:
        val = bool(body['MUSIC_MULTI_DISC_SUBFOLDERS'])
        config.MUSIC_MULTI_DISC_SUBFOLDERS = val
        cfg.arm_config["MUSIC_MULTI_DISC_SUBFOLDERS"] = val
        changes.append(f"Multi-Disc Subfolders={val}")

    if 'MUSIC_DISC_FOLDER_PATTERN' in body:
        val = str(body['MUSIC_DISC_FOLDER_PATTERN']).strip()
        if not val or '{num}' not in val:
            return JSONResponse(
                {"success": False, "error": "MUSIC_DISC_FOLDER_PATTERN must contain {num}"},
                status_code=400,
            )
        config.MUSIC_DISC_FOLDER_PATTERN = val
        cfg.arm_config["MUSIC_DISC_FOLDER_PATTERN"] = val
        changes.append(f"Disc Folder Pattern={val}")

    if not changes:
        return JSONResponse({"success": False, "error": "No valid fields provided"}, status_code=400)

    message = f"Parameters changed: {', '.join(changes)}"
    notification = Notifications(f"Job: {job.job_id} Config updated!", message)
    db.session.add(notification)
    svc_files.database_updater(job_args, job)

    return {"success": True, "job_id": job.job_id}


@router.post('/jobs/{job_id}/fix-permissions')
def fix_job_permissions(job_id: int):
    """Fix file permissions for a job."""
    return svc_files.fix_permissions(str(job_id))


@router.post('/jobs/{job_id}/send')
def send_job(job_id: int):
    """Send a job to a remote database."""
    return svc_files.send_to_remote_db(str(job_id))


_FIELD_MAP = {
    'title': ('title', 'title_manual'),
    'year': ('year', 'year_manual'),
    'video_type': ('video_type', 'video_type_manual'),
    'imdb_id': ('imdb_id', 'imdb_id_manual'),
    'poster_url': ('poster_url', 'poster_url_manual'),
    'artist': ('artist', 'artist_manual'),
    'album': ('album', 'album_manual'),
    'season': ('season', 'season_manual'),
    'episode': ('episode', 'episode_manual'),
}
_DIRECT_FIELDS = ('path', 'label', 'disctype', 'disc_number', 'disc_total')
_STRUCTURED_KEYS = frozenset(('artist', 'album', 'season', 'episode'))
_VALID_DISCTYPES = ('dvd', 'bluray', 'bluray4k', 'music', 'data')


def _process_mapped_fields(body):
    """Extract mapped fields from request body. Returns (args, updated, structured_changed)."""
    args, updated = {}, {}
    structured_changed = False
    for key, (eff, manual) in _FIELD_MAP.items():
        if key not in body or body[key] is None:
            continue
        value = str(body[key]).strip()
        if key == 'title':
            value = _clean_for_filename(value)
        args[eff] = value
        args[manual] = value
        updated[key] = value
        if key in _STRUCTURED_KEYS:
            structured_changed = True
    return args, updated, structured_changed


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
async def update_job_title(job_id: int, request: Request):
    """Update a job's title metadata."""
    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": _JOB_NOT_FOUND}, status_code=404)

    body = await request.json()
    old_title, old_year = job.title, job.year

    args, updated, structured_changed = _process_mapped_fields(body)
    error = _process_direct_fields(body, args, updated)
    if error:
        return error

    if not updated:
        return JSONResponse({"success": False, "error": "No fields to update"}, status_code=400)

    args['hasnicetitle'] = True
    notification = Notifications(
        f"Job: {job.job_id} was updated",
        f"Title: {old_title} ({old_year}) was updated to "
        f"{updated.get('title', old_title)} ({updated.get('year', old_year)})"
    )
    db.session.add(notification)
    svc_files.database_updater(args, job)

    if structured_changed and 'title' not in updated:
        _re_render_title(job, updated)

    return {"success": True, "job_id": job.job_id, "updated": updated}


@router.put('/jobs/{job_id}/tracks')
async def set_job_tracks(job_id: int, request: Request):
    """Replace a job's tracks with MusicBrainz track data."""
    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": _JOB_NOT_FOUND}, status_code=404)

    body = await request.json()
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
async def toggle_multi_title(job_id: int, request: Request):
    """Toggle the multi_title flag on a job."""
    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": _JOB_NOT_FOUND}, status_code=404)

    body = await request.json()
    enabled = bool(body.get('enabled', not getattr(job, 'multi_title', False)))
    svc_files.database_updater({"multi_title": enabled}, job)
    return {"success": True, "job_id": job.job_id, "multi_title": enabled}


@router.put('/jobs/{job_id}/tracks/{track_id}/title')
async def update_track_title(job_id: int, track_id: int, request: Request):
    """Set per-track title metadata for a multi-title disc."""
    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": _JOB_NOT_FOUND}, status_code=404)

    track = Track.query.get(track_id)
    if not track or track.job_id != job_id:
        return JSONResponse({"success": False, "error": "Track not found"}, status_code=404)

    body = await request.json()
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
            if key == 'title':
                value = _clean_for_filename(value)
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
async def naming_preview(request: Request):
    """Preview a naming pattern with given variables."""
    from arm.ripper.naming import render_preview
    body = await request.json()
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
async def update_job_naming(job_id: int, request: Request):
    """Update per-job naming pattern overrides."""
    from arm.ripper.naming import validate_pattern

    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": _JOB_NOT_FOUND}, status_code=404)

    body = await request.json()

    for field in ('title_pattern_override', 'folder_pattern_override'):
        if field in body:
            value = body[field]
            if value is not None and value != '':
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
async def validate_naming_pattern(request: Request):
    """Validate a naming pattern against known variables."""
    from arm.ripper.naming import validate_pattern

    body = await request.json()
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
    'video_encoder', 'video_quality', 'audio_encoder', 'subtitle_mode',
    'handbrake_preset', 'handbrake_preset_4k', 'handbrake_preset_dvd',
    'handbrake_preset_file', 'delete_source', 'output_extension',
}

# Type validation: int-valued, bool-valued, rest are strings
_INT_KEYS = {'video_quality'}
_BOOL_KEYS = {'delete_source'}


def _coerce_bool(value):
    """Coerce a value to boolean."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'yes')
    return bool(value)


def _validate_transcode_overrides(body):
    """Validate and coerce transcode override values. Returns (overrides, errors)."""
    overrides = {}
    errors = []
    for key, value in body.items():
        if key not in TRANSCODE_OVERRIDE_KEYS:
            errors.append(f"Unknown key: {key}")
            continue
        if value is None or value == '':
            continue
        if key in _INT_KEYS:
            try:
                overrides[key] = int(value)
            except (ValueError, TypeError):
                errors.append(f"{key} must be an integer")
        elif key in _BOOL_KEYS:
            overrides[key] = _coerce_bool(value)
        else:
            overrides[key] = str(value)
    return overrides, errors


@router.patch('/jobs/{job_id}/transcode-config')
async def update_transcode_config(job_id: int, request: Request):
    """Set per-job transcode override settings."""
    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": _JOB_NOT_FOUND}, status_code=404)

    body = await request.json()
    if not body or not isinstance(body, dict):
        return JSONResponse({"success": False, "error": "Request body must be a JSON object"}, status_code=400)

    overrides, errors = _validate_transcode_overrides(body)
    if errors:
        return JSONResponse({"success": False, "errors": errors}, status_code=400)

    job.transcode_overrides = json.dumps(overrides) if overrides else None
    db.session.commit()

    return {"success": True, "overrides": overrides}


@router.post('/jobs/{job_id}/transcode-callback')
async def transcode_callback(job_id: int, request: Request):
    """Receive status update from the external transcoder.

    Expected payload::

        {"status": "transcoding"|"completed"|"failed", "error": "..."}

    Multi-title jobs may also include per-track results::

        {"status": "completed", "track_results": [
            {"track_number": "1", "status": "completed", "output_path": "..."},
            {"track_number": "2", "status": "failed", "error": "codec error"},
        ]}
    """
    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": _JOB_NOT_FOUND}, status_code=404)

    body = await request.json()
    status = body.get("status")

    if status == "transcoding":
        job.status = JobState.TRANSCODE_ACTIVE.value
    elif status == "completed":
        job.status = JobState.SUCCESS.value
        notification = Notifications(
            f"Job: {job.job_id} transcode complete",
            f"'{job.title}' transcoding finished successfully"
        )
        db.session.add(notification)
    elif status == "partial":
        # Some tracks succeeded, some failed
        job.status = JobState.SUCCESS.value
        error_msg = body.get("error", "Some tracks failed to transcode")
        job.errors = error_msg
        notification = Notifications(
            f"Job: {job.job_id} transcode partial",
            f"'{job.title}' transcoding completed with errors: {error_msg}"
        )
        db.session.add(notification)
    elif status == "failed":
        job.status = JobState.FAILURE.value
        error_msg = body.get("error", "Transcode failed")
        job.errors = error_msg
        notification = Notifications(
            f"Job: {job.job_id} transcode failed",
            f"'{job.title}' transcoding failed: {error_msg}"
        )
        db.session.add(notification)
    else:
        return JSONResponse(
            {"success": False, "error": f"Unknown status: {status}"},
            status_code=400,
        )

    # Update per-track status from transcoder results
    track_results = body.get("track_results")
    if track_results and isinstance(track_results, list):
        track_map = {str(t.track_number): t for t in job.tracks}
        for tr in track_results:
            track_num = str(tr.get("track_number", ""))
            track = track_map.get(track_num)
            if track:
                tr_status = tr.get("status", "")
                if tr_status == "completed":
                    track.status = "transcoded"
                elif tr_status == "failed":
                    track.status = f"transcode_failed: {tr.get('error', '')[:200]}"

    db.session.commit()
    return {"success": True, "job_id": job.job_id, "status": job.status}


@router.post('/jobs/{job_id}/tvdb-match')
async def tvdb_match(job_id: int, request: Request):
    """Run TVDB episode matching for a job.

    Body: {"season": int|null, "tolerance": int|null, "apply": bool}
    season=null → auto-detect via multi-season scan
    """
    from arm.services.tvdb_sync import match_episodes_for_api

    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": _JOB_NOT_FOUND}, status_code=404)

    body = await request.json()
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


def _clean_for_filename(string):
    """Clean a string for use in filenames."""
    string = re.sub(r'\s+', ' ', string)
    string = string.replace(' : ', ' - ')
    string = string.replace(':', '-')
    string = string.replace('&', 'and')
    string = string.replace("\\", " - ")
    string = re.sub(r"[^\w -]", "", string)
    return string.strip()


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
    # Keep track.title in sync — the webhook payload reads track.title for
    # the filename, so it must reflect the current episode_name when set.
    if "episode_name" in clean and clean["episode_name"]:
        track.title = clean["episode_name"]
    db.session.commit()
    return {"success": True, "job_id": job_id, "track_id": track_id, "updated": clean}
