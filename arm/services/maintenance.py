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


def _resolve_within(name: str, root: Path) -> Path | None:
    """Resolve a filename safely within a root directory.

    Only the basename is used — any directory components in *name* are
    stripped to prevent path traversal.  Returns the resolved path if it
    lives within *root*, or None otherwise.
    """
    try:
        safe_name = Path(name).name  # strip directory components
        if not safe_name or safe_name in ('.', '..'):
            return None
        resolved = (root / safe_name).resolve()
        root_resolved = root.resolve()
        if resolved.is_relative_to(root_resolved):
            return resolved
    except (ValueError, OSError):
        pass
    return None


def delete_log(path_str: str) -> dict[str, Any]:
    """Delete a single log file. Only the filename is used; it must exist within LOGPATH."""
    log_root = Path(cfg.arm_config["LOGPATH"])
    resolved = _resolve_within(path_str, log_root)

    if resolved is None:
        return {"success": False, "path": path_str, "error": "Path outside allowed root"}

    if not resolved.is_file():
        return {"success": False, "path": path_str, "error": "File not found"}

    try:
        resolved.unlink()
        return {"success": True, "path": path_str}
    except OSError as exc:
        log.error("Failed to delete log %s: %s", path_str, exc)
        return {"success": False, "path": path_str, "error": "Failed to delete file"}


def delete_folder(path_str: str) -> dict[str, Any]:
    """Delete a single folder. Only the folder name is used; it must exist within RAW_PATH or COMPLETED_PATH."""
    allowed_roots = [
        Path(cfg.arm_config.get("RAW_PATH", "")),
        Path(cfg.arm_config.get("COMPLETED_PATH", "")),
    ]

    resolved = None
    for root in allowed_roots:
        resolved = _resolve_within(path_str, root)
        if resolved is not None:
            break

    if resolved is None:
        return {"success": False, "path": path_str, "error": "Path outside allowed roots"}

    if not resolved.is_dir():
        return {"success": False, "path": path_str, "error": "Directory not found"}

    try:
        shutil.rmtree(resolved)
        return {"success": True, "path": path_str}
    except OSError as exc:
        log.error("Failed to delete folder %s: %s", path_str, exc)
        return {"success": False, "path": path_str, "error": "Failed to delete directory"}


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


def clear_raw_directories() -> dict[str, Any]:
    """Clear all contents of the raw/scratch directory.

    Removes all files and subdirectories within RAW_PATH but keeps the
    directory itself.  Returns count of items removed and bytes freed.
    """
    raw_path = Path(cfg.arm_config.get("RAW_PATH", ""))
    if not raw_path.is_dir():
        return {"success": False, "error": "RAW_PATH not configured or does not exist"}

    cleared = 0
    freed_bytes = 0
    errors = []

    for item in raw_path.iterdir():
        try:
            if item.is_file() or item.is_symlink():
                freed_bytes += item.stat().st_size
                item.unlink()
                cleared += 1
            elif item.is_dir():
                dir_size = sum(f.stat().st_size for f in item.rglob('*') if f.is_file())
                shutil.rmtree(item)
                freed_bytes += dir_size
                cleared += 1
        except OSError as exc:
            log.error("Failed to remove %s: %s", item.name, exc)
            errors.append(item.name)

    return {
        "success": True,
        "cleared": cleared,
        "freed_bytes": freed_bytes,
        "errors": errors,
        "path": str(raw_path),
    }
