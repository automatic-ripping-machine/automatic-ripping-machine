"""Callback payload: transcoder -> arm-neu POST /api/v1/jobs/{id}/transcode-callback.

The transcoder's TranscodeCallbackDrainer (src/callback_drainer.py) builds
this dict per pending row and POSTs it to arm-neu. arm-neu's callback
receiver consumes it. Status is one of the JobStatus enum values; both
sides should import from contracts so adding a new status (or renaming
one) ripples to consumers via the lockstep workflow.
"""
from pydantic import BaseModel, ConfigDict

from arm_contracts.enums import JobStatus


class TrackResult(BaseModel):
    """One entry in TranscodeCallbackPayload.track_results.

    Multi-title jobs send per-track outcomes so arm-neu can mark individual
    tracks completed/failed independently. ``output_path`` is set on
    completion; ``error`` is set on failure. Both may be unset for the
    intermediate ``processing`` status, though that status normally fires
    a single payload (no track_results) earlier in the run.
    """
    model_config = ConfigDict(extra="ignore")

    track_number: str
    status: JobStatus
    output_path: str | None = None
    error: str | None = None


class TranscodeCallbackPayload(BaseModel):
    """Payload for POST /api/v1/jobs/{job_id}/transcode-callback.

    The drainer always sets ``status``. ``error`` accompanies a terminal
    failure status. ``track_results`` is set when a multi-title job
    finishes (any terminal status) so arm-neu can update each track row
    independently.
    """
    model_config = ConfigDict(extra="ignore")

    status: JobStatus
    error: str | None = None
    track_results: list[TrackResult] | None = None
