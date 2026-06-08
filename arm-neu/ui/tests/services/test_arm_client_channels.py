"""Tests for arm_client channel/catalog/dispatch proxy functions."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from backend.services import arm_client


async def test_list_channels_proxies_to_neu():
    with patch.object(arm_client, "_request", new_callable=AsyncMock,
                      return_value=[{"id": 1}]) as req:
        out = await arm_client.list_channels()
    req.assert_awaited_once_with("GET", "/api/v1/notifications/channels")
    assert out == [{"id": 1}]


async def test_get_channel_proxies():
    with patch.object(arm_client, "_request", new_callable=AsyncMock,
                      return_value={"id": 3}) as req:
        out = await arm_client.get_channel(3)
    req.assert_awaited_once_with("GET", "/api/v1/notifications/channels/3")
    assert out == {"id": 3}


async def test_create_channel_proxies_body():
    body = {"type": "apprise", "name": "x", "config": {"type": "apprise", "url": "discord://a/b"}, "subscribed_events": []}
    with patch.object(arm_client, "_request", new_callable=AsyncMock,
                      return_value={"id": 9}) as req:
        out = await arm_client.create_channel(body)
    req.assert_awaited_once_with("POST", "/api/v1/notifications/channels", json=body)
    assert out == {"id": 9}


async def test_update_channel_proxies_body():
    body = {"name": "renamed"}
    with patch.object(arm_client, "_request", new_callable=AsyncMock,
                      return_value={"id": 9, "name": "renamed"}) as req:
        out = await arm_client.update_channel(9, body)
    req.assert_awaited_once_with("PATCH", "/api/v1/notifications/channels/9", json=body)
    assert out["name"] == "renamed"


async def test_delete_channel_proxies():
    with patch.object(arm_client, "_request", new_callable=AsyncMock,
                      return_value={}) as req:
        await arm_client.delete_channel(9)
    req.assert_awaited_once_with("DELETE", "/api/v1/notifications/channels/9")


async def test_test_send_channel_proxies():
    with patch.object(arm_client, "_request", new_callable=AsyncMock,
                      return_value={"dispatch_id": 5}) as req:
        out = await arm_client.test_send_channel(2, {"event_key": "job.started"})
    req.assert_awaited_once_with("POST", "/api/v1/notifications/channels/2/test", json={"event_key": "job.started"})
    assert out["dispatch_id"] == 5


async def test_get_dispatch_proxies():
    with patch.object(arm_client, "_request", new_callable=AsyncMock,
                      return_value={"status": "success"}) as req:
        out = await arm_client.get_dispatch(5)
    req.assert_awaited_once_with("GET", "/api/v1/notifications/dispatch/5")
    assert out["status"] == "success"


async def test_list_dispatches_proxies_query():
    with patch.object(arm_client, "_request", new_callable=AsyncMock,
                      return_value=[]) as req:
        await arm_client.list_dispatches(channel_id=2, status="success", limit=20)
    req.assert_awaited_once_with(
        "GET", "/api/v1/notifications/dispatches",
        params={"channel_id": 2, "status": "success", "limit": 20},
    )


async def test_get_services_proxies():
    with patch.object(arm_client, "_request", new_callable=AsyncMock,
                      return_value={"featured": [], "services": []}) as req:
        out = await arm_client.get_services()
    req.assert_awaited_once_with("GET", "/api/v1/notifications/services")
    assert "services" in out


async def test_compose_url_proxies_body():
    body = {"required": {"webhook_id": "1"}, "advanced": {}}
    with patch.object(arm_client, "_request", new_callable=AsyncMock,
                      return_value={"url": "discord://1"}) as req:
        out = await arm_client.compose_channel_url("discord", body)
    req.assert_awaited_once_with("POST", "/api/v1/notifications/services/discord/compose-url", json=body)
    assert out["url"] == "discord://1"


async def test_compose_url_encodes_service_id():
    body = {"required": {}, "advanced": {}}
    with patch.object(arm_client, "_request", new_callable=AsyncMock,
                      return_value={"url": "x"}) as req:
        await arm_client.compose_channel_url("weird/id", body)
    req.assert_awaited_once_with(
        "POST", "/api/v1/notifications/services/weird%2Fid/compose-url", json=body)


async def test_test_channel_config_proxies_body():
    body = {"type": "apprise", "config": {"type": "apprise", "url": "discord://a/b"}, "event_key": "job.started"}
    with patch.object(arm_client, "_request", new_callable=AsyncMock,
                      return_value={"ok": True, "error": None}) as req:
        out = await arm_client.test_channel_config(body)
    req.assert_awaited_once_with("POST", "/api/v1/notifications/test", json=body)
    assert out == {"ok": True, "error": None}
