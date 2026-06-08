"""Tests for the rsync --info=name1,progress2 parser.

Fail-soft contract: parse_progress_line never raises. Lines that do not match
either of the two expected shapes return None. The parser is stateless;
RsyncProgressTracker pairs filenames with subsequent progress samples.
"""
from pathlib import Path

import pytest

from arm_contracts import (
    RsyncProgressEvent,
    RsyncProgressTracker,
    parse_progress_line,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_progress_line_basic_progress2():
    """A standard progress2 line yields a populated event."""
    line = "       12,345  47%   10.00MB/s    0:00:42 (xfr#3, to-chk=2/5)"
    evt = parse_progress_line(line)
    assert evt is not None
    assert evt.progress_pct == pytest.approx(47.0)
    assert evt.bytes_transferred == 12345
    assert evt.files_transferred == 3
    assert evt.current_file is None  # parser is stateless; tracker pairs filenames


def test_parse_progress_line_zero_byte_transfer():
    """A 0%/0-byte progress2 line still produces a valid event."""
    line = "        0   0%    0.00kB/s    0:00:00 (xfr#0, to-chk=0/0)"
    evt = parse_progress_line(line)
    assert evt is not None
    assert evt.progress_pct == pytest.approx(0.0)
    assert evt.bytes_transferred == 0
    assert evt.files_transferred == 0


def test_parse_progress_line_filename_returns_none():
    """A bare filename (--info=name1 output) is not a progress event by itself.
    The tracker holds it; the parser does not."""
    assert parse_progress_line("file_a.bin") is None
    assert parse_progress_line("subdir/file_with_spaces in name.bin") is None


def test_parse_progress_line_blank_and_garbage_return_none():
    """Fail-soft on anything that does not match a known shape."""
    assert parse_progress_line("") is None
    assert parse_progress_line("   ") is None
    assert parse_progress_line("PRGV:not_an_rsync_line") is None
    assert parse_progress_line("random garbage ::: not a progress line") is None


def test_parse_progress_line_malformed_does_not_raise():
    """A line missing the bytes column is fail-soft."""
    line = "            0% bare percentage line with no bytes"
    # Either return None or return an event - both are acceptable.
    # The hard requirement is that it does not raise.
    parse_progress_line(line)


def test_parse_progress_line_strips_carriage_return():
    """rsync uses \\r to overwrite the same terminal line; the parser must
    accept a trailing CR and produce the same event as without."""
    line_lf = "       12,345  47%   10.00MB/s    0:00:42 (xfr#3, to-chk=2/5)"
    line_cr = line_lf + "\r"
    assert parse_progress_line(line_lf) == parse_progress_line(line_cr)


def test_tracker_pairs_filename_with_subsequent_progress():
    """RsyncProgressTracker remembers the most-recent filename and pairs it
    with subsequent progress samples."""
    tracker = RsyncProgressTracker()
    # Bare filenames update internal state but yield None
    assert tracker.consume("file_a.bin") is None
    # Subsequent progress event picks up the remembered filename
    evt = tracker.consume(
        "       12,345  47%   10.00MB/s    0:00:42 (xfr#3, to-chk=2/5)"
    )
    assert evt is not None
    assert evt.current_file == "file_a.bin"
    assert evt.progress_pct == pytest.approx(47.0)


def test_tracker_filename_updates_between_progress_events():
    """When rsync moves to the next file, the tracker's stored filename
    updates and subsequent progress samples reflect the new file."""
    tracker = RsyncProgressTracker()
    tracker.consume("file_a.bin")
    e1 = tracker.consume(
        "       12,345  47%   10.00MB/s    0:00:42 (xfr#1, to-chk=1/2)"
    )
    tracker.consume("file_b.bin")
    e2 = tracker.consume(
        "      999,999  99%   12.00MB/s    0:00:01 (xfr#2, to-chk=0/2)"
    )
    assert e1.current_file == "file_a.bin"
    assert e2.current_file == "file_b.bin"


def test_tracker_handles_real_fixture_without_raising():
    """End-to-end: feed every line of the real-rsync fixture through the
    tracker. The tracker must produce at least one mid-transfer event
    (0 < pct < 100) and end with progress_pct == 100.0."""
    raw = (FIXTURES / "rsync_progress2_real.txt").read_bytes().decode(
        "utf-8", errors="replace"
    )
    # rsync emits both \r and \n; split on either
    lines = raw.replace("\r", "\n").splitlines()

    tracker = RsyncProgressTracker()
    events = []
    for line in lines:
        evt = tracker.consume(line)
        if evt is not None:
            events.append(evt)

    assert len(events) > 0, "fixture produced zero events; check fixture capture"
    assert any(0 < e.progress_pct < 100 for e in events), \
        "expected at least one mid-transfer event"
    assert events[-1].progress_pct == pytest.approx(100.0), \
        f"last event was {events[-1].progress_pct}, expected 100.0"


def test_tracker_handles_edge_fixture_without_raising():
    """Edge-case fixture must not raise and must yield a sensible event count."""
    raw = (FIXTURES / "rsync_progress2_edge.txt").read_text()
    tracker = RsyncProgressTracker()
    events = []
    for line in raw.splitlines():
        evt = tracker.consume(line)
        if evt is not None:
            events.append(evt)
    # The exact count is fixture-dependent; the contract is "no raise" plus
    # "at least the well-formed progress lines parsed successfully".
    assert any(e.progress_pct == pytest.approx(47.0) for e in events)
    assert any(e.progress_pct == pytest.approx(0.0) for e in events)


def test_tracker_ignores_rsync_verbose_noise():
    """rsync verbose-mode informational lines must not be latched as
    current_file. Repro: a line like 'skipping non-regular file foo.bin'
    fits the old permissive regex (letters, dots, spaces, hyphens) and
    would corrupt the tracker's filename state."""
    tracker = RsyncProgressTracker()
    tracker.consume("skipping non-regular file foo.bin")
    tracker.consume("sending incremental file list")
    tracker.consume("sent 7,344,332 bytes received 35 bytes")
    evt = tracker.consume(
        "       12,345  47%   10.00MB/s    0:00:42 (xfr#3, to-chk=2/5)"
    )
    assert evt is not None
    # The tracker must NOT have latched the noise lines; current_file
    # should be None because no real filename was seen.
    assert evt.current_file is None


def test_tracker_accepts_filenames_with_separators():
    """Filenames containing a path separator are accepted regardless of
    extension."""
    tracker = RsyncProgressTracker()
    tracker.consume("subdir/anything.bin")
    evt = tracker.consume(
        "       12,345  47%   10.00MB/s    0:00:42 (xfr#3, to-chk=2/5)"
    )
    assert evt is not None
    assert evt.current_file == "subdir/anything.bin"


def test_tracker_accepts_filenames_with_known_extensions():
    """Filenames at the root with a media extension are accepted."""
    tracker = RsyncProgressTracker()
    tracker.consume("Annihilation_t00.mkv")
    evt = tracker.consume(
        "       12,345  47%   10.00MB/s    0:00:42 (xfr#3, to-chk=2/5)"
    )
    assert evt is not None
    assert evt.current_file == "Annihilation_t00.mkv"
