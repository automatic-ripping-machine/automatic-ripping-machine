"""Synchronous metadata wrappers for the ripper process.

The ripper is spawned by udev and has no running event loop, so
``asyncio.run()`` is safe here.

MetadataConfigError is intentionally NOT caught — callers should
handle it (or let it propagate to fail the identification phase).
Network errors from httpx are caught and logged to prevent a
transient API outage from crashing the ripper.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from arm.services import metadata
from arm.services.metadata import MetadataConfigError  # noqa: F401 — re-export for callers

log = logging.getLogger(__name__)


def search_sync(query: str, year: str | None = None) -> list[dict[str, Any]]:
    """Sync wrapper for metadata.search().

    Raises MetadataConfigError if no API key is configured.
    Returns empty list on network/timeout errors.
    """
    try:
        return asyncio.run(metadata.search(query, year))
    except MetadataConfigError:
        raise
    except (httpx.HTTPError, httpx.ConnectError, httpx.TimeoutException) as exc:
        log.error("Metadata search network error for %r: %s", query, exc)
        return []


def get_details_sync(imdb_id: str) -> dict[str, Any] | None:
    """Sync wrapper for metadata.get_details().

    Raises MetadataConfigError if no API key is configured.
    Returns None on network/timeout errors.
    """
    try:
        return asyncio.run(metadata.get_details(imdb_id))
    except MetadataConfigError:
        raise
    except (httpx.HTTPError, httpx.ConnectError, httpx.TimeoutException) as exc:
        log.error("Metadata detail network error for %s: %s", imdb_id, exc)
        return None


def lookup_crc_sync(crc64: str) -> dict[str, Any]:
    """Sync wrapper for metadata.lookup_crc().

    Always returns a dict (never raises). Network errors are caught
    internally by lookup_crc() and returned as {"found": False, "error": ...}.
    """
    return asyncio.run(metadata.lookup_crc(crc64))
