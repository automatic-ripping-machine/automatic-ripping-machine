"""
Devtools service - bug finding: DB integrity, job consistency and route health.
"""
from __future__ import annotations

from typing import Any

from flask import current_app
from sqlalchemy import text

from models.db_setup import db


def check_db_integrity() -> dict[str, Any]:
    """
    Run MySQL CHECK TABLE against every ARM table.

    Returns:
        dict: per-table check results
    """
    tables = {}
    for name in ("alembic_version", "config", "job", "notifications", "system_drives",
                 "system_info", "track", "ui_settings", "user"):
        try:
            rows = db.session.execute(text(f"CHECK TABLE `{name}`")).fetchall()
            tables[name] = [{"type": row[2], "text": row[3]} for row in rows]
        except Exception as error:  # noqa: BLE001 - per-table failures are the report
            tables[name] = [{"type": "error", "text": str(error)}]
    healthy = all(
        all(entry["type"] == "status" for entry in result)
        for result in tables.values()
    )
    return {"tables": tables, "healthy": healthy}


def check_job_consistency() -> dict[str, Any]:
    """
    Heuristic consistency checks over the job tables.

    Returns:
        dict: findings list
    """
    import psutil

    from models.config import Config
    from models.job import Job
    from models.system_drives import SystemDrives

    findings = []

    # Active jobs whose pid is no longer alive
    for job in Job.query.filter(Job.status.in_(["active", "ripping"])).all():
        if job.pid and not psutil.pid_exists(int(job.pid)):
            findings.append({"job_id": job.job_id, "check": "pid_not_alive",
                             "detail": f"status={job.status} pid={job.pid}"})

    # Jobs with titles recorded but no tracks
    for job in Job.query.filter(Job.no_of_titles > 0).all():
        if job.video_type in ("movie", "series") and job.tracks.count() == 0:
            findings.append({"job_id": job.job_id, "check": "no_tracks",
                             "detail": f"no_of_titles={job.no_of_titles} tracks=0"})

    # Config rows whose job no longer exists
    job_ids = {job_id for (job_id,) in Job.query.with_entities(Job.job_id).all()}
    for config in Config.query.all():
        if config.job_id not in job_ids:
            findings.append({"job_id": config.job_id, "check": "orphaned_config",
                             "detail": f"config_id={config.CONFIG_ID}"})

    # Active jobs not referenced as current by any drive
    active_ids = {job.job_id for job in Job.query.filter(Job.status.in_(["active", "ripping"])).all()}
    referenced_ids = {drive.job_id_current for drive in SystemDrives.query.all() if drive.job_id_current}
    for job_id in sorted(active_ids - referenced_ids):
        findings.append({"job_id": job_id, "check": "active_job_no_drive",
                         "detail": "no system_drives row references this job as current"})

    return {"findings": findings, "count": len(findings), "healthy": not findings}


def check_route_health() -> dict[str, Any]:
    """
    GET every parameterless route through the test client and report non-2xx.

    Returns:
        dict: healthy and failing routes
    """
    from ui.devtools.adapters import route_adapter

    failing = []
    checked = 0
    for rule in sorted(current_app.url_map.iter_rules(), key=lambda r: r.rule):
        if "<" in rule.rule or "GET" not in (rule.methods or ()) or rule.endpoint.startswith("static"):
            continue
        if rule.rule.startswith("/__devtools"):
            continue
        try:
            rendered = route_adapter.fetch_path(rule.rule, follow_redirects=False)
            checked += 1
            if rendered["status_code"] >= 400:
                failing.append({"path": rule.rule, "status_code": rendered["status_code"],
                                "endpoint": rendered["endpoint"]})
        except Exception as error:  # noqa: BLE001 - failures are the report
            failing.append({"path": rule.rule, "status_code": None, "endpoint": rule.endpoint,
                            "error": str(error)})
    return {"checked": checked, "failing": failing, "healthy": not failing}


def run_type_check() -> dict[str, Any]:
    """
    Run pyright against the UI package when installed.

    Returns:
        dict: type-check result or an install hint
    """
    from ui.devtools.services import exec_service

    result = exec_service._run_subprocess(["pyright", "arm/ui"], timeout=600)
    result["command"] = "pyright arm/ui"
    if result["returncode"] == -1 and "No such file" in result.get("stderr", ""):
        result["error"] = "pyright not installed - run: pip3 install pyright"
    return result
