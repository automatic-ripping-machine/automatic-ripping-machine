"""Job, JobDetail, and JobList response shapes for the BFF.

JobSchema re-exports arm_contracts.Job and adds the transcode_overrides
field validator that strips legacy top-level keys before contract
validation. JobDetailSchema extends JobSchema with the per-detail tracks
and config payload composed by the BFF.

The transcode_overrides allowlist mirrors arm_contracts.TranscodeJobConfig
field names; kept in sync by hand.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from arm_contracts import Job as _JobContract
from arm_contracts import Track as TrackSchema
from pydantic import BaseModel, ConfigDict, field_validator

log = logging.getLogger(__name__)


TRANSCODE_OVERRIDES_ALLOWLIST: frozenset[str] = frozenset({
    "preset_slug",
    "overrides",
    "delete_source",
    "output_extension",
})


class JobSchema(_JobContract):
    """arm-ui's view of a Job: the shared contract plus a transcode_overrides
    field validator that strips legacy keys before contract validation."""

    @field_validator("transcode_overrides", mode="before")
    @classmethod
    def _parse_transcode_overrides(cls, v: Any) -> dict | None:
        """Validate transcode_overrides via TranscodeJobConfig.

        Accepts a JSON string (from the arm-neu DB) or a dict (from the API
        body). Strips legacy top-level keys (video_encoder, handbrake_preset*,
        etc.) with a WARN log before validating so mixed legacy + new-shape
        rows still yield their valid subset.
        """
        from arm_contracts import TranscodeJobConfig
        from pydantic import ValidationError

        if v is None:
            return None
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        elif isinstance(v, dict):
            parsed = v
        else:
            return None

        if not isinstance(parsed, dict):
            return None

        offending = set(parsed.keys()) - TRANSCODE_OVERRIDES_ALLOWLIST
        if offending:
            log.warning(
                "Stripping legacy transcode_overrides keys: %s",
                sorted(offending),
            )
            parsed = {k: v for k, v in parsed.items() if k in TRANSCODE_OVERRIDES_ALLOWLIST}

        try:
            TranscodeJobConfig.model_validate(parsed)
        except ValidationError as exc:
            log.warning(
                "transcode_overrides failed contract validation: %s",
                [{"loc": e["loc"], "msg": e["msg"]} for e in exc.errors()],
            )
            return None
        return parsed


class JobConfigSnapshot(BaseModel):
    """Per-job config snapshot returned in JobDetailSchema.config.

    The BFF surfaces a few high-traffic keys explicitly for type help,
    but arm-neu's per-job arm.yaml has ~90 keys; extra='allow' keeps
    the rest flowing through (e.g. TV_TITLE_PATTERN, MOVIE_TITLE_PATTERN,
    naming variables) so the frontend can read them without a schema
    update each time arm-neu adds a knob.
    """
    model_config = ConfigDict(extra="allow")

    RIPMETHOD: str | None = None
    DISCTYPE: str | None = None
    MAINFEATURE: bool | None = None
    MINLENGTH: int | None = None
    MAXLENGTH: int | None = None
    AUDIO_FORMAT: str | None = None
    SKIP_TRANSCODE: bool | None = None


class JobDetailSchema(JobSchema):
    tracks: list[TrackSchema]
    config: JobConfigSnapshot | None


class JobTranscodeOverridesUpdate(BaseModel):
    """Body for PATCH /jobs/{id}/transcode-config.

    Mirrors arm_contracts.TranscodeJobConfig allowlist; arm-neu rejects
    unknown keys server-side, so we accept extras here and let upstream
    decide.
    """
    model_config = ConfigDict(extra="allow")

    preset_slug: str | None = None
    overrides: dict[str, Any] | None = None
    delete_source: bool | str | None = None
    output_extension: str | None = None


class JobListResponse(BaseModel):
    jobs: list[JobSchema]
    total: int
    page: int
    per_page: int
    pages: int
