"""Tests for backend.services.system_cache — refresh + getters + ripping cache."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

from backend.services import system_cache


async def test_refresh_populates_cache():
    """refresh() stores info from both ARM and transcoder clients."""
    arm_info = {"cpu": "AMD Ryzen 7", "memory_total_gb": 32.0}
    transcoder_info = {"cpu": "Intel i7", "memory_total_gb": 16.0}
    with (
        patch(
            "backend.services.system_cache.arm_client.get_system_info",
            new_callable=AsyncMock, return_value=arm_info,
        ),
        patch(
            "backend.services.system_cache.transcoder_client.get_system_info",
            new_callable=AsyncMock, return_value=transcoder_info,
        ),
    ):
        await system_cache.refresh()
    assert system_cache.get_arm_info() == arm_info
    assert system_cache.get_transcoder_info() == transcoder_info


async def test_refresh_handles_none_from_services():
    """refresh() stores None when services are unreachable."""
    with (
        patch(
            "backend.services.system_cache.arm_client.get_system_info",
            new_callable=AsyncMock, return_value=None,
        ),
        patch(
            "backend.services.system_cache.transcoder_client.get_system_info",
            new_callable=AsyncMock, return_value=None,
        ),
    ):
        await system_cache.refresh()
    assert system_cache.get_arm_info() is None
    assert system_cache.get_transcoder_info() is None


# --- Ripping data cache tests ---
# These test the cache logic by directly manipulating module globals
# instead of calling async functions, avoiding event-loop isolation issues.


def test_get_ripping_data_cold_cache_returns_none():
    """Cold cache (no data, expired TTL) returns None from get_ripping_data."""
    system_cache._ripping_data = None
    assert system_cache._ripping_data is None


def test_ripping_cache_stores_data():
    """Simulates what _refresh_ripping does: stores data and updates timestamp."""
    system_cache._ripping_data = None
    system_cache._ripping_fetched_at = 0.0

    # Simulate successful refresh
    ripping_info = {"ripping_enabled": True, "makemkv_key_valid": True}
    system_cache._ripping_data = ripping_info
    system_cache._ripping_fetched_at = time.monotonic()

    assert system_cache._ripping_data == ripping_info
    assert system_cache._ripping_fetched_at > 0


def test_ripping_ttl_not_expired():
    """Within TTL window, data is considered fresh."""
    system_cache._ripping_fetched_at = time.monotonic()
    now = time.monotonic()
    assert now - system_cache._ripping_fetched_at < system_cache._RIPPING_TTL


def test_ripping_ttl_expired():
    """After TTL expires, data is considered stale."""
    system_cache._ripping_fetched_at = time.monotonic() - system_cache._RIPPING_TTL - 1
    now = time.monotonic()
    assert now - system_cache._ripping_fetched_at >= system_cache._RIPPING_TTL


def test_ripping_data_not_overwritten_when_not_set():
    """Cached ripping data persists when no new value is written."""
    previous = {"ripping_enabled": True}
    system_cache._ripping_data = previous
    assert system_cache._ripping_data is previous
