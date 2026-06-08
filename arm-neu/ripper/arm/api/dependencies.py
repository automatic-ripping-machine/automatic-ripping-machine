"""Shared FastAPI dependencies for the v1 API surface."""
from __future__ import annotations

from fastapi import Header, HTTPException

from arm.version import (
    ACCEPT_MISSING_VERSION_HEADER,
    ACCEPTED_VERSIONS,
)


async def require_api_version(
    x_api_version: str | None = Header(default=None, alias="X-Api-Version"),
) -> str | None:
    """Validate the X-Api-Version header on cross-service inbound calls.

    Mirrors transcoder/src/routers/jobs.py:require_api_version. Returns the
    accepted header value (or None when missing-and-lenient) so route
    handlers can log it. Raises HTTPException(400) on rejection.
    """
    if x_api_version is None:
        if ACCEPT_MISSING_VERSION_HEADER:
            return None
        raise HTTPException(
            status_code=400,
            detail="X-Api-Version header is required",
        )
    if x_api_version not in ACCEPTED_VERSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported X-Api-Version: {x_api_version!r}. "
                f"Accepted: {sorted(ACCEPTED_VERSIONS)}"
            ),
        )
    return x_api_version
