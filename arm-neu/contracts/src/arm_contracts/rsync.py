"""Pure parser for rsync --info=name1,progress2 output.

Used by every service that calls rsync (arm-neu's _move_to_shared_storage,
arm-transcoder's async_copy / async_move_file). Parser lives here so behaviour
cannot drift between services - the per-service subprocess wrappers share this
single source of truth.

Fail-soft: parse_progress_line never raises. Lines that do not match either
of the two expected rsync output shapes return None. Wrappers are expected to
log unparseable lines at DEBUG and continue; one bad line must not crash a
40-minute rsync.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RsyncProgressEvent:
    """One sample from rsync's --info=name1,progress2 output stream.

    progress_pct: 0.0 .. 100.0, aggregate across the whole transfer.
    current_file: most recent file rsync emitted via --info=name1, or None
                  when the parser is invoked without prior filename context
                  (parse_progress_line is stateless; RsyncProgressTracker
                  injects the filename).
    files_transferred: rsync's xfr#N counter.
    bytes_transferred: bytes seen so far across the transfer.
    """
    progress_pct: float
    current_file: str | None
    files_transferred: int | None
    bytes_transferred: int | None


# Matches:  "       12,345  47%   10.00MB/s    0:00:42 (xfr#3, to-chk=2/5)"
# Bytes column may contain commas. The xfr# group is required - that is what
# distinguishes a real progress2 line from a bare percentage in noise.
_PROGRESS2_RE = re.compile(
    r"^\s*"
    r"(?P<bytes>[\d,]+)\s+"
    r"(?P<pct>\d+(?:\.\d+)?)%\s+"
    r"\S+\s+"  # rate (e.g. 10.00MB/s)
    r"\S+\s+"  # ETA (e.g. 0:00:42)
    r"\(xfr#(?P<xfr>\d+)"
    r".*?\)"
    r"\s*$"
)


def parse_progress_line(raw: str) -> RsyncProgressEvent | None:
    """Parse one --info=name1,progress2 line.

    Returns an event for progress2 lines only. Returns None for bare
    filenames, blank lines, or anything that does not match the progress2
    shape. Never raises.

    Strips a trailing carriage return because rsync uses \\r to overwrite
    the same terminal line; wrappers split on both \\r and \\n.
    """
    if raw is None:
        return None
    line = raw.rstrip("\r\n").rstrip()
    if not line:
        return None
    m = _PROGRESS2_RE.match(line)
    if not m:
        return None
    try:
        bytes_transferred = int(m.group("bytes").replace(",", ""))
        progress_pct = float(m.group("pct"))
        files_transferred = int(m.group("xfr"))
    except (ValueError, KeyError):
        # Defensive: if our regex matched but conversion failed, fail-soft.
        return None
    return RsyncProgressEvent(
        progress_pct=progress_pct,
        current_file=None,
        files_transferred=files_transferred,
        bytes_transferred=bytes_transferred,
    )


# A bare filename line is recognised by either:
#   - containing a path separator (most common: 'subdir/file.mkv'), OR
#   - ending in a media file extension we actually move via rsync
# This rejects rsync's verbose-mode informational lines like
# "skipping non-regular file ..." or "sent X bytes ..." which would
# otherwise contaminate the tracker's filename state.
_FILENAME_EXT = (
    ".mkv", ".iso", ".m2ts", ".vob", ".mp4", ".srt", ".sub", ".idx",
    ".ifo", ".bup", ".bin", ".log", ".nfo", ".jpg", ".png",
    ".flac", ".mp3", ".wav", ".m4a", ".aac",
)
_FILENAME_RE = re.compile(r"^(?![\s]*\d)[^\r\n]+$")


def _looks_like_filename(line: str) -> bool:
    """Return True if line plausibly is a bare filename emitted by
    rsync's --info=name1, false for verbose noise."""
    if not _FILENAME_RE.match(line):
        return False
    if "/" in line:
        return True
    # Without a path separator, reject anything containing whitespace -
    # rsync's verbose noise ("skipping non-regular file foo.bin",
    # "sent N bytes ...") all has whitespace, while bare filenames at
    # the rsync target root (e.g. "Annihilation_t00.mkv") do not.
    if any(ch.isspace() for ch in line):
        return False
    lower = line.lower()
    return any(lower.endswith(ext) for ext in _FILENAME_EXT)


class RsyncProgressTracker:
    """Stateful pairing of bare filenames with subsequent progress samples.

    rsync emits filenames and progress samples interleaved. The tracker
    remembers the most-recent filename so progress events know which file
    they refer to. Wrappers feed every stdout line through `consume`; non-None
    results are emitted as progress events.

    Cheap to instantiate. One tracker per rsync invocation.
    """

    def __init__(self) -> None:
        self._current_file: str | None = None

    def consume(self, raw: str) -> RsyncProgressEvent | None:
        """Feed one stdout line. Updates internal filename state when the
        line is a bare filename; returns an event when the line is a
        progress2 sample (with current_file populated from state)."""
        if raw is None:
            return None
        evt = parse_progress_line(raw)
        if evt is not None:
            # Inject the remembered filename
            return RsyncProgressEvent(
                progress_pct=evt.progress_pct,
                current_file=self._current_file,
                files_transferred=evt.files_transferred,
                bytes_transferred=evt.bytes_transferred,
            )
        # Not a progress line. Maybe a filename?
        line = raw.rstrip("\r\n").rstrip()
        if line and _looks_like_filename(line):
            self._current_file = line
        return None
