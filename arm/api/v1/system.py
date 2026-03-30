"""API v1 — System endpoints."""
import os
import platform
import subprocess

import psutil
from fastapi import APIRouter
from fastapi.responses import JSONResponse

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
def restart():
    """Restart the ARM UI service."""
    return svc_jobs.restart_ui()


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


@router.get('/system/version')
def get_version():
    """Return ARM, MakeMKV, and database versions."""
    import re
    import sqlite3
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    arm_version = "unknown"
    install_path = cfg.arm_config.get("INSTALLPATH", "")
    version_file = os.path.join(install_path, "VERSION")
    try:
        with open(version_file) as f:
            arm_version = f.read().strip()
    except OSError:
        pass

    makemkv_version = "unknown"
    try:
        result = subprocess.run(
            ["makemkvcon", "-r", "info", "dev:/dev/null"],
            capture_output=True, text=True, timeout=10
        )
        m = re.search(r'MakeMKV v([\d.]+)', result.stdout + result.stderr)
        if m:
            makemkv_version = m.group(1)
    except Exception:
        pass

    # Database Alembic revision
    db_version = "unknown"
    db_head = "unknown"
    db_file = cfg.arm_config.get("DBFILE", "")
    mig_dir = os.path.join(install_path, "arm", "migrations")
    try:
        config = Config()
        config.set_main_option("script_location", mig_dir)
        script = ScriptDirectory.from_config(config)
        db_head = script.get_current_head() or "unknown"
    except Exception:
        pass
    if db_file and os.path.isfile(db_file):
        try:
            conn = sqlite3.connect(db_file)
            c = conn.cursor()
            c.execute('SELECT version_num FROM alembic_version')
            row = c.fetchone()
            if row:
                db_version = row[0]
            conn.close()
        except Exception:
            pass

    return {
        "arm_version": arm_version,
        "makemkv_version": makemkv_version,
        "db_version": db_version,
        "db_head": db_head,
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


from arm.ripper.makemkv import prep_mkv


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


@router.post('/system/makemkv-key-check')
def check_makemkv_key():
    """Run prep_mkv() to validate/update the MakeMKV key."""
    from arm.ripper.makemkv import UpdateKeyRunTimeError, UpdateKeyErrorCodes

    message = "MakeMKV key is valid"
    try:
        prep_mkv()
    except UpdateKeyRunTimeError as exc:
        code = UpdateKeyErrorCodes(exc.returncode)
        messages = {
            UpdateKeyErrorCodes.URL_ERROR: (
                "Could not reach forum.makemkv.com — set MAKEMKV_PERMA_KEY "
                "in arm.yaml to use a purchased key"
            ),
            UpdateKeyErrorCodes.PARSE_ERROR: "MakeMKV settings file is corrupt",
            UpdateKeyErrorCodes.INTERNAL_ERROR: "Key update script produced invalid output",
            UpdateKeyErrorCodes.INVALID_MAKEMKV_SERIAL: (
                "Invalid MakeMKV serial key format — should match M-XXXX-..."
            ),
        }
        message = messages.get(code, f"Key update failed (error {code.name})")

    state = AppState.get()
    return {
        "key_valid": state.makemkv_key_valid,
        "checked_at": (
            state.makemkv_key_checked_at.isoformat()
            if state.makemkv_key_checked_at else None
        ),
        "message": message,
    }


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
