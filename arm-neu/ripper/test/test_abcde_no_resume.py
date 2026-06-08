"""Tests for fix/abcde-no-resume branch coverage gaps.

Covers:
- arm/ripper/utils.py: stale abcde workdir cleanup, select()-based timeout,
  iterator fallback, _stream_abcde_output timeout path, rip_music TimeoutError catch
- arm/ripper/identify.py: udev re-read after mount failure, unmounted non-music warning
- arm/api/v1/drives.py: rescan trigger after tray close
- arm/ripper/logger.py: stale log truncation
"""
import os
import select
import subprocess
import tempfile
import time
import unittest.mock
from unittest.mock import patch, MagicMock, PropertyMock

import pytest

from arm.database import db
from arm.models.job import Job, JobState
from arm.models.config import Config


# ── utils.py: stale abcde workdir cleanup ────────────────────────────────

class TestStaleAbcdeWorkdirCleanup:
    """Verify rip_music removes stale /home/arm/abcde.* dirs before ripping."""

    def test_stale_workdirs_removed(self, app_context, sample_job, tmp_path):
        """Stale abcde workdirs matching /home/arm/abcde.* are removed."""
        from arm.ripper import utils

        sample_job.disctype = "music"
        db.session.commit()

        # Create fake stale dirs in a temp location
        stale1 = tmp_path / "abcde.12345"
        stale1.mkdir()
        (stale1 / "track01.wav").write_text("stale data")
        stale2 = tmp_path / "abcde.67890"
        stale2.mkdir()
        # A file (not dir) should NOT be removed
        not_dir = tmp_path / "abcde.file"
        not_dir.write_text("not a dir")

        glob_pattern = str(tmp_path / "abcde.*")

        import glob as glob_mod
        with patch("arm.ripper.utils.cfg") as mock_cfg, \
             patch.object(glob_mod, "glob", return_value=[str(stale1), str(stale2), str(not_dir)]), \
             patch("arm.ripper.utils.subprocess.Popen") as mock_popen, \
             patch("arm.ripper.utils.database_updater"), \
             patch("arm.ripper.utils._stream_abcde_output", return_value=[]), \
             patch("arm.ripper.utils._update_music_tracks"):
            mock_cfg.arm_config = {
                "ABCDE_CONFIG_FILE": "/nonexistent/abcde.conf",
                "CD_RIP_TIMEOUT": 600,
                "AUDIO_FORMAT": "",
                "MUSIC_MULTI_DISC_SUBFOLDERS": False,
                "MUSIC_DISC_FOLDER_PATTERN": "Disc {num}",
                "RIP_SPEED_PROFILE": "safe",
            }

            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.wait.return_value = 0
            mock_popen.return_value = mock_proc

            utils.rip_music(sample_job, "test.log")

        # The dirs should have been removed by shutil.rmtree
        assert not stale1.exists()
        assert not stale2.exists()
        # The file should still exist (not a dir)
        assert not_dir.exists()


# ── utils.py: select()-based timeout in _stream_abcde_output ─────────────

class TestStreamAbcdeTimeout:
    """Test the select()-based timeout path in _stream_abcde_output."""

    def test_timeout_kills_process(self, app_context, sample_job):
        """When select() returns empty (no ready), proc is killed and TimeoutError raised."""
        from arm.ripper.utils import _stream_abcde_output

        mock_proc = MagicMock()
        # Make fileno() return a real int so use_select=True
        mock_proc.stdout.fileno.return_value = 99

        import select as select_mod
        with patch("arm.ripper.utils.cfg") as mock_cfg, \
             patch.object(select_mod, "select", return_value=([], [], [])):
            mock_cfg.arm_config = {"CD_RIP_TIMEOUT": 10}

            with pytest.raises(TimeoutError, match="timed out"):
                _stream_abcde_output(mock_proc, sample_job)

            mock_proc.kill.assert_called_once()
            mock_proc.wait.assert_called_once()

    def test_select_reads_lines_until_eof(self, app_context, sample_job):
        """When select() returns ready and readline returns data, lines are processed."""
        from arm.ripper.utils import _stream_abcde_output

        mock_proc = MagicMock()
        mock_proc.stdout.fileno.return_value = 99
        # Return two lines then EOF
        mock_proc.stdout.readline.side_effect = ["Grabbing track 1: foo\n", "Done.\n", ""]

        import select as select_mod
        with patch("arm.ripper.utils.cfg") as mock_cfg, \
             patch.object(select_mod, "select", return_value=([mock_proc.stdout], [], [])), \
             patch("arm.ripper.utils._apply_track_phases"):
            mock_cfg.arm_config = {"CD_RIP_TIMEOUT": 600}

            errors = _stream_abcde_output(mock_proc, sample_job)

        assert errors == []  # no error lines

    def test_iterator_fallback_when_fileno_unavailable(self, app_context, sample_job):
        """When fileno() raises, falls back to iterator-based reading."""
        from arm.ripper.utils import _stream_abcde_output

        mock_proc = MagicMock()
        mock_proc.stdout.fileno.side_effect = AttributeError("no fileno")
        # Make stdout iterable
        mock_proc.stdout.__iter__ = MagicMock(return_value=iter([
            "[ERROR] CDROM drive unavailable\n",
            "Grabbing track 1: ok\n",
            "",  # EOF
        ]))

        with patch("arm.ripper.utils.cfg") as mock_cfg, \
             patch("arm.ripper.utils._apply_track_phases"):
            mock_cfg.arm_config = {"CD_RIP_TIMEOUT": 600}

            errors = _stream_abcde_output(mock_proc, sample_job)

        assert len(errors) == 1
        assert "CDROM drive unavailable" in errors[0]

    def test_iterator_fallback_when_fileno_returns_non_int(self, app_context, sample_job):
        """When fileno() returns non-int, falls back to iterator."""
        from arm.ripper.utils import _stream_abcde_output

        mock_proc = MagicMock()
        mock_proc.stdout.fileno.return_value = "not_an_int"
        mock_proc.stdout.__iter__ = MagicMock(return_value=iter(["info line\n", ""]))

        with patch("arm.ripper.utils.cfg") as mock_cfg, \
             patch("arm.ripper.utils._apply_track_phases"):
            mock_cfg.arm_config = {"CD_RIP_TIMEOUT": 600}

            errors = _stream_abcde_output(mock_proc, sample_job)

        assert errors == []


# ── utils.py: rip_music TimeoutError catch block ─────────────────────────

class TestRipMusicTimeoutCatch:
    """Test that rip_music catches TimeoutError from _stream_abcde_output."""

    def test_timeout_sets_failure_status(self, app_context, sample_job):
        """When _stream_abcde_output raises TimeoutError, job is set to FAILURE."""
        from arm.ripper import utils

        sample_job.disctype = "music"
        db.session.commit()

        import glob as glob_mod
        with patch("arm.ripper.utils.cfg") as mock_cfg, \
             patch.object(glob_mod, "glob", return_value=[]), \
             patch("arm.ripper.utils.subprocess.Popen") as mock_popen, \
             patch("arm.ripper.utils.database_updater") as mock_db_update, \
             patch("arm.ripper.utils._stream_abcde_output",
                   side_effect=TimeoutError("CD rip timed out after 600s")), \
             patch("arm.ripper.utils._update_music_tracks") as mock_tracks:
            mock_cfg.arm_config = {
                "ABCDE_CONFIG_FILE": "/nonexistent/abcde.conf",
                "CD_RIP_TIMEOUT": 600,
                "AUDIO_FORMAT": "",
                "MUSIC_MULTI_DISC_SUBFOLDERS": False,
                "MUSIC_DISC_FOLDER_PATTERN": "Disc {num}",
                "RIP_SPEED_PROFILE": "safe",
            }
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_popen.return_value = mock_proc

            result = utils.rip_music(sample_job, "test.log")

        assert result is False
        # Check that database_updater was called with FAILURE status
        failure_calls = [c for c in mock_db_update.call_args_list
                         if c[0][0].get("status") == JobState.FAILURE.value]
        assert len(failure_calls) == 1
        assert "timed out" in failure_calls[0][0][0]["errors"]
        # Tracks must be marked ripped=False with status='failed' (the
        # generic per-track failure value added in TrackStatus v2.0.0).
        from arm_contracts.enums import TrackStatus
        mock_tracks.assert_called_once_with(
            sample_job, ripped=False, status=TrackStatus.failed.value,
        )


# ── identify.py: udev re-read after mount failure ────────────────────────

class TestIdentifyUdevReread:
    """Test udev re-read path when mount fails with unknown disctype."""

    def test_udev_reread_when_mount_fails_unknown_disc(self, app_context, sample_job):
        """When mount fails and disctype is unknown, parse_udev is retried."""
        from arm.ripper.identify import identify
        from arm.ripper.utils import RipperException

        sample_job.disctype = "unknown"
        db.session.commit()

        def _set_music_disctype():
            sample_job.disctype = "music"

        with patch("arm.ripper.identify.check_mount", return_value=False), \
             patch("arm.ripper.identify.time.sleep"), \
             patch.object(Job, "parse_udev", side_effect=_set_music_disctype), \
             patch("arm.ripper.identify.utils.database_updater") as mock_db_update:

            identify(sample_job)

        # parse_udev was called to re-read udev properties
        # database_updater should have been called with the new disctype
        mock_db_update.assert_called_once()
        assert mock_db_update.call_args[0][0]["disctype"] == "music"

    def test_unmounted_non_music_disc_returns_with_warning(self, app_context, sample_job):
        """Non-music disc identified via udev but not mounted logs warning and returns."""
        from arm.ripper.identify import identify

        sample_job.disctype = "unknown"
        db.session.commit()

        def _set_dvd_disctype():
            sample_job.disctype = "dvd"

        with patch("arm.ripper.identify.check_mount", return_value=False), \
             patch("arm.ripper.identify.time.sleep"), \
             patch.object(Job, "parse_udev", side_effect=_set_dvd_disctype), \
             patch("arm.ripper.identify.utils.database_updater"), \
             patch("arm.ripper.identify.logging") as mock_logging:

            # Should return without raising (warning path, not error)
            identify(sample_job)

        # Should have logged a warning about unmounted disc
        warning_calls = [c for c in mock_logging.warning.call_args_list
                         if "not mounted" in str(c)]
        assert len(warning_calls) >= 1

    def test_still_unknown_after_reread_raises(self, app_context, sample_job):
        """When disctype remains unknown after re-read, RipperException is raised."""
        from arm.ripper.identify import identify
        from arm.ripper.utils import RipperException

        sample_job.disctype = "unknown"
        db.session.commit()

        with patch("arm.ripper.identify.check_mount", return_value=False), \
             patch("arm.ripper.identify.time.sleep"), \
             patch.object(Job, "parse_udev"):  # doesn't change disctype

            with pytest.raises(RipperException, match="Could not mount or identify"):
                identify(sample_job)


# ── drives.py: rescan trigger after tray close ───────────────────────────

class TestEjectRescanTrigger:
    """Test that eject with close/toggle triggers rescan_drive.sh."""

    @pytest.fixture
    def drive_client(self, app_context):
        """FastAPI test client for drives router."""
        from arm.app import app
        from fastapi.testclient import TestClient
        with TestClient(app, raise_server_exceptions=True) as client:
            yield client

    def _make_drive(self, db_obj, mount="/dev/sr0"):
        from arm.models.system_drives import SystemDrives
        drive = SystemDrives()
        drive.name = "Test Drive"
        drive.mount = mount
        drive.drive_mode = "auto"
        db_obj.session.add(drive)
        db_obj.session.commit()
        return drive

    def test_close_triggers_rescan(self, app_context, drive_client):
        """Closing tray triggers rescan_drive.sh subprocess."""
        _, db_obj = app_context
        drive = self._make_drive(db_obj)

        from arm.models.system_drives import SystemDrives
        with patch.object(SystemDrives, 'eject'), \
             patch("arm.api.v1.drives.os.path.isfile", return_value=True), \
             patch("arm.api.v1.drives.subprocess.Popen") as mock_popen:

            resp = drive_client.post(
                f'/api/v1/drives/{drive.drive_id}/eject',
                json={"method": "close"},
            )
            assert resp.status_code == 200
            mock_popen.assert_called_once()
            args = mock_popen.call_args[0][0]
            assert "rescan_drive.sh" in args[0]
            assert args[1] == "sr0"

    def test_toggle_triggers_rescan(self, app_context, drive_client):
        """Toggle method also triggers rescan."""
        _, db_obj = app_context
        drive = self._make_drive(db_obj)

        from arm.models.system_drives import SystemDrives
        with patch.object(SystemDrives, 'eject'), \
             patch("arm.api.v1.drives.os.path.isfile", return_value=True), \
             patch("arm.api.v1.drives.subprocess.Popen") as mock_popen:

            resp = drive_client.post(
                f'/api/v1/drives/{drive.drive_id}/eject',
                json={"method": "toggle"},
            )
            assert resp.status_code == 200
            mock_popen.assert_called_once()

    def test_eject_does_not_trigger_rescan(self, app_context, drive_client):
        """Eject method does NOT trigger rescan."""
        _, db_obj = app_context
        drive = self._make_drive(db_obj)

        from arm.models.system_drives import SystemDrives
        with patch.object(SystemDrives, 'eject'), \
             patch("arm.api.v1.drives.subprocess.Popen") as mock_popen:

            resp = drive_client.post(
                f'/api/v1/drives/{drive.drive_id}/eject',
                json={"method": "eject"},
            )
            assert resp.status_code == 200
            mock_popen.assert_not_called()

    def test_rescan_not_triggered_when_script_missing(self, app_context, drive_client):
        """If rescan_drive.sh doesn't exist, Popen is not called."""
        _, db_obj = app_context
        drive = self._make_drive(db_obj)

        from arm.models.system_drives import SystemDrives
        with patch.object(SystemDrives, 'eject'), \
             patch("arm.api.v1.drives.os.path.isfile", return_value=False), \
             patch("arm.api.v1.drives.subprocess.Popen") as mock_popen:

            resp = drive_client.post(
                f'/api/v1/drives/{drive.drive_id}/eject',
                json={"method": "close"},
            )
            assert resp.status_code == 200
            mock_popen.assert_not_called()


# ── logger.py: stale log truncation ──────────────────────────────────────

class TestStaleLogTruncation:
    """Test that setup_job_log truncates an existing log file."""

    def test_existing_log_is_truncated(self, tmp_path):
        """If a log file already exists for the job ID, it's truncated."""
        from arm.ripper import logger

        log_dir = tmp_path
        # Create a "stale" log file with prior content
        stale_log = log_dir / "JOB_42_Rip.log"
        stale_log.write_text("old stale content from previous job\n" * 50)
        assert stale_log.stat().st_size > 0

        with patch.dict(
            "arm.config.config.arm_config",
            {"LOGPATH": str(log_dir), "LOGLEVEL": "DEBUG"},
        ):
            job = MagicMock()
            job.job_id = 42
            job.label = "TEST"
            job.devpath = "/dev/sr0"

            log_full = logger.setup_job_log(job)

        # The file should exist but be truncated (or only have new content)
        assert os.path.isfile(log_full)
        # After truncation and handler setup, old content must be gone
        content = stale_log.read_text()
        assert "old stale content" not in content

    def test_no_log_file_no_error(self, tmp_path):
        """If no prior log file exists, setup_job_log works normally."""
        from arm.ripper import logger

        log_dir = tmp_path
        log_path = log_dir / "JOB_99_Rip.log"
        assert not log_path.exists()

        with patch.dict(
            "arm.config.config.arm_config",
            {"LOGPATH": str(log_dir), "LOGLEVEL": "DEBUG"},
        ):
            job = MagicMock()
            job.job_id = 99
            job.label = "TEST"
            job.devpath = "/dev/sr0"

            log_full = logger.setup_job_log(job)

        assert log_full == str(log_path)
        assert job.logfile == "JOB_99_Rip.log"
