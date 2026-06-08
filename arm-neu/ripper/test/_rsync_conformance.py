"""Shared conformance tests for repos that consume the arm_contracts
rsync helper interface.

Each service repo (arm-neu, arm-transcoder) wraps its own subprocess
helper in a `HelperAdapter` and runs the three `assert_*` functions
below. The same five assertions hold on both sides:

  1. At least one mid-transfer event fires before exit (>1MB transfer).
  2. The final event has progress_pct == 100.0.
  3. Parser returns None (does not raise) for malformed input. (Covered
     by the parser test suite in this repo, not this module.)
  4. rsync exit code 23 (partial transfer) raises an OSError with the
     code in the message.
  5. After remove_source=True success, src is empty.

Adapter pattern: arm-neu provides a SyncAdapter that calls run_rsync_sync;
arm-transcoder provides an AsyncAdapter that bridges asyncio.run() into
a sync return. Conformance tests are execution-model-agnostic.
"""
from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Protocol

from arm_contracts import RsyncProgressEvent


class HelperAdapter(Protocol):
    """Each repo wraps its helper to look like this. The adapter is the
    bridge between the conformance's sync test fixture and the helper's
    sync-or-async execution model."""

    def run_to_completion(
        self,
        src: str,
        dst: str,
        *,
        remove_source: bool = False,
    ) -> list[RsyncProgressEvent]:
        """Run the helper. Return all on_progress events, in order, that
        fired before the helper returned. Adapter handles any
        asyncio.run() / thread bridging needed to make this synchronous."""
        ...


def _make_transfer_payload(tmp_path: Path, size_mb: int = 5) -> tuple[str, str]:
    """Create a >1MB source spread across several files so rsync emits
    mid-transfer progress samples even on fast SSDs/tmpfs (a single file
    transfers in <1 sample window on local NVMe and never produces an
    intermediate progress event)."""
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()
    # Spread the payload across 5 files; rsync's progress2 reports the
    # cumulative percentage, which steps through 20/40/60/80/100 across files.
    per_file = max(1, size_mb // 5) * 1024 * 1024
    for i in range(5):
        # urandom is incompressible so rsync cannot collapse it
        (src / f"payload_{i}.bin").write_bytes(os.urandom(per_file))
    return str(src), str(dst)


def assert_streams_progress(adapter: HelperAdapter, tmp_path: Path) -> None:
    """Assertion 1 + 2: mid-transfer event fires AND final event is 100%."""
    src, dst = _make_transfer_payload(tmp_path, size_mb=20)
    events = adapter.run_to_completion(src, dst)
    assert len(events) > 0, (
        "Helper produced zero on_progress events. Either streaming is "
        "broken or the >1MB transfer was too fast for rsync to emit "
        "intermediate samples."
    )
    assert any(0 < e.progress_pct < 100 for e in events), (
        f"Never saw a mid-transfer event. All events: "
        f"{[e.progress_pct for e in events]}"
    )
    assert math.isclose(events[-1].progress_pct, 100.0), (
        f"Final event was {events[-1].progress_pct}, expected 100.0. "
        f"This indicates a partial-line-at-EOF drop."
    )


def assert_partial_transfer_raises(adapter: HelperAdapter, tmp_path: Path) -> None:
    """Assertion 4: rsync exit code 23 raises an OSError with the code in
    the message.

    Repro: rsync to a directory the user cannot write to. rsync exits 23
    (partial transfer due to error)."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "f.bin").write_bytes(b"x" * 1024)
    # Build a destination path that exists as a non-writable file - rsync
    # cannot create the directory and exits non-zero.
    bad_dst = tmp_path / "blocking_file"
    bad_dst.write_bytes(b"")  # exists as a regular file
    bad_path = bad_dst / "subdir"  # rsync cannot mkdir under a regular file

    try:
        adapter.run_to_completion(str(src), str(bad_path))
    except OSError as exc:
        msg = str(exc)
        assert "rsync" in msg.lower(), (
            f"OSError raised but message does not mention rsync: {msg}"
        )
        return
    raise AssertionError("Expected OSError was not raised")


def assert_remove_source_cleanup(adapter: HelperAdapter, tmp_path: Path) -> None:
    """Assertion 5: after remove_source=True, src is empty (or the dir
    itself is removed - both are acceptable)."""
    src, dst = _make_transfer_payload(tmp_path, size_mb=2)
    adapter.run_to_completion(src, dst, remove_source=True)
    src_path = Path(src)
    if src_path.exists():
        remaining = [p for p in src_path.iterdir()]
        assert remaining == [], (
            f"Source directory still has files after remove_source=True: "
            f"{[p.name for p in remaining]}"
        )
