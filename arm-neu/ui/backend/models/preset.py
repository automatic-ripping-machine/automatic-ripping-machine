"""BFF response shapes for the preset editor surface."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class Encoder(BaseModel):
    model_config = ConfigDict(extra="ignore")

    slug: str
    name: str
    tuning_presets: list[str] = []


class AdvancedField(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: Literal["enum", "int", "string"]
    values: list[str] | None = None
    default: str | None = None
    description: str | None = None
    min: int | None = None
    max: int | None = None


class Scheme(BaseModel):
    model_config = ConfigDict(extra="ignore")

    slug: str
    name: str
    supported_encoders: list[Encoder] = []
    supported_audio_encoders: list[str] = []
    supported_subtitle_modes: list[str] = []
    advanced_fields: dict[str, AdvancedField] = {}


class Preset(BaseModel):
    model_config = ConfigDict(extra="ignore")

    slug: str
    name: str
    scheme: str
    description: str = ""
    builtin: bool = False
    shared: dict[str, Any] = {}
    tiers: dict[str, dict[str, Any]] = {}
    parent_slug: str | None = None
    unavailable: bool | None = None
    reason: str | None = None


class Overrides(BaseModel):
    model_config = ConfigDict(extra="ignore")

    shared: dict[str, Any]
    tiers: dict[str, dict[str, Any]]


class PresetEditorState(BaseModel):
    model_config = ConfigDict(extra="ignore")

    preset_slug: str
    overrides: Overrides


class PresetCreateRequest(BaseModel):
    """Body for POST /settings/transcoder/presets - clone a built-in preset
    with custom overrides."""
    model_config = ConfigDict(extra="ignore")

    name: str
    parent_slug: str
    overrides: Overrides = Overrides(shared={}, tiers={})


class PresetUpdateRequest(BaseModel):
    """Body for PATCH /settings/transcoder/presets/{slug} - rename and/or
    swap overrides on an existing custom preset."""
    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    overrides: Overrides | None = None


class PresetListResponse(BaseModel):
    """Wrapper around the transcoder's `{presets: [...]}` shape."""
    model_config = ConfigDict(extra="ignore")

    presets: list[Preset] = []
