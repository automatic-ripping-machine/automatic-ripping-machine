"""Tests for backend.routers.notifications - list and dismiss notifications."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch


# --- GET /api/notifications ---


async def test_list_notifications(app_client):
    """GET /api/notifications returns validated notification list."""
    payload = {"notifications": [
        {
            "id": 1, "seen": False, "cleared": False,
            "title": "Rip Complete", "message": "Movie ripped",
            "trigger_time": None, "dismiss_time": None,
        },
    ]}
    with patch(
        "backend.routers.notifications.arm_client.get_notifications",
        new_callable=AsyncMock,
        return_value=payload,
    ):
        resp = await app_client.get("/api/notifications")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Rip Complete"


async def test_list_notifications_empty(app_client):
    """GET /api/notifications returns empty list when no notifications."""
    with patch(
        "backend.routers.notifications.arm_client.get_notifications",
        new_callable=AsyncMock,
        return_value={"notifications": []},
    ):
        resp = await app_client.get("/api/notifications")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_notifications_arm_unreachable(app_client):
    """GET /api/notifications returns 503 when ARM is unreachable."""
    with patch(
        "backend.routers.notifications.arm_client.get_notifications",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await app_client.get("/api/notifications")
    assert resp.status_code == 503
    assert "unreachable" in resp.json()["detail"].lower()


# --- PATCH /api/notifications/{notify_id} ---


async def test_dismiss_notification_success(app_client):
    """PATCH /api/notifications/{id} returns result from ARM."""
    with patch(
        "backend.routers.notifications.arm_client.dismiss_notification",
        new_callable=AsyncMock,
        return_value={"success": True},
    ):
        resp = await app_client.patch("/api/notifications/1")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


async def test_dismiss_notification_arm_unreachable(app_client):
    """PATCH /api/notifications/{id} returns 503 when ARM is down."""
    with patch(
        "backend.routers.notifications.arm_client.dismiss_notification",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await app_client.patch("/api/notifications/1")
    assert resp.status_code == 503
    assert "unreachable" in resp.json()["detail"].lower()


async def test_dismiss_notification_failure(app_client):
    """PATCH /api/notifications/{id} returns 502 when ARM reports failure."""
    with patch(
        "backend.routers.notifications.arm_client.dismiss_notification",
        new_callable=AsyncMock,
        return_value={"success": False, "message": "Notification not found"},
    ):
        resp = await app_client.patch("/api/notifications/1")
    assert resp.status_code == 502
    assert "Notification not found" in resp.json()["detail"]


async def test_dismiss_notification_failure_no_message(app_client):
    """PATCH returns 502 with default detail when ARM failure has no message."""
    with patch(
        "backend.routers.notifications.arm_client.dismiss_notification",
        new_callable=AsyncMock,
        return_value={"success": False},
    ):
        resp = await app_client.patch("/api/notifications/1")
    assert resp.status_code == 502
    assert "Failed to dismiss" in resp.json()["detail"]


# --- Channels passthrough ---

async def test_list_channels_route(app_client):
    with patch(
        "backend.routers.notifications.arm_client.list_channels",
        new_callable=AsyncMock, return_value=[{"id": 1, "type": "apprise"}],
    ):
        resp = await app_client.get("/api/notifications/channels")
    assert resp.status_code == 200
    assert resp.json()[0]["id"] == 1


async def test_list_channels_route_unreachable(app_client):
    with patch(
        "backend.routers.notifications.arm_client.list_channels",
        new_callable=AsyncMock, return_value=None,
    ):
        resp = await app_client.get("/api/notifications/channels")
    assert resp.status_code == 503


async def test_get_channel_route(app_client):
    with patch(
        "backend.routers.notifications.arm_client.get_channel",
        new_callable=AsyncMock, return_value={"id": 3},
    ):
        resp = await app_client.get("/api/notifications/channels/3")
    assert resp.status_code == 200
    assert resp.json()["id"] == 3


async def test_create_channel_route(app_client):
    body = {"type": "apprise", "name": "x",
            "config": {"type": "apprise", "url": "discord://a/b"},
            "subscribed_events": []}
    with patch(
        "backend.routers.notifications.arm_client.create_channel",
        new_callable=AsyncMock, return_value={"id": 9, **body},
    ):
        resp = await app_client.post("/api/notifications/channels", json=body)
    assert resp.status_code == 200
    assert resp.json()["id"] == 9


async def test_update_channel_route(app_client):
    with patch(
        "backend.routers.notifications.arm_client.update_channel",
        new_callable=AsyncMock, return_value={"id": 9, "name": "renamed"},
    ):
        resp = await app_client.patch("/api/notifications/channels/9",
                                      json={"name": "renamed"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "renamed"


async def test_delete_channel_route(app_client):
    with patch(
        "backend.routers.notifications.arm_client.delete_channel",
        new_callable=AsyncMock, return_value={},
    ):
        resp = await app_client.delete("/api/notifications/channels/9")
    assert resp.status_code == 200


async def test_test_send_route(app_client):
    with patch(
        "backend.routers.notifications.arm_client.test_send_channel",
        new_callable=AsyncMock, return_value={"dispatch_id": 5, "sent_at": "now"},
    ):
        resp = await app_client.post("/api/notifications/channels/2/test",
                                     json={"event_key": "job.started"})
    assert resp.status_code == 200
    assert resp.json()["dispatch_id"] == 5


async def test_get_dispatch_route(app_client):
    with patch(
        "backend.routers.notifications.arm_client.get_dispatch",
        new_callable=AsyncMock, return_value={"status": "success"},
    ):
        resp = await app_client.get("/api/notifications/dispatch/5")
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"


async def test_list_dispatches_route(app_client):
    with patch(
        "backend.routers.notifications.arm_client.list_dispatches",
        new_callable=AsyncMock, return_value=[{"id": 1, "event_key": "job.started"}],
    ):
        resp = await app_client.get("/api/notifications/dispatches?channel_id=2")
    assert resp.status_code == 200
    assert resp.json()[0]["event_key"] == "job.started"


async def test_get_services_route(app_client):
    with patch(
        "backend.routers.notifications.arm_client.get_services",
        new_callable=AsyncMock, return_value={"featured": ["discord"], "services": []},
    ):
        resp = await app_client.get("/api/notifications/services")
    assert resp.status_code == 200
    assert "discord" in resp.json()["featured"]


async def test_compose_url_route(app_client):
    body = {"required": {"webhook_id": "1"}, "advanced": {}}
    with patch(
        "backend.routers.notifications.arm_client.compose_channel_url",
        new_callable=AsyncMock, return_value={"url": "discord://1"},
    ):
        resp = await app_client.post("/api/notifications/services/discord/compose-url", json=body)
    assert resp.status_code == 200
    assert resp.json()["url"] == "discord://1"


async def test_test_config_route(app_client):
    body = {"type": "apprise", "config": {"type": "apprise", "url": "discord://a/b"}}
    with patch(
        "backend.routers.notifications.arm_client.test_channel_config",
        new_callable=AsyncMock, return_value={"ok": True, "error": None},
    ):
        resp = await app_client.post("/api/notifications/test", json=body)
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "error": None}


async def test_test_config_route_unreachable(app_client):
    with patch(
        "backend.routers.notifications.arm_client.test_channel_config",
        new_callable=AsyncMock, return_value=None,
    ):
        resp = await app_client.post("/api/notifications/test", json={"type": "apprise", "config": {}})
    assert resp.status_code == 503
