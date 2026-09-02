"""
Devtools service - test fixtures for jobs and tracks.

Creates clearly-labelled rows so an agent can exercise the UI and the
devtools without real discs. Fixtures are written to the live database;
remove them with delete_job afterwards.
"""
from __future__ import annotations

from typing import Any

from config import config as cfg
from models.db_setup import db

_FIXTURE_LABEL = "DEVTOOLS_FIXTURE"


def create_test_job(device_path: str = "/dev/sr0") -> dict[str, Any]:
    """
    Create a test job with a config snapshot.

    Args:
        device_path: device path recorded on the job (default /dev/sr0)

    Returns:
        dict: the new job
    """
    from models.config import Config
    from models.job import Job

    job = Job(device_path)
    job.arm_version = "devtools-fixture"
    job.title = f"{_FIXTURE_LABEL} Title"
    job.title_auto = f"{_FIXTURE_LABEL} Title"
    job.year = "2026"
    job.year_auto = "2026"
    job.video_type = "movie"
    job.disctype = "dvd"
    job.label = _FIXTURE_LABEL
    job.status = "waiting"
    job.no_of_titles = 1
    job.path = "/tmp/devtools-fixture"
    db.session.add(job)
    db.session.flush()  # assign job_id before Config references it
    db.session.add(Config(cfg.arm_config, job.job_id))
    db.session.commit()
    return {"job_id": job.job_id, "title": job.title, "status": job.status}


def insert_test_track(job_id: int) -> dict[str, Any]:
    """
    Insert a test track on an existing job.

    Args:
        job_id: the job to attach the track to

    Returns:
        dict: the new track
    """
    from models.job import Job
    from models.track import Track

    job = Job.query.filter_by(job_id=job_id).first()
    if job is None:
        raise ValueError(f"No job with job_id {job_id}")
    # Track's v3 constructor is positional and sets ripped/process to False
    track = Track(
        job_id,
        "1",
        60,
        "16:9",
        23.976,
        True,
        "dvd",
        f"{_FIXTURE_LABEL}_TRACK",
        f"{_FIXTURE_LABEL}_TRACK.mkv",
    )
    track.orig_filename = f"{_FIXTURE_LABEL}_TRACK.mkv"
    track.new_filename = f"{_FIXTURE_LABEL}_TRACK.mkv"
    db.session.add(track)
    db.session.commit()
    return {"track_id": track.track_id, "job_id": job_id, "ripped": track.ripped}
