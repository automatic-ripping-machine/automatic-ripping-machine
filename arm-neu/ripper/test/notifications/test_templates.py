"""Tests for the templates module.

Defaults render each event into a sensible title/body without
configuration. Per-channel overrides use Python ``str.format_map`` so
templates look like ``"Found disc: {job_title}"``.

Missing variables are a failure — we don't silently substitute empty
strings, because that hides typos.
"""
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from arm_contracts import (
    JobStartedEvent,
    JobRipCompleteEvent,
    JobTranscodeCompleteEvent,
    JobFailedEvent,
    JobManualWaitRequiredEvent,
    JobDuplicateDetectedEvent,
)
from arm_contracts.enums import Disctype


def _started():
    return JobStartedEvent(
        event_id=uuid4(),
        occurred_at=datetime.now(timezone.utc),
        job_id=42,
        job_title="Some Movie",
        job_disc_type=Disctype.dvd,
        drive_mount="/dev/sr0",
    )


def _failed():
    return JobFailedEvent(
        event_id=uuid4(),
        occurred_at=datetime.now(timezone.utc),
        job_id=42,
        job_title="Some Movie",
        job_disc_type=Disctype.dvd,
        phase="rip",
        error_message="makemkvcon exited 253",
        error_code="MAKEMKV_FAILED",
    )


def test_default_template_renders_started():
    from arm.notifications.templates import render_title_and_body
    title, body = render_title_and_body(_started(), channel_template=None)
    assert "Some Movie" in title or "Some Movie" in body
    assert "42" in title or "42" in body or "started" in title.lower()


def test_default_template_renders_failed():
    from arm.notifications.templates import render_title_and_body
    title, body = render_title_and_body(_failed(), channel_template=None)
    assert "Some Movie" in title or "Some Movie" in body
    assert "rip" in body
    assert "makemkvcon" in body


def test_channel_override_uses_format_map():
    from arm.notifications.templates import render_title_and_body
    from arm_contracts import ChannelTemplate
    tmpl = ChannelTemplate(
        title="Job {job_id}",
        body="{job_title} failed: {error_message}",
    )
    title, body = render_title_and_body(_failed(), channel_template=tmpl)
    assert title == "Job 42"
    assert body == "Some Movie failed: makemkvcon exited 253"


def test_channel_override_with_only_title_falls_back_to_default_body():
    from arm.notifications.templates import render_title_and_body
    from arm_contracts import ChannelTemplate
    tmpl = ChannelTemplate(title="Override title for {job_id}")
    title, body = render_title_and_body(_started(), channel_template=tmpl)
    assert title == "Override title for 42"
    # body comes from the default
    assert "Some Movie" in body or "started" in body.lower()


def test_missing_variable_raises():
    from arm.notifications.templates import render_title_and_body, TemplateRenderError
    from arm_contracts import ChannelTemplate
    tmpl = ChannelTemplate(title="{nonexistent_field}", body="x")
    with pytest.raises(TemplateRenderError):
        render_title_and_body(_started(), channel_template=tmpl)


def test_all_six_events_have_defaults():
    """Every event type must have a usable default template — no event
    should crash at publish time because someone forgot to add a default."""
    from arm.notifications.templates import render_title_and_body

    events = [
        _started(),
        JobRipCompleteEvent(
            event_id=uuid4(), occurred_at=datetime.now(timezone.utc),
            job_id=1, job_disc_type=Disctype.dvd, job_title="X",
            rip_duration_seconds=10, track_count=1,
        ),
        JobTranscodeCompleteEvent(
            event_id=uuid4(), occurred_at=datetime.now(timezone.utc),
            job_id=1, job_disc_type=Disctype.dvd, job_title="X",
            transcode_duration_seconds=10, output_path="/x/y",
        ),
        _failed(),
        JobManualWaitRequiredEvent(
            event_id=uuid4(), occurred_at=datetime.now(timezone.utc),
            job_id=1, job_disc_type=Disctype.dvd, job_title="X",
            wait_minutes_remaining=5, reason="reminder",
        ),
        JobDuplicateDetectedEvent(
            event_id=uuid4(), occurred_at=datetime.now(timezone.utc),
            job_id=1, job_disc_type=Disctype.dvd, job_title="X",
            existing_job_id=10,
        ),
    ]
    for e in events:
        title, body = render_title_and_body(e, channel_template=None)
        assert title and body, f"no default for {e.event_key}"
