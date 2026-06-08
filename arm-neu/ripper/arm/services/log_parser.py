"""Structured log parsing - ported from arm-ui's log_reader for the v1 API."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import arm.config.config as cfg
from arm.common.path_safety import safe_join

# ARM plain text log format: "{timestamp} {logger}: {LEVEL}: {message}"
# e.g. "02-28-2026 04:59:16 ARM: INFO: Ripping complete"
# Anchor with \S at the very start to defeat the polynomial-ReDoS path
# (py/polynomial-redos): leading-space input would otherwise force the
# engine to backtrack every (.+?)\s+ split point.
_ARM_PLAIN_RE = re.compile(
    r'^(\S.{0,500}?)\s+(\w+):\s+(DEBUG|INFO|WARNING|ERROR|CRITICAL):\s*(.*)',
    re.IGNORECASE,
)

# Hard cap on per-line parsing to make the regex matchers linear under
# any input. Real ARM log lines are well under this.
_MAX_LINE_LEN = 8 * 1024

# Wrapper script format: "{weekday} {month} {day} {time} [{AM/PM}] {TZ} {year} [{logger}] {message}"
_WRAPPER_BRACKET_RE = re.compile(
    r'^(\w{3}\s+\w{3}\s+\d+\s+[\d:]+(?:\s+[AP]M)?\s+\w+\s+\d{4})\s+\[(\w+)\]\s*(.*)',
)

# ISO timestamp with bracket logger: "{YYYY-MM-DD HH:MM:SS} [{logger}] {message}"
_ISO_BRACKET_RE = re.compile(
    r'^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+\[(\w+)\]\s*(.*)',
)

# Wrapper script format without logger: "{timestamp} {message}"
_WRAPPER_PLAIN_RE = re.compile(
    r'^(\w{3}\s+\w{3}\s+\d+\s+[\d:]+(?:\s+[AP]M)?\s+\w+\s+\d{4})\s+(.*)',
)


def _log_dir() -> Path:
    return Path(cfg.arm_config["LOGPATH"])


def _resolve_within(name: str, root: Path) -> Path | None:
    """Resolve a filename safely within root, stripping any directory components.

    Log files live flat in LOGPATH, so any directory component in *name* is
    stripped before confinement. The basename is then routed through
    :func:`arm.common.path_safety.safe_join`, which resolves symlinks and
    rejects anything that escapes *root*.
    """
    try:
        safe_name = Path(name).name
        if not safe_name or safe_name in ('.', '..'):
            return None
        # safe_join raises ValueError on any path that escapes root.
        return Path(safe_join(str(root), safe_name))
    except (ValueError, OSError):
        pass
    return None


def list_logs() -> list[dict[str, Any]]:
    """List all *.log files in the ARM log directory, newest first."""
    log_dir = _log_dir()
    if not log_dir.is_dir():
        return []

    logs = []
    for entry in sorted(log_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if entry.is_file() and entry.suffix == ".log":
            stat = entry.stat()
            logs.append({
                "filename": entry.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            })
    return logs


def resolve_log_path(filename: str) -> Path | None:
    """Resolve a log filename to an absolute path under LOGPATH, or None."""
    resolved = _resolve_within(filename, _log_dir())
    if resolved is None or not resolved.is_file():
        return None
    return resolved


def delete_log(filename: str) -> bool:
    """Delete a log file. Returns True on success, False if not found."""
    log_path = resolve_log_path(filename)
    if log_path is None:
        return False
    try:
        log_path.unlink()
        return True
    except OSError:
        return False


# Cap on full-mode reads to protect the API thread pool. Active-job logs
# can grow to hundreds of MB on a long Blu-ray rip; tail mode is the
# default precisely so callers don't pull the whole thing every poll.
_FULL_MODE_MAX_BYTES = 10 * 1024 * 1024  # 10 MB


def read_log(filename: str, mode: str = "tail", lines: int = 100) -> dict | None:
    """Read a log file. Mode is 'tail' (last N lines) or 'full'."""
    log_path = resolve_log_path(filename)
    if log_path is None:
        return None

    truncated = False
    try:
        if mode == "full":
            size = log_path.stat().st_size
            if size > _FULL_MODE_MAX_BYTES:
                with open(log_path, "rb") as f:
                    f.seek(-_FULL_MODE_MAX_BYTES, 2)
                    data = f.read().decode("utf-8", errors="replace")
                # Drop the partial first line so callers don't see a fragment.
                content = data.split("\n", 1)[1] if "\n" in data else data
                truncated = True
                line_count = content.count("\n")
            else:
                with open(log_path, "r", errors="replace") as f:
                    content = f.read()
                line_count = content.count("\n")
        else:
            with open(log_path, "r", errors="replace") as f:
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
        "truncated": truncated,
    }


def _parse_log_line(line: str) -> dict:
    """Parse a single log line: JSON, ARM plain, wrapper, or ISO bracketed."""
    line = line.rstrip("\n")
    # Defence against ReDoS on adversarial log content: skip parsing on
    # absurdly long lines and just hand back the raw text. Real ARM lines
    # are short; a multi-KB line is either a stack trace or an attack.
    if len(line) > _MAX_LINE_LEN:
        return {
            "timestamp": "", "level": "info", "logger": "",
            "event": line[:_MAX_LINE_LEN] + "...",
            "job_id": None, "label": None, "raw": line,
        }
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
        pass

    m = _ARM_PLAIN_RE.match(line)
    if m:
        return {
            "timestamp": m.group(1).strip(),
            "level": m.group(3).lower(),
            "logger": m.group(2),
            "event": m.group(4),
            "job_id": None,
            "label": None,
            "raw": line,
        }

    m = _WRAPPER_BRACKET_RE.match(line)
    if m:
        return {
            "timestamp": m.group(1).strip(),
            "level": "info",
            "logger": m.group(2),
            "event": m.group(3),
            "job_id": None,
            "label": None,
            "raw": line,
        }

    m = _ISO_BRACKET_RE.match(line)
    if m:
        return {
            "timestamp": m.group(1).strip(),
            "level": "info",
            "logger": m.group(2),
            "event": m.group(3),
            "job_id": None,
            "label": None,
            "raw": line,
        }

    m = _WRAPPER_PLAIN_RE.match(line)
    if m:
        return {
            "timestamp": m.group(1).strip(),
            "level": "info",
            "logger": "wrapper",
            "event": m.group(2),
            "job_id": None,
            "label": None,
            "raw": line,
        }

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
    """Read and parse a log file with optional level + substring filter."""
    raw = read_log(filename, mode=mode, lines=lines)
    if raw is None:
        return None

    entries = [_parse_log_line(l) for l in raw["content"].splitlines() if l.strip()]

    if level:
        entries = [e for e in entries if e["level"] == level.lower()]
    if search:
        search_lower = search.lower()
        entries = [e for e in entries if search_lower in e["event"].lower()]

    return {
        "filename": filename,
        "entries": entries,
        "lines": len(entries),
        "truncated": raw.get("truncated", False),
    }
