"""Caches for hardware info and slow ARM endpoints.

Hardware info (CPU model, RAM) is fetched once at startup.
Ripping-enabled status (MakeMKV key validity) is cached with a TTL
because the ARM endpoint can take 9+ seconds.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from backend.services import arm_client, transcoder_client

logger = logging.getLogger(__name__)

_arm_info: dict[str, Any] | None = None
_transcoder_info: dict[str, Any] | None = None

# Ripping-enabled cache
_ripping_data: dict[str, Any] | None = None
_ripping_fetched_at: float = 0.0
_RIPPING_TTL: float = 60.0
_ripping_lock: asyncio.Lock | None = None
_background_tasks: set[asyncio.Task[None]] = set()


def _get_lock() -> asyncio.Lock:
    global _ripping_lock
    if _ripping_lock is None:
        _ripping_lock = asyncio.Lock()
    return _ripping_lock


async def refresh() -> None:
    """Fetch system info from ARM and transcoder, cache in memory."""
    global _arm_info, _transcoder_info
    _arm_info = await arm_client.get_system_info()
    _transcoder_info = await transcoder_client.get_system_info()
    logger.info(
        "System cache refreshed: arm=%s, transcoder=%s",
        "ok" if _arm_info else "unavailable",
        "ok" if _transcoder_info else "unavailable",
    )


def get_arm_info() -> dict[str, Any] | None:
    return _arm_info


def get_transcoder_info() -> dict[str, Any] | None:
    return _transcoder_info


async def get_ripping_data() -> dict[str, Any] | None:
    """Return cached ripping-enabled data, refreshing at most every 60s.

    The ARM /system/ripping-enabled endpoint can take 9+ seconds.
    This always returns immediately with cached (possibly stale) data
    and kicks off a background refresh when the TTL expires.
    """
    global _ripping_data, _ripping_fetched_at
    now = time.monotonic()
    if now - _ripping_fetched_at >= _RIPPING_TTL:
        lock = _get_lock()
        if not lock.locked():
            task = asyncio.create_task(_refresh_ripping(lock))
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)
    return _ripping_data


async def _refresh_ripping(lock: asyncio.Lock) -> None:
    """Background task to refresh ripping data without blocking callers."""
    global _ripping_data, _ripping_fetched_at
    async with lock:
        if time.monotonic() - _ripping_fetched_at < _RIPPING_TTL:
            return
        result = await arm_client.get_ripping_enabled()
        if result is not None:
            _ripping_data = result
            _ripping_fetched_at = time.monotonic()
            logger.debug("Ripping data cache refreshed")
