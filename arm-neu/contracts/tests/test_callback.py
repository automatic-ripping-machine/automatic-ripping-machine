"""Tests for TranscodeCallbackPayload (transcoder -> arm-neu)."""
import pytest
from pydantic import ValidationError

from arm_contracts import (
    JobStatus,
    TrackResult,
    TranscodeCallbackPayload,
)


def test_minimal_callback():
    p = TranscodeCallbackPayload(status=JobStatus.processing)
    assert p.status == JobStatus.processing
    assert p.error is None
    assert p.track_results is None


def test_status_accepts_string_value():
    """Wire form is the string value, not the enum member name."""
    p = TranscodeCallbackPayload.model_validate({"status": "completed"})
    assert p.status == JobStatus.completed


def test_status_rejects_unknown_value():
    with pytest.raises(ValidationError):
        TranscodeCallbackPayload.model_validate({"status": "weird-status"})


def test_failed_callback_with_error():
    p = TranscodeCallbackPayload(
        status=JobStatus.failed, error="HandBrake exit 3"
    )
    assert p.status == JobStatus.failed
    assert p.error == "HandBrake exit 3"


def test_partial_callback_with_track_results():
    """Multi-title jobs send per-track outcomes on completion/partial."""
    p = TranscodeCallbackPayload.model_validate({
        "status": "partial",
        "track_results": [
            {"track_number": "1", "status": "completed",
             "output_path": "/data/completed/movies/A/A.mkv"},
            {"track_number": "2", "status": "failed",
             "error": "codec error"},
        ],
    })
    assert p.status == JobStatus.partial
    assert p.track_results is not None and len(p.track_results) == 2
    assert isinstance(p.track_results[0], TrackResult)
    assert p.track_results[0].status == JobStatus.completed
    assert p.track_results[0].output_path.endswith("A.mkv")
    assert p.track_results[1].status == JobStatus.failed
    assert p.track_results[1].error == "codec error"


def test_track_result_requires_track_number_and_status():
    with pytest.raises(ValidationError):
        TrackResult.model_validate({"status": "completed"})
    with pytest.raises(ValidationError):
        TrackResult.model_validate({"track_number": "1"})


def test_unknown_field_ignored():
    """Producer may add fields ahead of consumer upgrades."""
    p = TranscodeCallbackPayload.model_validate({
        "status": "completed", "extra": "ignored",
    })
    assert p.status == JobStatus.completed
