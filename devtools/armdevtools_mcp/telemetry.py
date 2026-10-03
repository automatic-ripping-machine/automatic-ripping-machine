"""
Devtools MCP telemetry - bounded, redacted error logging.

Genuine tool failures are appended to devapi_errors.log as bounded JSON lines
with redacted arguments; the ``get_tool_errors`` tool reads them back.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ERROR_LOG = Path(__file__).parent / "devapi_errors.log"

_REDACT_KEYS = {"key", "password", "secret", "token", "perma", "api_key"}

_MAX_ERROR_ARG_CHARS = 1000
_MAX_ERROR_PAYLOAD_CHARS = 3000
_MAX_ERROR_LINE_CHARS = 4000

# Shared output caps (used by host tools and the external MCP gateway).
_MAX_RESULT_CHARS = 20000
_MAX_ERROR_CHARS = 5000


def truncate(text: str, limit: int, tail: bool = False) -> str:
    """Truncate text to *limit* chars with one shared marker."""
    if len(text) <= limit:
        return text
    cut = text[-limit:] if tail else text[:limit]
    return cut + f"... [truncated, {len(text) - limit} more chars]"


def failure(errors: str | list, **context: Any) -> dict[str, Any]:
    """The devapi failure envelope: success False, errors, plus any context."""
    payload: dict[str, Any] = {"success": False, "errors": [errors] if isinstance(errors, str) else errors}
    payload.update(context)
    return payload


def _redact(arguments: dict[str, Any]) -> dict[str, Any]:
    """Recursively mask arguments whose key looks secret."""
    result = {}
    for k, v in arguments.items():
        if any(r in k.lower() for r in _REDACT_KEYS):
            result[k] = "***"
        elif isinstance(v, dict):
            result[k] = _redact(v)
        else:
            result[k] = v
    return result


def _truncate_text(text: str, limit: int) -> str:
    return truncate(text, limit)


def _genuine_error_payload(result: Any) -> Any:
    """
    Return the error payload when a tool result indicates a genuine failure, else None.

    Tool results are the raw ``data`` payload of the API envelope - lists and
    dicts are normal successes. Only explicit failure signals qualify:
    truthy ``error``/``errors`` or ``success is False``.
    """
    if not isinstance(result, dict):
        return None
    error = result.get("error")
    if error:
        return error
    errors = result.get("errors")
    if isinstance(errors, (int, float)) and errors > 0:
        return errors
    if isinstance(errors, (list, tuple)) and len(errors) > 0:
        return errors
    if errors:  # other truthy forms
        return errors
    if result.get("success") is False:
        return result
    return None


def _log_tool_error(name: str, arguments: dict[str, Any], error_payload: Any) -> None:
    """Append one bounded JSON line to devapi_errors.log for a genuine tool failure."""
    try:
        args_text = _truncate_text(json.dumps(_redact(arguments), default=str), _MAX_ERROR_ARG_CHARS)
        error_text = _truncate_text(json.dumps(error_payload, default=str), _MAX_ERROR_PAYLOAD_CHARS)
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "tool": name,
            "args": args_text,
            "error": error_text,
        }
        line = json.dumps(entry)
        if len(line) > _MAX_ERROR_LINE_CHARS:
            line = line[:_MAX_ERROR_LINE_CHARS] + '"}'
        with _ERROR_LOG.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:  # noqa: BLE001 - logging must never crash the server
        pass


def _read_tool_errors(limit: int = 20) -> dict[str, Any]:
    """Read recent entries from devapi_errors.log, newest first."""
    try:
        if not _ERROR_LOG.exists():
            return {"success": True, "count": 0, "entries": [], "note": "No errors logged yet."}
        lines = _ERROR_LOG.read_text(encoding="utf-8").splitlines()
        entries = []
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            if len(line) > _MAX_ERROR_LINE_CHARS:
                line = line[:_MAX_ERROR_LINE_CHARS] + "..."
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                entries.append({"raw": line})
            if len(entries) >= limit:
                break
        return {
            "success": True,
            "count": len(entries),
            "total_in_log": len(lines),
            "entries": entries,
        }
    except Exception as error:  # noqa: BLE001
        return failure(str(error))

