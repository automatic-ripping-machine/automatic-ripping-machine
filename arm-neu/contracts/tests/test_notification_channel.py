"""Tests for notification channel models (config union, Channel,
ChannelCreate, ChannelUpdate)."""
from datetime import datetime, timezone

import pytest
from pydantic import TypeAdapter, ValidationError


def test_apprise_channel_config():
    from arm_contracts.notification_channel import AppriseChannelConfig
    c = AppriseChannelConfig(url="discord://id/token")
    assert c.type == "apprise"
    assert c.url == "discord://id/token"


def test_webhook_channel_config_with_secret():
    from arm_contracts.notification_channel import WebhookChannelConfig
    c = WebhookChannelConfig(
        url="https://example.com/hook",
        shared_secret="s3cret",
    )
    assert c.type == "webhook"
    # SecretStr masks on repr/str but exposes via get_secret_value().
    assert str(c.shared_secret) == "**********"
    assert c.shared_secret.get_secret_value() == "s3cret"


def test_webhook_channel_config_no_secret():
    from arm_contracts.notification_channel import WebhookChannelConfig
    c = WebhookChannelConfig(url="https://example.com/hook")
    assert c.shared_secret is None
    assert c.headers is None


def test_webhook_channel_config_rejects_non_http_url():
    from arm_contracts.notification_channel import WebhookChannelConfig
    with pytest.raises(ValidationError):
        WebhookChannelConfig(url="ftp://example.com/")


def test_bash_channel_config():
    from arm_contracts.notification_channel import BashChannelConfig
    c = BashChannelConfig(script_path="/opt/arm/scripts/notify.sh")
    assert c.type == "bash"
    assert c.script_path == "/opt/arm/scripts/notify.sh"


def test_channel_config_union_discriminates_apprise():
    from arm_contracts.notification_channel import (
        ChannelConfig,
        AppriseChannelConfig,
    )
    adapter = TypeAdapter(ChannelConfig)
    parsed = adapter.validate_python({"type": "apprise", "url": "discord://x/y"})
    assert isinstance(parsed, AppriseChannelConfig)


def test_channel_config_union_discriminates_webhook():
    from arm_contracts.notification_channel import (
        ChannelConfig,
        WebhookChannelConfig,
    )
    adapter = TypeAdapter(ChannelConfig)
    parsed = adapter.validate_python({
        "type": "webhook",
        "url": "https://example.com/hook",
    })
    assert isinstance(parsed, WebhookChannelConfig)


def test_channel_config_union_discriminates_bash():
    from arm_contracts.notification_channel import (
        ChannelConfig,
        BashChannelConfig,
    )
    adapter = TypeAdapter(ChannelConfig)
    parsed = adapter.validate_python({"type": "bash", "script_path": "/x"})
    assert isinstance(parsed, BashChannelConfig)


def test_channel_config_union_rejects_unknown_type():
    from arm_contracts.notification_channel import ChannelConfig
    adapter = TypeAdapter(ChannelConfig)
    with pytest.raises(ValidationError):
        adapter.validate_python({"type": "smoke-signal", "url": "x"})


def test_event_keys_literal_matches_event_union():
    """The EventKey literal must enumerate exactly the event_key
    discriminator values used by NotificationEvent. Adding a 5th event
    to the union without updating EventKey would break channel
    subscriptions silently — this test fails if that drift ever happens.

    Derives the expected set from NotificationEvent itself (not a
    hardcoded class list) so the guard is self-maintaining."""
    from typing import get_args
    from arm_contracts.notification_channel import EventKey
    from arm_contracts.notification_event import NotificationEvent

    # NotificationEvent is Annotated[Union[...], Field(discriminator=...)].
    # get_args(NotificationEvent) returns (Union[...], FieldInfo). The
    # first element is the Union; get_args on that yields the concrete
    # event classes.
    annotated_args = get_args(NotificationEvent)
    union_type = annotated_args[0]
    event_classes = get_args(union_type)

    union_keys = {
        cls.model_fields["event_key"].default for cls in event_classes
    }
    event_keys_set = set(get_args(EventKey))
    assert event_keys_set == union_keys


def test_channel_template_all_fields_optional():
    from arm_contracts.notification_channel import ChannelTemplate
    t = ChannelTemplate()
    assert t.title is None
    assert t.body is None
    t2 = ChannelTemplate(title="X", body="Y")
    assert t2.title == "X"
    assert t2.body == "Y"


def test_public_re_exports():
    """All new names must be importable from the package root."""
    from arm_contracts import (
        # event types
        NotificationEvent,
        JobStartedEvent,
        JobRipCompleteEvent,
        JobTranscodeCompleteEvent,
        JobFailedEvent,
        # channel types
        AppriseChannelConfig,
        WebhookChannelConfig,
        BashChannelConfig,
        ChannelConfig,
        ChannelTemplate,
        EventKey,
    )
    # If any name is missing the import raises ImportError, failing the test.
    assert NotificationEvent is not None
    assert ChannelConfig is not None


def _valid_apprise_config_dict():
    return {"type": "apprise", "url": "discord://id/token"}


def test_channel_model_minimal():
    from arm_contracts.notification_channel import Channel
    c = Channel(
        id=1,
        type="apprise",
        name="Family Discord",
        enabled=True,
        config=_valid_apprise_config_dict(),
        subscribed_events=["job.started"],
    )
    assert c.id == 1
    assert c.name == "Family Discord"
    assert c.templates == {}
    assert c.last_fired_at is None
    assert c.last_success_at is None
    assert c.last_error is None


def test_channel_model_with_template():
    from arm_contracts.notification_channel import Channel
    c = Channel(
        id=1,
        type="apprise",
        name="X",
        enabled=True,
        config=_valid_apprise_config_dict(),
        subscribed_events=["job.started", "job.failed"],
        templates={
            "job.started": {"title": "Disc detected", "body": "{job_title}"},
        },
    )
    assert c.templates["job.started"].title == "Disc detected"


def test_channel_create_defaults():
    from arm_contracts.notification_channel import ChannelCreate
    c = ChannelCreate(
        type="bash",
        name="Log everything",
        config={"type": "bash", "script_path": "/x"},
    )
    assert c.enabled is True
    assert c.subscribed_events == []
    assert c.templates == {}


def test_channel_update_all_optional():
    from arm_contracts.notification_channel import ChannelUpdate
    u = ChannelUpdate()  # all fields optional → empty patch
    assert u.name is None
    assert u.config is None
    assert u.subscribed_events is None

    u2 = ChannelUpdate(name="Renamed")
    assert u2.name == "Renamed"
    assert u2.config is None


def test_channel_rejects_invalid_event_key():
    from pydantic import ValidationError
    from arm_contracts.notification_channel import ChannelCreate
    with pytest.raises(ValidationError):
        ChannelCreate(
            type="apprise",
            name="X",
            config=_valid_apprise_config_dict(),
            subscribed_events=["job.someday-new"],
        )


def test_channel_template_keyed_by_event_key():
    """Pydantic v2 enforces dict keys against the Literal type."""
    from pydantic import ValidationError
    from arm_contracts.notification_channel import ChannelCreate
    with pytest.raises(ValidationError):
        ChannelCreate(
            type="apprise",
            name="X",
            config=_valid_apprise_config_dict(),
            templates={"not.a.valid.event": {"title": "x"}},
        )


def test_channel_apprise_channel_re_exports():
    """Channel, ChannelCreate, ChannelUpdate must be importable from
    the package root."""
    from arm_contracts import Channel, ChannelCreate, ChannelUpdate
    assert Channel is not None
    assert ChannelCreate is not None
    assert ChannelUpdate is not None


def test_apprise_channel_config_with_service_id():
    from arm_contracts.notification_channel import AppriseChannelConfig
    c = AppriseChannelConfig(url="discord://id/token", service_id="discord")
    assert c.service_id == "discord"


def test_apprise_channel_config_service_id_optional():
    from arm_contracts.notification_channel import AppriseChannelConfig
    c = AppriseChannelConfig(url="discord://id/token")
    assert c.service_id is None


def test_apprise_channel_config_with_fields():
    from arm_contracts.notification_channel import AppriseChannelConfig
    c = AppriseChannelConfig(url="discord://1/2", service_id="discord",
                              fields={"webhook_id": "1", "webhook_token": "2"})
    assert c.fields == {"webhook_id": "1", "webhook_token": "2"}


def test_apprise_channel_config_fields_accepts_bool_and_int():
    """Apprise advanced fields include bools (tts) and ints (thread).
    fields must accept JSON primitives, not str-only."""
    from arm_contracts.notification_channel import AppriseChannelConfig
    c = AppriseChannelConfig(url="discord://1/2", service_id="discord",
                              fields={"webhook_id": "1", "tts": True, "thread": 5})
    assert c.fields == {"webhook_id": "1", "tts": True, "thread": 5}


def test_apprise_channel_config_fields_optional():
    from arm_contracts.notification_channel import AppriseChannelConfig
    c = AppriseChannelConfig(url="discord://1/2")
    assert c.fields is None
