"""Outbox operations consumed by the dispatcher.

Producer-side enqueue happens directly in ``events.publish_event``;
this module owns the consumer-side dequeue/mark/retry/cleanup loop.
"""
import datetime
import logging

from arm.database import db
from arm.notifications.models import NotificationChannel, NotificationOutbox

log = logging.getLogger(__name__)

_MAX_ATTEMPTS = 5
_BACKOFF_BASE_SECONDS = 30
_BACKOFF_CAP_SECONDS = 3600


def _backoff_seconds(attempts: int) -> int:
    """Exponential backoff: 30 * 2^attempts, capped at 1h."""
    seconds = _BACKOFF_BASE_SECONDS * (2 ** attempts)
    return min(seconds, _BACKOFF_CAP_SECONDS)


def dequeue_due(limit: int = 50) -> list[NotificationOutbox]:
    """Find pending rows past their next_attempt_at, mark them in_flight,
    and return them for the dispatcher to send."""
    now = datetime.datetime.utcnow()
    rows = (NotificationOutbox.query
            .filter(NotificationOutbox.status == "pending",
                    NotificationOutbox.next_attempt_at <= now)
            .order_by(NotificationOutbox.next_attempt_at.asc())
            .limit(limit)
            .all())
    for r in rows:
        r.status = "in_flight"
        r.next_attempt_at = now  # so the reaper can find stale ones
    db.session.commit()
    return rows


def record_success(outbox_id: int) -> None:
    """Mark an outbox row successful and update the channel's last_*."""
    row = NotificationOutbox.query.get(outbox_id)
    if row is None:
        log.warning("record_success: outbox row %s vanished", outbox_id)
        return
    now = datetime.datetime.utcnow()
    row.status = "success"
    row.completed_at = now
    row.last_error = None
    channel = NotificationChannel.query.get(row.channel_id)
    if channel is not None:
        channel.last_fired_at = now
        channel.last_success_at = now
        channel.last_error = None
    db.session.commit()


def record_failure(outbox_id: int, error: str, terminal: bool) -> None:
    """Mark an outbox row failed (or schedule a retry).

    :param outbox_id: target row id.
    :param error: short error message (truncated to 512 chars to fit
        the column).
    :param terminal: True for non-retryable failures (4xx, bad URL,
        template render). False for transient failures (5xx, timeout,
        connection error) which retry with backoff up to _MAX_ATTEMPTS.
    """
    row = NotificationOutbox.query.get(outbox_id)
    if row is None:
        log.warning("record_failure: outbox row %s vanished", outbox_id)
        return
    now = datetime.datetime.utcnow()
    short_error = (error or "")[:512]
    row.attempts += 1
    row.last_error = short_error
    if terminal or row.attempts >= _MAX_ATTEMPTS:
        row.status = "failed"
        row.completed_at = now
    else:
        row.status = "pending"
        row.next_attempt_at = now + datetime.timedelta(
            seconds=_backoff_seconds(row.attempts))
    channel = NotificationChannel.query.get(row.channel_id)
    if channel is not None:
        channel.last_fired_at = now
        channel.last_error = short_error
    db.session.commit()


def reap_stale_in_flight(stale_after_minutes: int = 5) -> int:
    """Return stale in_flight rows to pending on dispatcher startup.

    Rows whose ``next_attempt_at`` (which dequeue_due sets to "now"
    when marking in_flight) is older than the threshold are rescued.
    Returns the count rescued.
    """
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(
        minutes=stale_after_minutes)
    stale = (NotificationOutbox.query
             .filter(NotificationOutbox.status == "in_flight",
                     NotificationOutbox.next_attempt_at < cutoff)
             .all())
    for r in stale:
        r.status = "pending"
        r.next_attempt_at = datetime.datetime.utcnow()
    if stale:
        db.session.commit()
    return len(stale)


def cleanup_completed(older_than_days: int = 7) -> int:
    """Delete success/failed outbox rows older than the threshold.

    Returns the count deleted. Called from the existing periodic
    cleanup hook in arm-neu (no new scheduler).
    """
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(
        days=older_than_days)
    q = (NotificationOutbox.query
         .filter(NotificationOutbox.status.in_(("success", "failed")),
                 NotificationOutbox.completed_at < cutoff))
    count = q.count()
    q.delete(synchronize_session=False)
    db.session.commit()
    return count
