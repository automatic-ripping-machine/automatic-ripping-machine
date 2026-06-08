"""Tests for arm-neu's sync rsync wrapper.

Imports the shared conformance from arm_contracts and runs it against
a SyncAdapter wrapping run_rsync_sync. Storage-wiring tests live alongside
because they cannot be shared (arm-neu uses a side-file; arm-transcoder
uses a DB column)."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from arm_contracts import RsyncProgressEvent
from test._rsync_conformance import (
    assert_partial_transfer_raises,
    assert_remove_source_cleanup,
    assert_streams_progress,
)


class SyncAdapter:
    """Adapter for the conformance suite. Calls run_rsync_sync, captures
    each on_progress event into a list, returns the list."""

    def run_to_completion(
        self,
        src: str,
        dst: str,
        *,
        remove_source: bool = False,
    ) -> list[RsyncProgressEvent]:
        from arm.ripper.rsync_helper import run_rsync_sync
        events: list[RsyncProgressEvent] = []
        run_rsync_sync(src, dst, on_progress=events.append, remove_source=remove_source)
        return events


@pytest.fixture
def adapter():
    return SyncAdapter()


def test_conformance_streams_progress(adapter, tmp_path):
    assert_streams_progress(adapter, tmp_path)


def test_conformance_partial_transfer_raises(adapter, tmp_path):
    assert_partial_transfer_raises(adapter, tmp_path)


def test_conformance_remove_source_cleanup(adapter, tmp_path):
    assert_remove_source_cleanup(adapter, tmp_path)


# --- arm-neu storage wiring (not in conformance) ---


def test_helper_writes_side_file(tmp_path, monkeypatch):
    """When run_rsync_sync is invoked with a job_id and stage, it writes
    progress lines to {LOGPATH}/progress/{job_id}.copy.log in the form
    'stage,progress_pct,files_transferred,current_file'."""
    import arm.config.config as cfg
    monkeypatch.setitem(cfg.arm_config, "LOGPATH", str(tmp_path))
    (tmp_path / "progress").mkdir()

    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()
    (src / "payload.bin").write_bytes(os.urandom(2 * 1024 * 1024))

    from arm.ripper.rsync_helper import run_rsync_with_side_file
    run_rsync_with_side_file(
        str(src), str(dst),
        job_id=42,
        stage="scratch-to-media",
    )

    side_file = tmp_path / "progress" / "42.copy.log"
    assert side_file.is_file(), "side-file was not created"
    content = side_file.read_text()
    assert "scratch-to-media" in content
    # Final line should be at 100%
    last = [l for l in content.strip().splitlines() if l][-1]
    parts = last.split(",")
    assert parts[0] == "scratch-to-media"
    assert float(parts[1]) == pytest.approx(100.0)


def test_move_to_shared_storage_writes_side_file(tmp_path, monkeypatch):
    """When _move_to_shared_storage runs, the same side-file is written
    that run_rsync_with_side_file would have written. Proves the migration
    didn't break the producer-side wiring."""
    import arm.config.config as cfg
    monkeypatch.setitem(cfg.arm_config, "LOGPATH", str(tmp_path))
    (tmp_path / "progress").mkdir()

    local_raw = tmp_path / "scratch"
    shared_raw = tmp_path / "media"
    local_raw.mkdir()
    shared_raw.mkdir()

    raw_basename = "abc123"
    job_dir = local_raw / raw_basename
    job_dir.mkdir()
    (job_dir / "rip.mkv").write_bytes(os.urandom(2 * 1024 * 1024))

    # Mock job
    class FakeJob:
        job_id = 99

    job = FakeJob()
    cfg_dict = {
        "LOCAL_RAW_PATH": str(local_raw),
        "SHARED_RAW_PATH": str(shared_raw),
        "LOGPATH": str(tmp_path),
    }

    # Mock database_updater so we don't need a real DB session
    monkeypatch.setattr(
        "arm.ripper.utils.database_updater",
        lambda *a, **kw: None,
    )

    from arm.ripper.utils import _move_to_shared_storage
    _move_to_shared_storage(cfg_dict, raw_basename, job=job)

    side_file = tmp_path / "progress" / "99.copy.log"
    assert side_file.is_file(), "side-file should be written by _move_to_shared_storage"
    content = side_file.read_text()
    assert "scratch-to-media" in content
