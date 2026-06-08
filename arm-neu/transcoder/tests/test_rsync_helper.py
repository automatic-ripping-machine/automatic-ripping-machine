"""Tests for arm-transcoder's async rsync wrapper.

Same conformance suite as arm-neu's sync helper, run through an
AsyncAdapter that bridges asyncio.run() into a sync return value."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest
from arm_contracts import RsyncProgressEvent

from tests._rsync_conformance import (
    assert_partial_transfer_raises,
    assert_remove_source_cleanup,
    assert_streams_progress,
)


class AsyncAdapter:
    """Wraps run_rsync_async behind a sync return so the conformance suite
    works without knowing the helper is async. Uses asyncio.run per call so
    each test runs in a fresh event loop."""

    def run_to_completion(
        self,
        src: str,
        dst: str,
        *,
        remove_source: bool = False,
    ) -> list[RsyncProgressEvent]:
        from rsync_helper import run_rsync_async
        events: list[RsyncProgressEvent] = []
        asyncio.run(
            run_rsync_async(src, dst, on_progress=events.append, remove_source=remove_source)
        )
        return events


@pytest.fixture
def adapter():
    return AsyncAdapter()


def test_conformance_streams_progress(adapter, tmp_path):
    assert_streams_progress(adapter, tmp_path)


def test_conformance_partial_transfer_raises(adapter, tmp_path):
    assert_partial_transfer_raises(adapter, tmp_path)


def test_conformance_remove_source_cleanup(adapter, tmp_path):
    assert_remove_source_cleanup(adapter, tmp_path)


@pytest.mark.asyncio
async def test_async_copy_drives_progress_callback(tmp_path):
    """async_copy accepts an on_progress callback and routes events to it
    when the new helper is wired through."""
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()
    (src / "payload.bin").write_bytes(os.urandom(2 * 1024 * 1024))

    events: list[RsyncProgressEvent] = []

    from file_transfer import async_copy
    await async_copy(str(src), str(dst), on_progress=events.append)

    assert any(0 < e.progress_pct <= 100 for e in events)
    assert events[-1].progress_pct == pytest.approx(100.0)


@pytest.mark.asyncio
async def test_copy_progress_drives_update_progress(tmp_path):
    """Wiring the callback into transcoder._update_progress should advance
    the rate-limited progress for a >5MB transfer."""
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()
    (src / "payload.bin").write_bytes(os.urandom(5 * 1024 * 1024))

    last_progress = {"value": 0.0}

    async def fake_update_progress(job_id, progress, fps=None):
        last_progress["value"] = progress

    from rsync_helper import run_rsync_async

    async def cb(evt: RsyncProgressEvent):
        await fake_update_progress(99, evt.progress_pct)

    await run_rsync_async(str(src), str(dst), on_progress=cb)
    assert last_progress["value"] == pytest.approx(100.0)
