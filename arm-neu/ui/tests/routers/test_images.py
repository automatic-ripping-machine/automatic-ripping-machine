"""Tests for backend.routers.images — image proxy endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch, MagicMock

import httpx


async def test_proxy_cache_hit(app_client):
    """Cached image is served without fetching."""
    with patch("backend.routers.images.image_cache.retrieve", return_value=(b"imgdata", "image/jpeg")):
        resp = await app_client.get("/api/images/proxy?url=https://m.media-amazon.com/img.jpg")
    assert resp.status_code == 200
    assert resp.content == b"imgdata"
    assert "max-age=604800" in resp.headers["cache-control"]


async def test_proxy_cache_miss_fetches(app_client):
    """Cache miss fetches from origin and stores."""
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.content = b"fetched-img"
    mock_resp.headers = {"content-type": "image/png"}
    mock_resp.raise_for_status = MagicMock()

    with (
        patch("backend.routers.images.image_cache.retrieve", return_value=None),
        patch("backend.routers.images.image_cache.store"),
        patch("backend.routers.images.httpx.AsyncClient") as MockClient,
    ):
        ctx = MagicMock()
        ctx.get = AsyncMock(return_value=mock_resp)
        MockClient.return_value.__aenter__ = AsyncMock(return_value=ctx)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
        resp = await app_client.get("/api/images/proxy?url=https://image.tmdb.org/poster.jpg")
    assert resp.status_code == 200


async def test_proxy_rejects_bad_host(app_client):
    """Non-allowlisted host returns cacheable 404."""
    resp = await app_client.get("/api/images/proxy?url=https://evil.com/img.jpg")
    assert resp.status_code == 404


async def test_proxy_rejects_non_http(app_client):
    """Non-HTTP scheme returns cacheable 404."""
    resp = await app_client.get("/api/images/proxy?url=ftp://example.com/img.jpg")
    assert resp.status_code == 404
