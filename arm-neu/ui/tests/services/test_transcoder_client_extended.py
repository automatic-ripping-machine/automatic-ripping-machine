"""Tests for transcoder_client.send_webhook."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from backend.services import transcoder_client


def _mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    return resp


# --- send_webhook ---


async def test_send_webhook_success():
    """send_webhook returns success when transcoder accepts the payload."""
    mock_resp = _mock_response({"queued": True})

    with patch("asyncio.to_thread", new_callable=AsyncMock, return_value="my-secret"), \
         patch("backend.services.transcoder_client.httpx.AsyncClient") as MockClient:
        ctx = AsyncMock()
        ctx.post.return_value = mock_resp
        MockClient.return_value.__aenter__ = AsyncMock(return_value=ctx)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await transcoder_client.send_webhook({"title": "Test"})

    assert result["success"] is True


async def test_send_webhook_auth_rejected():
    """send_webhook returns error when secret is rejected (401/403)."""
    mock_resp = _mock_response({}, status_code=403)

    with patch("asyncio.to_thread", new_callable=AsyncMock, return_value="bad-secret"), \
         patch("backend.services.transcoder_client.httpx.AsyncClient") as MockClient:
        ctx = AsyncMock()
        ctx.post.return_value = mock_resp
        MockClient.return_value.__aenter__ = AsyncMock(return_value=ctx)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await transcoder_client.send_webhook({"title": "Test"})

    assert result["success"] is False
    assert "secret rejected" in result["error"].lower()


async def test_send_webhook_connect_error():
    """send_webhook returns error when transcoder is offline."""
    with patch("asyncio.to_thread", new_callable=AsyncMock, return_value=""), \
         patch("backend.services.transcoder_client.httpx.AsyncClient") as MockClient:
        ctx = AsyncMock()
        ctx.post.side_effect = httpx.ConnectError("refused")
        MockClient.return_value.__aenter__ = AsyncMock(return_value=ctx)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await transcoder_client.send_webhook({"title": "Test"})

    assert result["success"] is False
    assert "offline" in result["error"].lower()


async def test_send_webhook_http_error():
    """send_webhook returns error on unexpected HTTP failure."""
    mock_resp = _mock_response({}, status_code=500)

    with patch("asyncio.to_thread", new_callable=AsyncMock, return_value="secret"), \
         patch("backend.services.transcoder_client.httpx.AsyncClient") as MockClient:
        ctx = AsyncMock()
        ctx.post.return_value = mock_resp
        MockClient.return_value.__aenter__ = AsyncMock(return_value=ctx)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await transcoder_client.send_webhook({"title": "Test"})

    assert result["success"] is False
    assert "failed" in result["error"].lower()


async def test_send_webhook_no_secret():
    """send_webhook works without a webhook secret (empty string)."""
    mock_resp = _mock_response({"queued": True})

    with patch("asyncio.to_thread", new_callable=AsyncMock, return_value=""), \
         patch("backend.services.transcoder_client.httpx.AsyncClient") as MockClient:
        ctx = AsyncMock()
        ctx.post.return_value = mock_resp
        MockClient.return_value.__aenter__ = AsyncMock(return_value=ctx)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await transcoder_client.send_webhook({"title": "Test"})

    assert result["success"] is True
    # Verify no X-Webhook-Secret header was sent
    call_kwargs = ctx.post.call_args
    headers = call_kwargs[1].get("headers", {})
    assert "X-Webhook-Secret" not in headers
