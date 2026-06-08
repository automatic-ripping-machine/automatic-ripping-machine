"""``publish_event`` — the only producer entry point into the notifications
module from the rest of arm-neu.

This function is intentionally synchronous and side-effect-only: it
writes one Notifications history row and N outbox rows, then returns.
The dispatcher (a separate asyncio task) picks up the outbox rows.

Callers in arm.ripper construct a contracts NotificationEvent and pass
it here. Adding a new event type is a contracts change first; arm-neu
ripper code then publishes it.
"""
import datetime
import json
import logging

from arm_contracts.notification_event import (
    JobStartedEvent,
    JobRipCompleteEvent,
    JobTranscodeCompleteEvent,
    JobFailedEvent,
    JobManualWaitRequiredEvent,
    JobDuplicateDetectedEvent,
)

from arm.database import db
from arm.models.notifications import Notifications
from arm.notifications.models import NotificationChannel, NotificationOutbox
from arm.notifications.templates import render_title_and_body

log = logging.getLogger(__name__)

# Tuple of concrete event classes so we can isinstance-check the union
# (you can't isinstance() a typing.Annotated union directly).
_EVENT_CLASSES = (
    JobStartedEvent,
    JobRipCompleteEvent,
    JobTranscodeCompleteEvent,
    JobFailedEvent,
    JobManualWaitRequiredEvent,
    JobDuplicateDetectedEvent,
)


def publish_event(event) -> None:
    """Publish a lifecycle event to the local history and the channel
    outbox.

    :param event: a contracts ``NotificationEvent`` (one of the six
        concrete subclasses). Passing anything else raises ``TypeError``.
    :raises TypeError: if ``event`` is not a NotificationEvent.
    """
    if not isinstance(event, _EVENT_CLASSES):
        raise TypeError(
            f"publish_event expected a NotificationEvent, got "
            f"{type(event).__name__}"
        )

    # 1. Write to history (using the default-template title/body so the
    #    UI's existing notification pane shows something readable).
    title, body = render_title_and_body(event, channel_template=None)
    db.session.add(Notifications(title=title, message=body))

    # 2. Enqueue per subscribed enabled channel.
    payload = json.loads(event.model_dump_json())
    channels = NotificationChannel.query.filter_by(enabled=True).all()
    for ch in channels:
        if event.event_key not in (ch.subscribed_events or []):
            continue
        db.session.add(NotificationOutbox(
            channel_id=ch.id,
            event_key=event.event_key,
            event_payload=payload,
            status="pending",
            attempts=0,
            next_attempt_at=datetime.datetime.utcnow(),
        ))

    db.session.commit()
    log.info("published event %s for job_id=%s",
             event.event_key, event.job_id)
