"""End-to-end integration test: publish_event -> outbox -> dispatcher
-> apprise send. Uses a mocked send_apprise so we don't actually hit
Discord — the goal is to confirm the wiring, not the apprise library.

Written as sync tests driving their own event loop via asyncio.run so
they don't depend on pytest-asyncio being installed in CI.
"""
import asyncio
import datetime
from unittest.mock import patch
from uuid import uuid4


def _started_event():
    from arm_contracts import JobStartedEvent
    from arm_contracts.enums import Disctype
    return JobStartedEvent(
        event_id=uuid4(),
        occurred_at=datetime.datetime.now(datetime.timezone.utc),
        job_id=42,
        job_title="Some Movie",
        job_disc_type=Disctype.dvd,
        drive_mount="/dev/sr0",
    )


def test_publish_then_dispatch_success(db_session, make_channel):
    from arm.notifications import publish_event
    from arm.notifications import dispatcher as dispatcher_module
    from arm.notifications.models import NotificationOutbox

    ch = make_channel(
        type="apprise",
        config={"type": "apprise", "url": "discord://x/y"},
        subscribed_events=["job.started"],
    )

    publish_event(_started_event())
    assert NotificationOutbox.query.filter_by(channel_id=ch.id).count() == 1

    async def _run():
        stop = asyncio.Event()
        with patch("arm.notifications.dispatcher.send_apprise",
                   return_value=(True, None)), \
                patch.object(dispatcher_module, "_TICK_INTERVAL_SECONDS", 0.05):
            task = asyncio.create_task(
                dispatcher_module.run_dispatcher_loop(stop_event=stop)
            )
            for _ in range(40):
                await asyncio.sleep(0.05)
                row = (NotificationOutbox.query
                       .filter_by(channel_id=ch.id).first())
                if row and row.status == "success":
                    break
            stop.set()
            await asyncio.wait_for(task, timeout=5.0)

    asyncio.run(_run())
    row = NotificationOutbox.query.filter_by(channel_id=ch.id).first()
    assert row.status == "success"
    assert row.completed_at is not None


def test_publish_then_dispatch_retry_then_succeed(
    db_session, make_channel
):
    """If the first send fails (transient), the dispatcher retries on
    the next tick. After two attempts succeed, the row is success."""
    from arm.notifications import publish_event
    from arm.notifications import dispatcher as dispatcher_module
    from arm.notifications.models import NotificationOutbox

    ch = make_channel(
        type="apprise",
        config={"type": "apprise", "url": "discord://x/y"},
        subscribed_events=["job.started"],
    )

    call_count = {"n": 0}

    def flaky_send(**kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return (False, "transient")
        return (True, None)

    publish_event(_started_event())

    async def _run():
        stop = asyncio.Event()
        with patch("arm.notifications.dispatcher.send_apprise",
                   side_effect=flaky_send), \
                patch.object(dispatcher_module, "_TICK_INTERVAL_SECONDS", 0.05):
            task = asyncio.create_task(
                dispatcher_module.run_dispatcher_loop(stop_event=stop)
            )
            for _ in range(60):
                await asyncio.sleep(0.05)
                row = (NotificationOutbox.query
                       .filter_by(channel_id=ch.id).first())
                if row and row.status == "pending":
                    # Force backoff to elapse so the retry happens within
                    # the test window.
                    row.next_attempt_at = datetime.datetime.utcnow()
                    db_session.commit()
                if row and row.status == "success":
                    break
            stop.set()
            await asyncio.wait_for(task, timeout=5.0)

    asyncio.run(_run())
    row = NotificationOutbox.query.filter_by(channel_id=ch.id).first()
    assert row.status == "success"
    # attempts increments on each failure; the successful retry does not
    # increment, so we expect exactly one failure recorded plus the call
    # counter reflecting both sends.
    assert row.attempts >= 1
    assert call_count["n"] >= 2
