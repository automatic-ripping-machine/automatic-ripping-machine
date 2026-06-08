"""Custom httpx transport that serves demo data and falls through to the
real transport (production) for unmapped routes or handler errors.

A custom AsyncBaseTransport is used rather than httpx.MockTransport because
MockTransport's handler is synchronous and cannot await the real async
transport for the production fallthrough.
"""
from __future__ import annotations

import logging

import httpx

from backend.demo import routes_arm, routes_transcoder
from backend.demo.data import build_demo_store
from backend.demo.store import DemoStore

log = logging.getLogger(__name__)

# Shared singleton so ARM and transcoder views stay consistent within a process.
_store: DemoStore | None = None


def get_store() -> DemoStore:
    global _store
    if _store is None:
        _store = build_demo_store()
    return _store


class DemoTransport(httpx.AsyncBaseTransport):
    def __init__(self, service: str, real: httpx.AsyncBaseTransport):
        if service == "arm":
            self._routes = routes_arm.ROUTES
        elif service == "transcoder":
            self._routes = routes_transcoder.ROUTES
        else:
            raise ValueError(f"unknown demo service: {service!r}")
        self._real = real

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        try:
            store = get_store()
            for method, pattern, fn in self._routes:
                if request.method != method:
                    continue
                m = pattern.match(request.url.path)
                if m:
                    resp = fn(request, store, **m.groupdict())
                    if resp is not None:
                        return resp
        except Exception:  # never serve demo on error — fall through to real
            log.exception("demo handler error for %s %s; forwarding to real",
                          request.method, request.url.path)
        else:
            # Only a genuine no-match reaches here (a matched route returns
            # above; an error is logged in `except`). Avoid the misleading
            # "unmapped" message on the error path.
            log.debug("demo: unmapped %s %s -> real transport",
                      request.method, request.url.path)
        return await self._real.handle_async_request(request)

    async def aclose(self) -> None:
        await self._real.aclose()


def make_demo_client(service: str, **client_kwargs) -> httpx.AsyncClient:
    """Build an AsyncClient whose transport serves demo data with a real
    transport fallback. ``client_kwargs`` are forwarded to AsyncClient
    (base_url, timeout, headers, limits)."""
    real = httpx.AsyncHTTPTransport()
    return httpx.AsyncClient(transport=DemoTransport(service, real),
                             **client_kwargs)
