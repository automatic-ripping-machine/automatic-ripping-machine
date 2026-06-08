"""Verification: multiple notification channels of the SAME type.

Confirms the system supports several apprise, several webhook, and
several bash channels at once, and that each one fires independently
when an event is published. Exercises the real publish_event -> outbox
-> dispatcher path with senders mocked (no real Discord/HTTP/subprocess).
"""
import asyncio
import datetime
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(db_session):
    """FastAPI test client wired against the in-memory DB."""
    from arm.app import app
    return TestClient(app)


def _started_event():
    from arm_contracts import JobStartedEvent
    from arm_contracts.enums import Disctype
    return JobStartedEvent(
        event_id=uuid4(),
        occurred_at=datetime.datetime.now(datetime.timezone.utc),
        job_id=7,
        job_title="Multi Channel Movie",
        job_disc_type=Disctype.dvd,
        drive_mount="/dev/sr0",
    )


# --- API level: can we ADD multiple of the same type? ---

def test_api_allows_multiple_same_type_channels(client):
    """POST two apprise, two webhook, two bash channels and confirm all
    six persist as distinct rows with no per-type limit."""
    bodies = [
        {"type": "apprise", "name": "Discord A",
         "config": {"type": "apprise", "url": "discord://1/a"},
         "subscribed_events": ["job.started"]},
        {"type": "apprise", "name": "Discord B",
         "config": {"type": "apprise", "url": "discord://2/b"},
         "subscribed_events": ["job.started"]},
        {"type": "webhook", "name": "Hook A",
         "config": {"type": "webhook", "url": "https://example.com/a"},
         "subscribed_events": ["job.started"]},
        {"type": "webhook", "name": "Hook B",
         "config": {"type": "webhook", "url": "https://example.com/b"},
         "subscribed_events": ["job.started"]},
        {"type": "bash", "name": "Script A",
         "config": {"type": "bash", "script_path": "/opt/arm/scripts/a.sh"},
         "subscribed_events": ["job.started"]},
        {"type": "bash", "name": "Script B",
         "config": {"type": "bash", "script_path": "/opt/arm/scripts/b.sh"},
         "subscribed_events": ["job.started"]},
    ]
    ids = []
    for b in bodies:
        resp = client.post("/api/v1/notifications/channels", json=b)
        assert resp.status_code == 201, resp.text
        ids.append(resp.json()["id"])
    assert len(set(ids)) == 6  # six distinct rows, none overwrote another

    listing = client.get("/api/v1/notifications/channels")
    assert listing.status_code == 200, listing.text
    types = sorted(r["type"] for r in listing.json())
    assert types == [
        "apprise", "apprise", "bash", "bash", "webhook", "webhook",
    ]


# --- Dispatch level: does each one FIRE independently? ---

def test_each_same_type_channel_fires_independently(db_session, make_channel):
    """Two channels of each type, all subscribed. One published event
    must produce one outbox row per channel, and the dispatcher must
    invoke each type's sender once per channel with that channel's own
    config — proving same-type channels are not collapsed or shadowed."""
    from arm.notifications import publish_event
    from arm.notifications import dispatcher as dispatcher_module
    from arm.notifications.models import NotificationOutbox

    channels = [
        make_channel(type="apprise", name="ap1",
                     config={"type": "apprise", "url": "discord://1/a"},
                     subscribed_events=["job.started"]),
        make_channel(type="apprise", name="ap2",
                     config={"type": "apprise", "url": "discord://2/b"},
                     subscribed_events=["job.started"]),
        make_channel(type="webhook", name="wh1",
                     config={"type": "webhook", "url": "https://e/1"},
                     subscribed_events=["job.started"]),
        make_channel(type="webhook", name="wh2",
                     config={"type": "webhook", "url": "https://e/2"},
                     subscribed_events=["job.started"]),
        make_channel(type="bash", name="b1",
                     config={"type": "bash", "script_path": "/x/1.sh"},
                     subscribed_events=["job.started"]),
        make_channel(type="bash", name="b2",
                     config={"type": "bash", "script_path": "/x/2.sh"},
                     subscribed_events=["job.started"]),
    ]

    publish_event(_started_event())

    # One outbox row per channel — same-type channels each get their own.
    assert NotificationOutbox.query.count() == 6
    for ch in channels:
        assert NotificationOutbox.query.filter_by(channel_id=ch.id).count() == 1

    apprise_urls: list[str] = []
    webhook_urls: list[str] = []
    bash_paths: list[str] = []

    def rec_apprise(*, url, title, body):
        apprise_urls.append(url)
        return (True, None)

    def rec_webhook(**kwargs):
        webhook_urls.append(kwargs.get("url"))
        return (True, None)

    def rec_bash(*, script_path, **kwargs):
        bash_paths.append(script_path)
        return (True, None)

    async def _run():
        stop = asyncio.Event()
        with patch("arm.notifications.dispatcher.send_apprise",
                   side_effect=rec_apprise), \
                patch("arm.notifications.dispatcher.send_webhook",
                      side_effect=rec_webhook), \
                patch("arm.notifications.dispatcher.send_bash",
                      side_effect=rec_bash), \
                patch.object(dispatcher_module,
                             "_TICK_INTERVAL_SECONDS", 0.05):
            task = asyncio.create_task(
                dispatcher_module.run_dispatcher_loop(stop_event=stop)
            )
            for _ in range(60):
                await asyncio.sleep(0.05)
                if NotificationOutbox.query.filter_by(
                        status="success").count() == 6:
                    break
            stop.set()
            await asyncio.wait_for(task, timeout=5.0)

    asyncio.run(_run())

    # Every channel sent successfully and independently.
    assert NotificationOutbox.query.filter_by(status="success").count() == 6
    assert sorted(apprise_urls) == ["discord://1/a", "discord://2/b"]
    assert sorted(webhook_urls) == ["https://e/1", "https://e/2"]
    assert sorted(bash_paths) == ["/x/1.sh", "/x/2.sh"]
