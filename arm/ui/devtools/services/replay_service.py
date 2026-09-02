"""
Devtools service - job-state replay fixtures.

Ported from the v2 replay_service. Complements export_job_as_json: a fixture
exported from one job (job row + config + tracks) can be re-imported to
reproduce a scenario without the original disc. v3 has no state-transition
model, so transitions are not carried - the v2 exporter's transition handling
has no v3 counterpart.
"""
from __future__ import annotations

from typing import Any

# Job fields worth carrying into a replay. Runtime/environment-specific
# columns (timestamps, process ids, filesystem paths, eject flags) are
# deliberately excluded - they are not reproducible from a fixture.
_REPLAYABLE_FIELDS = (
    "title", "title_auto", "title_manual",
    "year", "year_auto", "year_manual",
    "video_type", "video_type_auto", "video_type_manual",
    "disctype", "label", "status", "stage",
    "imdb_id", "imdb_id_auto", "imdb_id_manual",
    "poster_url", "poster_url_auto", "poster_url_manual",
    "no_of_titles", "errors",
)


def _to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "t")


def replay_job_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    """
    Import an export_job_as_json fixture into the database.

    Reconstructs the job row, a fresh config snapshot (from the current
    runtime config) and its tracks. Returns the new job id.

    Args:
        fixture: the export_job_as_json payload (job, config, tracks keys)

    Returns:
        dict: created flag, new job id and track count
    """
    from config import config as cfg
    from models.config import Config
    from models.db_setup import db
    from models.job import Job
    from models.track import Track

    if not isinstance(fixture, dict):
        raise ValueError("fixture must be a dict (the export_job_as_json output)")

    job_data = fixture.get("job") or {}
    job = Job(str(job_data.get("devpath") or "/dev/sr0"))
    for field in _REPLAYABLE_FIELDS:
        if field in job_data:
            setattr(job, field, job_data[field])

    db.session.add(job)
    db.session.flush()  # assign job_id before config/tracks
    new_job_id = job.job_id

    db.session.add(Config(cfg.arm_config, new_job_id))

    track_count = 0
    for raw_track in fixture.get("tracks") or []:
        if not isinstance(raw_track, dict):
            continue
        track = Track(
            job_id=new_job_id,
            track_number=str(raw_track.get("track_number") or "1"),
            length=_to_int(raw_track.get("length")) or 0,
            aspect_ratio=raw_track.get("aspect_ratio") or "16:9",
            fps=_to_float(raw_track.get("fps")) or 0.0,
            main_feature=_to_bool(raw_track.get("main_feature")),
            source=raw_track.get("source") or "disc",
            basename=raw_track.get("basename") or "",
            filename=raw_track.get("filename") or "",
        )
        for field in ("ripped", "status", "error", "process"):
            if field in raw_track:
                value = raw_track[field]
                if field in ("ripped", "process"):
                    value = _to_bool(value)
                setattr(track, field, value)
        for field in ("orig_filename", "new_filename"):
            if field in raw_track:
                setattr(track, field, raw_track[field])
        db.session.add(track)
        track_count += 1

    db.session.commit()

    return {
        "created": True,
        "job_id": new_job_id,
        "track_count": track_count,
    }
