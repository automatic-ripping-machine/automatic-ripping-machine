"""Shared helpers for HTTP-level tests against the transcoder app."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient


def versioned_test_client(app, base_url: str = "https://test") -> AsyncClient:
    """Build an httpx AsyncClient with X-Api-Version: 2 on every request.

    Tests that target webhook behaviour (not the version-handshake) should
    default the header so they aren't rejected by the release-N+2 guard.
    Handshake-specific tests live in test_version_handshake.py.
    """
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url=base_url,
        headers={"X-Api-Version": "2"},
    )


@asynccontextmanager
async def patched_app_client(mock_worker, test_get_db):
    """Start the main FastAPI app under the standard test patches.

    Patches `get_db` on the database module and every router that takes its
    own reference, stubs `main.init_db`, installs `mock_worker` on app
    state, and yields `(AsyncClient, main_module)`. The client has
    X-Api-Version: 2 set by default so webhook tests bypass the handshake.

    Kept here so every integration-style test fixture shares the same
    patch surface; extending the list in one place updates all callers.
    """
    import database as db_module
    with (
        patch.object(db_module, "get_db", test_get_db),
        patch("routers.jobs.get_db", test_get_db),
        patch("routers.stats.get_db", test_get_db),
        patch("routers.config.get_db", test_get_db),
        patch("main.init_db", AsyncMock()),
    ):
        import main as main_module
        main_module.app.state.worker = mock_worker
        try:
            async with versioned_test_client(main_module.app) as ac:
                yield ac, main_module
        finally:
            main_module.app.state.worker = None
