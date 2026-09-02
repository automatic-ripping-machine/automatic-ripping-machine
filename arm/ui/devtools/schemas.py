"""
Stable JSON response helpers for devtools endpoints.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def timestamp_now() -> str:
    """
    Return a stable UTC timestamp.

    Returns:
        str: ISO-8601 UTC timestamp
    """
    return datetime.now(timezone.utc).isoformat()


def make_response(
    *,
    success: bool,
    data: dict[str, Any] | None = None,
    errors: list[str] | None = None,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    """
    Return a consistent response envelope.

    Data stays nested under ``data`` - it is never flattened onto the
    envelope, which caused semantic collisions in the reference
    implementation (e.g. a failed-track count being read as a
    test-failure count by other tooling).

    Returns:
        dict: the enveloped response payload
    """
    payload = {
        "success": success,
        "timestamp": timestamp_now(),
        "errors": errors or [],
    }
    if data is not None:
        payload["data"] = data
    if notes is not None:
        payload["notes"] = notes
    return payload
