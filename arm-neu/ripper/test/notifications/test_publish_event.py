"""Tests for the public ``publish_event`` entry point."""
from datetime import datetime, timezone
from uuid import uuid4

import pytest


def _make_started_event():
    from arm_contracts import JobStartedEvent
    from arm_contracts.enums import Disctype
    return JobStartedEvent(
        event_id=uuid4(),
        occurred_at=datetime.now(timezone.utc),
        job_id=1,
        job_title="T",
        job_disc_type=Disctype.dvd,
        drive_mount="/dev/sr0",
    )


def test_publish_event_writes_notification_history(db_session):
    """The lifecycle event must appear in the Notifications history
    table so the UI's notification pane reflects it."""
    from arm.notifications import publish_event
    from arm.models.notifications import Notifications

    before = Notifications.query.count()
    publish_event(_make_started_event())
    after = Notifications.query.count()
    assert after == before + 1


def test_publish_event_enqueues_one_outbox_row_per_subscribed_channel(
    db_session, make_channel
):
    """Each channel whose subscribed_events includes the event_key
    should get exactly one outbox row."""
    from arm.notifications import publish_event
    from arm.notifications.models import NotificationOutbox

    subscribed = make_channel(
        type="apprise",
        config={"type": "apprise", "url": "discord://x/y"},
        subscribed_events=["job.started", "job.failed"],
    )
    unrelated = make_channel(
        type="apprise",
        config={"type": "apprise", "url": "discord://a/b"},
        subscribed_events=["job.failed"],  # not subscribed to job.started
    )
    publish_event(_make_started_event())

    for_subscribed = NotificationOutbox.query.filter_by(
        channel_id=subscribed.id).count()
    for_unrelated = NotificationOutbox.query.filter_by(
        channel_id=unrelated.id).count()
    assert for_subscribed == 1
    assert for_unrelated == 0


def test_publish_event_skips_disabled_channels(db_session, make_channel):
    """A channel with enabled=False must not receive outbox rows."""
    from arm.notifications import publish_event
    from arm.notifications.models import NotificationOutbox

    disabled = make_channel(
        type="apprise",
        config={"type": "apprise", "url": "discord://x/y"},
        subscribed_events=["job.started"],
        enabled=False,
    )
    publish_event(_make_started_event())
    rows = NotificationOutbox.query.filter_by(channel_id=disabled.id).count()
    assert rows == 0


def test_publish_event_payload_is_event_dump(db_session, make_channel):
    """The outbox row's event_payload is a JSON-serializable dump of
    the event, with the event_key discriminator present."""
    from arm.notifications import publish_event
    from arm.notifications.models import NotificationOutbox

    ch = make_channel(
        type="apprise",
        config={"type": "apprise", "url": "discord://x/y"},
        subscribed_events=["job.started"],
    )
    publish_event(_make_started_event())
    row = NotificationOutbox.query.filter_by(channel_id=ch.id).first()
    assert row.event_key == "job.started"
    assert row.event_payload["event_key"] == "job.started"
    assert row.event_payload["job_id"] == 1


def test_publish_event_rejects_non_event_arg():
    from arm.notifications import publish_event
    with pytest.raises(TypeError):
        publish_event("not an event")  # type: ignore[arg-type]
