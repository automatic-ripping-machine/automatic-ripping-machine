"""Async httpx client for the ARM Flask JSON API."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

import httpx

from backend.config import settings

log = logging.getLogger(__name__)

_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        if settings.demo_mode:
            try:
                from backend.demo.transport import make_demo_client
                _client = make_demo_client(
                    "arm", base_url=settings.arm_url, timeout=10.0,
                    limits=httpx.Limits(keepalive_expiry=30.0),
                )
                return _client
            except Exception:  # never serve demo on error — use real client
                log.exception("demo client unavailable; using real ARM client")
        # keepalive_expiry > dashboard poll cadence (5s) so connections
        # don't sit at the keepalive boundary where one side may close
        # the socket while the other still considers it alive — that
        # race surfaces as RemoteProtocolError and flips the sidebar
        # to "Cannot reach the ARM ripping service" for a poll cycle.
        _client = httpx.AsyncClient(
            base_url=settings.arm_url,
            timeout=10.0,
            limits=httpx.Limits(keepalive_expiry=30.0),
        )
    return _client


async def close_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


def _parse_error_response(resp: httpx.Response) -> dict[str, Any]:
    """Extract an error dict from a non-2xx ARM response.

    Returns a dict with ``success=False`` and the best error detail
    we can extract so that ``_check_result`` in the router can surface
    the real message instead of "ARM web UI is unreachable".
    """
    try:
        body = resp.json()
        if isinstance(body, dict):
            # FastAPI error responses use "detail", ARM uses "error"
            detail = body.get("detail") or body.get("error") or body.get("Error")
            if detail:
                return {"success": False, "error": f"ARM error ({resp.status_code}): {detail}"}
            return {"success": False, "error": f"ARM error ({resp.status_code}): {body}"}
    except Exception:
        pass
    return {"success": False, "error": f"ARM returned HTTP {resp.status_code}"}


async def _request(
    method: str, url: str, **kwargs: Any
) -> dict[str, Any] | None:
    """Send a request to the ARM API.

    Returns the parsed JSON on success, an error dict on HTTP errors,
    or None only when ARM is genuinely unreachable (connection refused,
    DNS failure, timeout).
    """
    try:
        resp = await get_client().request(method, url, **kwargs)
        if resp.is_success:
            # 204 No Content (e.g. channel DELETE) or any empty success body
            # has no JSON to parse. Return {} — a truthy-enough success marker
            # that is NOT None, so callers that treat None as "ARM unreachable"
            # do not misfire a 503.
            if resp.status_code == 204 or not resp.content:
                return {}
            return resp.json()
        return _parse_error_response(resp)
    except (httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError, httpx.ReadError, RuntimeError, OSError) as exc:
        log.debug("ARM unreachable (%s %s): %s", method, url, exc)
        return None


async def abandon_job(job_id: int) -> dict[str, Any] | None:
    """Abandon a running job. Returns None if ARM is unreachable."""
    return await _request("POST", f"/api/v1/jobs/{job_id}/abandon")


async def cancel_waiting_job(job_id: int) -> dict[str, Any] | None:
    """Cancel a job in 'waiting' status. Returns None if ARM is unreachable."""
    return await _request("POST", f"/api/v1/jobs/{job_id}/cancel")


async def delete_job(job_id: int) -> dict[str, Any] | None:
    """Delete a completed/failed job. Returns None if ARM is unreachable."""
    return await _request("DELETE", f"/api/v1/jobs/{job_id}")


async def get_config() -> dict[str, Any] | None:
    """Fetch live ARM config (with comments metadata). Returns None if unreachable."""
    return await _request("GET", "/api/v1/settings/config")


async def update_config(config: dict[str, Any]) -> dict[str, Any] | None:
    """Write ARM config. Returns response dict or None if unreachable."""
    return await _request("PUT", "/api/v1/settings/config", json={"config": config})


async def get_system_info() -> dict[str, Any] | None:
    """Fetch static hardware info (CPU, RAM) from the ARM container."""
    return await _request("GET", "/api/v1/system/info")


async def get_system_stats() -> dict[str, Any] | None:
    """Fetch live system stats (CPU, memory, storage) from the ARM container."""
    return await _request("GET", "/api/v1/system/stats")


async def fix_permissions(job_id: int) -> dict[str, Any] | None:
    """Fix file permissions for a job. Returns None if ARM is unreachable."""
    return await _request("POST", f"/api/v1/jobs/{job_id}/fix-permissions")


async def skip_and_finalize(job_id: int) -> dict[str, Any] | None:
    """Skip transcoding and finalize a stuck job. Returns None if ARM is unreachable."""
    return await _request("POST", f"/api/v1/jobs/{job_id}/skip-and-finalize")


async def force_complete(job_id: int) -> dict[str, Any] | None:
    """Mark a stuck job as SUCCESS without moving files. Returns None if ARM is unreachable."""
    return await _request("POST", f"/api/v1/jobs/{job_id}/force-complete")


async def scan_folder(path: str) -> dict[str, Any] | None:
    """Scan a folder for disc structure. Returns None if ARM is unreachable."""
    return await _request("POST", "/api/v1/jobs/folder/scan", json={"path": path})


async def create_folder_job(data: dict[str, Any]) -> dict[str, Any] | None:
    """Create a folder import job. Returns None if ARM is unreachable."""
    return await _request("POST", "/api/v1/jobs/folder", json=data)


async def scan_iso(path: str) -> dict[str, Any] | None:
    """Scan an ISO file for disc structure. Returns None if ARM is unreachable."""
    return await _request("POST", "/api/v1/jobs/iso/scan", json={"path": path})


async def create_iso_job(data: dict[str, Any]) -> dict[str, Any] | None:
    """Create an ISO import job. Returns None if ARM is unreachable."""
    return await _request("POST", "/api/v1/jobs/iso", json=data)


async def update_title(job_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    """Update a job's title metadata via ARM's REST API. Returns None if unreachable."""
    return await _request("PUT", f"/api/v1/jobs/{job_id}/title", json=data)


async def update_job_config(job_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    """Update a job's rip parameters via ARM's REST API. Returns None if unreachable."""
    return await _request("PATCH", f"/api/v1/jobs/{job_id}/config", json=data)


async def start_waiting_job(job_id: int) -> dict[str, Any] | None:
    """Start a job in 'waiting' status. Returns None if ARM is unreachable."""
    return await _request("POST", f"/api/v1/jobs/{job_id}/start")


async def pause_waiting_job(job_id: int, paused: bool | None = None) -> dict[str, Any] | None:
    """Set or toggle per-job pause for a waiting job. Returns None if ARM is unreachable."""
    kwargs: dict[str, Any] = {}
    if paused is not None:
        kwargs["json"] = {"paused": paused}
    return await _request("POST", f"/api/v1/jobs/{job_id}/pause", **kwargs)


async def set_ripping_enabled(enabled: bool) -> dict[str, Any] | None:
    """Toggle global ripping pause. Returns None if ARM is unreachable."""
    return await _request("POST", "/api/v1/system/ripping-enabled", json={"enabled": enabled})


async def get_version() -> dict[str, str] | None:
    """Fetch ARM and MakeMKV version info."""
    return await _request("GET", "/api/v1/system/version")


async def get_paths() -> list[dict[str, Any]] | None:
    """Fetch path existence/writability checks from the ARM container."""
    try:
        resp = await get_client().get("/api/v1/system/paths")
        if resp.is_success:
            return resp.json()
        return None
    except (httpx.ConnectError, httpx.TimeoutException, RuntimeError, OSError):
        return None


async def send_to_crc_db(job_id: int) -> dict[str, Any] | None:
    """Submit a job's CRC data to the community database. Returns None if ARM is unreachable."""
    return await _request("POST", f"/api/v1/jobs/{job_id}/send")


async def toggle_multi_title(job_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    """Toggle the multi_title flag on a job. Returns None if ARM is unreachable."""
    return await _request("POST", f"/api/v1/jobs/{job_id}/multi-title", json=data)


async def update_track_title(job_id: int, track_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    """Set per-track title metadata. Returns None if ARM is unreachable."""
    return await _request("PUT", f"/api/v1/jobs/{job_id}/tracks/{track_id}/title", json=data)


async def clear_track_title(job_id: int, track_id: int) -> dict[str, Any] | None:
    """Clear per-track title metadata. Returns None if ARM is unreachable."""
    return await _request("DELETE", f"/api/v1/jobs/{job_id}/tracks/{track_id}/title")


async def set_job_tracks(job_id: int, tracks: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Replace a job's tracks with MusicBrainz data. Returns None if ARM is unreachable."""
    return await _request("PUT", f"/api/v1/jobs/{job_id}/tracks", json={"tracks": tracks})


async def tvdb_match(job_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    """Run TVDB episode matching for a job. Returns None if ARM is unreachable."""
    return await _request("POST", f"/api/v1/jobs/{job_id}/tvdb-match", json=data)


async def tvdb_episodes(job_id: int, season: int) -> dict[str, Any] | None:
    """Fetch TVDB episodes for a job's series. Returns None if ARM is unreachable."""
    return await _request("GET", f"/api/v1/jobs/{job_id}/tvdb-episodes", params={"season": str(season)})


async def update_drive(drive_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    """Update a drive's name/description via ARM's REST API. Returns None if unreachable."""
    return await _request("PATCH", f"/api/v1/drives/{drive_id}", json=data)


async def scan_drive(drive_id: int) -> dict[str, Any] | None:
    """Trigger a disc scan on a drive. Returns None if ARM is unreachable."""
    return await _request("POST", f"/api/v1/drives/{drive_id}/scan")


async def rescan_drives(force: bool = False) -> dict[str, Any] | None:
    """Re-detect optical drives and update the database. Returns None if ARM is unreachable."""
    params = {"force": "true"} if force else None
    return await _request("POST", "/api/v1/drives/rescan", params=params)


async def drive_diagnostic() -> dict[str, Any] | None:
    """Run udev and device diagnostics. Returns None if ARM is unreachable."""
    return await _request("GET", "/api/v1/drives/diagnostic")


async def delete_drive(drive_id: int) -> dict[str, Any] | None:
    """Remove a stale drive from the database. Returns None if ARM is unreachable."""
    return await _request("DELETE", f"/api/v1/drives/{drive_id}")


async def dismiss_notification(notify_id: int) -> dict[str, Any] | None:
    """Mark a notification as read. Returns None if ARM is unreachable."""
    return await _request("PATCH", f"/api/v1/notifications/{notify_id}")


async def get_abcde_config() -> dict[str, Any] | None:
    """Fetch abcde.conf contents from ARM. Returns None if unreachable."""
    return await _request("GET", "/api/v1/settings/abcde")


async def update_abcde_config(content: str) -> dict[str, Any] | None:
    """Write abcde.conf contents via ARM. Returns None if unreachable."""
    return await _request("PUT", "/api/v1/settings/abcde", json={"content": content})


async def naming_preview(pattern: str, variables: dict[str, str]) -> dict[str, Any] | None:
    """Preview a naming pattern with given variables. Returns None if ARM is unreachable."""
    return await _request(
        "POST", "/api/v1/naming/preview",
        json={"pattern": pattern, "variables": variables},
    )


async def naming_preview_for_job(job_id: int) -> dict[str, Any] | None:
    """Get rendered filenames for all tracks on a job. Returns None if ARM is unreachable."""
    return await _request("GET", f"/api/v1/jobs/{job_id}/naming-preview")


# ---------------------------------------------------------------------------
# Metadata proxy — ARM is the single source of truth
# ---------------------------------------------------------------------------


async def search_metadata(query: str, year: str | None = None, page: int = 1) -> list[dict[str, Any]]:
    """Search OMDb/TMDb via ARM. Raises httpx.HTTPStatusError on 4xx/5xx."""
    params: dict[str, str] = {"q": query}
    if year:
        params["year"] = year
    if page > 1:
        params["page"] = str(page)
    resp = await get_client().get("/api/v1/metadata/search", params=params)
    resp.raise_for_status()
    return resp.json()


async def get_media_detail(imdb_id: str) -> dict[str, Any] | None:
    """Fetch full details for a title by IMDb ID via ARM."""
    resp = await get_client().get(f"/api/v1/metadata/{imdb_id}")
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


async def get_job_metadata(job_id: int) -> dict[str, Any] | None:
    """Fetch merged MediaMetadata for a job via ARM.

    Returns None on 404 (caller raises 404 to its own client) or on
    transport failure (caller raises 502).
    """
    try:
        resp = await get_client().get(f"/api/v1/jobs/{job_id}/metadata")
    except (httpx.ConnectError, httpx.HTTPError):
        return None
    if resp.status_code == 404:
        return {"detail": "Job not found"}
    resp.raise_for_status()
    return resp.json()


async def search_music_metadata(
    query: str, **kwargs: Any
) -> dict[str, Any]:
    """Search MusicBrainz via ARM."""
    params: dict[str, str] = {"q": query}
    for key, val in kwargs.items():
        if val is not None:
            params[key] = str(val)
    resp = await get_client().get("/api/v1/metadata/music/search", params=params)
    resp.raise_for_status()
    return resp.json()


async def get_music_detail(release_id: str) -> dict[str, Any] | None:
    """Fetch full release details from MusicBrainz via ARM."""
    resp = await get_client().get(f"/api/v1/metadata/music/{release_id}")
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


async def lookup_crc(crc64: str) -> dict[str, Any]:
    """Look up a CRC64 hash via ARM."""
    resp = await get_client().get(f"/api/v1/metadata/crc/{crc64}")
    resp.raise_for_status()
    return resp.json()


async def test_metadata_key(key: str | None = None, provider: str | None = None) -> dict[str, Any]:
    """Test a metadata API key via ARM. Uses saved config if overrides are omitted.

    The makemkv provider runs prep_mkv() which can fetch a fresh beta key from
    forum.makemkv.com on a cold check (15-30s); other providers respond
    quickly. Use a 30-second timeout uniformly so any provider has enough
    headroom for a slow upstream.
    """
    params: dict[str, str] = {}
    if key:
        params["key"] = key
    if provider:
        params["provider"] = provider
    resp = await get_client().get("/api/v1/metadata/test-key", params=params, timeout=30.0)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# File browser proxy — ARM has direct filesystem access
# ---------------------------------------------------------------------------


async def get_file_roots() -> list[dict[str, Any]] | None:
    """Fetch configured media root directories. Returns None if ARM is unreachable."""
    return await _request("GET", "/api/v1/files/roots")


async def list_files(path: str) -> dict[str, Any] | None:
    """List directory contents. Returns None if ARM is unreachable."""
    return await _request("GET", "/api/v1/files/list", params={"path": path})


async def rename_file(path: str, new_name: str) -> dict[str, Any] | None:
    """Rename a file or directory. Returns None if ARM is unreachable."""
    return await _request("POST", "/api/v1/files/rename", json={"path": path, "new_name": new_name})


async def move_file(path: str, destination: str) -> dict[str, Any] | None:
    """Move a file or directory. Returns None if ARM is unreachable."""
    return await _request("POST", "/api/v1/files/move", json={"path": path, "destination": destination})


async def create_directory(path: str, name: str) -> dict[str, Any] | None:
    """Create a new directory. Returns None if ARM is unreachable."""
    return await _request("POST", "/api/v1/files/mkdir", json={"path": path, "name": name})


async def fix_file_permissions(path: str) -> dict[str, Any] | None:
    """Fix ownership and permissions for a file or directory. Returns None if ARM is unreachable."""
    return await _request("POST", "/api/v1/files/fix-permissions", json={"path": path})


async def delete_file(path: str) -> dict[str, Any] | None:
    """Delete a file or directory. Returns None if ARM is unreachable."""
    return await _request("DELETE", "/api/v1/files/delete", json={"path": path})


async def get_setup_status() -> dict[str, Any] | None:
    """Fetch setup wizard status. Returns None if ARM is unreachable."""
    return await _request("GET", "/api/v1/setup/status")


async def complete_setup() -> dict[str, Any] | None:
    """Mark first-run setup as complete. Returns None if ARM is unreachable."""
    return await _request("POST", "/api/v1/setup/complete")


async def eject_drive(drive_id: int, method: str = "toggle") -> dict[str, Any] | None:
    """Eject, close, or toggle a drive tray. Returns None if ARM is unreachable."""
    return await _request("POST", f"/api/v1/drives/{drive_id}/eject", json={"method": method})


async def get_job_stats() -> dict[str, Any] | None:
    """Fetch job counts by status and type. Returns None if ARM is unreachable."""
    return await _request("GET", "/api/v1/system/stats/jobs")


async def restart_arm() -> dict[str, Any] | None:
    """Restart the ARM service. Returns None if ARM is unreachable."""
    return await _request("POST", "/api/v1/system/restart")


# --- Maintenance ---


async def get_maintenance_counts() -> dict[str, Any] | None:
    """Get orphan counts from ARM."""
    return await _request("GET", "/api/v1/maintenance/counts")


async def get_orphan_logs() -> dict[str, Any] | None:
    """Get orphan log files from ARM."""
    return await _request("GET", "/api/v1/maintenance/orphan-logs")


async def get_orphan_folders() -> dict[str, Any] | None:
    """Get orphan folders from ARM."""
    return await _request("GET", "/api/v1/maintenance/orphan-folders")


async def delete_orphan_log(path: str) -> dict[str, Any] | None:
    """Delete a single orphan log file via ARM."""
    return await _request("POST", "/api/v1/maintenance/delete-log", json={"path": path})


async def delete_orphan_folder(path: str) -> dict[str, Any] | None:
    """Delete a single orphan folder via ARM."""
    return await _request("POST", "/api/v1/maintenance/delete-folder", json={"path": path})


async def bulk_delete_logs(paths: list[str]) -> dict[str, Any] | None:
    """Bulk delete orphan log files via ARM."""
    return await _request("POST", "/api/v1/maintenance/bulk-delete-logs", json={"paths": paths})


async def bulk_delete_folders(paths: list[str]) -> dict[str, Any] | None:
    """Bulk delete orphan folders via ARM."""
    return await _request("POST", "/api/v1/maintenance/bulk-delete-folders", json={"paths": paths})


async def clear_raw() -> dict[str, Any] | None:
    """Clear all contents of the raw/scratch directory via ARM."""
    return await _request("POST", "/api/v1/maintenance/clear-raw")


async def update_job_naming(job_id: int, overrides: dict) -> dict[str, Any] | None:
    """Update per-job naming pattern overrides via ARM."""
    return await _request("PATCH", f"/api/v1/jobs/{job_id}/naming", json=overrides)


async def validate_naming_pattern(pattern: str) -> dict[str, Any] | None:
    """Validate a naming pattern against known variables."""
    return await _request("POST", "/api/v1/naming/validate", json={"pattern": pattern})


async def get_naming_variables() -> dict[str, Any] | None:
    """Get the list of valid naming pattern variables."""
    return await _request("GET", "/api/v1/naming/variables")


# --- Architecture debt fix: proxy these through ARM ---


async def update_transcode_overrides(job_id: int, overrides: dict) -> dict[str, Any] | None:
    """Update per-job transcode overrides via ARM (existing endpoint).

    Pre-validates the body against the shared contract so a frontend glitch
    surfaces locally with a proper ValidationError instead of as a
    round-trip 400 from arm-neu. Callers can catch ValidationError and
    render the loc/msg details in the UI.
    """
    from arm_contracts import TranscodeJobConfig
    TranscodeJobConfig.model_validate(overrides)  # raises on invalid
    return await _request("PATCH", f"/api/v1/jobs/{job_id}/transcode-config", json=overrides)


async def update_track_fields(job_id: int, track_id: int, fields: dict) -> dict[str, Any] | None:
    """Update track fields via ARM."""
    return await _request("PATCH", f"/api/v1/jobs/{job_id}/tracks/{track_id}", json=fields)


# --- MakeMKV Key Check ---


async def get_ripping_enabled() -> dict[str, Any] | None:
    """Get ripping-enabled status and MakeMKV key validity from ARM."""
    return await _request("GET", "/api/v1/system/ripping-enabled")


async def check_makemkv_key() -> dict[str, Any] | None:
    """Trigger a MakeMKV key validity check on ARM.

    Uses a 30-second timeout since prep_mkv() may fetch the beta key
    from forum.makemkv.com over the network.
    """
    return await _request("POST", "/api/v1/system/makemkv-key-check", timeout=30.0)


# --- Preflight checks ---


async def run_preflight() -> dict[str, Any] | None:
    """Run ARM preflight checks. Returns None if ARM is unreachable.

    Uses a 60-second timeout: preflight includes MakeMKV key validation
    (which may fetch the beta key from forum.makemkv.com via curl with
    a 15s cap) plus per-path stat/chown probes. 30s used to be enough,
    but a slow forum.makemkv.com round-trip plus the API key probes can
    push us past it; the upstream caps the MakeMKV step itself.
    """
    return await _request("POST", "/api/v1/system/preflight", timeout=60.0)


async def fix_preflight(items: list[str]) -> dict[str, Any] | None:
    """Fix specified preflight issues, then re-check. Returns None if ARM is unreachable."""
    return await _request("POST", "/api/v1/system/preflight/fix", json={"fix": items}, timeout=60.0)


# --- Jobs (read-side, replaces direct DB access via backend.services.arm_db) ---


async def get_active_jobs() -> dict[str, Any] | None:
    """Active jobs with track counts. Returns None if ARM is unreachable."""
    return await _request("GET", "/api/v1/jobs/active")


async def get_jobs_paginated(
    page: int = 1,
    per_page: int = 25,
    status: str | None = None,
    search: str | None = None,
    video_type: str | None = None,
    disctype: str | None = None,
    days: int | None = None,
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> dict[str, Any] | None:
    """Paginated job list with filters. Returns None if ARM is unreachable."""
    params: dict[str, Any] = {"page": page, "per_page": per_page}
    for key, val in (
        ("status", status), ("search", search), ("video_type", video_type),
        ("disctype", disctype), ("days", days),
        ("sort_by", sort_by), ("sort_dir", sort_dir),
    ):
        if val is not None and val != "":
            params[key] = val
    return await _request("GET", "/api/v1/jobs/paginated", params=params)


async def get_jobs_stats(
    search: str | None = None,
    video_type: str | None = None,
    disctype: str | None = None,
    days: int | None = None,
) -> dict[str, Any] | None:
    """Filter-aware bucketed counts (total/active/waiting/success/fail).

    Calls /api/v1/jobs/stats. Distinct from the legacy get_job_stats() which
    hits /system/stats/jobs and returns raw by-status counts with no filter
    support. Returns None if ARM is unreachable.
    """
    params: dict[str, Any] = {}
    for key, val in (
        ("search", search), ("video_type", video_type),
        ("disctype", disctype), ("days", days),
    ):
        if val is not None and val != "":
            params[key] = val
    return await _request("GET", "/api/v1/jobs/stats", params=params)


async def get_job_detail(job_id: int) -> dict[str, Any] | None:
    """Job + (masked) config + track_counts. Returns None if ARM is unreachable."""
    return await _request("GET", f"/api/v1/jobs/{job_id}/detail")


async def get_job_track_counts(job_id: int) -> dict[str, Any] | None:
    """Lightweight {total, ripped} for one job. Returns None if ARM is unreachable."""
    return await _request("GET", f"/api/v1/jobs/{job_id}/track-counts")


async def get_job_progress_state(job_id: int) -> dict[str, Any] | None:
    """Track counts + disctype/logfile/no_of_titles plus realtime PRGV/abcde
    progress for the BFF progress endpoint.

    One round trip instead of three - keeps the dashboard's per-job
    progress polls cheap. Returns None if ARM is unreachable.
    """
    return await _request("GET", f"/api/v1/jobs/{job_id}/progress-state")


# --- Logs (read + delete) ---


def _quote_log_name(filename: str) -> str:
    """Percent-encode a log filename so it cannot escape the /logs/ subtree.

    safe="" forces / and reserved chars to be encoded too, so a malicious
    `filename` cannot route to a different upstream endpoint. The arm-neu
    side does its own basename-strip + LOGPATH containment check, so this
    is defence in depth (Sonar python:S5145 - URL path from user data).
    """
    return quote(filename, safe="")


async def list_logs() -> list[dict[str, Any]] | None:
    """List log files in the ripper's LOGPATH. Returns None if unreachable."""
    return await _request("GET", "/api/v1/logs")


async def read_log(
    filename: str, mode: str = "tail", lines: int = 100
) -> dict[str, Any] | None:
    """Read a log file (tail or full). Returns None if unreachable, or a
    dict with `error` set if the upstream returned 4xx/5xx (caller maps
    that to 404)."""
    return await _request(
        "GET", f"/api/v1/logs/{_quote_log_name(filename)}",
        params={"mode": mode, "lines": str(lines)},
    )


async def read_log_structured(
    filename: str,
    mode: str = "tail",
    lines: int = 100,
    level: str | None = None,
    search: str | None = None,
) -> dict[str, Any] | None:
    """Read a log file with parsed entries + optional filters."""
    params: dict[str, str] = {"mode": mode, "lines": str(lines)}
    if level:
        params["level"] = level
    if search:
        params["search"] = search
    return await _request(
        "GET", f"/api/v1/logs/{_quote_log_name(filename)}/structured",
        params=params,
    )


async def delete_log(filename: str) -> dict[str, Any] | None:
    """Delete a log file by name. Returns None if unreachable."""
    return await _request("DELETE", f"/api/v1/logs/{_quote_log_name(filename)}")


async def stream_log_download(filename: str):
    """Async-iterate the upstream download bytes for the logs/{name}/download endpoint.

    Yields (status_code, headers, async-byte-iterator). The caller is
    responsible for relaying the status + content-type + bytes to the user.
    Returns None if the upstream is unreachable.
    """
    try:
        client = get_client()
        req = client.build_request(
            "GET", f"/api/v1/logs/{_quote_log_name(filename)}/download"
        )
        resp = await client.send(req, stream=True)
        return resp
    except (httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError, httpx.ReadError, RuntimeError, OSError) as exc:
        log.debug("ARM unreachable for log download (%s): %s", filename, exc)
        return None


async def get_job_retranscode_info(job_id: int) -> dict[str, Any] | None:
    """Retranscode payload for one job. Returns None if ARM is unreachable."""
    return await _request("GET", f"/api/v1/jobs/{job_id}/retranscode-info")


# --- Drives (read-side) ---


async def get_drives(include_stale: bool = True) -> dict[str, Any] | None:
    """List system drives. Default include_stale=True matches the legacy
    arm_db.get_drives() shape; pass False for non-stale drives only.
    Returns None if ARM is unreachable.
    """
    params = {"include_stale": "true"} if include_stale else None
    return await _request("GET", "/api/v1/drives", params=params)


async def get_drives_with_jobs() -> dict[str, Any] | None:
    """Drives + current-job summaries. Returns None if ARM is unreachable."""
    return await _request("GET", "/api/v1/drives/with-jobs")


# --- Notifications (read + bulk write) ---


async def get_notifications(include_cleared: bool = False) -> dict[str, Any] | None:
    """Notification list. Returns None if ARM is unreachable."""
    params = {"include_cleared": "true"} if include_cleared else None
    return await _request("GET", "/api/v1/notifications", params=params)


async def get_notification_count() -> dict[str, Any] | None:
    """Notification counts: {total, unseen, seen, cleared}. Returns None if ARM is unreachable."""
    return await _request("GET", "/api/v1/notifications/count")


async def dismiss_all_notifications() -> dict[str, Any] | None:
    """Mark all unseen notifications as seen. Returns None if ARM is unreachable."""
    return await _request("POST", "/api/v1/notifications/dismiss-all")


async def purge_cleared_notifications() -> dict[str, Any] | None:
    """Hard-delete all cleared notifications. Returns None if ARM is unreachable."""
    return await _request("POST", "/api/v1/notifications/purge")


# --- Notification channels (v4 channels system) ---


async def list_channels() -> list[dict[str, Any]] | None:
    """List notification channels. Returns None if ARM is unreachable."""
    return await _request("GET", "/api/v1/notifications/channels")


async def get_channel(channel_id: int) -> dict[str, Any] | None:
    """Fetch one channel. Returns None if ARM is unreachable."""
    return await _request("GET", f"/api/v1/notifications/channels/{channel_id}")


async def create_channel(body: dict[str, Any]) -> dict[str, Any] | None:
    """Create a channel. Returns None if ARM is unreachable."""
    return await _request("POST", "/api/v1/notifications/channels", json=body)


async def update_channel(channel_id: int, body: dict[str, Any]) -> dict[str, Any] | None:
    """Patch a channel. Returns None if ARM is unreachable."""
    return await _request("PATCH", f"/api/v1/notifications/channels/{channel_id}", json=body)


async def delete_channel(channel_id: int) -> dict[str, Any] | None:
    """Delete a channel. Returns None if ARM is unreachable."""
    return await _request("DELETE", f"/api/v1/notifications/channels/{channel_id}")


async def test_send_channel(channel_id: int, body: dict[str, Any]) -> dict[str, Any] | None:
    """Trigger a test send. Returns None if ARM is unreachable."""
    return await _request("POST", f"/api/v1/notifications/channels/{channel_id}/test", json=body)


async def get_dispatch(dispatch_id: int) -> dict[str, Any] | None:
    """Fetch one dispatch (outbox row) status. Returns None if unreachable."""
    return await _request("GET", f"/api/v1/notifications/dispatch/{dispatch_id}")


async def list_dispatches(channel_id: int | None = None, status: str | None = None,
                          limit: int = 50) -> list[dict[str, Any]] | None:
    """List dispatches with optional filters. Returns None if unreachable."""
    params: dict[str, Any] = {"limit": limit}
    if channel_id is not None:
        params["channel_id"] = channel_id
    if status is not None:
        params["status"] = status
    return await _request("GET", "/api/v1/notifications/dispatches", params=params)


async def get_services() -> dict[str, Any] | None:
    """Fetch the apprise service catalog. Returns None if unreachable."""
    return await _request("GET", "/api/v1/notifications/services")


async def compose_channel_url(service_id: str, body: dict[str, Any]) -> dict[str, Any] | None:
    """Compose an apprise URL from form values. Returns None if unreachable."""
    return await _request(
        "POST",
        f"/api/v1/notifications/services/{quote(service_id, safe='')}/compose-url",
        json=body,
    )


async def test_channel_config(body: dict[str, Any]) -> dict[str, Any] | None:
    """Test-send to an unsaved channel config. Returns None if unreachable."""
    return await _request("POST", "/api/v1/notifications/test", json=body)


# --- Health ---


async def is_available() -> bool:
    """True iff the ripper API responds to a cheap GET. Replaces arm_db.is_available()."""
    return await get_version() is not None
