"""API v1 — System endpoints."""
import os
import platform
import subprocess

import psutil
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, inspect, text

import arm.config.config as cfg
from arm.database import db
from arm.models.app_state import AppState
from arm.services import jobs as svc_jobs

router = APIRouter(prefix="/api/v1", tags=["system"])


def _detect_cpu() -> str:
    """Detect CPU model name from /proc/cpuinfo (Linux) or platform fallback."""
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "Unknown"


@router.get('/system/info')
def get_system_info():
    """Return static hardware identity (CPU model, total RAM). No DB access."""
    mem = psutil.virtual_memory()
    return {
        "cpu": _detect_cpu(),
        "memory_total_gb": round(mem.total / 1073741824, 1),
    }


@router.post('/system/restart')
def restart(background_tasks: BackgroundTasks):
    """Restart the ARM ripping service.

    Schedules SIGTERM on this process as a background task so the response
    flushes first. Docker's restart policy brings the container back."""
    background_tasks.add_task(svc_jobs.schedule_self_shutdown)
    return {"success": True, "message": "ARM ripping service is restarting"}


@router.get('/system/stats')
def get_system_stats():
    """Return live system metrics: CPU, memory, and disk usage."""
    cpu_percent = psutil.cpu_percent()
    cpu_temp = 0.0
    try:
        temps = psutil.sensors_temperatures()
        for key in ('coretemp', 'cpu_thermal', 'k10temp'):
            if temps.get(key):
                cpu_temp = temps[key][0].current
                break
    except (AttributeError, OSError):
        pass

    mem = psutil.virtual_memory()
    memory = {
        "total_gb": round(mem.total / 1073741824, 1),
        "used_gb": round(mem.used / 1073741824, 1),
        "free_gb": round(mem.available / 1073741824, 1),
        "percent": mem.percent,
    }

    from arm.services.disk_usage_cache import get_disk_usage

    media_paths = [
        ("Raw", cfg.arm_config.get("RAW_PATH", "")),
        ("Transcode", cfg.arm_config.get("TRANSCODE_PATH", "")),
        ("Completed", cfg.arm_config.get("COMPLETED_PATH", "")),
    ]
    storage = []
    for name, path in media_paths:
        if not path:
            continue
        usage = get_disk_usage(path)
        if usage:
            storage.append({
                "name": name,
                "path": path,
                "total_gb": round(usage["total"] / 1073741824, 1),
                "used_gb": round(usage["used"] / 1073741824, 1),
                "free_gb": round(usage["free"] / 1073741824, 1),
                "percent": usage["percent"],
            })

    return {
        "cpu_percent": cpu_percent,
        "cpu_temp": cpu_temp,
        "memory": memory,
        "storage": storage,
    }


@router.get('/system/ripping-enabled')
def get_ripping_enabled():
    """Return whether ripping is currently enabled, plus MakeMKV key status."""
    state = AppState.get()
    return {
        "ripping_enabled": not state.ripping_paused,
        "makemkv_key_valid": state.makemkv_key_valid,
        "makemkv_key_checked_at": (
            state.makemkv_key_checked_at.isoformat()
            if state.makemkv_key_checked_at else None
        ),
    }


def _read_arm_version(install_path: str) -> str:
    """Read the VERSION file inside INSTALLPATH; return 'unknown' on any error."""
    try:
        with open(os.path.join(install_path, "VERSION")) as f:
            return f.read().strip()
    except OSError:
        return "unknown"


def _read_makemkv_version() -> str:
    """Probe makemkvcon for its version string; return 'unknown' on any error."""
    import re
    try:
        result = subprocess.run(
            ["makemkvcon", "-r", "info", "dev:/dev/null"],
            capture_output=True, text=True, timeout=10,
        )
        m = re.search(r'MakeMKV v([\d.]+)', result.stdout + result.stderr)
        return m.group(1) if m else "unknown"
    except Exception:
        return "unknown"


def _read_db_revisions(db_uri: str, install_path: str) -> tuple[str, str]:
    """Return (current_revision, head_revision), both 'unknown' on lookup failure."""
    db_head = "unknown"
    try:
        config = Config()
        config.set_main_option("script_location", os.path.join(install_path, "arm", "migrations"))
        db_head = ScriptDirectory.from_config(config).get_current_head() or "unknown"
    except Exception:
        pass

    db_version = "unknown"
    if not db_uri:
        return db_version, db_head

    # For sqlite, returning early when the file doesn't exist preserves
    # the pre-PR-A behavior where _read_db_revisions never auto-created
    # an empty DB file as a side effect of the version probe.
    # check_db_version (the boot path) handles file creation; this
    # endpoint is purely diagnostic.
    if db_uri.startswith('sqlite:///'):
        db_file = db_uri[len('sqlite:///'):]
        if db_file and not os.path.isfile(db_file):
            return db_version, db_head

    try:
        engine = create_engine(db_uri)
        try:
            if not inspect(engine).has_table('alembic_version'):
                return db_version, db_head
            with engine.connect() as conn:
                row = conn.execute(text('SELECT version_num FROM alembic_version')).fetchone()
                if row:
                    db_version = row[0]
        finally:
            engine.dispose()
    except Exception:
        pass
    return db_version, db_head


def _db_file_size(db_uri: str) -> int | None:
    """Return the SQLite file size in bytes. Returns None for non-sqlite
    DSNs (postgres etc.) where file size is meaningless, and None for
    sqlite files that don't exist or can't be read."""
    if not db_uri or not db_uri.startswith('sqlite:///'):
        return None
    db_file = db_uri[len('sqlite:///'):]
    if not os.path.isfile(db_file):
        return None
    try:
        return os.path.getsize(db_file)
    except OSError:
        return None


@router.get('/system/version')
def get_version():
    """Return ARM, MakeMKV, and database versions."""
    install_path = cfg.arm_config.get("INSTALLPATH", "")
    db_uri = cfg.get_db_uri()
    db_version, db_head = _read_db_revisions(db_uri, install_path)
    # db_path: for sqlite, return the file path (operator-friendly);
    # for other DSNs, return the URI with password masked. The endpoint
    # is unauthenticated inside the docker network and arm-ui renders
    # this verbatim on the Settings page; an unmasked DSN would leak
    # the DB password to anyone with browser access.
    if db_uri.startswith('sqlite:///'):
        db_path = db_uri[len('sqlite:///'):] or None
    elif db_uri:
        from sqlalchemy.engine.url import make_url
        try:
            db_path = make_url(db_uri).render_as_string(hide_password=True)
        except Exception:
            # If the URI is malformed, fall back to None rather than
            # leaking the raw string.
            db_path = None
    else:
        db_path = None

    return {
        "arm_version": _read_arm_version(install_path),
        "makemkv_version": _read_makemkv_version(),
        "db_version": db_version,
        "db_head": db_head,
        "db_path": db_path,
        "db_size_bytes": _db_file_size(db_uri),
    }


@router.get('/system/paths')
def get_paths():
    """Check existence and writability of configured ARM paths.

    Reads from the disk-usage cache to avoid blocking on stale NFS mounts.
    Falls back to direct checks only for paths not yet in the cache (e.g.
    DBFILE, LOGPATH which are local and won't stall).
    """
    from arm.services.disk_usage_cache import get_path_status, register_paths as _reg

    path_keys = [
        "RAW_PATH", "COMPLETED_PATH", "TRANSCODE_PATH",
        "LOGPATH", "DBFILE", "INSTALLPATH",
    ]
    results = []
    for key in path_keys:
        value = cfg.arm_config.get(key, "")
        if not value:
            continue
        status = get_path_status(value)
        if status:
            exists = status["exists"]
            writable = status["writable"]
        else:
            # Path not in cache yet — register it and probe (with timeout).
            # Local paths (DBFILE, LOGPATH) resolve instantly; NFS paths
            # get a 5s timeout via the subprocess probe.
            _reg([value])
            status = get_path_status(value)
            if status:
                exists = status["exists"]
                writable = status["writable"]
            else:
                exists = False
                writable = False
        results.append({
            "setting": key,
            "path": value,
            "exists": exists,
            "writable": writable,
        })
    return results


@router.post('/system/ripping-enabled')
def set_ripping_enabled(body: dict):
    """Toggle global ripping pause."""
    if 'enabled' not in body:
        return JSONResponse(
            {"success": False, "error": "'enabled' field required"},
            status_code=400,
        )

    state = AppState.get()
    state.ripping_paused = not bool(body['enabled'])
    db.session.commit()

    return {
        "success": True,
        "ripping_enabled": not state.ripping_paused,
    }


@router.post('/system/makemkv-key-check', deprecated=True)
async def check_makemkv_key():
    """Validate/update the MakeMKV key.

    .. deprecated::
        Use ``GET /api/v1/metadata/test-key?provider=makemkv`` instead.
        This endpoint is retained as an alias for one release window so
        existing arm-ui versions keep working.

    Returns the legacy ``{key_valid, checked_at, message}`` shape; the
    unified endpoint returns the cross-provider
    ``{success, message, provider, checked_at}`` shape.
    """
    from arm.services.metadata import test_configured_key

    result = await test_configured_key(override_provider="makemkv")
    # Translate to the legacy shape so existing consumers don't break
    # mid-deploy. The unified endpoint is the new path.
    return {
        "key_valid": result["success"],
        "checked_at": result["checked_at"],
        "message": result["message"],
    }


@router.post('/system/preflight')
async def preflight():
    """Run all preflight checks: API keys, MakeMKV key, path permissions."""
    from arm.services.preflight import run_checks
    return await run_checks()


@router.post('/system/preflight/fix')
async def preflight_fix(body: dict):
    """Attempt to fix specified issues, then re-run all checks."""
    from arm.services.preflight import run_fixes
    items = body.get("fix", [])
    if not isinstance(items, list):
        return JSONResponse(
            {"success": False, "error": "'fix' must be a list"},
            status_code=400,
        )
    return await run_fixes(items)


@router.get('/system/stats/jobs')
def get_job_stats():
    """Return job counts grouped by status and video type."""
    from arm.models.job import Job
    from sqlalchemy import func

    try:
        # Counts by status
        status_rows = (
            db.session.query(Job.status, func.count(Job.job_id))
            .group_by(Job.status)
            .all()
        )
        by_status = {str(status): count for status, count in status_rows}

        # Counts by video_type
        type_rows = (
            db.session.query(Job.video_type, func.count(Job.job_id))
            .filter(Job.video_type.isnot(None))
            .group_by(Job.video_type)
            .all()
        )
        by_type = {str(vtype): count for vtype, count in type_rows}

        total = sum(by_status.values())

        return {
            "by_status": by_status,
            "by_type": by_type,
            "total": total,
        }
    except Exception as e:
        log.error("Failed to get job stats: %s", e)
        return JSONResponse(
            {"error": "Failed to retrieve job statistics"},
            status_code=500,
        )
