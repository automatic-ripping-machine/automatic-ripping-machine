"""Cached disk usage with subprocess-based refresh.

NFS mounts can enter kernel D-state during large file operations, causing
``statvfs()`` to block indefinitely. This module provides cached disk usage
that refreshes in a background thread using a subprocess with a timeout.
The subprocess can be abandoned if it stalls (unlike threads, D-state
subprocesses don't block the parent process).

The API endpoint reads from the cache and never calls statvfs() directly.
"""

import json
import logging
import subprocess
import threading
import time

log = logging.getLogger(__name__)

# Cache: path -> {"total": bytes, "used": bytes, "free": bytes, "percent": float, "ts": epoch}
_cache: dict[str, dict] = {}
_cache_lock = threading.Lock()

# How long cached values are considered fresh (seconds)
CACHE_TTL = 30

# Timeout for the subprocess that calls statvfs (seconds).
# If NFS is stalled, the subprocess blocks but we abandon it after this.
SUBPROCESS_TIMEOUT = 5

# Background refresh interval (seconds)
_REFRESH_INTERVAL = 30


def get_disk_usage(path: str) -> dict | None:
    """Return cached disk usage for *path*, or None if unavailable.

    Never blocks on NFS. Returns stale data (up to CACHE_TTL + REFRESH_INTERVAL
    seconds old) if the NFS mount is unresponsive.
    """
    with _cache_lock:
        entry = _cache.get(path)
    if entry:
        return {
            "total": entry["total"],
            "used": entry["used"],
            "free": entry["free"],
            "percent": entry["percent"],
        }
    # No cached value yet - try a synchronous fetch with timeout
    _refresh_path(path)
    with _cache_lock:
        entry = _cache.get(path)
    if entry:
        return {
            "total": entry["total"],
            "used": entry["used"],
            "free": entry["free"],
            "percent": entry["percent"],
        }
    return None


def get_path_status(path: str) -> dict | None:
    """Return cached path existence/writability for *path*, or None if unavailable.

    Never blocks on NFS — reads from the same cache populated by the
    background subprocess probe.
    """
    with _cache_lock:
        entry = _cache.get(path)
    if entry and "exists" in entry:
        return {"exists": entry["exists"], "writable": entry["writable"]}
    return None


def _refresh_path(path: str):
    """Refresh disk usage and path status using a subprocess with timeout."""
    try:
        # Use a subprocess so D-state statvfs doesn't block our threads.
        # The subprocess probes existence, writability, and disk usage in one call.
        result = subprocess.run(
            [
                "python3", "-c",
                "import os, json, sys; "
                "p = sys.argv[1]; "
                "e = os.path.exists(p); "
                "w = os.access(p, os.W_OK) if e else False; "
                "d = {'exists': e, 'writable': w}; "
                "try:\n"
                "  s = os.statvfs(p); "
                "  d['total'] = s.f_frsize * s.f_blocks; "
                "  d['free'] = s.f_frsize * s.f_bavail; "
                "  d['used'] = d['total'] - (s.f_frsize * s.f_bfree); "
                "  d['percent'] = round(d['used'] / d['total'] * 100, 1) if d['total'] else 0\n"
                "except OSError:\n"
                "  pass\n"
                "json.dump(d, sys.stdout)",
                path,
            ],
            capture_output=True,
            text=True,
            timeout=SUBPROCESS_TIMEOUT,
        )
        if result.returncode == 0 and result.stdout:
            data = json.loads(result.stdout)
            data["ts"] = time.time()
            with _cache_lock:
                _cache[path] = data
    except subprocess.TimeoutExpired:
        log.debug("Disk usage subprocess timed out for %s (NFS stall?)", path)
    except (json.JSONDecodeError, OSError, ValueError) as e:
        log.debug("Disk usage refresh failed for %s: %s", path, e)


def _refresh_all():
    """Refresh all registered paths."""
    with _cache_lock:
        paths = list(_cache.keys())
    for path in paths:
        _refresh_path(path)


def register_paths(paths: list[str]):
    """Register paths to be refreshed in the background.

    Call this at startup with the media paths from arm.yaml.
    """
    with _cache_lock:
        for path in paths:
            if path and path not in _cache:
                _cache[path] = {}
    # Do an initial refresh (blocking but with timeout)
    for path in paths:
        if path:
            _refresh_path(path)


_refresh_thread: threading.Thread | None = None


def start_background_refresh():
    """Start the background refresh thread (call once at startup)."""
    global _refresh_thread
    if _refresh_thread and _refresh_thread.is_alive():
        return

    def _loop():
        while True:
            time.sleep(_REFRESH_INTERVAL)
            _refresh_all()

    _refresh_thread = threading.Thread(target=_loop, daemon=True, name="disk-usage-cache")
    _refresh_thread.start()
    log.info("Disk usage cache: background refresh started (interval=%ds, timeout=%ds)",
             _REFRESH_INTERVAL, SUBPROCESS_TIMEOUT)
