"""
Devtools service - expected-output and completion inspection.

Ported from the v2 completion_service. v2 consumed arm.ripper.track_state for
the finalization verdict; v3 has no such module, so the completion check here
is built from the job/track rows and what exists on disk - read-only, and it
never re-derives ripper state.
"""
from __future__ import annotations

import os
from typing import Any


def _get_job(job_id: int) -> Any:
    from models.job import Job

    job = Job.query.get(job_id)
    if job is None:
        raise ValueError(f"Job {job_id} not found")
    return job


def _get_tracks(job_id: int) -> list[Any]:
    from models.track import Track

    return list(Track.query.filter_by(job_id=job_id).all())


def list_job_outputs(job_id: int) -> dict[str, Any]:
    """
    List the files on disk under a job's final destination directory.

    Args:
        job_id: the job to inspect

    Returns:
        dict: job_id, final_path and a directory listing (exists, files)
    """
    job = _get_job(job_id)
    final_path = getattr(job, "path", None)

    result: dict[str, Any] = {
        "job_id": job_id,
        "final_path": str(final_path) if final_path else None,
        "directories": [],
    }
    if not final_path or not os.path.isdir(str(final_path)):
        result["directories"].append(
            {"label": "final", "path": str(final_path) if final_path else None, "exists": False, "files": []}
        )
        return result

    files = []
    for root, _dirs, names in os.walk(str(final_path)):
        for name in names:
            files.append(os.path.join(root, name))
    result["directories"].append(
        {"label": "final", "path": str(final_path), "exists": True, "files": sorted(files)}
    )
    return result


def validate_job_completion(job_id: int) -> dict[str, Any]:
    """
    Check whether a job actually completed.

    A track is finished when its ``ripped`` flag is set. A finished track's
    output must exist as a file under the job's final destination; finished
    tracks without an output on disk are reported as ``missing_outputs``.

    Args:
        job_id: the job to verify

    Returns:
        dict: per-track entries, missing outputs and the overall verdict
    """
    job = _get_job(job_id)
    tracks = _get_tracks(job_id)

    disk_basenames: set[str] = set()
    final_path = getattr(job, "path", None)
    if final_path and os.path.isdir(str(final_path)):
        for root, _dirs, names in os.walk(str(final_path)):
            for name in names:
                disk_basenames.add(name)

    entries = []
    for track in tracks:
        candidates = []
        for value in (
            getattr(track, "new_filename", None),
            getattr(track, "filename", None),
            getattr(track, "orig_filename", None),
            getattr(track, "basename", None),
        ):
            if value and str(value) not in candidates:
                candidates.append(str(value))
        output_exists = any(c in disk_basenames for c in candidates)
        entries.append(
            {
                "track_id": track.track_id,
                "track_number": track.track_number,
                "ripped": bool(getattr(track, "ripped", False)),
                "status": getattr(track, "status", None),
                "filenames": candidates,
                "output_exists": output_exists,
            }
        )

    expected = [e for e in entries if e["filenames"]]
    ripped = [e for e in expected if e["ripped"]]
    missing_outputs = [e for e in expected if e["ripped"] and not e["output_exists"]]

    return {
        "job_id": job_id,
        "final_path": str(final_path) if final_path else None,
        "tracks_expected": len(expected),
        "tracks_ripped": len(ripped),
        "all_expected_tracks_finished": bool(expected) and len(ripped) == len(expected),
        "missing_outputs": missing_outputs,
        "tracks": entries,
    }
