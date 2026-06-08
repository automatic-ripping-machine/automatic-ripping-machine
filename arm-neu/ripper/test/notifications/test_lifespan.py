"""Confirm the dispatcher task is started by the FastAPI lifespan."""
import asyncio


def test_lifespan_starts_and_stops_dispatcher(monkeypatch):
    """Mock the dispatcher coroutine; assert it was scheduled and
    awaited by the lifespan context manager.

    Written as a sync test driving its own event loop via asyncio.run
    so it doesn't depend on pytest-asyncio being installed in CI.
    """
    started = asyncio.Event()
    stopped = asyncio.Event()

    async def fake_dispatcher(stop_event):
        started.set()
        await stop_event.wait()
        stopped.set()

    monkeypatch.setattr(
        "arm.notifications.dispatcher.run_dispatcher_loop",
        fake_dispatcher,
    )

    async def _run():
        from arm.app import app
        async with app.router.lifespan_context(app):
            await asyncio.wait_for(started.wait(), timeout=2.0)
        await asyncio.wait_for(stopped.wait(), timeout=2.0)

    asyncio.run(_run())
    assert started.is_set()
    assert stopped.is_set()
