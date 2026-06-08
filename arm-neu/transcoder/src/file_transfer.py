"""Async file transfer helpers using rsync subprocess.

All NFS-touching file operations run as child processes via
asyncio.create_subprocess_exec so that kernel D-state (uninterruptible
sleep) on NFS I/O never blocks the uvicorn event loop.

See ARM's arm/ripper/utils.py:_move_to_shared_storage() for the sync
equivalent used in the Flask ripper.
"""

import asyncio
import logging
import os
import shutil
from pathlib import Path
from typing import Awaitable, Callable

from arm_contracts import RsyncProgressEvent

from rsync_helper import run_rsync_async

logger = logging.getLogger(__name__)


async def async_copy(
    src: str,
    dst: str,
    *,
    remove_source: bool = False,
    on_progress: Callable[[RsyncProgressEvent], Awaitable[None] | None] | None = None,
) -> None:
    """Copy a file or directory tree using rsync. Progress streams to the
    optional on_progress callback (called with RsyncProgressEvent each
    sample). Caller is responsible for any rate-limiting / DB writes."""
    if on_progress is None:
        on_progress = lambda _evt: None  # noqa: E731
    await run_rsync_async(src, dst, on_progress=on_progress, remove_source=remove_source)


async def async_copy_file(
    src: str,
    dst: str,
    *,
    on_progress: Callable[[RsyncProgressEvent], Awaitable[None] | None] | None = None,
) -> None:
    """Copy a single file using rsync subprocess."""
    await async_copy(src, dst, remove_source=False, on_progress=on_progress)


async def async_move_file(
    src: str,
    dst: str,
    *,
    on_progress: Callable[[RsyncProgressEvent], Awaitable[None] | None] | None = None,
) -> None:
    """Move a single file using rsync --remove-source-files.

    For single files, rsync --remove-source-files handles cleanup.
    """
    src_path = Path(src)
    dst_path = Path(dst)
    os.makedirs(dst_path.parent, exist_ok=True)
    if on_progress is None:
        on_progress = lambda _evt: None  # noqa: E731
    await run_rsync_async(src, dst, on_progress=on_progress, remove_source=True)


async def async_rmtree(path: str) -> None:
    """Remove a directory tree using subprocess rm -rf.

    Runs as a child process so NFS D-state on unlink doesn't block
    the event loop.
    """
    if not Path(path).exists():
        return

    proc = await asyncio.create_subprocess_exec(
        "rm", "-rf", path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        err_msg = stderr.decode().strip()[:200]
        logger.error(f"rm -rf failed (exit {proc.returncode}): {err_msg}")
        raise OSError(f"rm -rf failed: {err_msg}")
