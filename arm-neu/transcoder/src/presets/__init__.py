"""
Scheme-centric preset system for ARM Transcoder.

Models:
- Encoder   - a video encoder supported by a scheme
- Preset    - a tier-bundle preset covering dvd/bluray/uhd
- Scheme    - GPU variant declaring capabilities and presets
- resolve_preset()    - merge shared + tier fields + optional overrides
- load_active_scheme() - load scheme based on GPU_VENDOR env var
"""

from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, field_validator


REQUIRED_TIERS = frozenset({"dvd", "bluray", "uhd"})


class Encoder(BaseModel):
    """A video encoder supported by a scheme."""

    slug: str
    name: str
    tuning_presets: list[str] = []


class Preset(BaseModel):
    """A tier-bundle preset covering dvd/bluray/uhd tiers."""

    slug: str
    name: str
    scheme: str
    description: str = ""
    shared: dict[str, Any] = {}
    tiers: dict[str, dict[str, Any]]

    @field_validator("tiers")
    @classmethod
    def validate_tiers(cls, v: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        """Ensure all required tiers (dvd, bluray, uhd) are present."""
        missing = REQUIRED_TIERS - v.keys()
        if missing:
            raise ValueError(
                f"Preset tiers must include all of {sorted(REQUIRED_TIERS)}. "
                f"Missing: {sorted(missing)}"
            )
        return v


class Scheme(BaseModel):
    """GPU variant declaring capabilities and built-in presets."""

    slug: str
    name: str
    supported_encoders: list[Encoder]
    supported_audio_encoders: list[str]
    supported_subtitle_modes: list[str]
    advanced_fields: dict[str, dict[str, Any]] = {}
    built_in_presets: list[Preset]

    @property
    def encoder_slugs(self) -> list[str]:
        """Return the slug strings of all supported encoders."""
        return [enc.slug for enc in self.supported_encoders]

    def get_preset(self, slug: str) -> Preset | None:
        """Return the preset with the given slug, or None if not found."""
        for preset in self.built_in_presets:
            if preset.slug == slug:
                return preset
        return None

    @field_validator("built_in_presets")
    @classmethod
    def validate_built_in_presets(cls, v: list[Preset]) -> list[Preset]:
        if not v:
            raise ValueError("Scheme must have at least one built-in preset")
        return v

    @property
    def default_preset(self) -> Preset:
        """Return the first built-in preset (the default)."""
        return self.built_in_presets[0]


def resolve_preset(
    preset: Preset,
    tier: str,
    overrides: dict[str, Any] | None,
) -> dict[str, Any]:
    """Merge shared + tier fields + optional overrides into effective settings.

    Merge order (later wins):
      1. preset.shared
      2. preset.tiers[tier]
      3. overrides["shared"]   (if provided)
      4. overrides["tiers"][tier] (if provided)

    Args:
        preset:    The Preset to resolve.
        tier:      One of "dvd", "bluray", "uhd".
        overrides: Optional dict with "shared" and/or "tiers" sub-dicts.
                   Pass None or {} for no overrides.

    Returns:
        Effective settings dict.
    """
    if tier not in REQUIRED_TIERS:
        raise ValueError(f"Invalid tier {tier!r}; must be one of {sorted(REQUIRED_TIERS)}")

    result: dict[str, Any] = {}
    result.update(preset.shared)
    result.update(preset.tiers.get(tier, {}))

    if overrides:
        # 3. Apply shared overrides
        if "shared" in overrides:
            result.update(overrides["shared"])

        # 4. Apply tier-specific overrides
        tier_overrides = overrides.get("tiers", {})
        if tier in tier_overrides:
            result.update(tier_overrides[tier])

    return result





_VENDOR_TO_MODULE: dict[str, str] = {
    "nvidia": "presets.schemes.nvidia",
    "intel":  "presets.schemes.intel",
    "amd":    "presets.schemes.amd",
    "":       "presets.schemes.software",
}


def load_active_scheme() -> Scheme:
    """Load and return the active Scheme based on the GPU_VENDOR env var.

    GPU_VENDOR values:
        "nvidia"  -> NVIDIA NVENC scheme
        "intel"   -> Intel QSV scheme
        "amd"     -> AMD VAAPI/AMF scheme
        ""        -> software (CPU) scheme (default)

    The corresponding scheme modules live under presets/schemes/<vendor>.py
    and must expose a module-level ``SCHEME: Scheme`` attribute.

    Raises:
        ImportError: if the scheme module cannot be imported.
        AttributeError: if the scheme module does not expose ``SCHEME``.
    """
    import importlib

    vendor = os.environ.get("GPU_VENDOR", "").lower()
    module_path = _VENDOR_TO_MODULE.get(vendor, _VENDOR_TO_MODULE[""])

    module = importlib.import_module(module_path)
    return module.SCHEME
