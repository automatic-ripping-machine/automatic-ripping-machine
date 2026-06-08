"""Async compatibility helper for running coroutines from sync code."""

from __future__ import annotations

import asyncio
from concurrent.futures import Future
from threading import Thread


def run_async(coro):
    """Run an async coroutine from sync code, regardless of event loop state.

    When called from a context with no running event loop (e.g. the ripper
    process), uses ``asyncio.run()``.  When called from inside an existing
    loop (e.g. a FastAPI endpoint), runs the coroutine in a background
    thread to avoid the "cannot be called from a running event loop" error.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No running loop — safe to use asyncio.run()
        return asyncio.run(coro)

    # Already inside an event loop — run in a new thread with its own loop
    result_future: Future = Future()

    def _thread_target():
        try:
            result_future.set_result(asyncio.run(coro))
        except Exception as e:
            result_future.set_exception(e)

    t = Thread(target=_thread_target, daemon=True)
    t.start()
    return result_future.result(timeout=60)
