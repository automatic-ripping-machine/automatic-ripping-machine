"""
Devtools service - ARM log reading and parsing.
"""
from __future__ import annotations

import re
from typing import Any

from ui.devtools.adapters import log_adapter

# ARM logs are plain text:
#   UI:     [%(asctime)s] %(levelname)s ARM: %(module)s.%(funcName)s %(message)s
#   Ripper: [%(asctime)s] %(levelname)s ARM: %(message)s
_LOG_LINE = re.compile(r"^\[(?P<ts>[^\]]+)\]\s+(?P<level>\w+)\s+ARM:\s+(?:(?P<where>[\w.]+\.\w+)\s+)?(?P<message>.*)$")


def parse_log_line(line: str) -> dict[str, Any] | None:
    """
    Parse one ARM plain-text log line.

    Args:
        line: a single log line

    Returns:
        dict: ts, level, where (optional), message - or None when unparseable
    """
    match = _LOG_LINE.match(line.strip())
    if not match:
        return None
    return {key: value for key, value in match.groupdict().items()}


def get_recent_logs(limit: int = 100, source: str | None = None, since: str | None = None) -> dict[str, Any]:
    """
    Return recent ARM log lines.

    Args:
        limit: max lines to return (default 100)
        source: name of a log file under LOGPATH, or None for the newest
        since: only return entries after this timestamp

    Returns:
        dict: logfile name, parsed entries, unparsed count and file list
    """
    limit = min(max(int(limit), 1), 1000)
    logfile, lines = log_adapter.read_recent_lines(limit=limit, source=source)
    entries = []
    unparsed = 0
    for line in lines:
        parsed = parse_log_line(line)
        if parsed is None:
            unparsed += 1
            parsed = {"raw": line.strip()}
        if since and parsed.get("ts", "") <= since:
            continue
        entries.append(parsed)
    return {
        "logfile": logfile,
        "entries": entries,
        "unparsed": unparsed,
        "files": log_adapter.list_log_files(),
    }
