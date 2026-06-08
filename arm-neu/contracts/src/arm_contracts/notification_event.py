"""NotificationEvent: events published by arm-neu's notification module
to its persistent outbox, then rendered into outbound messages per
subscribed channel.

The four event types (started, rip_complete, transcode_complete, failed)
form a closed discriminated union on ``event_key``. Adding a new event
type is intentionally a contracts change — consumers (neu, ui) re-pin
the contracts submodule and pick up the new variant together.

Each event carries enough job context that templates can render without
round-tripping back to neu for additional fields.
"""
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from arm_contracts.enums import Disctype


class JobEventBase(BaseModel):
    """Fields common to every notification event.

    ``event_id`` is the idempotency key used by the outbox to de-dupe
    accidental double-publishes (e.g. if a ripper retries the same
    code path). ``occurred_at`` is the producer's clock at publish time;
    consumers should not rely on monotonicity across events.
    """
    model_config = ConfigDict(extra="ignore")

    event_id: UUID
    occurred_at: datetime
    job_id: int
    job_title: str | None = None
    job_disc_type: Disctype
    job_imdb_id: str | None = None


class JobStartedEvent(JobEventBase):
    """Disc detected and job created. Fires once per job, at the entry
    of the rip pipeline."""
    event_key: Literal["job.started"] = "job.started"
    drive_mount: str | None = None


class JobRipCompleteEvent(JobEventBase):
    """MakeMKV (or folder-import) finished; raw files handed off to the
    transcoder. ``track_count`` is the number of tracks the rip
    produced, not the number selected for transcode."""
    event_key: Literal["job.rip_complete"] = "job.rip_complete"
    rip_duration_seconds: int
    track_count: int


class JobTranscodeCompleteEvent(JobEventBase):
    """Transcoder reported the job done. ``output_path`` is the final
    destination relative to the shared media root, matching the same
    convention used elsewhere in arm_contracts."""
    event_key: Literal["job.transcode_complete"] = "job.transcode_complete"
    transcode_duration_seconds: int
    output_path: str


class JobFailedEvent(JobEventBase):
    """Terminal failure of either the rip or transcode phase.
    ``error_message`` is a one-line summary suitable for a notification
    title or body; stack traces and structured detail belong in the log
    history, not here. ``error_code`` is populated when the failure
    classifier returned one; ``None`` otherwise."""
    event_key: Literal["job.failed"] = "job.failed"
    phase: Literal["rip", "transcode"]
    error_message: str
    error_code: str | None = None


class JobManualWaitRequiredEvent(JobEventBase):
    """ARM is paused waiting for the user to set up the rip manually
    (e.g. select tracks, confirm metadata). Fires when manual mode
    activates, and again on each reminder timer tick while waiting.

    ``wait_minutes_remaining`` ticks down on each fire so subscribers
    can render countdown messages (\"5 minutes left\"). ``reason`` is
    a short machine-readable code: \"manual_mode_activated\",
    \"reminder\", or \"final_warning\".
    """
    event_key: Literal["job.manual_wait_required"] = "job.manual_wait_required"
    wait_minutes_remaining: int
    reason: Literal["manual_mode_activated", "reminder", "final_warning"]


class JobDuplicateDetectedEvent(JobEventBase):
    """ARM detected a duplicate disc and is about to abort the job
    (ALLOW_DUPLICATES is false). The user can either let the abort
    happen or rename the existing rip to disambiguate."""
    event_key: Literal["job.duplicate_detected"] = "job.duplicate_detected"
    existing_job_id: int
    existing_output_path: str | None = None


NotificationEvent = Annotated[
    JobStartedEvent
    | JobRipCompleteEvent
    | JobTranscodeCompleteEvent
    | JobFailedEvent
    | JobManualWaitRequiredEvent
    | JobDuplicateDetectedEvent,
    Field(discriminator="event_key"),
]
"""Discriminated union over the four event types. Consumers should
type their dispatch / outbox fields as ``NotificationEvent`` to get
typed access to the variant via the ``event_key`` literal."""
