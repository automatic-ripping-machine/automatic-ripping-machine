"""System / hardware / GPU / storage response shapes."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SystemInfoSchema(BaseModel):
    id: int
    name: str | None = None
    cpu: str | None = None
    description: str | None = None
    mem_total: float | None = None

    model_config = {"from_attributes": True}


class HardwareInfoSchema(BaseModel):
    cpu: str | None = None
    memory_total_gb: float | None = None


class MemoryInfoSchema(BaseModel):
    total_gb: float
    used_gb: float
    free_gb: float
    percent: float


class StoragePathSchema(BaseModel):
    name: str
    path: str
    total_gb: float
    used_gb: float
    free_gb: float
    percent: float


class GpuSnapshotSchema(BaseModel):
    vendor: str
    utilization_percent: float | None = None
    memory_used_mb: float | None = None
    memory_total_mb: float | None = None
    temperature_c: float | None = None
    encoder_percent: float | None = None
    power_draw_w: float | None = None
    power_limit_w: float | None = None
    clock_core_mhz: float | None = None
    clock_memory_mhz: float | None = None


class SystemStatsSchema(BaseModel):
    cpu_percent: float = 0
    cpu_temp: float = 0
    memory: MemoryInfoSchema | None = None
    storage: list[StoragePathSchema] = []
    gpu: GpuSnapshotSchema | None = None


class JobStatsResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    total: int = 0
    completed: int = 0
    in_progress: int = 0
    failed: int = 0


class RestartResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    success: bool = True
    message: str | None = None


class PreflightResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    success: bool = True
    issues: list[str] = []


class PreflightFixResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    success: bool = True
    fixed: list[str] = []
    failed: list[str] = []


class RippingEnabledResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    success: bool = True
    ripping_enabled: bool | None = None
