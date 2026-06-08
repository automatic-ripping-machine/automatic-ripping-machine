"""arm-neu's sync wrapper around the rsync subprocess.

Streams stdout line-by-line, runs each line through the shared parser/tracker
in arm_contracts, and emits RsyncProgressEvent objects to the on_progress
callback. Blocks until rsync exits; raises OSError on non-zero exit.

Storage of the parsed events is the *caller's* responsibility. The thin
wrapper run_rsync_with_side_file plumbs events into the side-file at
{LOGPATH}/progress/{job_id}.copy.log so the existing progress_reader pattern
(see get_rip_progress) extends naturally.
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Callable

from arm_contracts import RsyncProgressEvent, RsyncProgressTracker

import arm.config.config as cfg

logger = logging.getLogger(__name__)


def _redact_rsync(target: str) -> str:
    """Strip embedded credentials from rsync/ssh/url-style targets before
    logging (e.g. ``user:password@host`` or ``rsync://user:pass@host``).

    Plain local paths contain no ``credential@`` segment and are returned
    unchanged. This also breaks the secret -> log taint flow that CodeQL
    reports for logged rsync targets.
    """
    return re.sub(r'(\b\w+:)[^@/\s]*(@)', r'\1<redacted>\2', str(target))


def run_rsync_sync(
    src: str,
    dst: str,
    *,
    on_progress: Callable[[RsyncProgressEvent], None],
    remove_source: bool = False,
) -> None:
    """Run rsync, streaming progress events to on_progress.

    Args:
        src: Source path. Trailing slash semantics match rsync's: with a
             trailing slash, source contents merge into dst; without, source
             dir is created inside dst.
        dst: Destination path. Created if missing (rsync handles this when
             dst's parent exists; the caller is responsible for the parent).
        on_progress: Called with each RsyncProgressEvent as it arrives.
                     Must not raise - exceptions inside the callback are
                     caught and logged; rsync continues uninterrupted.
        remove_source: If True, passes --remove-source-files. Empty source
                       directories are removed via shutil.rmtree on success.

    Raises:
        OSError: rsync exited non-zero. Message includes exit code and
                 a snippet of stderr.

    Behaviour:
        Stdout is read line-by-line; under text=True universal newlines
        already translates rsync's \\r progress-overwrites to \\n, so the
        helper splits on \\n. Stderr is drained concurrently in a daemon
        thread so a verbose stderr (e.g. permission errors across many
        files) cannot fill its 64KB pipe buffer and deadlock rsync while
        we wait on stdout.
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

    logger.info(
        f"rsync {'(move)' if remove_source else '(copy)'}: "
        f"{_redact_rsync(src)} -> {_redact_rsync(dst)}"
    )

    tracker = RsyncProgressTracker()
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,  # line-buffered
        text=True,
    )

    # Drain stderr concurrently so a verbose stderr (e.g. permission errors
    # across many files) cannot fill the 64KB pipe buffer and deadlock the
    # rsync subprocess waiting on stderr while we are waiting on stdout.
    stderr_chunks: list[str] = []

    def _drain_stderr() -> None:
        assert proc.stderr is not None
        try:
            for chunk in proc.stderr:
                stderr_chunks.append(chunk)
        except Exception:
            logger.debug("stderr drain raised", exc_info=True)

    stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
    stderr_thread.start()

    try:
        assert proc.stdout is not None
        buffer = ""
        while True:
            chunk = proc.stdout.read(1024)
            if not chunk:
                if buffer:
                    _emit(buffer, tracker, on_progress)
                break
            buffer += chunk
            # Split on \n only - text=True (universal_newlines) has already
            # translated rsync's \r progress-overwrites to \n. The line-by-line
            # consumption here drains the stdout pipe continuously, preventing
            # the buffer-fills-and-rsync-blocks regression.
            parts = buffer.split("\n")
            buffer = parts[-1]
            for line in parts[:-1]:
                _emit(line, tracker, on_progress)
    finally:
        proc.wait()
        stderr_thread.join(timeout=5.0)
        stderr = "".join(stderr_chunks)

    if proc.returncode != 0:
        msg = f"rsync failed (exit {proc.returncode}): {stderr.strip()[:200]}"
        logger.error(msg)
        raise OSError(msg)

    if remove_source and src_path.is_dir():
        # rsync --remove-source-files removes files but leaves empty dirs
        shutil.rmtree(src, ignore_errors=True)

    logger.info(f"rsync complete: {_redact_rsync(src)} -> {_redact_rsync(dst)}")


def _emit(
    line: str,
    tracker: RsyncProgressTracker,
    on_progress: Callable[[RsyncProgressEvent], None],
) -> None:
    """Push one line through the tracker; if it yields an event, call the
    callback. Callback exceptions are caught so a buggy callback cannot kill
    a 40-minute rsync."""
    try:
        evt = tracker.consume(line)
    except Exception:
        logger.debug("rsync tracker raised on line: %r", line, exc_info=True)
        return
    if evt is None:
        return
    try:
        on_progress(evt)
    except Exception:
        logger.debug("rsync on_progress callback raised", exc_info=True)


def run_rsync_with_side_file(
    src: str,
    dst: str,
    *,
    job_id: int,
    stage: str,
    remove_source: bool = False,
) -> None:
    """Convenience wrapper that pipes progress to the side-file used by
    progress_reader.get_copy_progress.

    Side-file location: {LOGPATH}/progress/{job_id}.copy.log
    Format (one line per event):
        stage,progress_pct,files_transferred,current_file

    File is opened in append mode every time so multiple stages
    (scratch-to-media, work-to-completed, etc.) for the same job land in
    the same file. The reader picks the latest entry per stage.
    """
    log_root = Path(cfg.arm_config.get("LOGPATH", "")).resolve()
    progress_dir = log_root / "progress"
    progress_dir.mkdir(parents=True, exist_ok=True)
    side_file = progress_dir / f"{job_id}.copy.log"

    # Append, line-buffered, so partial writes are atomic at line granularity.
    with open(side_file, "a", buffering=1) as f:

        def on_progress(evt: RsyncProgressEvent) -> None:
            current_file = (evt.current_file or "").replace(",", "_").replace("\n", " ")
            files = "" if evt.files_transferred is None else str(evt.files_transferred)
            f.write(f"{stage},{evt.progress_pct},{files},{current_file}\n")

        run_rsync_sync(src, dst, on_progress=on_progress, remove_source=remove_source)
