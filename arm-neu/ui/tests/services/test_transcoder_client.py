"""Tests for backend.services.transcoder_client — test_connection and test_webhook."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from backend.services import transcoder_client


def _mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    return resp


# --- test_connection ---


async def test_test_connection_reachable():
    """test_connection returns all-green when health and config both succeed."""
    health_data = {
        "status": "healthy",
        "worker_running": True,
        "queue_size": 2,
        "gpu_support": {"nvenc": True},
        "require_api_auth": True,
    }
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = [
        _mock_response(health_data),       # /health
        _mock_response({"config": {}}),    # /config
    ]
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.test_connection()

    assert result["reachable"] is True
    assert result["auth_ok"] is True
    assert result["auth_required"] is True
    assert result["worker_running"] is True
    assert result["queue_size"] == 2
    assert result["gpu_support"] == {"nvenc": True}
    assert result["error"] is None


async def test_test_connection_unreachable():
    """test_connection returns reachable=False on ConnectError."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.ConnectError("refused")
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.test_connection()

    assert result["reachable"] is False
    assert result["error"] is not None


async def test_test_connection_auth_required():
    """test_connection detects failed auth when /config returns 401."""
    health_data = {
        "status": "healthy",
        "worker_running": True,
        "queue_size": 0,
        "gpu_support": {},
        "require_api_auth": True,
    }
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = [
        _mock_response(health_data),           # /health
        _mock_response({}, status_code=401),   # /config — unauthorized
    ]
    with patch.object(transcoder_client, "get_client", return_value=mock_client):
        result = await transcoder_client.test_connection()

    assert result["reachable"] is True
    assert result["auth_ok"] is False
    assert result["auth_required"] is True


# --- test_webhook ---


async def test_test_webhook_success():
    """test_webhook returns secret_ok=True on 200 response."""
    mock_resp = _mock_response({"status": "ignored"})

    with patch("backend.services.transcoder_client.httpx.AsyncClient") as MockClient:
        ctx = AsyncMock()
        ctx.post.return_value = mock_resp
        MockClient.return_value.__aenter__ = AsyncMock(return_value=ctx)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await transcoder_client.test_webhook("my-secret")

    assert result["reachable"] is True
    assert result["secret_ok"] is True


async def test_test_webhook_bad_secret():
    """test_webhook returns secret_ok=False on 403 response."""
    mock_resp = _mock_response({}, status_code=403)

    with patch("backend.services.transcoder_client.httpx.AsyncClient") as MockClient:
        ctx = AsyncMock()
        ctx.post.return_value = mock_resp
        MockClient.return_value.__aenter__ = AsyncMock(return_value=ctx)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await transcoder_client.test_webhook("wrong-secret")

    assert result["reachable"] is True
    assert result["secret_ok"] is False
    assert result["secret_required"] is True


async def test_test_webhook_unreachable():
    """test_webhook returns reachable=False on ConnectError."""
    with patch("backend.services.transcoder_client.httpx.AsyncClient") as MockClient:
        ctx = AsyncMock()
        ctx.post.side_effect = httpx.ConnectError("refused")
        MockClient.return_value.__aenter__ = AsyncMock(return_value=ctx)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await transcoder_client.test_webhook("secret")

    assert result["reachable"] is False
    assert result["error"] is not None


async def test_test_webhook_uses_caller_secret_in_header():
    """Caller-supplied secret is sent in X-Webhook-Secret. No env fallback."""
    mock_resp = _mock_response({"status": "ignored"})

    with patch("backend.services.transcoder_client.httpx.AsyncClient") as MockClient:
        ctx = AsyncMock()
        ctx.post.return_value = mock_resp
        MockClient.return_value.__aenter__ = AsyncMock(return_value=ctx)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await transcoder_client.test_webhook("candidate-secret")

    _, kwargs = ctx.post.call_args
    assert kwargs["headers"]["X-Webhook-Secret"] == "candidate-secret"
    assert result["secret_ok"] is True
