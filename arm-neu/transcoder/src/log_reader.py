"""Log file reader service for the transcoder."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from config import settings


def _log_dir() -> Path:
    return Path(settings.log_path)


def list_logs() -> list[dict]:
    """List all log files in the log directory, newest first."""
    log_dir = _log_dir()
    if not log_dir.is_dir():
        return []

    logs = []
    for entry in sorted(log_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not entry.is_file():
            continue
        # Include .log files and rotated files (e.g. transcoder.log.1)
        if entry.suffix == ".log" or ".log." in entry.name:
            stat = entry.stat()
            logs.append({
                "filename": entry.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
            })
    return logs


def read_log(
    filename: str,
    mode: str = "tail",
    lines: int = 100,
) -> dict | None:
    """Read a log file. Mode is 'tail' (last N lines) or 'full'."""
    log_path = _log_dir() / filename

    # Prevent path traversal
    try:
        log_path = log_path.resolve()
        if not str(log_path).startswith(str(_log_dir().resolve())):
            return None
    except (OSError, ValueError):
        return None

    if not log_path.is_file():
        return None

    try:
        with open(log_path, "r", errors="replace") as f:
            if mode == "full":
                content = f.read()
                line_count = content.count("\n")
            else:
                all_lines = f.readlines()
                tail = all_lines[-lines:] if len(all_lines) > lines else all_lines
                content = "".join(tail)
                line_count = len(tail)
    except OSError:
        return None

    return {
        "filename": filename,
        "content": content,
        "lines": line_count,
    }


def _parse_log_line(line: str) -> dict:
    """Parse a single log line, expecting JSON from structlog."""
    line = line.rstrip("\n")
    try:
        parsed = json.loads(line)
        return {
            "timestamp": parsed.get("timestamp", ""),
            "level": parsed.get("level", "info"),
            "logger": parsed.get("logger", ""),
            "event": parsed.get("event", ""),
            "job_id": parsed.get("job_id"),
            "label": parsed.get("label"),
            "raw": line,
        }
    except (json.JSONDecodeError, TypeError):
        return {
            "timestamp": "",
            "level": "info",
            "logger": "",
            "event": line,
            "job_id": None,
            "label": None,
            "raw": line,
        }


def read_structured_log(
    filename: str,
    mode: str = "tail",
    lines: int = 100,
    level: str | None = None,
    search: str | None = None,
) -> dict | None:
    """Read and parse a structured (JSON lines) log file."""
    raw = read_log(filename, mode=mode, lines=lines)
    if raw is None:
        return None
    entries = [_parse_log_line(l) for l in raw["content"].splitlines() if l.strip()]
    if level:
        entries = [e for e in entries if e["level"] == level.lower()]
    if search:
        search_lower = search.lower()
        entries = [e for e in entries if search_lower in e["event"].lower()]
    return {"filename": filename, "entries": entries, "lines": len(entries)}
