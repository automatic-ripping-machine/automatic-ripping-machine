"""
Devtools service - job queries and mutations.

Deletion follows v3's own pattern (arm/ui/jobs/json_api.py): clear drive
references, delete tracks, config and job rows, and leave a notification.
Unlike the json_api version, both job_id_current and job_id_previous
references are cleared, so deletes cannot violate the FK constraints.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from flask import current_app

from models.db_setup import db
from ui.devtools.serializer import serialize_model

# Job statuses that mark a job as finished
_TERMINAL_STATUSES = ("success", "fail")

# Job fields the update tool may set
_UPDATEABLE_FIELDS = ("title", "year", "video_type", "imdb_id", "poster_url", "disctype", "label", "no_of_titles")


def _get_job(job_id: int) -> Any:
    """Fetch a job row or raise a clear error."""
    from models.job import Job

    job = Job.query.filter_by(job_id=job_id).first()
    if job is None:
        raise ValueError(f"No job with job_id {job_id}")
    return job


def _clear_drive_references(job_id: int) -> int:
    """Clear system_drives rows referencing this job; return rows touched."""
    from models.system_drives import SystemDrives

    touched = 0
    for drive in SystemDrives.query.filter(
        (SystemDrives.job_id_current == job_id) | (SystemDrives.job_id_previous == job_id)
    ).all():
        if drive.job_id_current == job_id:
            drive.job_id_current = None
        if drive.job_id_previous == job_id:
            drive.job_id_previous = None
        touched += 1
    return touched


def _delete_job_rows(job_id: int) -> dict[str, Any]:
    """Delete tracks, config and the job row itself; returns what was removed."""
    from models.config import Config
    from models.job import Job
    from models.track import Track

    tracks = Track.query.filter_by(job_id=job_id).delete()
    configs = Config.query.filter_by(job_id=job_id).delete()
    jobs = Job.query.filter_by(job_id=job_id).delete()
    return {"tracks": tracks, "configs": configs, "jobs": jobs}


def get_job(job_id: int) -> dict[str, Any]:
    """
    Return a full job payload: the serialized row plus attached config,
    track count and drive references.

    Args:
        job_id: the job to fetch

    Returns:
        dict: job data
    """
    from models.system_drives import SystemDrives

    job = _get_job(job_id)
    data = serialize_model(job)
    data["tracks_count"] = job.tracks.count()
    data["config"] = serialize_model(job.config) if job.config else None
    data["drives"] = []
    for drive in SystemDrives.query.filter(
        (SystemDrives.job_id_current == job_id) | (SystemDrives.job_id_previous == job_id)
    ).all():
        data["drives"].append({
            "drive_id": drive.drive_id,
            "name": drive.name,
            "mount": drive.mount,
            "reference": "current" if drive.job_id_current == job_id else "previous",
        })
    return data


def get_jobs_by_status(status: str, limit: int = 500) -> dict[str, Any]:
    """
    Return jobs with the given status, newest first.

    Args:
        status: job status string, e.g. active, success, fail, waiting
        limit: max jobs to return (capped at 500)

    Returns:
        dict: matching jobs
    """
    from models.job import Job

    limit = min(limit, 500)
    jobs = Job.query.filter_by(status=status).order_by(Job.job_id.desc()).limit(limit).all()
    return {"status": status, "count": len(jobs), "jobs": [serialize_model(job) for job in jobs]}


def get_recent_jobs(limit: int = 25) -> dict[str, Any]:
    """
    Return the most recent jobs with key fields only.

    Args:
        limit: max jobs to return (capped at 200)

    Returns:
        dict: recent jobs
    """
    from models.job import Job

    limit = min(limit, 200)
    jobs = Job.query.order_by(Job.job_id.desc()).limit(limit).all()
    keys = ("job_id", "title", "year", "video_type", "status", "disctype", "start_time", "stop_time")
    return {
        "count": len(jobs),
        "jobs": [{key: serialize_model(job).get(key) for key in keys} for job in jobs],
    }


def export_job_as_json(job_id: int) -> dict[str, Any]:
    """
    Export a job, its redacted config and its tracks as a fixture.

    Args:
        job_id: the job to export

    Returns:
        dict: the fixture payload
    """
    from models.track import Track

    job = _get_job(job_id)
    return {
        "job": serialize_model(job),
        "config": serialize_model(job.config) if job.config else None,
        "tracks": [serialize_model(track) for track in Track.query.filter_by(job_id=job_id).all()],
    }


def reset_job_status(job_id: int, status: str = "waiting") -> dict[str, Any]:
    """
    Reset a job to a clean state.

    Clears stop_time, job_length, errors, ejected and pid fields.

    Args:
        job_id: the job to reset
        status: target status (default waiting)

    Returns:
        dict: the updated job
    """
    job = _get_job(job_id)
    job.status = status
    job.stop_time = None
    job.job_length = None
    job.errors = None
    job.ejected = False
    job.pid = None
    job.pid_hash = None
    db.session.commit()
    return {"job_id": job_id, "status": job.status}


def update_job(job_id: int, fields: dict[str, Any]) -> dict[str, Any]:
    """
    Update allowlisted manual fields on a job.

    Args:
        job_id: the job to update
        fields: dict of field=value; unknown or disallowed fields error out

    Returns:
        dict: the updated fields
    """
    job = _get_job(job_id)
    unknown = set(fields) - set(_UPDATEABLE_FIELDS)
    if unknown:
        raise ValueError(f"Unsupported fields: {sorted(unknown)}. Allowed: {sorted(_UPDATEABLE_FIELDS)}")
    for key, value in fields.items():
        setattr(job, key, value)
    db.session.commit()
    return {"job_id": job_id, "updated": fields}


def abandon_job(job_id: int, dry_run: bool = False) -> dict[str, Any]:
    """
    Abandon a job: terminate its process (when alive) and mark it failed.

    Args:
        job_id: the job to abandon
        dry_run: report what would happen without doing it

    Returns:
        dict: outcome
    """
    import psutil

    job = _get_job(job_id)
    pid = job.pid
    pid_alive = bool(pid) and psutil.pid_exists(int(pid))
    result = {"job_id": job_id, "status_before": job.status, "pid": pid, "pid_alive": pid_alive}
    if dry_run:
        result["dry_run"] = True
        return result
    if pid_alive:
        try:
            psutil.Process(int(pid)).terminate()
        except Exception as error:  # noqa: BLE001 - best-effort terminate
            current_app.logger.warning(f"Devtools: failed to terminate pid {pid}: {error}")
    job.status = "fail"
    job.stop_time = datetime.now(timezone.utc)
    db.session.commit()
    result["status_after"] = job.status
    return result


def delete_job(job_id: int, dry_run: bool = False) -> dict[str, Any]:
    """
    Delete one job, its tracks and config (the v3 deletion pattern).

    Args:
        job_id: the job to delete
        dry_run: report what would happen without doing it

    Returns:
        dict: outcome
    """
    job = _get_job(job_id)
    drives_touched = _clear_drive_references(job_id) if not dry_run else 0
    result = {
        "job_id": job_id,
        "title": job.title,
        "status": job.status,
        "tracks": job.tracks.count(),
        "drive_references_cleared": drives_touched,
    }
    if dry_run:
        result["dry_run"] = True
        return result
    removed = _delete_job_rows(job_id)
    db.session.commit()
    result["removed"] = removed
    return result


def delete_jobs(job_ids: list[int], dry_run: bool = False) -> dict[str, Any]:
    """
    Delete several jobs by id.

    Args:
        job_ids: list of job ids
        dry_run: report what would happen without doing it

    Returns:
        dict: per-job outcomes
    """
    results = []
    for job_id in job_ids:
        results.append(delete_job(job_id, dry_run=dry_run))
    return {"deleted": results, "dry_run": dry_run}


def delete_all_jobs(dry_run: bool = False) -> dict[str, Any]:
    """
    Delete every job row (plus tracks, config and drive references).

    Args:
        dry_run: report what would happen without doing it

    Returns:
        dict: outcome
    """
    from models.job import Job

    job_ids = [job_id for (job_id,) in Job.query.with_entities(Job.job_id).all()]
    return delete_jobs(job_ids, dry_run=dry_run)


def clean_jobs(job_ids: list[int] | None = None, dry_run: bool = False) -> dict[str, Any]:
    """
    Delete finished jobs (success/fail). A job that is still active is refused.

    Args:
        job_ids: optional subset of job ids to consider
        dry_run: report what would happen without doing it

    Returns:
        dict: outcome
    """
    from models.job import Job

    query = Job.query.filter(Job.status.in_(_TERMINAL_STATUSES))
    if job_ids:
        query = query.filter(Job.job_id.in_(job_ids))
    terminal_ids = [job_id for (job_id,) in query.with_entities(Job.job_id).all()]
    skipped = []
    if job_ids:
        skipped = sorted(set(job_ids) - set(terminal_ids))
    results = []
    for job_id in terminal_ids:
        results.append(delete_job(job_id, dry_run=dry_run))
    return {"deleted": results, "skipped_not_terminal": skipped, "dry_run": dry_run}


def reset_all(dry_run: bool = False) -> dict[str, Any]:
    """
    Reset every job to waiting and clear its finish fields.

    Args:
        dry_run: report what would happen without doing it

    Returns:
        dict: outcome
    """
    from models.job import Job

    jobs = Job.query.all()
    count = len(jobs)
    if dry_run:
        return {"jobs": count, "dry_run": True}
    for job in jobs:
        job.status = "waiting"
        job.stop_time = None
        job.job_length = None
        job.errors = None
        job.ejected = False
        job.pid = None
        job.pid_hash = None
    db.session.commit()
    return {"jobs": count, "dry_run": False}
