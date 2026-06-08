"""Tests for the dispatcher's per-row processing logic.

The actual asyncio loop is exercised by the integration test in
Task 12 (the publish→dispatch→success end-to-end). Here we test
``process_one_row`` in isolation so behavior is fully covered without
spinning up the loop.
"""
import datetime
from unittest.mock import patch, MagicMock

import pytest


def _outbox_row(db_session, channel_id, event_payload, status="in_flight"):
    from arm.notifications.models import NotificationOutbox
    row = NotificationOutbox(
        channel_id=channel_id,
        event_key=event_payload["event_key"],
        event_payload=event_payload,
        status=status,
        attempts=0,
        next_attempt_at=datetime.datetime.utcnow(),
    )
    db_session.add(row)
    db_session.commit()
    return row


def _started_payload():
    from uuid import uuid4
    return {
        "event_key": "job.started",
        "event_id": str(uuid4()),
        "occurred_at": datetime.datetime.utcnow().isoformat(),
        "job_id": 1,
        "job_title": "X",
        "job_disc_type": "dvd",
        "job_imdb_id": None,
        "drive_mount": "/dev/sr0",
    }


def test_dispatcher_apprise_success_marks_row_success(db_session, make_channel):
    from arm.notifications.dispatcher import process_one_row
    from arm.notifications.models import NotificationOutbox

    ch = make_channel(
        type="apprise",
        config={"type": "apprise", "url": "discord://x/y"},
        subscribed_events=["job.started"],
    )
    row = _outbox_row(db_session, ch.id, _started_payload())

    with patch("arm.notifications.dispatcher.send_apprise",
               return_value=(True, None)) as send:
        process_one_row(row.id)

    db_session.refresh(row)
    assert row.status == "success"
    send.assert_called_once()


def test_dispatcher_apprise_transient_failure_reschedules(
    db_session, make_channel
):
    from arm.notifications.dispatcher import process_one_row
    from arm.notifications.models import NotificationOutbox

    ch = make_channel(
        type="apprise",
        config={"type": "apprise", "url": "discord://x/y"},
        subscribed_events=["job.started"],
    )
    row = _outbox_row(db_session, ch.id, _started_payload())

    with patch("arm.notifications.dispatcher.send_apprise",
               return_value=(False, "apprise.notify() returned False")):
        process_one_row(row.id)

    db_session.refresh(row)
    assert row.status == "pending"  # retried
    assert row.attempts == 1


def test_dispatcher_webhook_4xx_is_terminal(db_session, make_channel):
    from arm.notifications.dispatcher import process_one_row
    from arm.notifications.models import NotificationOutbox

    ch = make_channel(
        type="webhook",
        config={"type": "webhook",
                "url": "https://example.com/hook"},
        subscribed_events=["job.started"],
    )
    row = _outbox_row(db_session, ch.id, _started_payload())

    with patch("arm.notifications.dispatcher.send_webhook",
               return_value=(False, "HTTP 400: bad request terminal=true")):
        process_one_row(row.id)

    db_session.refresh(row)
    assert row.status == "failed"


def test_dispatcher_bash_runs_with_correct_env(db_session, make_channel):
    from arm.notifications.dispatcher import process_one_row

    ch = make_channel(
        type="bash",
        config={"type": "bash", "script_path": "/x"},
        subscribed_events=["job.started"],
    )
    row = _outbox_row(db_session, ch.id, _started_payload())

    with patch("arm.notifications.dispatcher.send_bash",
               return_value=(True, None)) as send:
        process_one_row(row.id)

    send.assert_called_once()
    kwargs = send.call_args.kwargs
    assert kwargs["script_path"] == "/x"
    env = kwargs["env_vars"]
    assert env["ARM_EVENT_KEY"] == "job.started"
    assert env["ARM_JOB_ID"] == "1"
    assert "ARM_TITLE" in env


def test_dispatcher_template_render_failure_is_terminal(
    db_session, make_channel
):
    """If the template references a missing variable, fail terminal."""
    from arm.notifications.dispatcher import process_one_row

    ch = make_channel(
        type="apprise",
        config={"type": "apprise", "url": "discord://x/y"},
        subscribed_events=["job.started"],
        templates={"job.started": {
            "title": "{nonexistent_field}", "body": "x"}},
    )
    row = _outbox_row(db_session, ch.id, _started_payload())

    process_one_row(row.id)
    db_session.refresh(row)
    assert row.status == "failed"
    assert "template" in row.last_error.lower()


def test_dispatcher_skips_disabled_channel(db_session, make_channel):
    """A channel disabled between enqueue and dispatch is skipped:
    mark the row failed (since we can't retry a disabled channel)."""
    from arm.notifications.dispatcher import process_one_row

    ch = make_channel(
        type="apprise",
        config={"type": "apprise", "url": "discord://x/y"},
        subscribed_events=["job.started"],
        enabled=False,
    )
    row = _outbox_row(db_session, ch.id, _started_payload())

    process_one_row(row.id)
    db_session.refresh(row)
    assert row.status == "failed"
    assert "disabled" in row.last_error.lower()


def test_dispatcher_handles_vanished_channel(db_session, make_channel):
    """If the channel row is deleted between enqueue and dispatch, mark
    the outbox row failed and move on."""
    from arm.notifications.dispatcher import process_one_row
    from arm.notifications.models import NotificationChannel

    ch = make_channel(
        type="apprise",
        config={"type": "apprise", "url": "discord://x/y"},
        subscribed_events=["job.started"],
    )
    row = _outbox_row(db_session, ch.id, _started_payload())
    db_session.delete(ch)
    db_session.commit()

    process_one_row(row.id)
    db_session.refresh(row)
    assert row.status == "failed"


def test_process_one_row_returns_silently_when_outbox_vanished(db_session):
    """Calling process_one_row with a missing outbox id must not raise
    and must not invoke record_failure (there's nothing to fail)."""
    from arm.notifications import dispatcher as dispatcher_mod
    from arm.notifications.dispatcher import process_one_row

    with patch.object(dispatcher_mod, "record_failure") as rec_fail, \
         patch.object(dispatcher_mod, "record_success") as rec_ok:
        # 999999 is well outside any test-fixture-allocated id space.
        process_one_row(999999)

    rec_fail.assert_not_called()
    rec_ok.assert_not_called()


def test_process_one_row_bash_failure_is_terminal_regardless_of_marker(
    db_session, make_channel
):
    """Per N9 contract, bash failures are always terminal — even when the
    sender's error string lacks ``terminal=true`` (or explicitly says
    ``terminal=false``). The dispatcher must bypass _parse_terminal_flag
    for bash."""
    from arm.notifications.dispatcher import process_one_row

    ch = make_channel(
        type="bash",
        config={"type": "bash", "script_path": "/x"},
        subscribed_events=["job.started"],
    )
    row = _outbox_row(db_session, ch.id, _started_payload())

    # Note: NO terminal=true in the error string. In fact, claim the
    # opposite, so a naive _parse_terminal_flag call would mark this as
    # retryable. The dispatcher must override and treat it as terminal.
    with patch("arm.notifications.dispatcher.send_bash",
               return_value=(False, "bash script exit code 1 terminal=false")):
        process_one_row(row.id)

    db_session.refresh(row)
    assert row.status == "failed", (
        "bash failures must be terminal regardless of sender marker"
    )
    assert row.last_error is not None
    assert "bash" in row.last_error.lower()


def test_process_one_row_webhook_success_constructs_payload(
    db_session, make_channel
):
    """Happy-path webhook: assert send_webhook receives a payload_dict
    matching the documented HMAC-signed shape (event/title/body/channel/
    sent_at)."""
    from arm.notifications.dispatcher import process_one_row

    ch = make_channel(
        type="webhook",
        config={"type": "webhook",
                "url": "https://example.com/hook",
                "shared_secret": "s3cret"},
        subscribed_events=["job.started"],
    )
    row = _outbox_row(db_session, ch.id, _started_payload())

    with patch("arm.notifications.dispatcher.send_webhook",
               return_value=(True, None)) as send:
        process_one_row(row.id)

    send.assert_called_once()
    kwargs = send.call_args.kwargs
    payload = kwargs["payload_dict"]

    # Top-level shape:
    for key in ("event", "title", "body", "channel", "sent_at"):
        assert key in payload, f"missing top-level key '{key}' in webhook payload"

    # channel sub-shape:
    channel_ref = payload["channel"]
    assert channel_ref["id"] == ch.id
    assert channel_ref["name"] == ch.name
    assert channel_ref["type"] == "webhook"

    db_session.refresh(row)
    assert row.status == "success"


def test_dispatcher_event_reconstruction_failure_is_terminal(
    db_session, make_channel
):
    """A corrupt event_payload that the contracts TypeAdapter can't
    parse is a terminal failure (retrying won't fix bad data)."""
    from arm.notifications.dispatcher import process_one_row

    ch = make_channel(
        type="apprise",
        config={"type": "apprise", "url": "discord://x/y"},
        subscribed_events=["job.started"],
    )
    # event_key is valid (so it gets enqueued/dispatched) but the payload
    # is missing required fields, so reconstruction raises.
    bad_payload = {"event_key": "job.started"}
    row = _outbox_row(db_session, ch.id, bad_payload)

    process_one_row(row.id)
    db_session.refresh(row)
    assert row.status == "failed"
    assert "reconstruction" in row.last_error.lower()


def test_dispatcher_unknown_channel_type_is_terminal(
    db_session, make_channel
):
    """A channel row with an unrecognized type is a terminal failure."""
    from arm.notifications.dispatcher import process_one_row
    from arm.notifications.models import NotificationChannel

    ch = make_channel(
        type="apprise",
        config={"type": "apprise", "url": "discord://x/y"},
        subscribed_events=["job.started"],
    )
    row = _outbox_row(db_session, ch.id, _started_payload())
    # Mutate the stored type to something the dispatcher doesn't handle.
    persisted = NotificationChannel.query.get(ch.id)
    persisted.type = "carrier-pigeon"
    db_session.commit()

    process_one_row(row.id)
    db_session.refresh(row)
    assert row.status == "failed"
    assert "unknown channel type" in row.last_error.lower()


def test_dispatcher_sender_raised_is_transient(db_session, make_channel):
    """If a channel sender raises (it shouldn't, but defensively), the
    dispatcher records a transient failure so a bug doesn't permanently
    wedge dispatch."""
    from arm.notifications.dispatcher import process_one_row

    ch = make_channel(
        type="apprise",
        config={"type": "apprise", "url": "discord://x/y"},
        subscribed_events=["job.started"],
    )
    row = _outbox_row(db_session, ch.id, _started_payload())

    with patch("arm.notifications.dispatcher.send_apprise",
               side_effect=RuntimeError("kaboom")):
        process_one_row(row.id)

    db_session.refresh(row)
    # Transient -> back to pending (attempts < max), error captured.
    assert row.status == "pending"
    assert "sender raised" in row.last_error.lower()
    assert "kaboom" in row.last_error


def test_dispatcher_loop_survives_tick_exception(db_session):
    """A failure inside the tick body (e.g. dequeue raises) is logged and
    the loop keeps running rather than crashing."""
    import asyncio
    from arm.notifications import dispatcher as dispatcher_mod

    calls = {"n": 0}

    def boom(*a, **k):
        calls["n"] += 1
        raise RuntimeError("dequeue blew up")

    async def _run():
        stop = asyncio.Event()
        with patch.object(dispatcher_mod, "_TICK_INTERVAL_SECONDS", 0.01), \
                patch.object(dispatcher_mod, "_CLEANUP_INTERVAL_SECONDS", 1e9), \
                patch.object(dispatcher_mod, "dequeue_due", side_effect=boom):
            task = asyncio.create_task(
                dispatcher_mod.run_dispatcher_loop(stop_event=stop)
            )
            for _ in range(20):
                await asyncio.sleep(0.01)
                if calls["n"] >= 2:
                    break
            stop.set()
            await asyncio.wait_for(task, timeout=2.0)

    asyncio.run(_run())
    # Loop ticked more than once despite every tick raising — proof it
    # caught the exception and continued.
    assert calls["n"] >= 2


def test_dispatcher_loop_survives_cleanup_exception(db_session):
    """A failure inside the periodic cleanup is logged and the loop keeps
    running."""
    import asyncio
    from arm.notifications import dispatcher as dispatcher_mod

    calls = {"n": 0}

    def boom(*a, **k):
        calls["n"] += 1
        raise RuntimeError("cleanup blew up")

    async def _run():
        stop = asyncio.Event()
        with patch.object(dispatcher_mod, "_TICK_INTERVAL_SECONDS", 0.01), \
                patch.object(dispatcher_mod, "_CLEANUP_INTERVAL_SECONDS", 0.0), \
                patch.object(dispatcher_mod, "cleanup_completed",
                             side_effect=boom):
            task = asyncio.create_task(
                dispatcher_mod.run_dispatcher_loop(stop_event=stop)
            )
            for _ in range(20):
                await asyncio.sleep(0.01)
                if calls["n"] >= 1:
                    break
            stop.set()
            await asyncio.wait_for(task, timeout=2.0)

    asyncio.run(_run())
    assert calls["n"] >= 1


def test_process_one_row_outer_safety_net_swallows_commit_error(
    db_session, make_channel
):
    """If record_success itself raises (e.g. a DB commit error), the
    outer try/except in process_one_row swallows it so the function
    never raises — the dispatcher loop relies on this guarantee."""
    from arm.notifications import dispatcher as dispatcher_mod
    from arm.notifications.dispatcher import process_one_row

    ch = make_channel(
        type="apprise",
        config={"type": "apprise", "url": "discord://x/y"},
        subscribed_events=["job.started"],
    )
    row = _outbox_row(db_session, ch.id, _started_payload())

    with patch("arm.notifications.dispatcher.send_apprise",
               return_value=(True, None)), \
            patch.object(dispatcher_mod, "record_success",
                         side_effect=RuntimeError("commit failed")):
        # Must NOT raise.
        process_one_row(row.id)


def test_dispatcher_loop_logs_rescued_stale_rows(db_session):
    """On startup the loop reaps stale in_flight rows; when any are
    rescued it logs a count (covers the rescued>0 branch)."""
    import asyncio
    from arm.notifications import dispatcher as dispatcher_mod

    reap_mock = {}

    async def _run():
        stop = asyncio.Event()
        with patch.object(dispatcher_mod, "_TICK_INTERVAL_SECONDS", 0.01), \
                patch.object(dispatcher_mod, "_CLEANUP_INTERVAL_SECONDS", 1e9), \
                patch.object(dispatcher_mod, "reap_stale_in_flight",
                             return_value=3) as reap, \
                patch.object(dispatcher_mod, "dequeue_due", return_value=[]):
            task = asyncio.create_task(
                dispatcher_mod.run_dispatcher_loop(stop_event=stop)
            )
            await asyncio.sleep(0.05)
            stop.set()
            await asyncio.wait_for(task, timeout=2.0)
            reap_mock["count"] = reap.call_count

    asyncio.run(_run())
    assert reap_mock["count"] == 1


def _started_event():
    """A reconstructed NotificationEvent model from the started payload."""
    from arm.notifications.dispatcher import _reconstruct_event
    return _reconstruct_event(_started_payload())


def test_send_now_apprise_renders_and_calls_sender():
    """send_now for apprise renders title/body and forwards to
    send_apprise, returning the sender's (ok, error) tuple."""
    from arm.notifications.dispatcher import send_now

    with patch("arm.notifications.dispatcher.send_apprise",
               return_value=(True, None)) as send:
        ok, error = send_now(
            "apprise", {"type": "apprise", "url": "json://localhost/x"},
            _started_event())

    assert (ok, error) == (True, None)
    send.assert_called_once()
    kwargs = send.call_args.kwargs
    assert kwargs["url"] == "json://localhost/x"
    assert "ARM started" in kwargs["title"]
    assert kwargs["body"]


def test_send_now_webhook_builds_payload_and_calls_sender():
    """send_now for webhook constructs the OutboundWebhookPayload dict and
    passes shared_secret/headers through to send_webhook."""
    from arm.notifications.dispatcher import send_now

    with patch("arm.notifications.dispatcher.send_webhook",
               return_value=(True, None)) as send:
        ok, error = send_now(
            "webhook",
            {"type": "webhook", "url": "https://example.com/hook",
             "shared_secret": "s3cret", "headers": {"X-Test": "1"}},
            _started_event())

    assert (ok, error) == (True, None)
    send.assert_called_once()
    kwargs = send.call_args.kwargs
    assert kwargs["url"] == "https://example.com/hook"
    assert kwargs["shared_secret"] == "s3cret"
    assert kwargs["headers"] == {"X-Test": "1"}
    payload = kwargs["payload_dict"]
    for key in ("event", "title", "body", "channel", "sent_at"):
        assert key in payload


def test_send_now_bash_builds_env_and_calls_sender():
    """send_now for bash builds the ARM_* env from the event model and
    forwards script_path/env_vars to send_bash."""
    from arm.notifications.dispatcher import send_now

    with patch("arm.notifications.dispatcher.send_bash",
               return_value=(True, None)) as send:
        ok, error = send_now(
            "bash", {"type": "bash", "script_path": "/x"},
            _started_event())

    assert (ok, error) == (True, None)
    send.assert_called_once()
    kwargs = send.call_args.kwargs
    assert kwargs["script_path"] == "/x"
    env = kwargs["env_vars"]
    assert env["ARM_EVENT_KEY"] == "job.started"
    assert env["ARM_JOB_ID"] == "1"
    assert "ARM_TITLE" in env


def test_send_now_propagates_sender_failure():
    """send_now returns the sender's failure tuple verbatim."""
    from arm.notifications.dispatcher import send_now

    with patch("arm.notifications.dispatcher.send_apprise",
               return_value=(False, "boom")):
        ok, error = send_now(
            "apprise", {"type": "apprise", "url": "json://localhost/x"},
            _started_event())

    assert (ok, error) == (False, "boom")


def test_send_now_unknown_type_returns_error():
    """An unrecognized channel type returns (False, descriptive error)
    without raising."""
    from arm.notifications.dispatcher import send_now

    ok, error = send_now("carrier-pigeon", {}, _started_event())
    assert ok is False
    assert "unknown channel type" in error.lower()
    assert "carrier-pigeon" in error


def test_dispatcher_loop_logs_cleanup_deletions(db_session):
    """When the periodic cleanup deletes rows, the loop logs the count
    (covers the deleted>0 branch)."""
    import asyncio
    from arm.notifications import dispatcher as dispatcher_mod

    calls = {"n": 0}

    def fake_cleanup(older_than_days):
        calls["n"] += 1
        return 7  # non-zero -> exercises the deleted>0 log line

    async def _run():
        stop = asyncio.Event()
        with patch.object(dispatcher_mod, "_TICK_INTERVAL_SECONDS", 0.01), \
                patch.object(dispatcher_mod, "_CLEANUP_INTERVAL_SECONDS", 0.0), \
                patch.object(dispatcher_mod, "dequeue_due", return_value=[]), \
                patch.object(dispatcher_mod, "cleanup_completed",
                             side_effect=fake_cleanup):
            task = asyncio.create_task(
                dispatcher_mod.run_dispatcher_loop(stop_event=stop)
            )
            for _ in range(20):
                await asyncio.sleep(0.01)
                if calls["n"] >= 1:
                    break
            stop.set()
            await asyncio.wait_for(task, timeout=2.0)

    asyncio.run(_run())
    assert calls["n"] >= 1
