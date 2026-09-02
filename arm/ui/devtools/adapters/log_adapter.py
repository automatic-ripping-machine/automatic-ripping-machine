"""
Adapter for ARM log file access.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from config import config as cfg


def _log_root() -> Path:
    """
    Return the configured ARM log directory.

    Returns:
        Path: the LOGPATH directory from arm.yaml
    """
    return Path(cfg.arm_config.get("LOGPATH", "/home/arm/logs/")).expanduser()


def list_log_files() -> list[dict[str, Any]]:
    """
    List log files under LOGPATH, newest first.

    Returns:
        list: dicts of name, path, size and mtime
    """
    files = []
    for path in sorted(_log_root().glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True):
        files.append({
            "name": path.name,
            "path": str(path),
            "size": path.stat().st_size,
            "mtime": path.stat().st_mtime,
        })
    return files


def resolve_log_file(source: str | None = None) -> Path | None:
    """
    Resolve a named log file, or the newest log when source is None.

    Args:
        source: name of a log file under LOGPATH

    Returns:
        Path: the log file, or None when no log files exist
    """
    if source:
        candidate = (_log_root() / source).expanduser()
        return candidate if candidate.is_file() else None
    files = list(_log_root().glob("*.log"))
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def read_recent_lines(limit: int = 100, source: str | None = None) -> tuple[str | None, list[str]]:
    """
    Read the most recent lines of a log file.

    Args:
        limit: max lines to return
        source: name of a log file under LOGPATH, or None for the newest

    Returns:
        tuple: (resolved log file name, list of lines oldest first)
    """
    log_file = resolve_log_file(source)
    if log_file is None:
        return None, []
    with log_file.open("r", errors="replace") as fh:
        lines = fh.readlines()
    return log_file.name, lines[-limit:]
