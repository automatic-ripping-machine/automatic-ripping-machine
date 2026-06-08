"""Job and JobSummary: arm-neu -> arm-ui /jobs/* and /drives/with-jobs.

Job is the full row produced by arm-neu's `_job_to_dict` (arm/api/v1/jobs.py)
and consumed by arm-ui's `backend/models/schemas.py:JobSchema`. Frontend
mirror lives at `frontend/src/lib/types/arm.ts:Job`.

`transcode_overrides` arrives from the producer as a dict (already JSON-
parsed from the DB Text column) and is validated against `TranscodeJobConfig`.
Legacy-key stripping for pre-v15 ARM data is a CONSUMER concern (arm-ui's
schemas.py wraps this contract with a field validator); the producer always
emits clean shape going forward.

JobSummary is a 9-field slim shape used by `/drives/with-jobs` to attach
the current job to a drive entry. Only carries the fields the dashboard
needs to render a "now playing" badge.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from arm_contracts.expected_title import ExpectedTitle
from arm_contracts.track import TrackCounts


class Job(BaseModel):
    """A rip job (disc or folder import).

    Field groups, in declaration order:

    - Identity: job_id, arm_version, crc_id, guid
    - Lifecycle: logfile, start_time, stop_time, job_length, status, stage,
      no_of_titles, errors, updated, ejected, pid, pid_hash
    - Title metadata triple: title/title_auto/title_manual,
      year/year_auto/year_manual, video_type/_auto/_manual,
      imdb_id/_auto/_manual, poster_url/_auto/_manual.
      Manual wins display priority; auto is the metadata-provider guess.
    - Disc/source: devpath, mountpoint, hasnicetitle, disctype, label,
      path, raw_path, transcode_path, source_type, source_path, is_iso
    - Music triple: artist/_auto/_manual, album/_auto/_manual
    - TV triple: season/_auto/_manual, episode/_auto/_manual
    - Multi-disc: multi_title, disc_number, disc_total, tvdb_id
    - Manual control: manual_start, manual_pause, manual_mode,
      wait_start_time
    - Naming overrides: title_pattern_override, folder_pattern_override
    - Per-job transcode config: transcode_overrides (dict, see contract)
    - Progress (only on /jobs/active and /jobs/{id}/detail): track_counts
    """
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    # Identity
    job_id: int
    arm_version: str | None = None
    crc_id: str | None = None
    guid: str | None = None

    # Lifecycle
    logfile: str | None = None
    start_time: datetime | None = None
    stop_time: datetime | None = None
    job_length: str | None = None
    status: str | None = None
    stage: str | None = None
    no_of_titles: int | None = None
    errors: str | None = None
    updated: bool | None = None
    ejected: bool | None = None
    pid: int | None = None
    pid_hash: int | None = None

    # Title metadata
    title: str | None = None
    title_auto: str | None = None
    title_manual: str | None = None
    year: str | None = None
    year_auto: str | None = None
    year_manual: str | None = None
    video_type: str | None = None
    video_type_auto: str | None = None
    video_type_manual: str | None = None
    imdb_id: str | None = None
    imdb_id_auto: str | None = None
    imdb_id_manual: str | None = None
    poster_url: str | None = None
    poster_url_auto: str | None = None
    poster_url_manual: str | None = None

    # Disc / source
    devpath: str | None = None
    mountpoint: str | None = None
    hasnicetitle: bool | None = None
    disctype: str | None = None
    label: str | None = None
    path: str | None = None
    raw_path: str | None = None
    transcode_path: str | None = None
    source_type: str | None = None
    source_path: str | None = None
    is_iso: bool | None = None

    # Music
    artist: str | None = None
    artist_auto: str | None = None
    artist_manual: str | None = None
    album: str | None = None
    album_auto: str | None = None
    album_manual: str | None = None

    # TV
    season: str | None = None
    season_auto: str | None = None
    season_manual: str | None = None
    episode: str | None = None
    episode_auto: str | None = None
    episode_manual: str | None = None

    # Multi-disc / external IDs
    multi_title: bool | None = None
    disc_number: int | None = None
    disc_total: int | None = None
    tvdb_id: int | None = None

    # Manual control
    manual_start: bool | None = None
    manual_pause: bool | None = None
    manual_mode: bool | None = None
    wait_start_time: datetime | None = None

    # Naming pattern overrides
    title_pattern_override: str | None = None
    folder_pattern_override: str | None = None

    # Per-job transcode config (already-parsed JSON from DB Text column).
    # Contract intentionally typed as dict here so the consumer can attach
    # its own legacy-key stripper before validating against TranscodeJobConfig.
    transcode_overrides: dict | None = None

    # Progress, only present on endpoints that compute it.
    track_counts: TrackCounts | None = None

    # Metadata-derived expected titles, populated at identification time.
    # Empty list means identification did not produce runtime-bearing data.
    expected_titles: list[ExpectedTitle] = []


class JobSummary(BaseModel):
    """Slim 9-field Job projection for /drives/with-jobs.

    Carries only the fields the dashboard's "drive currently working on"
    badge needs to render. Producer is `_job_summary` in
    arm-neu/arm/api/v1/drives.py.
    """
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    job_id: int
    title: str | None = None
    year: str | None = None
    video_type: str | None = None
    status: str | None = None
    stage: str | None = None
    disctype: str | None = None
    label: str | None = None
    poster_url: str | None = None
    no_of_titles: int | None = None
