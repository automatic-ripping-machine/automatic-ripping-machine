"""
Devtools service - track queries and resets.
"""
from __future__ import annotations

from typing import Any

from models.db_setup import db
from ui.devtools.serializer import serialize_model


def get_job_tracks(job_id: int) -> dict[str, Any]:
    """
    Return the tracks of a job with ripped/failed/pending counts.

    Args:
        job_id: the job whose tracks to fetch

    Returns:
        dict: track list and counts
    """
    from models.job import Job
    from models.track import Track

    job = Job.query.filter_by(job_id=job_id).first()
    if job is None:
        raise ValueError(f"No job with job_id {job_id}")
    tracks = Track.query.filter_by(job_id=job_id).all()
    ripped = sum(1 for track in tracks if track.ripped)
    failed = sum(1 for track in tracks if track.status == "fail" or track.error)
    pending = len(tracks) - ripped - failed
    return {
        "job_id": job_id,
        "count": len(tracks),
        "ripped": ripped,
        "failed": failed,
        "pending": pending,
        "tracks": [serialize_model(track) for track in tracks],
    }


def find_orphaned_tracks() -> dict[str, Any]:
    """
    Return tracks whose job no longer exists.

    Returns:
        dict: orphaned track list
    """
    from models.job import Job
    from models.track import Track

    job_ids = {job_id for (job_id,) in Job.query.with_entities(Job.job_id).all()}
    orphans = [track for track in Track.query.all() if track.job_id not in job_ids]
    return {"count": len(orphans), "tracks": [serialize_model(track) for track in orphans]}


def reset_track_state(track_id: int) -> dict[str, Any]:
    """
    Reset a track to its unripped state.

    Args:
        track_id: the track to reset

    Returns:
        dict: the updated track
    """
    from models.track import Track

    track = Track.query.filter_by(track_id=track_id).first()
    if track is None:
        raise ValueError(f"No track with track_id {track_id}")
    track.ripped = False
    track.status = None
    track.error = None
    track.process = False
    db.session.commit()
    return {"track_id": track_id, "job_id": track.job_id, "ripped": track.ripped}
