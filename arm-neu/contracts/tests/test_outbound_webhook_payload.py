"""Tests for OutboundWebhookPayload — the v18 rich-payload wire shape
sent by arm-neu's notification dispatcher to webhook channels."""
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

FIXTURES = Path(__file__).parent / "fixtures"


def _event_payload_dict():
    return {
        "event_key": "job.failed",
        "event_id": str(uuid4()),
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "job_id": 169,
        "job_title": "Mysterysuspense",
        "job_disc_type": "dvd",
        "job_imdb_id": None,
        "phase": "rip",
        "error_message": "makemkvcon failed",
        "error_code": "MAKEMKV_FAILED",
    }


def test_channel_ref_minimal():
    from arm_contracts.outbound_webhook_payload import ChannelRef
    r = ChannelRef(id=1, name="HA", type="webhook")
    assert r.id == 1


def test_outbound_webhook_payload_basic():
    from arm_contracts.outbound_webhook_payload import (
        OutboundWebhookPayload,
        ChannelRef,
    )
    p = OutboundWebhookPayload(
        event=_event_payload_dict(),
        title="Job failed",
        body="Job 169 failed during rip",
        channel=ChannelRef(id=1, name="HA", type="webhook"),
        arm_instance_name="hifi",
        sent_at=datetime.now(timezone.utc),
    )
    assert p.schema_version == 1
    assert p.event.event_key == "job.failed"
    assert p.title == "Job failed"
    assert p.channel.name == "HA"


def test_outbound_webhook_payload_schema_version_locked():
    """schema_version must be the literal 1; anything else is a wire
    incompatibility and must fail validation."""
    from arm_contracts.outbound_webhook_payload import (
        OutboundWebhookPayload,
        ChannelRef,
    )
    with pytest.raises(ValidationError):
        OutboundWebhookPayload(
            schema_version=2,  # type: ignore[arg-type]
            event=_event_payload_dict(),
            title="X",
            body="Y",
            channel=ChannelRef(id=1, name="HA", type="webhook"),
            arm_instance_name=None,
            sent_at=datetime.now(timezone.utc),
        )


def test_outbound_webhook_payload_arm_instance_name_optional():
    from arm_contracts.outbound_webhook_payload import (
        OutboundWebhookPayload,
        ChannelRef,
    )
    p = OutboundWebhookPayload(
        event=_event_payload_dict(),
        title="X",
        body="Y",
        channel=ChannelRef(id=1, name="HA", type="webhook"),
        arm_instance_name=None,
        sent_at=datetime.now(timezone.utc),
    )
    assert p.arm_instance_name is None


def test_outbound_webhook_payload_public_re_exports():
    from arm_contracts import OutboundWebhookPayload, ChannelRef
    assert OutboundWebhookPayload is not None
    assert ChannelRef is not None


def test_outbound_webhook_payload_top_level_keys_are_stable():
    """The set of top-level keys in OutboundWebhookPayload is a public
    wire contract. Any addition or removal is a schema_version bump.
    This test guards against accidental field churn."""
    from arm_contracts import OutboundWebhookPayload
    raw = json.loads((FIXTURES / "outbound_webhook_payload.json").read_text())
    p = OutboundWebhookPayload.model_validate(raw)
    dumped = json.loads(p.model_dump_json())
    assert set(dumped.keys()) == {
        "schema_version",
        "event",
        "title",
        "body",
        "channel",
        "arm_instance_name",
        "sent_at",
    }
