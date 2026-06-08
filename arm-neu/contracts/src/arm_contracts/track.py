"""Track and TrackCounts: arm-neu -> arm-ui /jobs/{id}/detail and progress.

Track is the per-title metadata row inside a Job. arm-neu's `_track_to_dict`
(arm/api/v1/jobs.py) is the producer; arm-ui consumes via
`backend/models/schemas.py:TrackSchema`. Frontend mirror lives at
`frontend/src/lib/types/arm.ts:Track`.

The `enabled` field is producer-side folded from `track.enabled or
track.main_feature` so consumers don't need to know about the legacy
`main_feature` ORM column. `main_feature` is intentionally NOT on the wire.
"""
from pydantic import BaseModel, ConfigDict

from arm_contracts.enums import SkipReason  # noqa: F401  (re-export)


class Track(BaseModel):
    """Single ripped/rippable title within a Job.

    Per-track title metadata (title/year/imdb_id/poster_url/video_type) is
    nullable; null means "inherit job-level". Episode metadata
    (episode_number/episode_name) is populated by TVDB matching for series.
    `custom_filename` overrides pattern-rendered filenames.
    """
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    track_id: int
    job_id: int
    track_number: str | None = None
    length: int | None = None
    aspect_ratio: str | None = None
    fps: float | None = None
    enabled: bool | None = None
    basename: str | None = None
    filename: str | None = None
    orig_filename: str | None = None
    new_filename: str | None = None
    ripped: bool | None = None
    status: str | None = None
    error: str | None = None
    source: str | None = None

    # Per-track title metadata (null = inherits job-level).
    title: str | None = None
    year: str | None = None
    imdb_id: str | None = None
    poster_url: str | None = None
    video_type: str | None = None

    # TVDB episode matching.
    episode_number: str | None = None
    episode_name: str | None = None

    # Output-filename override; bypasses pattern rendering when set.
    custom_filename: str | None = None

    # Filter pipeline: should-rip signal and reason if skipped.
    process: bool = True
    skip_reason: SkipReason | None = None


class TrackCounts(BaseModel):
    """Rippable-track progress for one Job.

    `total` and `ripped` count only rippable tracks (enabled and above
    MINLENGTH for video; all enabled for music) - matching the UI's
    progress widget semantics. Returned both standalone (from
    /jobs/{id}/track-counts) and nested under `Job.track_counts` /
    `JobProgressState.track_counts`.
    """
    model_config = ConfigDict(extra="ignore")

    total: int = 0
    ripped: int = 0
