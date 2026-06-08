"""Tests for logging level correctness.

Verifies that key MakeMKV events are logged at INFO (visible in production)
and that rsync progress lines are logged at DEBUG (not flooding structured logs).
"""
import io
import logging
import os
import subprocess
import unittest.mock

import pytest


class TestMakeMKVLogLevels:
    """Verify MakeMKV output is logged at appropriate levels."""

    def test_tcount_logged_at_info(self, caplog):
        """Title count (TCOUNT) should be logged at INFO."""
        from arm.ripper.makemkv import run, OutputType

        # Mock makemkvcon to emit a TCOUNT line
        mock_stdout = "TCOUNT:3\n"
        mock_proc = unittest.mock.MagicMock()
        mock_proc.stdout = io.StringIO(mock_stdout)
        mock_proc.returncode = 0
        mock_proc.pid = 12345

        with (
            unittest.mock.patch("subprocess.Popen", return_value=mock_proc),
            unittest.mock.patch("shutil.which", return_value="/usr/bin/makemkvcon"),
            caplog.at_level(logging.DEBUG),
        ):
            list(run(["info"], OutputType.TCOUNT))

        info_messages = [r.message for r in caplog.records if r.levelno == logging.INFO]
        assert any("Found 3 titles" in m for m in info_messages), (
            f"TCOUNT should produce an INFO log. Got: {info_messages}"
        )

    def test_msg_logged_at_info(self, caplog):
        """MakeMKV MSG output should be logged at INFO."""
        from arm.ripper.makemkv import run, OutputType

        mock_stdout = 'MSG:5010,0,0,"Copy complete - 1 titles saved.","%1 titles saved.","1"\n'
        mock_proc = unittest.mock.MagicMock()
        mock_proc.stdout = io.StringIO(mock_stdout)
        mock_proc.returncode = 0
        mock_proc.pid = 12345

        with (
            unittest.mock.patch("subprocess.Popen", return_value=mock_proc),
            unittest.mock.patch("shutil.which", return_value="/usr/bin/makemkvcon"),
            caplog.at_level(logging.DEBUG),
        ):
            list(run(["info"], OutputType.MSG))

        info_messages = [r.message for r in caplog.records if r.levelno == logging.INFO]
        assert any("MakeMKV:" in m for m in info_messages), (
            f"MSG should produce an INFO log. Got: {info_messages}"
        )

    def test_prgv_stays_at_debug(self, caplog):
        """Progress values (PRGV) should stay at DEBUG."""
        from arm.ripper.makemkv import run, OutputType

        mock_stdout = "PRGV:100,200,65536\n"
        mock_proc = unittest.mock.MagicMock()
        mock_proc.stdout = io.StringIO(mock_stdout)
        mock_proc.returncode = 0
        mock_proc.pid = 12345

        with (
            unittest.mock.patch("subprocess.Popen", return_value=mock_proc),
            unittest.mock.patch("shutil.which", return_value="/usr/bin/makemkvcon"),
            caplog.at_level(logging.DEBUG),
        ):
            list(run(["info"], OutputType.PRGV))

        info_messages = [r.message for r in caplog.records if r.levelno == logging.INFO]
        # PRGV should NOT appear in INFO logs (only in DEBUG)
        prgv_in_info = [m for m in info_messages if "PRGV" in m or "100" in m and "200" in m]
        assert not prgv_in_info, (
            f"PRGV progress should NOT be logged at INFO. Found: {prgv_in_info}"
        )

    def test_sinfo_stays_at_debug(self, caplog):
        """Stream info (SINFO) should stay at DEBUG."""
        from arm.ripper.makemkv import run, OutputType

        mock_stdout = 'SINFO:0,0,1,6201,"Video"\n'
        mock_proc = unittest.mock.MagicMock()
        mock_proc.stdout = io.StringIO(mock_stdout)
        mock_proc.returncode = 0
        mock_proc.pid = 12345

        with (
            unittest.mock.patch("subprocess.Popen", return_value=mock_proc),
            unittest.mock.patch("shutil.which", return_value="/usr/bin/makemkvcon"),
            caplog.at_level(logging.DEBUG),
        ):
            list(run(["info"], OutputType.SINFO))

        info_messages = [r.message for r in caplog.records if r.levelno == logging.INFO]
        sinfo_in_info = [m for m in info_messages if "SINFO" in m or "Video" in m]
        assert not sinfo_in_info, (
            f"SINFO should NOT be logged at INFO. Found: {sinfo_in_info}"
        )


class TestRsyncLogLevels:
    """Verify rsync helper logs start/complete at INFO and does not flood
    structured logs with per-line progress data (progress now goes to a
    side-file consumed by progress_reader)."""

    def test_rsync_progress_not_at_info(self, tmp_path, caplog):
        """Per-line progress samples must not land in the structured log -
        they belong in the side-file. Helper emits two INFO messages
        (start + complete); progress lines (containing 'MB/s') must not
        appear at INFO."""
        from arm.ripper.utils import _move_to_shared_storage

        local_raw = tmp_path / "local"
        shared_raw = tmp_path / "shared"
        local_raw.mkdir()
        shared_raw.mkdir()
        src_dir = local_raw / "test_movie"
        src_dir.mkdir()
        (src_dir / "title.mkv").write_bytes(b"\x00" * 100)

        cfg = {
            "LOCAL_RAW_PATH": str(local_raw),
            "SHARED_RAW_PATH": str(shared_raw),
            "LOGPATH": str(tmp_path),
        }

        # Mock Popen to feed back rsync-shaped stdout including a progress line
        mock_proc = unittest.mock.MagicMock()
        # Two reads: payload then EOF.
        mock_proc.stdout = unittest.mock.MagicMock()
        mock_proc.stdout.read.side_effect = [
            "title.mkv\n  100,000 100%  50.00MB/s    0:00:00\n",
            "",
        ]
        mock_proc.stderr = unittest.mock.MagicMock()
        mock_proc.stderr.read.return_value = ""
        mock_proc.returncode = 0
        mock_proc.wait.return_value = None

        with (
            unittest.mock.patch("arm.ripper.rsync_helper.subprocess.Popen", return_value=mock_proc),
            unittest.mock.patch("shutil.rmtree"),
            caplog.at_level(logging.DEBUG),
        ):
            _move_to_shared_storage(cfg, "test_movie")

        info_messages = [r.message for r in caplog.records if r.levelno == logging.INFO]

        # Per-line progress must not leak to INFO structured logs
        rsync_info_progress = [m for m in info_messages if "MB/s" in m]
        assert not rsync_info_progress, (
            f"rsync progress should NOT be at INFO. Found: {rsync_info_progress}"
        )

    def test_rsync_summary_at_info(self, tmp_path, caplog):
        """rsync start and completion should be logged at INFO."""
        from arm.ripper.utils import _move_to_shared_storage

        local_raw = tmp_path / "local"
        shared_raw = tmp_path / "shared"
        local_raw.mkdir()
        shared_raw.mkdir()
        src_dir = local_raw / "test_movie"
        src_dir.mkdir()
        (src_dir / "title.mkv").write_bytes(b"\x00" * 100)

        cfg = {
            "LOCAL_RAW_PATH": str(local_raw),
            "SHARED_RAW_PATH": str(shared_raw),
            "LOGPATH": str(tmp_path),
        }

        mock_proc = unittest.mock.MagicMock()
        mock_proc.stdout = unittest.mock.MagicMock()
        mock_proc.stdout.read.side_effect = ["title.mkv\n", ""]
        mock_proc.stderr = unittest.mock.MagicMock()
        mock_proc.stderr.read.return_value = ""
        mock_proc.returncode = 0
        mock_proc.wait.return_value = None

        with (
            unittest.mock.patch("arm.ripper.rsync_helper.subprocess.Popen", return_value=mock_proc),
            unittest.mock.patch("shutil.rmtree"),
            caplog.at_level(logging.DEBUG),
        ):
            _move_to_shared_storage(cfg, "test_movie")

        info_messages = [r.message for r in caplog.records if r.levelno == logging.INFO]

        # Start message
        assert any("rsync" in m and "->" in m for m in info_messages), (
            f"rsync start should be at INFO. Got: {info_messages}"
        )
        # Completion (file-count suffix dropped after refactor; the helper
        # logs 'rsync complete: src -> dst' and progress is in the side-file)
        assert any("rsync complete" in m for m in info_messages), (
            f"rsync complete should be at INFO. Got: {info_messages}"
        )
