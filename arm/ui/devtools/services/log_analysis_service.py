"""
Devtools service - log filtering, search, stats and exception extraction.

Ported from the v2 armm_devtools log tools (log_filter_service,
log_stats_service) and adapted to v3's plain-text log format via the shared
parser in log_service.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from ui.devtools.adapters import log_adapter
from ui.devtools.services.log_service import parse_log_line

_MAX_ENTRIES = 500
_MAX_SCAN = 2000


def _read(limit: int) -> tuple[str | None, list[str]]:
    """Read up to *limit* recent log lines."""
    return log_adapter.read_recent_lines(limit=limit, source=None)


def _level_set(levels: list[str] | None) -> set[str] | None:
    return {lvl.upper() for lvl in levels} if levels else None


def get_logs_for_job(job_id: int, limit: int = 200, levels: list[str] | None = None) -> dict[str, Any]:
    """
    Return recent log entries that mention one job, optionally by level.

    v3 logs are plain text with no structured job field, so matching is a
    substring search for the job id in the message.

    Args:
        job_id: the job whose log lines to find
        limit: max entries (capped at 500)
        levels: optional levels to keep, e.g. ["ERROR", "WARNING"]

    Returns:
        dict: job_id, matched count, levels_filter and entries
    """
    limit = min(limit, _MAX_ENTRIES)
    level_set = _level_set(levels)
    needle = str(job_id)

    _, lines = _read(min(limit * 5, _MAX_SCAN))
    entries = []
    for line in lines:
        parsed = parse_log_line(line)
        if parsed is None:
            continue
        message = parsed.get("message") or ""
        if needle not in message:
            continue
        level = (parsed.get("level") or "").upper()
        if level_set and (not level or level not in level_set):
            continue
        entries.append(
            {
                "ts": parsed.get("ts"),
                "level": parsed.get("level"),
                "where": parsed.get("where"),
                "message": message,
            }
        )
        if len(entries) >= limit:
            break

    return {
        "job_id": job_id,
        "matched": len(entries),
        "levels_filter": levels,
        "entries": entries,
    }


def search_logs(query: str, limit: int = 100, levels: list[str] | None = None) -> dict[str, Any]:
    """
    Full-text search across recent log lines (case-insensitive substring).

    Args:
        query: text to search for in log messages
        limit: max entries (capped at 500)
        levels: optional levels to keep, e.g. ["ERROR"]

    Returns:
        dict: query, matched count, levels_filter and entries
    """
    limit = min(limit, _MAX_ENTRIES)
    level_set = _level_set(levels)
    needle = query.lower()

    _, lines = _read(min(limit * 5, _MAX_SCAN))
    entries = []
    for line in lines:
        parsed = parse_log_line(line)
        if parsed is None:
            continue
        message = parsed.get("message") or ""
        if needle not in message.lower():
            continue
        level = (parsed.get("level") or "").upper()
        if level_set and (not level or level not in level_set):
            continue
        entries.append(
            {
                "ts": parsed.get("ts"),
                "level": parsed.get("level"),
                "where": parsed.get("where"),
                "message": message,
            }
        )
        if len(entries) >= limit:
            break

    return {
        "query": query,
        "matched": len(entries),
        "levels_filter": levels,
        "entries": entries,
    }


def get_log_stats(lines_to_scan: int = 1000) -> dict[str, Any]:
    """
    Summarise recent log activity: level counts plus the newest errors.

    Args:
        lines_to_scan: how many recent lines to analyse (capped at 5000)

    Returns:
        dict: lines scanned/parsed, counts by level, recent errors/criticals,
        error rate
    """
    lines_to_scan = min(lines_to_scan, 5000)
    _, lines = _read(lines_to_scan)

    counts: Counter[str] = Counter()
    errors: list[dict[str, Any]] = []
    criticals: list[dict[str, Any]] = []
    unparsed = 0

    for line in lines:
        parsed = parse_log_line(line)
        if parsed is None:
            unparsed += 1
            continue
        level = parsed.get("level")
        if not level:
            unparsed += 1
            continue
        counts[level] += 1
        entry = {
            "ts": parsed.get("ts"),
            "message": parsed.get("message"),
            "where": parsed.get("where"),
        }
        if level == "ERROR" and len(errors) < 10:
            errors.append(entry)
        elif level == "CRITICAL" and len(criticals) < 10:
            criticals.append(entry)

    total_parsed = sum(counts.values())
    return {
        "lines_scanned": len(lines),
        "lines_parsed": total_parsed,
        "lines_unparsed": unparsed,
        "counts_by_level": dict(counts),
        "recent_errors": errors,
        "recent_criticals": criticals,
        "error_rate_pct": round(counts.get("ERROR", 0) / total_parsed * 100, 1) if total_parsed > 0 else 0,
    }


def get_recent_exceptions(limit: int = 20) -> dict[str, Any]:
    """
    Extract Python traceback blocks from recent logs.

    Traceback lines are raw (unparsed) in v3 logs; a parsed line whose message
    starts with "Traceback" opens a block and indented raw lines continue it.

    Args:
        limit: max exception blocks (capped at 100)

    Returns:
        dict: found count and exceptions list (ts, message, lines)
    """
    limit = min(limit, 100)
    _, lines = _read(_MAX_SCAN)

    exceptions: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    def flush() -> None:
        nonlocal current
        if current is not None:
            exceptions.append(current)
        current = None

    for line in lines:
        parsed = parse_log_line(line)
        if parsed is not None:
            message = parsed.get("message") or ""
            if "Traceback" in message:
                flush()
                current = {"ts": parsed.get("ts"), "message": message, "lines": [line.strip()]}
            elif current is not None:
                if (parsed.get("level") or "").upper() in ("ERROR", "CRITICAL") or "Error" in message:
                    current.setdefault("final", message)
                    current["lines"].append(line.strip())
                else:
                    flush()
        elif current is not None:
            stripped = line.strip()
            if stripped:
                current["lines"].append(stripped)
        if len(exceptions) >= limit:
            break

    flush()
    exceptions = exceptions[:limit]
    return {"found": len(exceptions), "exceptions": exceptions}
