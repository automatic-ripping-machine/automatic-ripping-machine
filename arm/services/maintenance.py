"""Maintenance service — orphan detection and filesystem cleanup."""
from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Any

import arm.config.config as cfg
from arm.database import db
from arm.models.job import Job

log = logging.getLogger(__name__)


def get_orphan_logs() -> dict[str, Any]:
    """Find log files not referenced by any job.

    Scans LOGPATH for *.log files and cross-references against Job.logfile.
    Returns dict with root, total_size_bytes, and files list.
    """
    log_path = Path(cfg.arm_config["LOGPATH"])
    if not log_path.is_dir():
        return {"root": str(log_path), "total_size_bytes": 0, "files": []}

    # Get all logfile references from jobs
    referenced = set()
    for (logfile,) in db.session.query(Job.logfile).filter(Job.logfile.isnot(None)).all():
        referenced.add(logfile)

    orphans = []
    total_size = 0
    for f in sorted(log_path.glob("*.log")):
        if f.name not in referenced:
            size = f.stat().st_size
            orphans.append({
                "path": str(f),
                "relative_path": f.name,
                "size_bytes": size,
            })
            total_size += size

    return {"root": str(log_path), "total_size_bytes": total_size, "files": orphans}


def _dir_size(path: Path) -> int:
    """Compute total size of all files in a directory tree."""
    total = 0
    try:
        for entry in os.scandir(path):
            if entry.is_file(follow_symlinks=False):
                total += entry.stat().st_size
            elif entry.is_dir(follow_symlinks=False):
                total += _dir_size(Path(entry.path))
    except PermissionError:
        pass
    return total


def _get_job_references() -> set[str]:
    """Collect all folder name references from jobs (title, label, raw_path basename)."""
    refs: set[str] = set()
    rows = db.session.query(Job.title, Job.label, Job.raw_path, Job.path).all()
    for title, label, raw_path, path in rows:
        if title:
            refs.add(title)
        if label:
            refs.add(label)
        if raw_path:
            refs.add(Path(raw_path).name)
        if path:
            refs.add(Path(path).name)
    return refs


def get_orphan_folders() -> dict[str, Any]:
    """Find folders in RAW_PATH and COMPLETED_PATH not referenced by any job.

    Cross-references directory names against Job.title, Job.label,
    Job.raw_path basename, and Job.path basename.
    """
    raw_path = Path(cfg.arm_config.get("RAW_PATH", ""))
    completed_path = Path(cfg.arm_config.get("COMPLETED_PATH", ""))

    refs = _get_job_references()

    orphans = []
    total_size = 0

    def _scan_dir(root: Path, category: str):
        nonlocal total_size
        if not root.is_dir():
            return
        for entry in sorted(root.iterdir()):
            if entry.is_dir() and entry.name not in refs:
                size = _dir_size(entry)
                orphans.append({
                    "path": str(entry),
                    "name": entry.name,
                    "category": category,
                    "size_bytes": size,
                })
                total_size += size

    _scan_dir(raw_path, "raw")
    # Scan completed subdirectories (completed/movies/, completed/series/, etc.)
    if completed_path.is_dir():
        for subdir in completed_path.iterdir():
            if subdir.is_dir():
                _scan_dir(subdir, "completed")

    return {"total_size_bytes": total_size, "folders": orphans}


def get_counts() -> dict[str, int]:
    """Return orphan counts for summary display."""
    logs = get_orphan_logs()
    folders = get_orphan_folders()
    return {
        "orphan_logs": len(logs["files"]),
        "orphan_folders": len(folders["folders"]),
    }


def _is_path_within(path: Path, root: Path) -> bool:
    """Check if path is contained within root after resolving symlinks."""
    try:
        resolved = path.resolve()
        root_resolved = root.resolve()
        return resolved.is_relative_to(root_resolved)
    except (ValueError, OSError):
        return False


def delete_log(path_str: str) -> dict[str, Any]:
    """Delete a single log file. Path must be within LOGPATH."""
    target = Path(path_str)
    log_root = Path(cfg.arm_config["LOGPATH"])

    if not _is_path_within(target, log_root):
        return {"success": False, "path": path_str, "error": "Path outside allowed root"}

    resolved = target.resolve()
    if not resolved.is_file():
        return {"success": False, "path": path_str, "error": "File not found"}

    try:
        resolved.unlink()
        return {"success": True, "path": path_str}
    except OSError as exc:
        return {"success": False, "path": path_str, "error": str(exc)}


def delete_folder(path_str: str) -> dict[str, Any]:
    """Delete a single folder. Path must be within RAW_PATH or COMPLETED_PATH."""
    target = Path(path_str)
    allowed_roots = [
        Path(cfg.arm_config.get("RAW_PATH", "")),
        Path(cfg.arm_config.get("COMPLETED_PATH", "")),
    ]

    if not any(_is_path_within(target, root) for root in allowed_roots):
        return {"success": False, "path": path_str, "error": "Path outside allowed roots"}

    resolved = target.resolve()
    if not resolved.is_dir():
        return {"success": False, "path": path_str, "error": "Directory not found"}

    try:
        shutil.rmtree(resolved)
        return {"success": True, "path": path_str}
    except OSError as exc:
        return {"success": False, "path": path_str, "error": str(exc)}


def bulk_delete_logs(paths: list[str]) -> dict[str, Any]:
    """Delete multiple log files. Best-effort — continues on failures."""
    removed = []
    errors = []
    for p in paths:
        result = delete_log(p)
        if result["success"]:
            removed.append(p)
        else:
            errors.append(f"{Path(p).name}: {result.get('error', 'unknown')}")
    return {"removed": removed, "errors": errors}


def bulk_delete_folders(paths: list[str]) -> dict[str, Any]:
    """Delete multiple folders. Best-effort — continues on failures."""
    removed = []
    errors = []
    for p in paths:
        result = delete_folder(p)
        if result["success"]:
            removed.append(p)
        else:
            errors.append(f"{Path(p).name}: {result.get('error', 'unknown')}")
    return {"removed": removed, "errors": errors}
