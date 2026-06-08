"""Preflight readiness checks - API keys, MakeMKV key, path permissions.

Orchestrates all startup checks and returns a unified response for the
setup wizard and system health dashboard.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

import arm.config.config as cfg

log = logging.getLogger(__name__)

# Env var fallback map: container prefix -> env var name
_ENV_PATH_MAP: dict[str, str] = {
    "/home/arm/media": "ARM_MEDIA_PATH",
    "/etc/arm/config": "ARM_CONFIG_PATH",
    "/home/arm/logs": "ARM_LOGS_PATH",
    "/home/arm/music": "ARM_MUSIC_PATH",
}


def resolve_host_path(container_path: str) -> str | None:
    """Resolve a container path to its host-side path.

    Parses ``/proc/self/mountinfo`` to find the bind-mount source for
    *container_path*.  Falls back to env var mapping when mountinfo is
    unavailable or the path is not a direct mount point.

    Returns ``None`` when no mapping can be determined.
    """
    if not container_path:
        return None

    # Strategy 1: parse /proc/self/mountinfo for bind-mount sources
    try:
        host = _parse_mountinfo(container_path)
        if host is not None:
            return host
    except OSError:
        pass

    # Strategy 2: env var fallback
    for prefix, env_var in _ENV_PATH_MAP.items():
        if container_path == prefix or container_path.startswith(prefix + "/"):
            host_base = os.environ.get(env_var)
            if host_base:
                suffix = container_path[len(prefix):]
                return host_base + suffix
    return None


def _parse_mountinfo(container_path: str) -> str | None:
    """Search /proc/self/mountinfo for bind-mount source of *container_path*.

    Each line has the format (space-separated fields):
      mount_id parent_id major:minor root mount_point ... - fs_type source ...

    For Docker bind mounts, ``root`` (field 3) contains the host-side path
    and ``mount_point`` (field 4) is the container-side path. When ``root``
    is ``/`` the entry is a full filesystem mount (not a bind), so we skip it.
    """
    best_mount = ""
    best_root = None

    with open("/proc/self/mountinfo") as f:
        for line in f:
            parts = line.split()
            if len(parts) < 5:
                continue
            root = parts[3]
            mount_point = parts[4]

            # Skip non-bind mounts (root is "/" for full filesystem mounts)
            if root == "/":
                continue

            # Check if this mount_point is a prefix of container_path
            if container_path == mount_point or container_path.startswith(
                mount_point + "/"
            ):
                # Prefer the longest (most specific) mount point match
                if len(mount_point) > len(best_mount):
                    best_mount = mount_point
                    best_root = root

    if best_root is not None:
        suffix = container_path[len(best_mount):]
        return best_root + suffix
    return None


def check_path(
    name: str,
    path: str,
    expected_uid: int,
    expected_gid: int,
) -> dict:
    """Check a single path for existence, writability, and UID/GID ownership.

    Returns a dict with all relevant status fields.
    """
    result: dict = {
        "name": name,
        "container_path": path,
        "host_path": resolve_host_path(path),
        "exists": False,
        "writable": False,
        "owner_uid": None,
        "owner_gid": None,
        "expected_uid": expected_uid,
        "expected_gid": expected_gid,
        "match": False,
        "fixable": False,
    }

    if not path:
        return result

    try:
        st = os.stat(path)
    except OSError:
        # Path does not exist - check if parent is fixable
        result["fixable"] = _is_fixable(path)
        return result

    result["exists"] = True
    result["writable"] = os.access(path, os.W_OK)
    result["owner_uid"] = st.st_uid
    result["owner_gid"] = st.st_gid
    result["match"] = st.st_uid == expected_uid and st.st_gid == expected_gid

    if not result["match"]:
        result["fixable"] = _is_fixable(path)

    return result


def _is_fixable(path: str) -> bool:
    """Determine whether we could fix ownership on *path*.

    True when running as root, or when we own the parent directory.
    """
    if os.getuid() == 0:
        return True
    try:
        parent = str(Path(path).parent)
        parent_stat = os.stat(parent)
        return parent_stat.st_uid == os.getuid()
    except OSError:
        return False


# -------------------------------------------------------------------
# Internal check helpers
# -------------------------------------------------------------------


async def _check_omdb_key() -> dict:
    """Check the OMDB API key."""
    key = cfg.arm_config.get("OMDB_API_KEY", "")
    if not key or not str(key).strip():
        return {"name": "omdb_key", "success": False, "message": "Not configured", "fixable": False}
    from arm.services.metadata import test_configured_key
    result = await test_configured_key(override_key=str(key).strip(), override_provider="omdb")
    return {
        "name": "omdb_key",
        "success": result.get("success", False),
        "message": result.get("message", "Unknown"),
        "fixable": False,
    }


async def _check_tmdb_key() -> dict:
    """Check the TMDB API key."""
    key = cfg.arm_config.get("TMDB_API_KEY", "")
    if not key or not str(key).strip():
        return {"name": "tmdb_key", "success": False, "message": "Not configured", "fixable": False}
    from arm.services.metadata import test_configured_key
    result = await test_configured_key(override_key=str(key).strip(), override_provider="tmdb")
    return {
        "name": "tmdb_key",
        "success": result.get("success", False),
        "message": result.get("message", "Unknown"),
        "fixable": False,
    }


async def _check_tvdb_key() -> dict:
    """Check the TVDB API key."""
    key = cfg.arm_config.get("TVDB_API_KEY", "")
    if not key or not str(key).strip():
        return {"name": "tvdb_key", "success": False, "message": "Not configured", "fixable": False}
    from arm.services.tvdb import validate_tvdb_key
    result = await validate_tvdb_key(str(key).strip())
    return {
        "name": "tvdb_key",
        "success": result.get("success", False),
        "message": result.get("message", "Unknown"),
        "fixable": False,
    }


async def _check_makemkv_key() -> dict:
    """Check the MakeMKV key via prep_mkv().

    prep_mkv() spawns a blocking subprocess that hits forum.makemkv.com,
    which can stall for tens of seconds; run it in the default executor
    so the asyncio loop stays responsive for other concurrent requests.
    """
    from arm.ripper.makemkv import UpdateKeyRunTimeError, UpdateKeyErrorCodes, prep_mkv

    try:
        await asyncio.get_running_loop().run_in_executor(None, prep_mkv)
        return {
            "name": "makemkv_key",
            "success": True,
            "message": "MakeMKV key is valid",
            "fixable": True,
        }
    except UpdateKeyRunTimeError as exc:
        code = UpdateKeyErrorCodes(exc.returncode)
        messages = {
            UpdateKeyErrorCodes.URL_ERROR: (
                "Could not reach forum.makemkv.com - set MAKEMKV_PERMA_KEY "
                "in arm.yaml to use a purchased key"
            ),
            UpdateKeyErrorCodes.PARSE_ERROR: "MakeMKV settings file is corrupt",
            UpdateKeyErrorCodes.INTERNAL_ERROR: "Key update script produced invalid output",
            UpdateKeyErrorCodes.INVALID_MAKEMKV_SERIAL: (
                "Invalid MakeMKV serial key format - should match M-XXXX-..."
            ),
        }
        return {
            "name": "makemkv_key",
            "success": False,
            "message": messages.get(code, f"Key update failed (error {code.name})"),
            "fixable": True,
        }
    except Exception as exc:
        log.warning("MakeMKV key check failed unexpectedly: %s", exc)
        return {
            "name": "makemkv_key",
            "success": False,
            "message": f"Key check failed: {type(exc).__name__}",
            "fixable": True,
        }


def _get_path_checks() -> list[dict]:
    """Run ownership/permission checks on all configured paths."""
    expected_uid = os.getuid()
    expected_gid = os.getgid()

    # (name, path, require_writable)
    # TRANSCODE_PATH is mounted read-only in ARM (the transcoder owns it).
    path_entries = [
        ("RAW_PATH", cfg.arm_config.get("RAW_PATH", ""), True),
        ("COMPLETED_PATH", cfg.arm_config.get("COMPLETED_PATH", ""), True),
        ("TRANSCODE_PATH", cfg.arm_config.get("TRANSCODE_PATH", ""), False),
        ("LOGPATH", cfg.arm_config.get("LOGPATH", ""), True),
        ("DBFILE", cfg.arm_config.get("DBFILE", ""), True),
        ("ARM_CONFIG", "/etc/arm/config", True),
    ]

    results = []
    for name, path, require_writable in path_entries:
        if not path:
            continue
        entry = check_path(name, path, expected_uid, expected_gid)
        entry["require_writable"] = require_writable
        results.append(entry)
    return results


# -------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------


async def run_checks() -> dict:
    """Run all preflight checks and return a unified response.

    Returns a dict with arm_uid, arm_gid, checks (API key statuses),
    and paths (ownership/permission statuses).
    """
    checks = [
        await _check_omdb_key(),
        await _check_tmdb_key(),
        await _check_tvdb_key(),
        await _check_makemkv_key(),
    ]

    paths = _get_path_checks()

    return {
        "arm_uid": os.getuid(),
        "arm_gid": os.getgid(),
        "checks": checks,
        "paths": paths,
    }


async def run_fixes(items: list[str]) -> dict:
    """Attempt to fix specified items, then re-run all checks.

    Supported item names:
    - ``makemkv_key``: re-run prep_mkv() to fetch/update the key
    - Any path name from _get_path_checks(): attempt chown to expected UID/GID

    Returns the full run_checks() response after fixes are applied.
    """
    from arm.ripper.makemkv import prep_mkv

    expected_uid = os.getuid()
    expected_gid = os.getgid()
    path_names = {
        "RAW_PATH", "COMPLETED_PATH", "TRANSCODE_PATH",
        "LOGPATH", "DBFILE", "ARM_CONFIG",
    }

    for item in items:
        if item == "makemkv_key":
            try:
                prep_mkv()
                log.info("MakeMKV key fix: prep_mkv() succeeded")
            except Exception as exc:
                log.warning("MakeMKV key fix failed: %s", exc)

        elif item in path_names:
            # Find the actual path for this name
            path_map = {
                "RAW_PATH": cfg.arm_config.get("RAW_PATH", ""),
                "COMPLETED_PATH": cfg.arm_config.get("COMPLETED_PATH", ""),
                "TRANSCODE_PATH": cfg.arm_config.get("TRANSCODE_PATH", ""),
                "LOGPATH": cfg.arm_config.get("LOGPATH", ""),
                "DBFILE": cfg.arm_config.get("DBFILE", ""),
                "ARM_CONFIG": "/etc/arm/config",
            }
            path = path_map.get(item, "")
            if path:
                try:
                    os.chown(path, expected_uid, expected_gid)
                    log.info("Fixed ownership on %s (%s)", item, path)
                except OSError as exc:
                    log.warning("Cannot fix ownership on %s (%s): %s", item, path, exc)
        else:
            log.warning("Unknown fix item: %s", item)

    return await run_checks()
