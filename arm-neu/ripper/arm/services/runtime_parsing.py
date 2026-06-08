"""Parse runtime strings from metadata providers into seconds.

OMDb returns strings like "95 min" or occasionally "2 h 31 min".
TMDb returns integer minutes. TVDB runtimes are handled separately
in arm/services/tvdb.py because they come pre-parsed.

Returns None for missing/invalid/zero runtimes - downstream code
treats None as "no runtime data, use static MIN/MAX fallback."
"""
from __future__ import annotations

import re

_OMDB_MIN_PATTERN = re.compile(r"^(\d+)\s*min$", re.IGNORECASE)
_OMDB_HOUR_MIN_PATTERN = re.compile(
    r"^(\d+)\s*h(?:our)?s?\s*(\d+)\s*min$", re.IGNORECASE
)


def parse_runtime(raw: str | int | None) -> int | None:
    if raw is None:
        return None
    if isinstance(raw, int) and not isinstance(raw, bool):
        return raw * 60 if raw > 0 else None
    if not isinstance(raw, str):
        return None
    s = raw.strip()
    if not s or s.upper() == "N/A":
        return None
    m = _OMDB_MIN_PATTERN.match(s)
    if m:
        minutes = int(m.group(1))
        return minutes * 60 if minutes > 0 else None
    m = _OMDB_HOUR_MIN_PATTERN.match(s)
    if m:
        hours = int(m.group(1))
        minutes = int(m.group(2))
        total = hours * 60 + minutes
        return total * 60 if total > 0 else None
    return None
