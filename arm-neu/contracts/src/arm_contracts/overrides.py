"""Overrides models: the inner shape of the preset/transcode-config wire contract.

Scheme-specific advanced fields (x265_preset, nvenc_preset, qsv_preset, etc.)
pass through SharedOverrides and TierOverrides as extras (extra='allow').
The transcoder applies scheme-aware validation at the routers/presets.py
boundary against scheme.advanced_fields. Typing each scheme's advanced fields
with a discriminated union is a v2 enhancement.
"""
from pydantic import BaseModel, ConfigDict, Field


class SharedOverrides(BaseModel):
    """Fields that apply to every tier of a resolved preset."""
    model_config = ConfigDict(extra="allow")

    video_encoder: str | None = None
    audio_encoder: str | None = None
    subtitle_mode: str | None = None


class TierOverrides(BaseModel):
    """Fields for a single resolution tier (dvd/bluray/uhd)."""
    model_config = ConfigDict(extra="allow")

    handbrake_preset: str | None = None
    video_quality: int | None = Field(default=None, ge=0, le=51)
    handbrake_extra_args: list[str] | None = None


class TierOverridesByName(BaseModel):
    """Closed set of tiers (dvd, bluray, uhd). Unknown tier names rejected.

    Every tier defaults to an empty TierOverrides, so callers can supply
    only the tiers they care about.
    """
    model_config = ConfigDict(extra="forbid")

    dvd: TierOverrides = Field(default_factory=TierOverrides)
    bluray: TierOverrides = Field(default_factory=TierOverrides)
    uhd: TierOverrides = Field(default_factory=TierOverrides)


class TranscodeOverrides(BaseModel):
    """The inner envelope: shared + per-tier overrides.

    This is the shape stored in CustomPresetDB.overrides_json and in the
    transcoder's global_overrides setting. It is also the `overrides`
    field of TranscodeJobConfig.
    """
    model_config = ConfigDict(extra="forbid")

    shared: SharedOverrides = Field(default_factory=SharedOverrides)
    tiers: TierOverridesByName = Field(default_factory=TierOverridesByName)
