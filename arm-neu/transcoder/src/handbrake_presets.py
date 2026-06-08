"""Discover HandBrakeCLI built-in preset names for the UI picker.

Shells out to ``HandBrakeCLI --preset-list`` and parses the indented
hierarchy. Result is cached in-process for the lifetime of the worker
because the list is fixed for a given HandBrake binary.
"""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

# 5 second wall-clock cap; the subprocess normally returns in <1s. If the
# binary hangs (rare but observed when libdvd-stuff misbehaves on container
# startup), the request returns an empty result and the UI falls through to
# the existing free-text input.
_PRESET_LIST_TIMEOUT = 5.0

_cache: dict[str, list[str]] | None = None


async def list_handbrake_presets() -> dict[str, list[str]]:
    """Return ``{category: [preset_name, ...]}`` from HandBrakeCLI.

    Empty dict on any failure (binary missing, parse error, timeout).
    The caller is responsible for surfacing a user-visible fallback.
    """
    global _cache
    if _cache is not None:
        return _cache

    try:
        proc = await asyncio.create_subprocess_exec(
            "HandBrakeCLI",
            "--preset-list",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        logger.warning("HandBrakeCLI not found on PATH; preset list unavailable")
        _cache = {}
        return _cache

    try:
        stdout_b, stderr_b = await asyncio.wait_for(
            proc.communicate(), timeout=_PRESET_LIST_TIMEOUT
        )
    except asyncio.TimeoutError:
        logger.warning("HandBrakeCLI --preset-list timed out after %ss", _PRESET_LIST_TIMEOUT)
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        _cache = {}
        return _cache

    # HandBrake writes the preset hierarchy to stderr in some versions and
    # stdout in others. Concatenate and parse.
    text = (stdout_b.decode("utf-8", errors="replace")
            + stderr_b.decode("utf-8", errors="replace"))

    parsed = _parse_preset_list(text)
    if not parsed:
        logger.warning("HandBrakeCLI --preset-list returned no recognizable presets")
    _cache = parsed
    return _cache


def _parse_preset_list(output: str) -> dict[str, list[str]]:
    """Parse HandBrake's indented preset hierarchy.

    Format (verbatim from ``HandBrakeCLI --preset-list``)::

        General/
          Fast 1080p30
          HQ 1080p30 Surround
        Web/
          Vimeo YouTube HQ 1080p60

    Lines ending in ``/`` at depth 0 are categories; subsequent indented
    lines until the next category are preset names. Blank lines and lines
    that don't match either pattern are skipped (HandBrake prints status
    chatter on its own line first).
    """
    result: dict[str, list[str]] = {}
    current_category: str | None = None

    for raw in output.splitlines():
        if not raw.strip():
            continue
        # Strip leading whitespace; the indent depth is the only signal.
        indent = len(raw) - len(raw.lstrip(" \t"))
        body = raw.strip()

        # Category line: depth 0 (or 1 leading space, some versions vary)
        # ending in "/".
        if body.endswith("/") and indent <= 2:
            current_category = body.rstrip("/")
            result.setdefault(current_category, [])
            continue

        # Preset name: indented line under the current category. Skip
        # un-categorized stray output (status messages, version banners).
        if current_category is not None and indent >= 2:
            result[current_category].append(body)

    # Drop categories that ended up empty (defensive against malformed output).
    return {k: v for k, v in result.items() if v}


def _reset_cache_for_tests() -> None:
    """Test-only hook to clear the cache between subprocess mocks."""
    global _cache
    _cache = None
