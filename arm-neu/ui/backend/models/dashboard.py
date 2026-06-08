"""Dashboard composite response shape."""

from __future__ import annotations

from pydantic import BaseModel

from backend.models.job import JobSchema
from backend.models.system import HardwareInfoSchema, SystemStatsSchema
from backend.models.transcoder import TranscoderJob, TranscoderStatsSummary


class DashboardResponse(BaseModel):
    db_available: bool
    arm_online: bool
    # Per-field optionality: None signals "this ARM endpoint blipped on
    # this poll, frontend should keep its prior value" rather than
    # overwriting with zero/empty and flickering badges to nothing.
    # Fields without `= None` defaults emit as required-nullable
    # (`T | null` on the wire) since the BFF always populates them.
    active_jobs: list[JobSchema] | None
    system_info: HardwareInfoSchema | None
    drives_online: int | None
    drive_names: dict[str, str] | None
    notification_count: int | None
    ripping_enabled: bool | None
    makemkv_key_valid: bool | None
    makemkv_key_checked_at: str | None
    transcoder_online: bool
    transcoder_stats: TranscoderStatsSummary | None
    transcoder_system_stats: SystemStatsSchema | None
    active_transcodes: list[TranscoderJob]
    system_stats: SystemStatsSchema | None
    transcoder_info: HardwareInfoSchema | None
