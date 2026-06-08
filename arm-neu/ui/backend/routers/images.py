"""Image proxy with disk-backed caching."""

from __future__ import annotations

import time
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Query
from fastapi.responses import Response

from backend.services import image_cache

_NEGATIVE_CACHE: dict[str, float] = {}
_NEGATIVE_TTL_SECONDS = 3600

router = APIRouter(prefix="/api", tags=["images"])

_SAFE_CONTENT_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml",
}

_ALLOWED_IMAGE_HOSTS = {
    "m.media-amazon.com",
    "image.tmdb.org",
    "images-na.ssl-images-amazon.com",
    "coverartarchive.org",
    "ia.media-imdb.com",
}


def _not_found(detail: str) -> Response:
    """Return a cacheable 404 so the browser stops re-requesting missing images."""
    return Response(
        content=f'{{"detail":"{detail}"}}',
        status_code=404,
        media_type="application/json",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/images/proxy")
async def proxy_image(url: str = Query(..., description="Image URL to proxy")) -> Response:
    """Proxy and cache external images to avoid browser ORB/CORS issues."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return _not_found("Only HTTP(S) URLs are allowed")
    if parsed.hostname not in _ALLOWED_IMAGE_HOSTS:
        return _not_found("Image host not allowed")

    safe_url = parsed.geturl()

    cached = image_cache.retrieve(safe_url)
    if cached is not None:
        content, content_type = cached
        safe_type = content_type if content_type in _SAFE_CONTENT_TYPES else "application/octet-stream"
        return Response(content=content, media_type=safe_type,
                        headers={"Cache-Control": "public, max-age=604800"})

    now = time.time()
    neg_expiry = _NEGATIVE_CACHE.get(safe_url)
    if neg_expiry is not None and neg_expiry > now:
        return _not_found("Image unavailable")

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(safe_url)  # NOSONAR — host validated above
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "image/jpeg")
            safe_type = content_type if content_type in _SAFE_CONTENT_TYPES else "image/jpeg"
            image_cache.store(safe_url, resp.content, safe_type)
            _NEGATIVE_CACHE.pop(safe_url, None)
            return Response(content=resp.content, media_type=safe_type,
                            headers={"Cache-Control": "public, max-age=604800"})
    except httpx.HTTPError:
        _NEGATIVE_CACHE[safe_url] = now + _NEGATIVE_TTL_SECONDS
        return _not_found("Failed to fetch image")
