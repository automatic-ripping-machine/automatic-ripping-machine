"""arm-transcoder's async wrapper around the rsync subprocess.

Streams stdout via asyncio so the event loop is never blocked by a slow
rsync. Same parser, same semantics as arm-neu's run_rsync_sync; the
difference is purely the execution model."""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Awaitable, Callable

from arm_contracts import RsyncProgressEvent, RsyncProgressTracker

logger = logging.getLogger(__name__)


async def _drain_stderr(stream: asyncio.StreamReader | None) -> bytes:
    """Concurrently drain rsync's stderr while stdout is being read.

    rsync can buffer >64KB of stderr (e.g. when many files trigger
    permission warnings); reading stderr only after the process exits
    risks a deadlock if the OS pipe fills and rsync blocks on its
    stderr write before we read stdout to EOF.
    """
    if stream is None:
        return b""
    chunks: list[bytes] = []
    try:
        while True:
            chunk = await stream.read(1024)
            if not chunk:
                break
            chunks.append(chunk)
    except Exception:
        logger.debug("stderr drain raised", exc_info=True)
    return b"".join(chunks)


async def run_rsync_async(
    src: str,
    dst: str,
    *,
    on_progress: Callable[[RsyncProgressEvent], Awaitable[None] | None],
    remove_source: bool = False,
) -> None:
    """Async equivalent of run_rsync_sync.

    on_progress may be sync or async. Async callbacks are awaited; sync
    callbacks are called inline. Either way, callback exceptions are
    caught and logged at DEBUG so a buggy callback cannot kill rsync.

    Raises:
        OSError: rsync exited non-zero. Message includes exit code and
                 a snippet of stderr.
    """
    src_path = Path(src)
    if not src_path.exists():
        raise FileNotFoundError(f"Source does not exist: {src}")

    cmd = ["rsync", "-a", "--info=name1,progress2"]
    if remove_source:
        cmd.append("--remove-source-files")

    try:
        if src_path.is_dir():
            os.makedirs(dst, exist_ok=True)
            cmd.extend([src.rstrip("/") + "/", dst.rstrip("/") + "/"])
        else:
            os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
            cmd.extend([src, dst])
    except OSError as exc:
        # Re-raise so callers see a uniform "rsync ..." OSError regardless
        # of whether the failure happened before rsync was even invoked.
        raise OSError(f"rsync setup failed for {dst}: {exc}") from exc

    logger.info(f"rsync {'(move)' if remove_source else '(copy)'}: {src} -> {dst}")

    tracker = RsyncProgressTracker()
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    assert proc.stdout is not None

    # Drain stderr concurrently to avoid deadlock when rsync emits more
    # stderr than the OS pipe buffer can hold.
    stderr_task = asyncio.create_task(_drain_stderr(proc.stderr))

    buffer = b""
    try:
        while True:
            chunk = await proc.stdout.read(1024)
            if not chunk:
                if buffer:
                    await _emit_async(buffer.decode("utf-8", "replace"), tracker, on_progress)
                break
            buffer += chunk
            text = buffer.decode("utf-8", "replace")
            parts = text.replace("\r", "\n").split("\n")
            # The trailing partial may have lost bytes during decode; encode
            # the last partial back to bytes for the next iteration to keep
            # decode boundaries clean.
            buffer = parts[-1].encode("utf-8")
            for line in parts[:-1]:
                await _emit_async(line, tracker, on_progress)
    finally:
        await proc.wait()
        stderr_bytes = await stderr_task

    if proc.returncode != 0:
        msg = f"rsync failed (exit {proc.returncode}): {stderr_bytes.decode('utf-8', 'replace').strip()[:200]}"
        logger.error(msg)
        raise OSError(msg)

    if remove_source and src_path.is_dir():
        # Reuse the existing async_rmtree from file_transfer for parity with
        # the previous behaviour - empty directories were swept up there.
        from file_transfer import async_rmtree
        await async_rmtree(src)

    logger.info(f"rsync complete: {src} -> {dst}")


async def _emit_async(line, tracker, on_progress):
    try:
        evt = tracker.consume(line)
    except Exception:
        logger.debug("rsync tracker raised on line: %r", line, exc_info=True)
        return
    if evt is None:
        return
    try:
        result = on_progress(evt)
        if asyncio.iscoroutine(result):
            await result
    except Exception:
        logger.debug("rsync on_progress callback raised", exc_info=True)
