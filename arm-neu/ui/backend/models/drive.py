"""Drive response and update-request shapes."""

from __future__ import annotations

from arm_contracts import JobSummary
from pydantic import BaseModel, ConfigDict


class DriveSchema(BaseModel):
    drive_id: int
    name: str | None = None
    mount: str | None = None
    job_id_current: int | None = None
    job_id_previous: int | None = None
    description: str | None = None
    drive_mode: str | None = None
    maker: str | None = None
    model: str | None = None
    serial: str | None = None
    connection: str | None = None
    capabilities: list[str] | None = None
    firmware: str | None = None
    location: str | None = None
    stale: bool | None = None
    mdisc: int | None = None
    serial_id: str | None = None
    uhd_capable: bool | None = None
    rip_speed: int | None = None
    prescan_cache_mb: int | None = None
    prescan_timeout: int | None = None
    prescan_retries: int | None = None
    disc_enum_timeout: int | None = None
    current_job: JobSummary | None = None

    model_config = {"from_attributes": True}


class DriveUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    uhd_capable: bool | None = None
    drive_mode: str | None = None
    rip_speed: int | None = None
    prescan_cache_mb: int | None = None
    prescan_timeout: int | None = None
    prescan_retries: int | None = None
    disc_enum_timeout: int | None = None


class DriveEjectResult(BaseModel):
    """`POST /drives/{id}/eject` upstream response."""
    model_config = ConfigDict(extra="ignore")

    success: bool
    drive_id: int | None = None
    method: str | None = None
    error: str | None = None
