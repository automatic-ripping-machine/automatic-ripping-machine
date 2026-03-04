"""Tests for ripping business logic (no hardware required)."""
import datetime
import os
import unittest.mock

import pytest


class TestJobState:
    """Test JobState enum and status sets."""

    def test_success_value(self):
        from arm.models.job import JobState
        assert JobState.SUCCESS.value == "success"

    def test_failure_value(self):
        from arm.models.job import JobState
        assert JobState.FAILURE.value == "fail"

    def test_idle_value(self):
        from arm.models.job import JobState
        assert JobState.IDLE.value == "active"

    def test_ripping_value(self):
        from arm.models.job import JobState
        assert JobState.VIDEO_RIPPING.value == "ripping"

    def test_transcoding_value(self):
        from arm.models.job import JobState
        assert JobState.TRANSCODE_ACTIVE.value == "transcoding"

    def test_finished_set(self):
        from arm.models.job import JobState, JOB_STATUS_FINISHED
        assert JobState.SUCCESS in JOB_STATUS_FINISHED
        assert JobState.FAILURE in JOB_STATUS_FINISHED
        assert JobState.IDLE not in JOB_STATUS_FINISHED

    def test_ripping_set(self):
        from arm.models.job import JobState, JOB_STATUS_RIPPING
        assert JobState.VIDEO_RIPPING in JOB_STATUS_RIPPING
        assert JobState.AUDIO_RIPPING in JOB_STATUS_RIPPING
        assert JobState.IDLE not in JOB_STATUS_RIPPING

    def test_transcoding_set(self):
        from arm.models.job import JobState, JOB_STATUS_TRANSCODING
        assert JobState.TRANSCODE_ACTIVE in JOB_STATUS_TRANSCODING
        assert JobState.TRANSCODE_WAITING in JOB_STATUS_TRANSCODING
        assert JobState.IDLE not in JOB_STATUS_TRANSCODING


class TestRipData:
    """Test rip_data() data disc ripping logic."""

    def test_duplicate_label_gets_unique_filename(self, app_context, sample_job, tmp_path):
        """Second data disc with same label should NOT overwrite the first (#1651)."""
        from arm.ripper.utils import rip_data

        raw = tmp_path / "raw"
        completed = tmp_path / "completed"
        raw.mkdir()
        completed.mkdir()

        sample_job.disctype = "data"
        sample_job.label = "MYDATA"
        sample_job.video_type = "unknown"
        sample_job.config.RAW_PATH = str(raw)
        sample_job.config.COMPLETED_PATH = str(completed)

        # First rip: create the raw directory so the second call thinks it's a collision
        (raw / "MYDATA").mkdir()

        with unittest.mock.patch('arm.ripper.utils.subprocess.check_output') as mock_dd, \
             unittest.mock.patch('arm.ripper.utils.shutil.move') as mock_move:
            mock_dd.return_value = b""
            rip_data(sample_job)

            # shutil.move should have been called with a timestamped .iso filename
            assert mock_move.called, "shutil.move was never called"
            final_file = mock_move.call_args[0][1]  # full_final_file
            # The ISO filename should NOT be just "MYDATA.iso" — it should have a suffix
            assert os.path.basename(final_file) != "MYDATA.iso"

    def test_unique_label_uses_plain_filename(self, app_context, sample_job, tmp_path):
        """Data disc with unique label uses plain label as filename."""
        from arm.ripper.utils import rip_data

        raw = tmp_path / "raw"
        completed = tmp_path / "completed"
        raw.mkdir()
        completed.mkdir()

        sample_job.disctype = "data"
        sample_job.label = "UNIQUE_DISC"
        sample_job.video_type = "unknown"
        sample_job.config.RAW_PATH = str(raw)
        sample_job.config.COMPLETED_PATH = str(completed)

        with unittest.mock.patch('arm.ripper.utils.subprocess.check_output') as mock_dd, \
             unittest.mock.patch('arm.ripper.utils.shutil.move') as mock_move:
            mock_dd.return_value = b""
            rip_data(sample_job)

            assert mock_move.called, "shutil.move was never called"
            final_file = mock_move.call_args[0][1]
            assert final_file.endswith("UNIQUE_DISC.iso")


class TestRipMusic:
    """Test rip_music() audio CD ripping logic."""

    def test_abcde_error_in_log_detected(self, app_context, sample_job, tmp_path):
        """abcde exit 0 with [ERROR] in log should be treated as failure (#1526)."""
        from arm.ripper.utils import rip_music

        sample_job.disctype = "music"
        sample_job.config.LOGPATH = str(tmp_path)

        # Write a log file with abcde error markers
        logfile = "test_music.log"
        (tmp_path / logfile).write_text(
            "Grabbing track 01...\n"
            "[ERROR] cdparanoia could not read disc\n"
            "CDROM drive unavailable\n"
        )

        with unittest.mock.patch('arm.ripper.utils.subprocess.check_output', return_value=b""), \
             unittest.mock.patch('arm.ripper.utils.cfg') as mock_cfg:
            mock_cfg.arm_config = {"ABCDE_CONFIG_FILE": "/nonexistent"}
            result = rip_music(sample_job, logfile)

        assert result is False
        assert sample_job.status == "fail"

    def test_abcde_clean_log_succeeds(self, app_context, sample_job, tmp_path):
        """abcde exit 0 with clean log should be treated as success."""
        from arm.ripper.utils import rip_music

        sample_job.disctype = "music"
        sample_job.config.LOGPATH = str(tmp_path)

        logfile = "test_music.log"
        (tmp_path / logfile).write_text(
            "Grabbing track 01...\n"
            "Grabbing track 02...\n"
            "Finished.\n"
        )

        with unittest.mock.patch('arm.ripper.utils.subprocess.check_output', return_value=b""), \
             unittest.mock.patch('arm.ripper.utils.cfg') as mock_cfg:
            mock_cfg.arm_config = {"ABCDE_CONFIG_FILE": "/nonexistent"}
            result = rip_music(sample_job, logfile)

        assert result is True

    def test_abcde_nonzero_exit_detected(self, app_context, sample_job, tmp_path):
        """abcde with non-zero exit code should be caught."""
        import subprocess
        from arm.ripper.utils import rip_music

        sample_job.disctype = "music"
        sample_job.config.LOGPATH = str(tmp_path)

        with unittest.mock.patch('arm.ripper.utils.subprocess.check_output',
                                 side_effect=subprocess.CalledProcessError(1, "abcde", b"error")), \
             unittest.mock.patch('arm.ripper.utils.cfg') as mock_cfg:
            mock_cfg.arm_config = {"ABCDE_CONFIG_FILE": "/nonexistent"}
            result = rip_music(sample_job, "test.log")

        assert result is False


class TestMakemkvDiscDiscovery:
    """Test MakeMKV disc number discovery guard (#1545)."""

    def test_mdisc_none_no_drives_raises(self, app_context, sample_job):
        """When job.drive is None and get_drives yields nothing, raise ValueError."""
        from arm.ripper.makemkv import makemkv

        # Ensure no SystemDrives linked
        assert sample_job.drive is None

        with unittest.mock.patch('arm.ripper.makemkv.prep_mkv'), \
             unittest.mock.patch('arm.ripper.makemkv.get_drives', return_value=iter([])):
            with pytest.raises(ValueError, match="No MakeMKV disc number"):
                makemkv(sample_job)

    def test_mdisc_none_drive_exists_but_mdisc_null_raises(self, app_context, sample_job):
        """When job.drive exists but mdisc is None, and scan finds no match, raise ValueError."""
        from arm.models.system_drives import SystemDrives
        from arm.database import db
        from arm.ripper.makemkv import makemkv

        # Create a SystemDrives row linked to this job, but mdisc=None
        drive = SystemDrives()
        drive.mount = sample_job.devpath
        drive.job_id_current = sample_job.job_id
        drive.mdisc = None
        db.session.add(drive)
        db.session.commit()
        db.session.refresh(sample_job)
        assert sample_job.drive is not None
        assert sample_job.drive.mdisc is None

        with unittest.mock.patch('arm.ripper.makemkv.prep_mkv'), \
             unittest.mock.patch('arm.ripper.makemkv.get_drives', return_value=iter([])):
            with pytest.raises(ValueError, match="No MakeMKV disc number"):
                makemkv(sample_job)

    def test_mdisc_populated_skips_scan(self, app_context, sample_job, tmp_path):
        """When job.drive.mdisc is already set, skip disc:9999 scan entirely."""
        from arm.models.system_drives import SystemDrives
        from arm.database import db
        from arm.ripper.makemkv import makemkv

        # Create a SystemDrives row with mdisc already populated
        drive = SystemDrives()
        drive.mount = sample_job.devpath
        drive.job_id_current = sample_job.job_id
        drive.mdisc = 0
        db.session.add(drive)
        db.session.commit()
        db.session.refresh(sample_job)

        mock_get_drives = unittest.mock.MagicMock()

        with unittest.mock.patch('arm.ripper.makemkv.prep_mkv'), \
             unittest.mock.patch('arm.ripper.makemkv.get_drives', mock_get_drives), \
             unittest.mock.patch('arm.ripper.makemkv.setup_rawpath', return_value=str(tmp_path)), \
             unittest.mock.patch('arm.ripper.makemkv.makemkv_mkv'), \
             unittest.mock.patch.object(sample_job, 'eject'), \
             unittest.mock.patch('arm.ripper.makemkv._reconcile_filenames'), \
             unittest.mock.patch.object(sample_job, 'build_raw_path', return_value='raw'):
            makemkv(sample_job)

        # get_drives should NOT have been called — mdisc was already set
        mock_get_drives.assert_not_called()


class TestDuplicateRunCheck:
    """Test duplicate_run_check() grace period and active-job detection."""

    def _make_drive(self, db, devpath, job_current=None, job_previous=None):
        from arm.models.system_drives import SystemDrives
        drive = SystemDrives()
        drive.mount = devpath
        drive.stale = False
        if job_current:
            drive.job_id_current = job_current.job_id
        if job_previous:
            drive.job_id_previous = job_previous.job_id
        db.session.add(drive)
        db.session.commit()
        return drive

    def test_active_job_raises(self, app_context, sample_job):
        """Active job on drive should raise RipperException."""
        from arm.ripper.utils import duplicate_run_check, RipperException
        _, db = app_context

        sample_job.start_time = datetime.datetime.now()
        db.session.commit()
        self._make_drive(db, sample_job.devpath, job_current=sample_job)

        with pytest.raises(RipperException, match="Job already running"):
            duplicate_run_check(sample_job.devpath)

    def test_previous_job_within_grace_period_raises(self, app_context, sample_job):
        """Previous job finished <30s ago should raise (grace period)."""
        from arm.ripper.utils import duplicate_run_check, RipperException
        from arm.models.job import Job
        _, db = app_context

        # Create a previous job that finished 5 seconds ago
        with unittest.mock.patch.object(Job, 'parse_udev'), \
             unittest.mock.patch.object(Job, 'get_pid'):
            prev_job = Job('/dev/sr0')
        prev_job.status = "success"
        prev_job.stop_time = datetime.datetime.now() - datetime.timedelta(seconds=5)
        prev_job.devpath = sample_job.devpath
        db.session.add(prev_job)
        db.session.flush()

        self._make_drive(db, sample_job.devpath, job_previous=prev_job)

        with pytest.raises(RipperException, match="Post-eject grace period"):
            duplicate_run_check(sample_job.devpath)

    def test_previous_job_beyond_grace_period_passes(self, app_context, sample_job):
        """Previous job finished >30s ago should NOT raise."""
        from arm.ripper.utils import duplicate_run_check
        from arm.models.job import Job
        _, db = app_context

        with unittest.mock.patch.object(Job, 'parse_udev'), \
             unittest.mock.patch.object(Job, 'get_pid'):
            prev_job = Job('/dev/sr0')
        prev_job.status = "success"
        prev_job.stop_time = datetime.datetime.now() - datetime.timedelta(seconds=60)
        prev_job.devpath = sample_job.devpath
        db.session.add(prev_job)
        db.session.flush()

        self._make_drive(db, sample_job.devpath, job_previous=prev_job)

        # Should not raise
        duplicate_run_check(sample_job.devpath)

    def test_no_previous_job_passes(self, app_context, sample_job):
        """No previous job on drive should NOT raise."""
        from arm.ripper.utils import duplicate_run_check
        _, db = app_context

        self._make_drive(db, sample_job.devpath)

        # Should not raise
        duplicate_run_check(sample_job.devpath)


class TestCleanOldJobs:
    """Test clean_old_jobs() status exclusions."""

    def _make_job(self, db, status, pid=99999):
        from arm.models.job import Job
        with unittest.mock.patch.object(Job, 'parse_udev'), \
             unittest.mock.patch.object(Job, 'get_pid'):
            job = Job('/dev/sr0')
        job.status = status
        job.pid = pid
        job.pid_hash = 0
        db.session.add(job)
        db.session.commit()
        return job

    def test_waiting_transcode_not_marked_failed(self, app_context):
        """Job in waiting_transcode with dead PID should NOT be marked failed."""
        from arm.ripper.utils import clean_old_jobs
        _, db = app_context

        job = self._make_job(db, "waiting_transcode", pid=99999)

        with unittest.mock.patch('arm.ripper.utils.psutil.pid_exists', return_value=False):
            clean_old_jobs()

        db.session.refresh(job)
        assert job.status == "waiting_transcode"

    def test_transcoding_not_marked_failed(self, app_context):
        """Job in transcoding with dead PID should NOT be marked failed."""
        from arm.ripper.utils import clean_old_jobs
        _, db = app_context

        job = self._make_job(db, "transcoding", pid=99999)

        with unittest.mock.patch('arm.ripper.utils.psutil.pid_exists', return_value=False):
            clean_old_jobs()

        db.session.refresh(job)
        assert job.status == "transcoding"

    def test_active_with_dead_pid_marked_failed(self, app_context):
        """Job in active state with dead PID should be marked failed."""
        from arm.ripper.utils import clean_old_jobs
        _, db = app_context

        job = self._make_job(db, "active", pid=99999)

        with unittest.mock.patch('arm.ripper.utils.psutil.pid_exists', return_value=False):
            clean_old_jobs()

        db.session.refresh(job)
        assert job.status == "fail"


class TestDriveReadinessTimeout:
    """Test drive readiness polling logic in setup()."""

    def test_disc_ok_ready_immediately(self, app_context, sample_job):
        """DISC_OK on first poll should return ready."""
        from arm.models.system_drives import CDS, SystemDrives
        _, db = app_context

        drive = SystemDrives()
        drive.mount = sample_job.devpath
        drive.stale = False
        db.session.add(drive)
        db.session.commit()

        # Simulate tray_status returning DISC_OK
        with unittest.mock.patch.object(SystemDrives, 'tray_status') as mock_ts:
            mock_ts.side_effect = lambda: setattr(drive, '_tray', CDS.DISC_OK.value)
            drive._tray = CDS.DISC_OK.value
            assert drive.ready is True

    def test_no_disc_returns_not_ready(self, app_context, sample_job):
        """NO_DISC state should indicate drive is not ready."""
        from arm.models.system_drives import CDS, SystemDrives
        _, db = app_context

        drive = SystemDrives()
        drive.mount = sample_job.devpath
        drive.stale = False
        db.session.add(drive)
        db.session.commit()

        drive._tray = CDS.NO_DISC.value
        assert drive.ready is False
        assert drive.tray == CDS.NO_DISC
