"""Tests for the outbox module: dequeue, retry policy, reaper, cleanup."""
import datetime

import pytest


def _outbox_row(db_session, channel_id, status="pending",
                next_at=None, attempts=0):
    from arm.notifications.models import NotificationOutbox
    row = NotificationOutbox(
        channel_id=channel_id,
        event_key="job.started",
        event_payload={"event_key": "job.started", "job_id": 1},
        status=status,
        attempts=attempts,
        next_attempt_at=next_at or datetime.datetime.utcnow(),
    )
    db_session.add(row)
    db_session.commit()
    return row


def test_dequeue_returns_pending_due_rows(db_session, make_channel):
    from arm.notifications.outbox import dequeue_due
    ch = make_channel(type="apprise",
                      config={"type": "apprise", "url": "discord://x/y"},
                      subscribed_events=["job.started"])

    due = _outbox_row(db_session, ch.id, status="pending",
                      next_at=datetime.datetime.utcnow() - datetime.timedelta(minutes=1))
    future = _outbox_row(db_session, ch.id, status="pending",
                         next_at=datetime.datetime.utcnow() + datetime.timedelta(hours=1))
    completed = _outbox_row(db_session, ch.id, status="success",
                            next_at=datetime.datetime.utcnow() - datetime.timedelta(minutes=1))

    rows = dequeue_due(limit=10)
    ids = {r.id for r in rows}
    assert due.id in ids
    assert future.id not in ids
    assert completed.id not in ids


def test_dequeue_marks_in_flight(db_session, make_channel):
    from arm.notifications.outbox import dequeue_due
    from arm.notifications.models import NotificationOutbox
    ch = make_channel(type="apprise",
                      config={"type": "apprise", "url": "discord://x/y"},
                      subscribed_events=["job.started"])
    r = _outbox_row(db_session, ch.id, status="pending",
                    next_at=datetime.datetime.utcnow() - datetime.timedelta(minutes=1))
    rows = dequeue_due(limit=10)
    assert len(rows) == 1
    refreshed = NotificationOutbox.query.get(r.id)
    assert refreshed.status == "in_flight"


def test_record_success(db_session, make_channel):
    from arm.notifications.outbox import record_success
    from arm.notifications.models import NotificationOutbox, NotificationChannel
    ch = make_channel(type="apprise",
                      config={"type": "apprise", "url": "discord://x/y"},
                      subscribed_events=["job.started"])
    r = _outbox_row(db_session, ch.id, status="in_flight")
    record_success(r.id)
    refreshed = NotificationOutbox.query.get(r.id)
    assert refreshed.status == "success"
    assert refreshed.completed_at is not None
    channel = NotificationChannel.query.get(ch.id)
    assert channel.last_success_at is not None
    assert channel.last_error is None


def test_record_success_on_vanished_row_is_noop(db_session):
    """If the row was deleted between dequeue and record, record_success
    logs and returns without raising."""
    from arm.notifications.outbox import record_success
    # No exception, no DB write — just a silent no-op.
    record_success(999999)


def test_record_failure_on_vanished_row_is_noop(db_session):
    """Same guard on the failure path."""
    from arm.notifications.outbox import record_failure
    record_failure(999999, "anything", terminal=False)


def test_record_failure_transient_schedules_retry(db_session, make_channel):
    """Transient failure: status returns to pending, attempts++, backoff applied."""
    from arm.notifications.outbox import record_failure
    from arm.notifications.models import NotificationOutbox
    ch = make_channel(type="apprise",
                      config={"type": "apprise", "url": "discord://x/y"},
                      subscribed_events=["job.started"])
    r = _outbox_row(db_session, ch.id, status="in_flight", attempts=1)
    before = datetime.datetime.utcnow()
    record_failure(r.id, error="boom", terminal=False)
    refreshed = NotificationOutbox.query.get(r.id)
    assert refreshed.status == "pending"
    assert refreshed.attempts == 2
    assert refreshed.next_attempt_at > before
    assert refreshed.last_error == "boom"


def test_record_failure_after_max_attempts_becomes_failed(db_session, make_channel):
    """After 5 attempts, transient failures become terminal."""
    from arm.notifications.outbox import record_failure
    from arm.notifications.models import NotificationOutbox
    ch = make_channel(type="apprise",
                      config={"type": "apprise", "url": "discord://x/y"},
                      subscribed_events=["job.started"])
    r = _outbox_row(db_session, ch.id, status="in_flight", attempts=5)
    record_failure(r.id, error="still failing", terminal=False)
    refreshed = NotificationOutbox.query.get(r.id)
    assert refreshed.status == "failed"


def test_record_failure_terminal_no_retry(db_session, make_channel):
    """Terminal failure (e.g. 4xx, bad URL): status=failed immediately."""
    from arm.notifications.outbox import record_failure
    from arm.notifications.models import NotificationOutbox
    ch = make_channel(type="apprise",
                      config={"type": "apprise", "url": "discord://x/y"},
                      subscribed_events=["job.started"])
    r = _outbox_row(db_session, ch.id, status="in_flight", attempts=0)
    record_failure(r.id, error="HTTP 400", terminal=True)
    refreshed = NotificationOutbox.query.get(r.id)
    assert refreshed.status == "failed"
    assert refreshed.attempts == 1  # we still increment to record the attempt


def test_backoff_grows_with_attempts():
    """Backoff is 30 * 2^attempts seconds, capped at 1h."""
    from arm.notifications.outbox import _backoff_seconds
    assert _backoff_seconds(0) == 30
    assert _backoff_seconds(1) == 60
    assert _backoff_seconds(2) == 120
    assert _backoff_seconds(10) == 3600  # capped


def test_reap_in_flight_returns_stale_rows(db_session, make_channel):
    """Rows stuck in in_flight for >5min get returned to pending."""
    from arm.notifications.outbox import reap_stale_in_flight
    from arm.notifications.models import NotificationOutbox
    ch = make_channel(type="apprise",
                      config={"type": "apprise", "url": "discord://x/y"},
                      subscribed_events=["job.started"])
    # Stale: 10 min old
    stale = _outbox_row(db_session, ch.id, status="in_flight")
    # Backdate the next_attempt_at to simulate the row sitting there for 10 min
    stale.next_attempt_at = datetime.datetime.utcnow() - datetime.timedelta(minutes=10)
    db_session.commit()

    # Recent: just-started
    recent = _outbox_row(db_session, ch.id, status="in_flight")

    rescued = reap_stale_in_flight(stale_after_minutes=5)
    assert rescued == 1
    db_session.refresh(stale)
    db_session.refresh(recent)
    assert stale.status == "pending"
    assert recent.status == "in_flight"


def test_cleanup_completed_older_than_7_days(db_session, make_channel):
    from arm.notifications.outbox import cleanup_completed
    from arm.notifications.models import NotificationOutbox
    ch = make_channel(type="apprise",
                      config={"type": "apprise", "url": "discord://x/y"},
                      subscribed_events=["job.started"])
    old = _outbox_row(db_session, ch.id, status="success")
    old.completed_at = datetime.datetime.utcnow() - datetime.timedelta(days=10)
    recent = _outbox_row(db_session, ch.id, status="success")
    recent.completed_at = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    pending = _outbox_row(db_session, ch.id, status="pending")
    db_session.commit()

    # Store IDs before cleanup (bulk delete can detach instances)
    old_id = old.id
    recent_id = recent.id
    pending_id = pending.id

    deleted = cleanup_completed(older_than_days=7)
    assert deleted == 1
    assert NotificationOutbox.query.get(old_id) is None
    assert NotificationOutbox.query.get(recent_id) is not None
    assert NotificationOutbox.query.get(pending_id) is not None


def test_cleanup_completed_is_callable_from_outbox_module():
    """cleanup_completed must remain importable as
    arm.notifications.outbox.cleanup_completed so the dispatcher loop
    (and any future periodic hook) can call it without reaching into
    internals."""
    from arm.notifications.outbox import cleanup_completed
    assert callable(cleanup_completed)


def test_dispatcher_loop_invokes_cleanup_completed(db_session, make_channel):
    """Dispatcher loop is the periodic hook for outbox retention. Verify
    cleanup_completed is called at least once when the loop runs for
    long enough that the cleanup interval elapses (we force-elapse the
    deadline via monkey-patching the module constant)."""
    import asyncio
    from unittest.mock import patch

    from arm.notifications import dispatcher as dispatcher_module

    calls = {"n": 0}

    def fake_cleanup(older_than_days):
        calls["n"] += 1
        assert older_than_days == dispatcher_module._CLEANUP_RETENTION_DAYS
        return 0

    async def _run():
        stop = asyncio.Event()
        with patch.object(dispatcher_module, "_CLEANUP_INTERVAL_SECONDS", 0.0), \
                patch.object(dispatcher_module, "_TICK_INTERVAL_SECONDS", 0.01), \
                patch.object(dispatcher_module, "cleanup_completed",
                             side_effect=fake_cleanup):
            task = asyncio.create_task(
                dispatcher_module.run_dispatcher_loop(stop_event=stop)
            )
            # Let the loop tick a few times.
            for _ in range(10):
                await asyncio.sleep(0.01)
                if calls["n"] > 0:
                    break
            stop.set()
            await asyncio.wait_for(task, timeout=2.0)

    asyncio.run(_run())
    assert calls["n"] >= 1
