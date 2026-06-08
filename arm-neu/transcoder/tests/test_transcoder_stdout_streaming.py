"""Regression tests for the CR-overwrite stdout reader.

Job 222 (Annihilation 4K BD) hit asyncio.exceptions.LimitOverrunError after
55 min of HandBrake transcoding because HandBrake's progress output uses
\\r to overwrite the same terminal line; the asyncio readline() default
splits on \\n only and accumulated the CR-overwrites until the buffer
filled. This file exercises the chunk-and-split reader."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


async def test_stream_progress_lines_handles_cr_overwrites():
    """The reader must dispatch each \\r-terminated line, not buffer them
    together until LimitOverrunError."""
    from transcoder import TranscodeWorker

    # Simulate HandBrake progress output: many \\r-terminated lines, no \\n.
    payload = b""
    for pct in range(0, 101):
        payload += f"{pct:.2f} % (10.00 fps, avg 9.00 fps, ETA 00h00m01s)\r".encode()
    # Also include one final \\n-terminated line so the stream ends cleanly
    payload += b"Encode done!\n"

    # Build a mock process whose stdout returns the payload in chunks
    chunks_iter = iter([payload[i:i + 512] for i in range(0, len(payload), 512)] + [b""])
    mock_stdout = AsyncMock()
    mock_stdout.read = AsyncMock(side_effect=lambda n: next(chunks_iter))
    mock_process = MagicMock()
    mock_process.stdout = mock_stdout

    handler_calls: list[str] = []

    def handler(line: str):
        handler_calls.append(line)

    tc = TranscodeWorker.__new__(TranscodeWorker)  # bypass __init__
    await tc._stream_progress_lines(mock_process, job_id=42, line_handler=handler)

    # We should see ~101 progress lines plus "Encode done!"
    assert len(handler_calls) >= 100
    assert any("100.00 %" in line for line in handler_calls)
    assert any("Encode done" in line for line in handler_calls)


async def test_stream_progress_lines_handler_exception_does_not_kill_reader():
    """A buggy line_handler must not interrupt streaming."""
    from transcoder import TranscodeWorker

    payload = b"line1\rline2\rline3\n"
    chunks_iter = iter([payload, b""])
    mock_stdout = AsyncMock()
    mock_stdout.read = AsyncMock(side_effect=lambda n: next(chunks_iter))
    mock_process = MagicMock()
    mock_process.stdout = mock_stdout

    seen: list[str] = []

    def buggy_handler(line: str):
        seen.append(line)
        if line == "line2":
            raise RuntimeError("boom")

    tc = TranscodeWorker.__new__(TranscodeWorker)
    await tc._stream_progress_lines(mock_process, job_id=42, line_handler=buggy_handler)
    assert seen == ["line1", "line2", "line3"]
