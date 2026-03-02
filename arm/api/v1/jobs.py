"""API v1 — Job endpoints."""
import json
import re

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import arm.config.config as cfg
from arm.database import db
from arm.models.job import Job, JobState
from arm.models.track import Track
from arm.models.notifications import Notifications
from arm.services import jobs as svc_jobs
from arm.services import files as svc_files

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
        return JSONResponse({"success": False, "error": "Job not found"}, status_code=404)

    if job.status != JobState.MANUAL_WAIT_STARTED.value:
        return JSONResponse({"success": False, "error": "Job is not in waiting state"}, status_code=409)

    svc_files.database_updater({"manual_start": True}, job)
    return {"success": True, "job_id": job.job_id}


@router.post('/jobs/{job_id}/pause')
def pause_waiting_job(job_id: int):
    """Toggle per-job pause for a job in 'waiting' status."""
    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": "Job not found"}, status_code=404)

    if job.status != JobState.MANUAL_WAIT_STARTED.value:
        return JSONResponse({"success": False, "error": "Job is not in waiting state"}, status_code=409)

    new_val = not (getattr(job, 'manual_pause', False) or False)
    svc_files.database_updater({"manual_pause": new_val}, job)
    return {"success": True, "job_id": job.job_id, "paused": new_val}


@router.post('/jobs/{job_id}/cancel')
def cancel_waiting_job(job_id: int):
    """Cancel a job that is in 'waiting' status."""
    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": "Job not found"}, status_code=404)

    if job.status != JobState.MANUAL_WAIT_STARTED.value:
        return JSONResponse({"success": False, "error": "Job is not in waiting state"}, status_code=409)

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
        return JSONResponse({"success": False, "error": "Job not found"}, status_code=404)

    body = await request.json()
    if not body:
        return JSONResponse({"success": False, "error": "No fields to update"}, status_code=400)

    config = job.config
    job_args = {}
    changes = []

    valid_ripmethods = ('mkv', 'backup')
    valid_disctypes = ('dvd', 'bluray', 'bluray4k', 'music', 'data')

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


@router.put('/jobs/{job_id}/title')
async def update_job_title(job_id: int, request: Request):
    """Update a job's title metadata."""
    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": "Job not found"}, status_code=404)

    body = await request.json()

    old_title = job.title
    old_year = job.year
    updated = {}

    field_map = {
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

    direct_fields = ('path', 'label', 'disctype')

    args = {}
    structured_changed = False
    for key, (eff, manual) in field_map.items():
        if key in body and body[key] is not None:
            value = str(body[key]).strip()
            if key == 'title':
                value = _clean_for_filename(value)
            args[eff] = value
            args[manual] = value
            updated[key] = value
            if key in ('artist', 'album', 'season', 'episode'):
                structured_changed = True

    valid_disctypes = ('dvd', 'bluray', 'bluray4k', 'music', 'data')

    for key in direct_fields:
        if key in body and body[key] is not None:
            value = str(body[key]).strip()
            if key == 'disctype':
                value = value.lower()
                if value not in valid_disctypes:
                    return JSONResponse(
                        {"success": False, "error": f"disctype must be one of {valid_disctypes}"},
                        status_code=400,
                    )
            args[key] = value
            updated[key] = value

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

    # If structured fields changed and title wasn't explicitly set,
    # re-render the display title from the pattern engine
    if structured_changed and 'title' not in updated:
        try:
            from arm.ripper.naming import render_title
            db.session.flush()
            rendered = render_title(job, cfg.arm_config)
            if rendered:
                svc_files.database_updater({
                    'title': rendered,
                    'title_manual': rendered,
                }, job)
                updated['title'] = rendered
        except Exception:
            pass

    return {
        "success": True,
        "job_id": job.job_id,
        "updated": updated,
    }


@router.put('/jobs/{job_id}/tracks')
async def set_job_tracks(job_id: int, request: Request):
    """Replace a job's tracks with MusicBrainz track data."""
    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": "Job not found"}, status_code=404)

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


TRANSCODE_OVERRIDE_KEYS = {
    'video_encoder', 'video_quality', 'audio_encoder', 'subtitle_mode',
    'handbrake_preset', 'handbrake_preset_4k', 'handbrake_preset_dvd',
    'handbrake_preset_file', 'delete_source', 'output_extension',
}

# Type validation: int-valued, bool-valued, rest are strings
_INT_KEYS = {'video_quality'}
_BOOL_KEYS = {'delete_source'}


@router.patch('/jobs/{job_id}/transcode-config')
async def update_transcode_config(job_id: int, request: Request):
    """Set per-job transcode override settings."""
    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": "Job not found"}, status_code=404)

    body = await request.json()
    if not body or not isinstance(body, dict):
        return JSONResponse({"success": False, "error": "Request body must be a JSON object"}, status_code=400)

    overrides = {}
    errors = []
    for key, value in body.items():
        if key not in TRANSCODE_OVERRIDE_KEYS:
            errors.append(f"Unknown key: {key}")
            continue
        if value is None or value == '':
            continue  # skip empty — means "use global default"
        if key in _INT_KEYS:
            try:
                overrides[key] = int(value)
            except (ValueError, TypeError):
                errors.append(f"{key} must be an integer")
        elif key in _BOOL_KEYS:
            if isinstance(value, bool):
                overrides[key] = value
            elif isinstance(value, str):
                overrides[key] = value.lower() in ('true', '1', 'yes')
            else:
                overrides[key] = bool(value)
        else:
            overrides[key] = str(value)

    if errors:
        return JSONResponse({"success": False, "errors": errors}, status_code=400)

    job.transcode_overrides = json.dumps(overrides) if overrides else None
    db.session.commit()

    return {"success": True, "overrides": overrides}


@router.post('/jobs/{job_id}/transcode-callback')
async def transcode_callback(job_id: int, request: Request):
    """Receive status update from the external transcoder.

    Expected payload: {"status": "completed"|"failed", "error": "..."}
    """
    job = Job.query.get(job_id)
    if not job:
        return JSONResponse({"success": False, "error": "Job not found"}, status_code=404)

    body = await request.json()
    status = body.get("status")

    if status == "completed":
        job.status = JobState.SUCCESS.value
        notification = Notifications(
            f"Job: {job.job_id} transcode complete",
            f"'{job.title}' transcoding finished successfully"
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

    db.session.commit()
    return {"success": True, "job_id": job.job_id, "status": job.status}


def _clean_for_filename(string):
    """Clean a string for use in filenames."""
    string = re.sub(r'\s+', ' ', string)
    string = string.replace(' : ', ' - ')
    string = string.replace(':', '-')
    string = string.replace('&', 'and')
    string = string.replace("\\", " - ")
    string = re.sub(r"[^\w -]", "", string)
    return string.strip()
