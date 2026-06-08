"""TranscodeJobConfig: the wire envelope for per-job transcoder configuration.

This is the shape that:
  - Arrives in webhook.config_overrides (arm-neu -> transcoder).
  - Is persisted in arm-neu Job.transcode_overrides (JSON text).
  - Is persisted in transcoder TranscodeJobDB.config_overrides (JSON text).

CustomPresetDB.overrides_json and the transcoder's global_overrides setting
use only the inner TranscodeOverrides (no preset_slug wrapping), so import
those directly when you want the preset-diff shape.
"""
from pydantic import BaseModel, ConfigDict, Field

from arm_contracts.overrides import TranscodeOverrides

# Canonical preset-slug shape, enforced on every producer boundary.
# First character is alphanumeric; remaining may include '-' or '_'.
# Matches arm-neu PR #242's validator.
PRESET_SLUG_PATTERN = r"^[a-z0-9][a-z0-9_-]{0,63}$"


class TranscodeJobConfig(BaseModel):
    """The full wire envelope used for per-job transcoder configuration."""
    model_config = ConfigDict(extra="forbid")

    preset_slug: str = Field(pattern=PRESET_SLUG_PATTERN)
    overrides: TranscodeOverrides = Field(default_factory=TranscodeOverrides)
    delete_source: bool | None = None
    output_extension: str | None = None
