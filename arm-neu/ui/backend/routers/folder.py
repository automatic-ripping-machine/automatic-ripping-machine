"""Folder import proxy - routes folder scan/create through the ARM backend."""
from typing import Any
from urllib.parse import quote, urlparse

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from backend.models.folder import (
    FolderCreateRequest,
    FolderCreateResponse,
    FolderScanRequest,
    FolderScanResult,
)
from backend.services import arm_client

router = APIRouter(prefix="/api/jobs/folder", tags=["folder"])

_ARM_UI_UNREACHABLE = "ARM web UI is unreachable"


def _check_result(result: dict[str, Any] | None) -> dict[str, Any]:
    if result is None:
        raise HTTPException(status_code=503, detail=_ARM_UI_UNREACHABLE)
    if isinstance(result, dict) and result.get("success") is False:
        detail = result.get("error") or "Action failed"
        raise HTTPException(status_code=502, detail=detail)
    return result


@router.post("/scan", response_model=FolderScanResult)
async def scan_folder(req: FolderScanRequest) -> dict[str, Any]:
    """Scan a folder for disc structure and metadata."""
    return _check_result(await arm_client.scan_folder(req.path))


@router.post("", status_code=201, response_model=FolderCreateResponse)
async def create_folder_job(req: FolderCreateRequest) -> dict[str, Any]:
    """Create a folder import job."""
    return _check_result(await arm_client.create_folder_job(req.model_dump()))


def _safe_proxy_redirect(url: str) -> str:
    """Return a safe same-app redirect to the image proxy.

    Poster URLs are legitimately absolute (e.g. https://image.tmdb.org/...),
    so they are allowed — but the redirect *target* is always the hardcoded
    same-app path ``/api/images/proxy`` and the caller-supplied URL is only
    ever a percent-encoded query-string value. That prevents an open redirect
    (the Location path/host is constant and the value can't break out of the
    query string). Only http(s) poster URLs are accepted so the downstream
    proxy can never be pointed at file://, gopher://, etc.
    """
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ("http", "https"):
        raise HTTPException(
            status_code=400,
            detail="Invalid url parameter: must be an http(s) URL.",
        )
    # percent-encode the value so it stays confined to the query string
    safe_url = quote(url, safe="")
    return f"/api/images/proxy?url={safe_url}"


@router.get("/poster-proxy")
async def poster_proxy_redirect(url: str = Query(..., description="Poster image URL")):
    """Redirect to new image proxy endpoint (backward compatibility)."""
    return RedirectResponse(_safe_proxy_redirect(url), status_code=301)
