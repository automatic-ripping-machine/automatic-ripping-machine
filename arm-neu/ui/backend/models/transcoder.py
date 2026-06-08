"""BFF response shapes for the transcoder integration.

TranscoderJob mirrors the shape returned by transcoder_client and is
exposed to the frontend via DashboardResponse.active_transcodes and
TranscoderJobListResponse.jobs. Other transcoder-side response shapes
(stats, config, auth, workers) follow the same pattern.

extra='ignore' is set on every model so an upstream transcoder field
addition does not crash the BFF; type-incompatible required fields
would raise but every model uses Optional fields where the upstream
shape might drift.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class TranscoderJob(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    title: str
    source_path: str
    status: str
    progress: float = 0.0
    current_fps: float | None = None
    error: str | None = None
    logfile: str | None = None
    video_type: str | None = None
    year: str | None = None
    disctype: str | None = None
    output_path: str | None = None
    total_tracks: int | None = None
    poster_url: str | None = None
    config_overrides: dict[str, Any] | None = None
    created_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


class TranscoderStatsSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    pending: int = 0
    processing: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0
    worker_running: bool = False
    current_job: str | None = None
    active_count: int = 0
    max_concurrent: int = 0


class TranscoderConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    config: dict[str, Any] = {}
    updatable_keys: list[str] = []
    paths: dict[str, str] | None = None
    valid_video_encoders: list[str] | None = None
    valid_audio_encoders: list[str] | None = None
    valid_subtitle_modes: list[str] | None = None
    valid_log_levels: list[str] | None = None
    valid_preset_files: list[str] | None = None
    presets_by_file: dict[str, list[str]] | None = None


class TranscoderAuthStatus(BaseModel):
    model_config = ConfigDict(extra="ignore")

    require_api_auth: bool = False
    webhook_secret_configured: bool = False


class WorkerStatus(BaseModel):
    model_config = ConfigDict(extra="ignore")

    worker_id: int
    status: Literal["idle", "processing"]
    current_job: str | None = None
    current_job_id: int | None = None
    started_at: str | None = None


class WorkersResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    max_concurrent: int = 0
    active_count: int = 0
    workers: list[WorkerStatus] = []


class TranscoderJobListResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    jobs: list[TranscoderJob] = []
    total: int = 0


class TranscoderStatsResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    online: bool = False
    stats: TranscoderStatsSummary | None = None


class TranscoderJobForArmResponse(BaseModel):
    """Lookup result for /api/transcoder/job-for-arm/{arm_job_id}."""
    model_config = ConfigDict(extra="ignore")

    found: bool
    logfile: str | None = None
    transcoder_job_id: int | None = None
    status: str | None = None
    phase: str | None = None
    progress: float | None = None
    current_fps: float | None = None


class RetranscodeResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: str = "ok"
    message: str = ""


class DeleteResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: str = "deleted"


class RetryResult(BaseModel):
    """`POST /jobs/{id}/retry` returns ``{status: queued}`` on success."""
    model_config = ConfigDict(extra="ignore")

    status: str
