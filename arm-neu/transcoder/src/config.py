"""
Configuration settings for ARM Transcoder
"""

import json
import logging
import typing

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

logger = logging.getLogger(__name__)


UPDATABLE_KEYS = {
    # Preset selection
    "selected_preset_slug",
    "global_overrides",
    # File handling
    "delete_source",
    "output_extension",
    # Concurrency
    "max_concurrent",
    "stabilize_seconds",
    # Operational
    "minimum_free_space_gb",
    "max_retry_count",
    "log_level",
    "log_level_libraries",
}

VALID_LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)

    # Paths
    raw_path: str = Field("/data/raw", description="Path to raw MKV files from ARM")
    completed_path: str = Field("/data/completed", description="Path for completed transcodes")
    work_path: str = Field("/data/work", description="Temporary working directory")
    db_path: str = Field("/data/db/transcoder.db", description="SQLite database path")
    log_path: str = Field("/data/logs", description="Directory for log files")

    # Authentication
    require_api_auth: bool = Field(
        False,
        description="Require API key authentication for all endpoints"
    )
    api_keys: str = Field(
        "",
        description="Comma-separated API keys. Format: 'key1,key2' or 'admin:key1,readonly:key2'"
    )
    webhook_secret: str = Field(
        "",
        description="Optional secret for webhook authentication (X-Webhook-Secret header)"
    )
    arm_callback_url: str = Field(
        "",
        description="ARM API base URL for status callbacks (e.g. http://arm-rippers:8080). "
                    "When set, the transcoder notifies ARM when jobs complete or fail."
    )

    # Preset selection
    selected_preset_slug: str = Field("", description="Active preset slug (empty = scheme default)")
    global_overrides: str = Field("{}", description="JSON-encoded field overrides applied to the selected preset")

    # File handling
    delete_source: bool = Field(
        True,
        description="Delete source files after successful transcode"
    )
    output_extension: str = Field("mkv", description="Output file extension")

    # Output organization is now driven entirely by ARM via the webhook
    # output_path field. The transcoder joins payload.output_path to
    # completed_path; no per-type subdir partitioning here.

    # Concurrency
    max_concurrent: int = Field(
        1,
        ge=1,
        le=10,
        description="Max concurrent transcodes. Each job consumes a GPU encoder session. "
                    "NVIDIA: 3-5 sessions (GTX 1660: 3, RTX 3060+: 5). "
                    "AMD (VCN/AMF): 1-2 sessions. Intel (QSV): 2-3 sessions. "
                    "CPU (x265/x264): bounded by cores, 2-3 recommended. "
                    "Default 1 unless hardware supports multiple sessions."
    )
    stabilize_seconds: int = Field(
        60,
        ge=10,
        le=600,
        description="Seconds to wait for source folder to stabilize"
    )

    # Disk space
    minimum_free_space_gb: float = Field(
        10.0,
        ge=1.0,
        description="Minimum free disk space required (GB)"
    )

    # Retry configuration
    max_retry_count: int = Field(
        3,
        ge=0,
        le=10,
        description="Maximum retry attempts for failed jobs"
    )

    # Logging
    log_level: str = Field("INFO", description="Logging level")
    log_level_libraries: str = Field(
        "WARNING",
        description="Logging level for third-party libraries (aiosqlite, httpcore, httpx, uvicorn.access)",
    )

    # GPU monitoring
    gpu_vendor: str = Field(
        "",
        description="GPU vendor for monitoring: nvidia, amd, intel, or empty for CPU-only. "
                    "Set automatically by Docker image layer (Dockerfile.nvidia/amd/intel).",
    )

    @field_validator("log_level", "log_level_libraries")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(
                f"Invalid log level: {v}. "
                f"Valid options: {', '.join(valid_levels)}"
            )
        return v_upper


settings = Settings()


# Settings fields that are declared as `str` but whose value is a JSON-encoded
# document (dict or list). On load, we json.loads to validate. On write, these
# are handled by _serialize_for_storage in src/routers/config.py (dict/list
# branch) and the dict-to-JSON preconversion at src/routers/config.py (~L93).
# If you add a new JSON str field, update ALL THREE sites.
_JSON_STRING_KEYS = frozenset({"global_overrides"})


def unwrap_optional(annotation):
    """Unwrap Optional[T] / Union[T, None] to T. Leaves other types alone."""
    origin = typing.get_origin(annotation)
    if origin is typing.Union:
        args = [a for a in typing.get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return annotation


async def load_config_overrides():
    """Load persisted config overrides from DB and patch the settings singleton.

    Coercion is annotation-aware:
      - bool/int/float use their type constructor (skip row on ValueError)
      - dict / list values are json.loads-ed (skip row on JSONDecodeError)
      - str-typed fields whose content is expected to be JSON (see
        _JSON_STRING_KEYS) are validated as valid JSON before assignment
      - Optional[T] is unwrapped to T

    Malformed rows are skipped with a WARN so operators can see the drift.

    Legacy rows whose keys are no longer in UPDATABLE_KEYS (removed by the
    preset rollout) are DELETEd from the DB with a WARN log. This runs once
    per upgrade; subsequent startups find no legacy rows.
    """
    from database import get_db
    from models import ConfigOverrideDB
    from sqlalchemy import delete, select

    async with get_db() as db:
        result = await db.execute(select(ConfigOverrideDB))
        overrides = result.scalars().all()

        legacy_keys: list[tuple[str, str]] = []  # (key, value) pairs for logging
        for override in overrides:
            if override.key not in UPDATABLE_KEYS:
                legacy_keys.append((override.key, override.value))
                continue
            field_info = Settings.model_fields.get(override.key)
            if not field_info:
                continue

            annotation = unwrap_optional(field_info.annotation)
            origin = typing.get_origin(annotation)

            try:
                if annotation is bool:
                    coerced = override.value.lower() in ("true", "1", "yes")
                elif annotation is int:
                    coerced = int(override.value)
                elif annotation is float:
                    coerced = float(override.value)
                elif annotation is dict or origin is dict:
                    coerced = json.loads(override.value)
                    if not isinstance(coerced, dict):
                        raise ValueError(f"Expected dict, got {type(coerced).__name__}")
                elif annotation is list or origin is list:
                    coerced = json.loads(override.value)
                    if not isinstance(coerced, list):
                        raise ValueError(f"Expected list, got {type(coerced).__name__}")
                elif annotation is str and override.key in _JSON_STRING_KEYS:
                    # Validate content parses as JSON; store the original string
                    # so downstream consumers can json.loads it unchanged.
                    json.loads(override.value)
                    coerced = override.value
                else:
                    coerced = override.value
                setattr(settings, override.key, coerced)
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                logger.warning(
                    "Skipping config override %s: invalid value %r (%s)",
                    override.key, override.value, exc,
                )

        # Drop legacy rows and warn for each
        for key, value in legacy_keys:
            logger.warning(
                "Dropping legacy config override %s=%r - flat encoding keys "
                "were replaced by the preset system. Use PATCH /config with "
                "{\"selected_preset_slug\": \"...\"} if you need to pin a preset.",
                key, value,
            )
            await db.execute(
                delete(ConfigOverrideDB).where(ConfigOverrideDB.key == key)
            )
        if legacy_keys:
            await db.commit()
