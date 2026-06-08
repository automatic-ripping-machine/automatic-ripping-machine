"""Tests for NotificationEvent (the discriminated event union published
by arm-neu's notification module to its outbox)."""
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError


from arm_contracts.enums import Disctype


def _base_kwargs():
    return dict(
        event_id=uuid4(),
        occurred_at=datetime.now(timezone.utc),
        job_id=42,
        job_title="Some Movie",
        job_disc_type=Disctype.dvd,
        job_imdb_id="tt1234567",
    )


def test_job_event_base_is_abstract_in_spirit():
    """JobEventBase carries the fields all events share. It's not a
    discriminator target on its own; the four concrete subclasses are."""
    from arm_contracts.notification_event import JobEventBase
    # Construct via a concrete subclass test below; here we just confirm
    # the import works and the field set is what we expect.
    assert set(JobEventBase.model_fields.keys()) == {
        "event_id", "occurred_at", "job_id", "job_title",
        "job_disc_type", "job_imdb_id",
    }


def test_job_started_event_has_drive_mount():
    from arm_contracts.notification_event import JobStartedEvent
    e = JobStartedEvent(**_base_kwargs(), drive_mount="/dev/sr0")
    assert e.event_key == "job.started"
    assert e.drive_mount == "/dev/sr0"


def test_job_started_event_drive_mount_optional():
    from arm_contracts.notification_event import JobStartedEvent
    e = JobStartedEvent(**_base_kwargs())
    assert e.drive_mount is None


def test_job_rip_complete_event():
    from arm_contracts.notification_event import JobRipCompleteEvent
    e = JobRipCompleteEvent(
        **_base_kwargs(),
        rip_duration_seconds=1830,
        track_count=7,
    )
    assert e.event_key == "job.rip_complete"
    assert e.rip_duration_seconds == 1830
    assert e.track_count == 7


def test_job_transcode_complete_event():
    from arm_contracts.notification_event import JobTranscodeCompleteEvent
    e = JobTranscodeCompleteEvent(
        **_base_kwargs(),
        transcode_duration_seconds=3600,
        output_path="/completed/movies/some-movie.mkv",
    )
    assert e.event_key == "job.transcode_complete"
    assert e.output_path == "/completed/movies/some-movie.mkv"


def test_job_failed_event_phase_rip():
    from arm_contracts.notification_event import JobFailedEvent
    e = JobFailedEvent(
        **_base_kwargs(),
        phase="rip",
        error_message="makemkvcon exited 253",
        error_code="MAKEMKV_FAILED",
    )
    assert e.event_key == "job.failed"
    assert e.phase == "rip"
    assert e.error_code == "MAKEMKV_FAILED"


def test_job_failed_event_phase_transcode():
    from arm_contracts.notification_event import JobFailedEvent
    e = JobFailedEvent(
        **_base_kwargs(),
        phase="transcode",
        error_message="ffmpeg crashed",
        error_code=None,
    )
    assert e.phase == "transcode"


def test_job_failed_event_rejects_unknown_phase():
    from arm_contracts.notification_event import JobFailedEvent
    with pytest.raises(ValidationError):
        JobFailedEvent(
            **_base_kwargs(),
            phase="weird",
            error_message="x",
        )


def test_event_key_is_immutable_default():
    """The discriminator literal must default to the type's key and not
    be set explicitly by callers in production code."""
    from arm_contracts.notification_event import JobStartedEvent
    e = JobStartedEvent(**_base_kwargs())
    # Pydantic v2 still allows the literal default; setting a different
    # value would fail validation.
    assert e.event_key == "job.started"
    with pytest.raises(ValidationError):
        JobStartedEvent(**_base_kwargs(), event_key="job.failed")


def test_union_discriminates_on_event_key():
    """A consumer that types a field as NotificationEvent should get
    back the correct concrete subclass based on the wire ``event_key``."""
    from pydantic import TypeAdapter
    from arm_contracts.notification_event import (
        NotificationEvent,
        JobStartedEvent,
        JobFailedEvent,
    )
    adapter = TypeAdapter(NotificationEvent)

    started_wire = {
        "event_key": "job.started",
        "event_id": str(uuid4()),
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "job_id": 1,
        "job_title": "T",
        "job_disc_type": "dvd",
        "job_imdb_id": None,
        "drive_mount": "/dev/sr0",
    }
    parsed = adapter.validate_python(started_wire)
    assert isinstance(parsed, JobStartedEvent)
    assert parsed.drive_mount == "/dev/sr0"

    failed_wire = {
        "event_key": "job.failed",
        "event_id": str(uuid4()),
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "job_id": 1,
        "job_disc_type": "dvd",
        "phase": "rip",
        "error_message": "boom",
    }
    parsed = adapter.validate_python(failed_wire)
    assert isinstance(parsed, JobFailedEvent)
    assert parsed.phase == "rip"


def test_union_rejects_unknown_event_key():
    from pydantic import TypeAdapter
    from arm_contracts.notification_event import NotificationEvent
    adapter = TypeAdapter(NotificationEvent)
    with pytest.raises(ValidationError):
        adapter.validate_python({
            "event_key": "job.someday-new-event",
            "event_id": str(uuid4()),
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "job_id": 1,
            "job_disc_type": "dvd",
        })


def test_job_manual_wait_required_event():
    from arm_contracts.notification_event import JobManualWaitRequiredEvent
    e = JobManualWaitRequiredEvent(
        **_base_kwargs(),
        wait_minutes_remaining=25,
        reason="manual_mode_activated",
    )
    assert e.event_key == "job.manual_wait_required"
    assert e.wait_minutes_remaining == 25
    assert e.reason == "manual_mode_activated"


def test_job_manual_wait_rejects_unknown_reason():
    from arm_contracts.notification_event import JobManualWaitRequiredEvent
    with pytest.raises(ValidationError):
        JobManualWaitRequiredEvent(
            **_base_kwargs(),
            wait_minutes_remaining=5,
            reason="not_a_real_reason",
        )


def test_job_duplicate_detected_event():
    from arm_contracts.notification_event import JobDuplicateDetectedEvent
    e = JobDuplicateDetectedEvent(
        **_base_kwargs(),
        existing_job_id=42,
        existing_output_path="/completed/movies/some-movie.mkv",
    )
    assert e.event_key == "job.duplicate_detected"
    assert e.existing_job_id == 42


def test_job_duplicate_detected_existing_output_path_optional():
    from arm_contracts.notification_event import JobDuplicateDetectedEvent
    e = JobDuplicateDetectedEvent(
        **_base_kwargs(),
        existing_job_id=42,
    )
    assert e.existing_output_path is None
