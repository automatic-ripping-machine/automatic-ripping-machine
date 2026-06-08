"""Async httpx client for the arm-transcoder REST API."""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from backend.config import settings

# Transcoder stores timestamps in UTC but without a trailing Z.
# JavaScript's Date() parses bare ISO strings as local time, causing
# time-ago displays to show "0s ago" for recent UTC timestamps.
_TS_FIELDS = {"created_at", "started_at", "completed_at"}
_ISO_NO_TZ = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

# Preset slugs must match what the transcoder's _slugify() produces:
# lowercase alphanumerics separated by single hyphens, 1-100 chars.
# Validating here prevents path traversal / query-string smuggling when the
# slug is interpolated into an outbound URL.
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _validate_slug(slug: str) -> str:
    if not isinstance(slug, str) or not (1 <= len(slug) <= 100) or not _SLUG_RE.fullmatch(slug):
        raise ValueError(f"Invalid preset slug: {slug!r}")
    return slug


def _normalize_timestamps(data: Any) -> Any:
    """Append 'Z' to bare ISO timestamps in transcoder responses."""
    if isinstance(data, dict):
        return {
            k: _append_z(v) if k in _TS_FIELDS and isinstance(v, str) else _normalize_timestamps(v)
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [_normalize_timestamps(item) for item in data]
    return data


def _append_z(val: str) -> str:
    if _ISO_NO_TZ.match(val) and not val.endswith("Z") and "+" not in val:
        return val + "Z"
    return val

log = logging.getLogger(__name__)

_CONFIG_ENDPOINT = "/config"
_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        headers = {}
        if settings.transcoder_api_key:
            headers["X-API-Key"] = settings.transcoder_api_key
        if settings.demo_mode:
            try:
                from backend.demo.transport import make_demo_client
                _client = make_demo_client(
                    "transcoder", base_url=settings.transcoder_url,
                    headers=headers,
                    timeout=httpx.Timeout(15.0, connect=5.0),
                    limits=httpx.Limits(keepalive_expiry=30.0),
                )
                return _client
            except Exception:
                log.exception(
                    "demo client unavailable; using real transcoder client")
        # keepalive_expiry > dashboard poll cadence (5s); see arm_client.get_client
        # for the same rationale (avoids RemoteProtocolError flicker).
        _client = httpx.AsyncClient(
            base_url=settings.transcoder_url,
            headers=headers,
            timeout=httpx.Timeout(15.0, connect=5.0),
            limits=httpx.Limits(keepalive_expiry=30.0),
        )
    return _client


async def close_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


async def health() -> dict[str, Any] | None:
    """Check transcoder health. Returns None if offline."""
    try:
        resp = await get_client().get("/health")
        resp.raise_for_status()
        return resp.json()
    except (httpx.HTTPError, httpx.ConnectError, RuntimeError, OSError):
        return None


async def test_connection() -> dict[str, Any]:
    """Two-step probe: check reachability via /health, then auth via /config."""
    result: dict[str, Any] = {
        "reachable": False,
        "auth_ok": False,
        "auth_required": False,
        "gpu_support": None,
        "worker_running": False,
        "queue_size": 0,
        "error": None,
    }
    try:
        resp = await get_client().get("/health")
        resp.raise_for_status()
        data = resp.json()
        result["reachable"] = True
        result["gpu_support"] = data.get("gpu_support")
        result["worker_running"] = data.get("worker_running", False)
        result["queue_size"] = data.get("queue_size", 0)
        result["auth_required"] = data.get("require_api_auth", False)
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        result["error"] = f"Connection failed: {e}"
        return result
    except httpx.HTTPError as e:
        result["error"] = f"Health check failed: {e}"
        return result

    # Step 2: verify API key by hitting an authenticated endpoint
    try:
        config_resp = await get_client().get(_CONFIG_ENDPOINT)
        if config_resp.status_code in (401, 403):
            result["auth_ok"] = False
        else:
            config_resp.raise_for_status()
            result["auth_ok"] = True
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (401, 403):
            result["auth_ok"] = False
        else:
            result["error"] = f"Config check failed: {e}"
    except (httpx.ConnectError, httpx.TimeoutException):
        # Reachability already confirmed via /health; this is unexpected
        result["error"] = "Lost connection during auth check"

    return result


async def test_webhook(webhook_secret: str) -> dict[str, Any]:
    """Send a test webhook payload to verify a candidate webhook secret.

    The caller must provide a non-empty ``webhook_secret``. There is no
    deploy-env fallback: whether the deployed secret is configured is
    already surfaced in /health (transcoder_auth_status.webhook_secret_configured),
    and silently testing the deploy value would make the result ambiguous
    about which secret was actually validated.
    """
    result: dict[str, Any] = {
        "reachable": False,
        "secret_ok": False,
        "secret_required": False,
        "error": None,
    }

    headers = {"X-Webhook-Secret": webhook_secret}

    try:
        # Use a fresh client without the shared X-API-Key header
        async with httpx.AsyncClient(
            base_url=settings.transcoder_url,
            timeout=httpx.Timeout(10.0, connect=3.0),
        ) as client:
            resp = await client.post(
                "/webhook/arm",
                json={"title": "ARM UI connection test", "body": "test", "type": "info"},
                headers=headers,
            )
        result["reachable"] = True
        if resp.status_code in (401, 403):
            result["secret_ok"] = False
            result["secret_required"] = True
        else:
            # Any non-auth error (400, 200 "ignored") means the secret was accepted
            result["secret_ok"] = True
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        result["error"] = f"Connection failed: {e}"
    except httpx.HTTPError as e:
        result["reachable"] = True
        result["error"] = f"Webhook test failed: {e}"

    return result


async def send_webhook(payload: dict) -> dict[str, Any]:
    """Send a webhook payload to the transcoder to trigger a transcode job.

    Reads ``TRANSCODER_WEBHOOK_SECRET`` from the deploy environment (set on
    both arm-neu and arm-ui sides at deploy time, mirroring how
    ``transcoder_api_key`` is wired).

    Returns {"success": True} or {"success": False, "error": "..."}.
    """
    webhook_secret = settings.transcoder_webhook_secret

    headers: dict[str, str] = {}
    if webhook_secret:
        headers["X-Webhook-Secret"] = webhook_secret

    try:
        async with httpx.AsyncClient(
            base_url=settings.transcoder_url,
            timeout=httpx.Timeout(10.0, connect=3.0),
        ) as client:
            resp = await client.post("/webhook/arm", json=payload, headers=headers)
        if resp.status_code in (401, 403):
            return {"success": False, "error": "Webhook secret rejected"}
        resp.raise_for_status()
        return {"success": True}
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        return {"success": False, "error": f"Transcoder offline: {e}"}
    except httpx.HTTPError as e:
        return {"success": False, "error": f"Webhook failed: {e}"}


async def get_job(job_id: int) -> dict[str, Any] | None:
    """Fetch a single transcoder job by ID."""
    try:
        resp = await get_client().get("/jobs", params={"job_id": job_id, "limit": 1})
        resp.raise_for_status()
        data = resp.json()
        jobs = data.get("jobs", [])
        return jobs[0] if jobs else None
    except (httpx.HTTPError, httpx.ConnectError, RuntimeError, OSError, IndexError):
        return None


async def get_system_info() -> dict[str, Any] | None:
    """Fetch static hardware info (CPU, RAM, GPU) from the transcoder."""
    try:
        resp = await get_client().get("/system/info")
        resp.raise_for_status()
        return resp.json()
    except (httpx.HTTPError, httpx.ConnectError, RuntimeError, OSError):
        return None


async def get_system_stats() -> dict[str, Any] | None:
    """Fetch live system metrics (CPU%, temp, memory) from the transcoder."""
    try:
        resp = await get_client().get("/system/stats")
        resp.raise_for_status()
        return resp.json()
    except (httpx.HTTPError, httpx.ConnectError, RuntimeError, OSError):
        return None


async def restart_transcoder() -> dict[str, Any] | None:
    """Restart the transcoder service. Returns None if offline."""
    try:
        resp = await get_client().post("/system/restart")
        resp.raise_for_status()
        return resp.json()
    except (httpx.HTTPError, httpx.ConnectError, RuntimeError, OSError):
        return None


async def get_scheme() -> dict[str, Any] | None:
    """Fetch active scheme from transcoder. Returns None if offline."""
    try:
        resp = await get_client().get("/api/v1/scheme")
        resp.raise_for_status()
        return resp.json()
    except (httpx.HTTPError, httpx.ConnectError, RuntimeError, OSError):
        return None


async def get_presets() -> dict[str, Any] | None:
    """Fetch all presets from transcoder. Returns None if offline."""
    try:
        resp = await get_client().get("/api/v1/presets")
        resp.raise_for_status()
        return resp.json()
    except (httpx.HTTPError, httpx.ConnectError, RuntimeError, OSError):
        return None


async def list_handbrake_presets() -> dict[str, list[str]] | None:
    """Fetch HandBrakeCLI built-in preset names from transcoder.

    Result shape: ``{category_name: [preset_name, ...]}``. Returns None
    if the transcoder is offline OR if the endpoint isn't available
    (older transcoder versions); the caller is expected to fall back to
    free-text in either case.
    """
    try:
        resp = await get_client().get("/api/v1/handbrake-presets")
        if resp.status_code == 404:
            # Older transcoder without the endpoint - signal "no list"
            # rather than 500ing the BFF.
            return None
        resp.raise_for_status()
        return resp.json()
    except (httpx.HTTPError, httpx.ConnectError, RuntimeError, OSError):
        return None


async def create_preset(body: dict[str, Any]) -> dict[str, Any] | None:
    """Create a custom preset. Returns None if transcoder offline. Raises HTTPStatusError on 4xx/5xx."""
    try:
        resp = await get_client().post("/api/v1/presets", json=body)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError:
        raise
    except (httpx.HTTPError, RuntimeError, OSError):
        return None


async def update_preset(slug: str, body: dict[str, Any]) -> dict[str, Any] | None:
    """Update a custom preset. Returns None if transcoder offline. Raises HTTPStatusError on 4xx/5xx."""
    safe_slug = _validate_slug(slug)
    try:
        resp = await get_client().patch(f"/api/v1/presets/{safe_slug}", json=body)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError:
        raise
    except (httpx.HTTPError, RuntimeError, OSError):
        return None


async def delete_preset(slug: str) -> dict[str, Any] | None:
    """Delete a custom preset. Returns None if transcoder offline. Raises HTTPStatusError on 4xx/5xx."""
    safe_slug = _validate_slug(slug)
    try:
        resp = await get_client().delete(f"/api/v1/presets/{safe_slug}")
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError:
        raise
    except (httpx.HTTPError, RuntimeError, OSError):
        return None


async def get_config() -> dict[str, Any] | None:
    """Fetch transcoder config with valid option lists. Returns None if offline."""
    try:
        resp = await get_client().get(_CONFIG_ENDPOINT)
        resp.raise_for_status()
        return resp.json()
    except (httpx.HTTPError, httpx.ConnectError, RuntimeError, OSError):
        return None


async def update_config(config: dict[str, Any]) -> dict[str, Any] | None:
    """Patch transcoder config.

    Returns parsed response on 2xx, None if transcoder is unreachable.
    Raises httpx.HTTPStatusError on 4xx/5xx so the caller can surface
    the real error (e.g. validation 422) instead of a generic offline message.
    """
    try:
        resp = await get_client().patch(_CONFIG_ENDPOINT, json=config)
    except (httpx.ConnectError, httpx.TimeoutException, RuntimeError, OSError):
        return None
    resp.raise_for_status()
    return resp.json()


async def get_jobs(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    job_id: int | None = None,
) -> dict[str, Any] | None:
    """List transcoder jobs.

    The transcoder uses the ARM job_id as its own primary key, so filtering
    on job_id returns the transcoder-side record for that ARM job (if any).
    """
    try:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        if job_id is not None:
            params["job_id"] = job_id
        resp = await get_client().get("/jobs", params=params)
        resp.raise_for_status()
        return _normalize_timestamps(resp.json())
    except (httpx.HTTPError, httpx.ConnectError, RuntimeError, OSError):
        return None


async def get_workers() -> dict[str, Any] | None:
    """Fetch per-worker status from the transcoder."""
    try:
        resp = await get_client().get("/workers")
        resp.raise_for_status()
        return resp.json()
    except (httpx.HTTPError, httpx.ConnectError, RuntimeError, OSError):
        return None


async def get_stats() -> dict[str, Any] | None:
    try:
        resp = await get_client().get("/stats")
        resp.raise_for_status()
        return resp.json()
    except (httpx.HTTPError, httpx.ConnectError, RuntimeError, OSError):
        return None


async def retry_job(job_id: int) -> dict[str, Any] | None:
    try:
        resp = await get_client().post(f"/jobs/{job_id}/retry")
        resp.raise_for_status()
        return resp.json()
    except (httpx.HTTPError, httpx.ConnectError, RuntimeError, OSError):
        return None


async def delete_job(job_id: int) -> bool:
    try:
        resp = await get_client().delete(f"/jobs/{job_id}")
        resp.raise_for_status()
        return True
    except (httpx.HTTPError, httpx.ConnectError, RuntimeError, OSError):
        return False


async def list_logs() -> list[dict[str, Any]] | None:
    """List transcoder log files. Returns None if offline."""
    try:
        resp = await get_client().get("/logs")
        resp.raise_for_status()
        return resp.json()
    except (httpx.HTTPError, httpx.ConnectError, RuntimeError, OSError):
        return None


async def read_log(
    filename: str, mode: str = "tail", lines: int = 100
) -> dict[str, Any] | None:
    """Read a transcoder log file. Returns None if offline."""
    try:
        resp = await get_client().get(
            f"/logs/{filename}", params={"mode": mode, "lines": lines}
        )
        resp.raise_for_status()
        return resp.json()
    except (httpx.HTTPError, httpx.ConnectError, RuntimeError, OSError):
        return None


async def read_structured_log(
    filename: str,
    mode: str = "tail",
    lines: int = 100,
    level: str | None = None,
    search: str | None = None,
) -> dict[str, Any] | None:
    """Read a structured transcoder log file. Returns None if offline."""
    try:
        params: dict[str, Any] = {"mode": mode, "lines": lines}
        if level:
            params["level"] = level
        if search:
            params["search"] = search
        resp = await get_client().get(
            f"/logs/{filename}/structured", params=params
        )
        resp.raise_for_status()
        return resp.json()
    except (httpx.HTTPError, httpx.ConnectError, RuntimeError, OSError):
        return None


async def restart_transcoder() -> dict[str, Any] | None:
    """Restart the transcoder service. Returns None if unreachable."""
    try:
        resp = await get_client().post("/system/restart")
        if resp.is_success:
            return resp.json()
        return {"success": False, "error": f"Transcoder returned HTTP {resp.status_code}"}
    except (httpx.ConnectError, httpx.TimeoutException, RuntimeError, OSError):
        return None
