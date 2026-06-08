"""Fixture-backed round-trip tests.

Each fixture represents a payload shape we've actually seen on the wire.
If the models grow, this is where we confirm legacy payloads still parse.
"""
import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def test_legacy_webhook_parses():
    """A real webhook payload captured from the deployed transcoder must
    still deserialize into TranscodeJobConfig without ValidationError."""
    from arm_contracts import TranscodeJobConfig
    raw = json.loads((FIXTURES / "legacy_webhook.json").read_text())
    m = TranscodeJobConfig.model_validate(raw)
    assert m.preset_slug == "software-balanced"
    assert m.overrides.tiers.uhd.video_quality == 24


def test_legacy_webhook_round_trip():
    from arm_contracts import TranscodeJobConfig
    raw = json.loads((FIXTURES / "legacy_webhook.json").read_text())
    m = TranscodeJobConfig.model_validate(raw)
    dumped = json.loads(m.model_dump_json())
    reparsed = TranscodeJobConfig.model_validate(dumped)
    assert reparsed == m


def test_job_started_event_round_trip():
    from pydantic import TypeAdapter
    from arm_contracts import NotificationEvent
    from arm_contracts.notification_event import JobStartedEvent
    adapter = TypeAdapter(NotificationEvent)
    raw = json.loads((FIXTURES / "job_started_event.json").read_text())
    parsed = adapter.validate_python(raw)
    assert isinstance(parsed, JobStartedEvent)
    # Round-trip: dump and re-validate.
    again = adapter.validate_python(json.loads(parsed.model_dump_json()))
    assert again == parsed


def test_job_rip_complete_event_round_trip():
    from pydantic import TypeAdapter
    from arm_contracts import NotificationEvent
    from arm_contracts.notification_event import JobRipCompleteEvent
    adapter = TypeAdapter(NotificationEvent)
    raw = json.loads((FIXTURES / "job_rip_complete_event.json").read_text())
    parsed = adapter.validate_python(raw)
    assert isinstance(parsed, JobRipCompleteEvent)
    again = adapter.validate_python(json.loads(parsed.model_dump_json()))
    assert again == parsed


def test_job_transcode_complete_event_round_trip():
    from pydantic import TypeAdapter
    from arm_contracts import NotificationEvent
    from arm_contracts.notification_event import JobTranscodeCompleteEvent
    adapter = TypeAdapter(NotificationEvent)
    raw = json.loads((FIXTURES / "job_transcode_complete_event.json").read_text())
    parsed = adapter.validate_python(raw)
    assert isinstance(parsed, JobTranscodeCompleteEvent)
    again = adapter.validate_python(json.loads(parsed.model_dump_json()))
    assert again == parsed


def test_job_failed_event_round_trip():
    from pydantic import TypeAdapter
    from arm_contracts import NotificationEvent
    from arm_contracts.notification_event import JobFailedEvent
    adapter = TypeAdapter(NotificationEvent)
    raw = json.loads((FIXTURES / "job_failed_event.json").read_text())
    parsed = adapter.validate_python(raw)
    assert isinstance(parsed, JobFailedEvent)
    again = adapter.validate_python(json.loads(parsed.model_dump_json()))
    assert again == parsed


def test_apprise_channel_round_trip():
    from arm_contracts import Channel
    raw = json.loads((FIXTURES / "apprise_channel.json").read_text())
    c = Channel.model_validate(raw)
    assert c.type == "apprise"
    assert c.config.url.startswith("discord://")
    again = Channel.model_validate(json.loads(c.model_dump_json()))
    assert again == c


def test_webhook_channel_round_trip():
    from arm_contracts import Channel
    raw = json.loads((FIXTURES / "webhook_channel.json").read_text())
    c = Channel.model_validate(raw)
    assert c.type == "webhook"
    # SecretStr survives round-trip through model_dump_json (which would
    # serialize as the masked literal); we round-trip from the raw fixture
    # twice via model_validate of the original raw to assert structural
    # equality without the SecretStr-mask trap.
    again = Channel.model_validate(raw)
    assert c == again
    assert c.config.shared_secret.get_secret_value() == "supersecret123"


def test_bash_channel_round_trip():
    from arm_contracts import Channel
    raw = json.loads((FIXTURES / "bash_channel.json").read_text())
    c = Channel.model_validate(raw)
    assert c.type == "bash"
    assert c.enabled is False
    again = Channel.model_validate(json.loads(c.model_dump_json()))
    assert again == c


def test_outbound_webhook_payload_round_trip():
    from arm_contracts import OutboundWebhookPayload
    raw = json.loads((FIXTURES / "outbound_webhook_payload.json").read_text())
    p = OutboundWebhookPayload.model_validate(raw)
    assert p.schema_version == 1
    assert p.event.event_key == "job.failed"
    again = OutboundWebhookPayload.model_validate(json.loads(p.model_dump_json()))
    assert again == p


def test_job_manual_wait_required_event_round_trip():
    from pydantic import TypeAdapter
    from arm_contracts import NotificationEvent
    from arm_contracts.notification_event import JobManualWaitRequiredEvent
    adapter = TypeAdapter(NotificationEvent)
    raw = json.loads((FIXTURES / "job_manual_wait_required_event.json").read_text())
    parsed = adapter.validate_python(raw)
    assert isinstance(parsed, JobManualWaitRequiredEvent)
    again = adapter.validate_python(json.loads(parsed.model_dump_json()))
    assert again == parsed


def test_job_duplicate_detected_event_round_trip():
    from pydantic import TypeAdapter
    from arm_contracts import NotificationEvent
    from arm_contracts.notification_event import JobDuplicateDetectedEvent
    adapter = TypeAdapter(NotificationEvent)
    raw = json.loads((FIXTURES / "job_duplicate_detected_event.json").read_text())
    parsed = adapter.validate_python(raw)
    assert isinstance(parsed, JobDuplicateDetectedEvent)
    again = adapter.validate_python(json.loads(parsed.model_dump_json()))
    assert again == parsed
