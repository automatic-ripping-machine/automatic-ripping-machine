"""
Adapter for ARM state queries.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import config as cfg

from ui.devtools.serializer import serialize_model

# Curated allowlist of arm.yaml keys safe to expose to tooling
_SAFE_CONFIG_KEYS = {
    "ABCDE_CONFIG_FILE", "ALLOW_DUPLICATES", "ARM_CHECK_UDF", "ARM_NAME", "AUTO_EJECT",
    "CHMOD_VALUE", "CHOWN_GROUP", "CHOWN_USER", "COMPLETED_PATH", "DATA_RIP_PARAMETERS",
    "DATE_FORMAT", "DELRAWFILES", "DEST_EXT", "DISABLE_LOGIN", "ENABLE_DEVTOOLS",
    "EMBY_REFRESH", "EXTRAS_SUB", "GET_AUDIO_TITLE", "GET_VIDEO_TITLE", "HANDBRAKE_CLI",
    "HANDBRAKE_LOCAL", "HB_ARGS_BD", "HB_ARGS_DVD", "HB_PRESET_BD", "HB_PRESET_DVD",
    "INSTALLPATH", "JSON_URL", "LOGLEVEL", "LOGLIFE", "LOGPATH", "MAINFEATURE",
    "MANUAL_WAIT", "MANUAL_WAIT_TIME", "MAX_CONCURRENT_TRANSCODES", "MAXLENGTH",
    "METADATA_PROVIDER", "MINLENGTH", "MKV_ARGS", "NOTIFY_JOBID", "NOTIFY_RIP",
    "NOTIFY_TRANSCODE", "RAW_PATH", "RIPMETHOD", "RIPMETHOD_BR", "RIPMETHOD_DVD",
    "RIP_POSTER", "SET_MEDIA_OWNER", "SET_MEDIA_PERMISSIONS", "SKIP_TRANSCODE",
    "TRANSCODE_PATH", "UI_BASE_URL", "UMASK", "UNIDENTIFIED_EJECT", "VIDEOTYPE",
    "WEBSERVER_IP", "WEBSERVER_PORT",
}


def get_jobs_summary(limit: int = 25) -> dict[str, Any]:
    """
    Summarise the most recent jobs plus status counts.

    Args:
        limit: max detailed jobs to return

    Returns:
        dict: status_counts, total and detailed job list
    """
    from models.job import Job
    from sqlalchemy import func

    jobs = Job.query.order_by(Job.job_id.desc()).limit(limit).all()
    status_counts = {
        str(status): count for status, count in Job.query.with_entities(Job.status, func.count()).group_by(Job.status).all()
    }
    return {
        "status_counts": status_counts,
        "total": sum(status_counts.values()),
        "jobs": [serialize_model(job) for job in jobs],
    }


def get_drive_state_summary() -> list[dict[str, Any]]:
    """
    List optical drives and their current and previous jobs.

    Returns:
        list: serialized drive rows with job references
    """
    from models.system_drives import SystemDrives

    drives = []
    for drive in SystemDrives.query.all():
        data = serialize_model(drive)
        data.pop("job_current", None)
        data.pop("job_previous", None)
        if drive.job_current:
            data["job_current"] = {
                "job_id": drive.job_current.job_id,
                "title": drive.job_current.title,
                "status": drive.job_current.status,
            }
        if drive.job_previous:
            data["job_previous"] = {
                "job_id": drive.job_previous.job_id,
                "title": drive.job_previous.title,
                "status": drive.job_previous.status,
            }
        drives.append(data)
    return drives


def get_service_health() -> dict[str, Any]:
    """
    Report health of registered ARM services.

    v3 keeps one SystemInfo row per service (ui and ripper); a service
    is stale when its last update is older than 5 minutes.

    Returns:
        dict: db status and per-service rows with a stale flag
    """
    from models.system_info import SystemInfo

    services = []
    for row in SystemInfo.query.all():
        data = serialize_model(row)
        stale = True
        if row.last_update_time:
            stale = (datetime.now(timezone.utc) - row.last_update_time.astimezone(timezone.utc)).total_seconds() > 300
        data["stale"] = stale
        services.append(data)
    return {"db": "connected", "services": services}


def get_warning_summary() -> list[str]:
    """
    Return non-fatal warnings about the ARM setup.

    Returns:
        list: warning strings
    """
    warnings = []
    if cfg.arm_config.get("DISABLE_LOGIN", False):
        warnings.append("login_disabled")
    logpath = cfg.arm_config.get("LOGPATH")
    if not logpath or not Path(logpath).expanduser().is_dir():
        warnings.append("logpath_missing_or_unreadable")
    return warnings


def get_safe_config_summary() -> dict[str, Any]:
    """
    Return the curated allowlist of non-secret arm.yaml settings.

    Returns:
        dict: key/value pairs from _SAFE_CONFIG_KEYS present in arm.yaml
    """
    return {key: cfg.arm_config.get(key) for key in sorted(_SAFE_CONFIG_KEYS) if key in cfg.arm_config}
