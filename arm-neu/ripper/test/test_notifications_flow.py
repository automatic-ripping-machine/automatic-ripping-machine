"""Tests for notification flow and ripping dispatch — README Features:
Notifications (event publish), Audio CD Ripping, Data Disc ISO Backup.

Covers notify_entry(), rip_music(), rip_data(), and clean_old_jobs().
The legacy ``notify()`` / ``bash_notify()`` pipeline was removed in
N19 — channels are now driven by ``publish_event`` + the outbox
dispatcher.
"""
import os
import tempfile
import unittest.mock

import pytest


class TestNotifyEntry:
    """Test notify_entry() publishes JobStartedEvent.

    The per-disc-type text branching that lived here historically has
    moved into channel-side templates rendered from a single typed
    event. notify_entry's job now is (a) write a history row, (b)
    publish a JobStartedEvent with the correct disctype, (c) reject
    truly-unrecognised disctypes early.
    """

    def _make_job(self, disctype='dvd'):
        job = unittest.mock.MagicMock()
        job.job_id = 1
        job.disctype = disctype
        job.title = 'Test Title'
        job.label = 'TEST_LABEL'
        job.imdb_id = None
        job.devpath = '/dev/sr0'
        job.config.MAINFEATURE = False
        job.config.WEBSERVER_PORT = 8080
        return job

    def test_dvd_publishes_started_event(self):
        from arm.ripper.utils import notify_entry
        from arm_contracts import JobStartedEvent
        from arm_contracts.enums import Disctype

        job = self._make_job('dvd')
        with unittest.mock.patch('arm.ripper.utils.database_adder'), \
             unittest.mock.patch('arm.notifications.publish_event') as mock_publish:
            notify_entry(job)
            mock_publish.assert_called_once()
            event = mock_publish.call_args[0][0]
            assert isinstance(event, JobStartedEvent)
            assert event.job_disc_type == Disctype.dvd
            assert event.job_title == 'Test Title'
            assert event.drive_mount == '/dev/sr0'

    def test_music_publishes_started_event(self):
        from arm.ripper.utils import notify_entry
        from arm_contracts import JobStartedEvent
        from arm_contracts.enums import Disctype

        job = self._make_job('music')
        with unittest.mock.patch('arm.ripper.utils.database_adder'), \
             unittest.mock.patch('arm.notifications.publish_event') as mock_publish:
            notify_entry(job)
            mock_publish.assert_called_once()
            event = mock_publish.call_args[0][0]
            assert isinstance(event, JobStartedEvent)
            assert event.job_disc_type == Disctype.music

    def test_data_publishes_started_event(self):
        from arm.ripper.utils import notify_entry
        from arm_contracts import JobStartedEvent
        from arm_contracts.enums import Disctype

        job = self._make_job('data')
        with unittest.mock.patch('arm.ripper.utils.database_adder'), \
             unittest.mock.patch('arm.notifications.publish_event') as mock_publish:
            notify_entry(job)
            mock_publish.assert_called_once()
            event = mock_publish.call_args[0][0]
            assert isinstance(event, JobStartedEvent)
            assert event.job_disc_type == Disctype.data

    def test_unknown_disc_raises_ripper_exception(self):
        """Unknown disc type raises RipperException — preserving the
        pre-N17 behaviour for anything outside the closed set."""
        from arm.ripper.utils import notify_entry, RipperException

        job = self._make_job('unknown')
        with unittest.mock.patch('arm.ripper.utils.database_adder'), \
             unittest.mock.patch('arm.notifications.publish_event'), \
             pytest.raises(RipperException):
            notify_entry(job)


class TestRipMusic:
    """Test rip_music() audio CD ripping dispatch."""

    def _make_job(self):
        job = unittest.mock.MagicMock()
        job.disctype = 'music'
        job.devpath = '/dev/sr0'
        job.config.LOGPATH = tempfile.gettempdir()
        return job

    @staticmethod
    def _mock_popen(returncode=0):
        """Create a mock Popen that finishes immediately with given return code."""
        proc = unittest.mock.MagicMock()
        proc.poll.return_value = returncode
        proc.wait.return_value = returncode
        proc.returncode = returncode
        return proc

    def test_uses_abcde_config_when_exists(self):
        """Uses custom abcde config file when it exists."""
        from arm.ripper.utils import rip_music
        import arm.config.config as cfg

        job = self._make_job()
        original = cfg.arm_config.get('ABCDE_CONFIG_FILE', '')
        fd, abcde_conf = tempfile.mkstemp(prefix='test_abcde_', suffix='.conf')
        os.close(fd)
        cfg.arm_config['ABCDE_CONFIG_FILE'] = abcde_conf
        try:
            mock_proc = self._mock_popen(0)
            with unittest.mock.patch('os.path.isfile', return_value=True), \
                 unittest.mock.patch('arm.ripper.utils.database_updater'), \
                 unittest.mock.patch('arm.ripper.utils._stream_abcde_output', return_value=[]), \
                 unittest.mock.patch('arm.ripper.utils._update_music_tracks'), \
                 unittest.mock.patch('subprocess.Popen',
                                     return_value=mock_proc) as mock_cmd:
                result = rip_music(job, 'test.log')
                assert result is True
                cmd = mock_cmd.call_args[0][0]
                assert '-c' in cmd and abcde_conf in cmd
        finally:
            cfg.arm_config['ABCDE_CONFIG_FILE'] = original
            os.remove(abcde_conf)

    def test_default_abcde_when_no_config(self):
        """Uses default abcde when no config file exists."""
        from arm.ripper.utils import rip_music
        import arm.config.config as cfg

        job = self._make_job()
        original = cfg.arm_config.get('ABCDE_CONFIG_FILE', '')
        cfg.arm_config['ABCDE_CONFIG_FILE'] = '/nonexistent/path'
        try:
            mock_proc = self._mock_popen(0)
            with unittest.mock.patch('os.path.isfile', return_value=False), \
                 unittest.mock.patch('arm.ripper.utils.database_updater'), \
                 unittest.mock.patch('arm.ripper.utils._stream_abcde_output', return_value=[]), \
                 unittest.mock.patch('arm.ripper.utils._update_music_tracks'), \
                 unittest.mock.patch('subprocess.Popen',
                                     return_value=mock_proc) as mock_cmd:
                result = rip_music(job, 'test.log')
                assert result is True
                cmd = mock_cmd.call_args[0][0]
                assert '-c' not in cmd
        finally:
            cfg.arm_config['ABCDE_CONFIG_FILE'] = original

    def test_sets_status_ripping(self):
        """Sets job status to 'audio_ripping' before calling abcde."""
        from arm.ripper.utils import rip_music
        import arm.config.config as cfg

        job = self._make_job()
        original = cfg.arm_config.get('ABCDE_CONFIG_FILE', '')
        cfg.arm_config['ABCDE_CONFIG_FILE'] = ''
        try:
            mock_proc = self._mock_popen(0)
            with unittest.mock.patch('os.path.isfile', return_value=False), \
                 unittest.mock.patch('arm.ripper.utils.database_updater') as mock_updater, \
                 unittest.mock.patch('arm.ripper.utils._stream_abcde_output', return_value=[]), \
                 unittest.mock.patch('arm.ripper.utils._update_music_tracks'), \
                 unittest.mock.patch('subprocess.Popen', return_value=mock_proc):
                rip_music(job, 'test.log')
                # First call should set status to audio_ripping (the
                # disambiguated wire string for music ripping; was
                # 'ripping' before contracts v2.0.0 alias-collision fix).
                first_call = mock_updater.call_args_list[0][0][0]
                assert first_call['status'] == 'audio_ripping'
        finally:
            cfg.arm_config['ABCDE_CONFIG_FILE'] = original

    def test_returns_false_on_failure(self):
        """Returns False when abcde command fails (non-zero exit)."""
        from arm.ripper.utils import rip_music
        import arm.config.config as cfg

        job = self._make_job()
        original = cfg.arm_config.get('ABCDE_CONFIG_FILE', '')
        cfg.arm_config['ABCDE_CONFIG_FILE'] = ''
        try:
            mock_proc = self._mock_popen(1)
            with unittest.mock.patch('os.path.isfile', return_value=False), \
                 unittest.mock.patch('arm.ripper.utils.database_updater'), \
                 unittest.mock.patch('arm.ripper.utils._stream_abcde_output', return_value=[]), \
                 unittest.mock.patch('arm.ripper.utils._update_music_tracks'), \
                 unittest.mock.patch('subprocess.Popen', return_value=mock_proc):
                result = rip_music(job, 'test.log')
                assert result is False
        finally:
            cfg.arm_config['ABCDE_CONFIG_FILE'] = original

    def test_non_music_returns_false(self):
        """Non-music disc returns False immediately."""
        from arm.ripper.utils import rip_music

        job = self._make_job()
        job.disctype = 'dvd'
        result = rip_music(job, 'test.log')
        assert result is False


class TestRipData:
    """Test rip_data() ISO backup of data discs."""

    def _make_job(self, tmp_path):
        job = unittest.mock.MagicMock()
        job.label = 'DATA_DISC'
        job.devpath = '/dev/sr0'
        job.video_type = 'unknown'
        job.config.RAW_PATH = str(tmp_path / 'raw')
        job.config.COMPLETED_PATH = str(tmp_path / 'completed')
        job.config.LOGPATH = str(tmp_path / 'logs')
        job.logfile = 'test.log'
        os.makedirs(job.config.RAW_PATH)
        os.makedirs(job.config.COMPLETED_PATH)
        os.makedirs(job.config.LOGPATH)
        return job

    def test_creates_directories_and_rips(self, tmp_path):
        """Creates raw and final directories, runs dd, moves file."""
        from arm.ripper.utils import rip_data

        job = self._make_job(tmp_path)
        with unittest.mock.patch('subprocess.check_output', return_value=b''), \
             unittest.mock.patch('arm.ripper.utils.shutil.move') as mock_move, \
             unittest.mock.patch('arm.ripper.utils.database_updater'):
            result = rip_data(job)
        assert result is True
        mock_move.assert_called_once()

    def test_empty_label_defaults(self, tmp_path):
        """Empty label defaults to 'data-disc'."""
        from arm.ripper.utils import rip_data

        job = self._make_job(tmp_path)
        job.label = ""
        with unittest.mock.patch('subprocess.check_output', return_value=b''), \
             unittest.mock.patch('arm.ripper.utils.shutil.move'), \
             unittest.mock.patch('arm.ripper.utils.database_updater'):
            rip_data(job)
        assert job.label == 'data-disc'

    def test_dd_failure_sets_status_fail(self, tmp_path):
        """dd failure sets job status to 'fail'."""
        import subprocess
        from arm.ripper.utils import rip_data

        job = self._make_job(tmp_path)

        with unittest.mock.patch('subprocess.check_output',
                                 side_effect=subprocess.CalledProcessError(1, 'dd', b'error')), \
             unittest.mock.patch('arm.ripper.utils.database_updater') as mock_updater, \
             unittest.mock.patch('os.unlink'):
            result = rip_data(job)
        assert result is False
        # Should have called database_updater with failure status
        fail_calls = [c for c in mock_updater.call_args_list
                      if 'status' in c[0][0] and c[0][0]['status'] == 'fail']
        assert len(fail_calls) >= 1


class TestCleanOldJobs:
    """Test clean_old_jobs() zombie job cleanup."""

    def test_marks_abandoned_job_as_fail(self, app_context):
        """Jobs with non-existent PIDs are marked as 'fail'."""
        from arm.ripper.utils import clean_old_jobs
        from arm.models.job import Job
        from arm.database import db

        with unittest.mock.patch.object(Job, 'parse_udev'), \
             unittest.mock.patch.object(Job, 'get_pid'):
            job = Job('/dev/sr0')
        job.title = 'ZOMBIE'
        job.title_auto = 'ZOMBIE'
        job.label = 'ZOMBIE'
        job.status = 'video_ripping'
        job.pid = 999999  # Non-existent PID
        job.pid_hash = 0
        db.session.add(job)
        db.session.commit()

        with unittest.mock.patch('psutil.pid_exists', return_value=False):
            clean_old_jobs()

        db.session.refresh(job)
        assert job.status == 'fail'

    def test_leaves_running_job(self, app_context):
        """Jobs with running PIDs are NOT marked as fail."""
        from arm.ripper.utils import clean_old_jobs
        from arm.models.job import Job
        from arm.database import db

        with unittest.mock.patch.object(Job, 'parse_udev'), \
             unittest.mock.patch.object(Job, 'get_pid'):
            job = Job('/dev/sr0')
        job.title = 'RUNNING'
        job.title_auto = 'RUNNING'
        job.label = 'RUNNING'
        job.status = 'video_ripping'
        job.pid = os.getpid()  # This PID exists
        job.pid_hash = hash(unittest.mock.MagicMock())
        db.session.add(job)
        db.session.commit()

        mock_process = unittest.mock.MagicMock()
        with unittest.mock.patch('psutil.pid_exists', return_value=True), \
             unittest.mock.patch('psutil.Process', return_value=mock_process):
            # hash must match
            mock_process.__hash__ = lambda self: job.pid_hash
            clean_old_jobs()

        db.session.refresh(job)
        assert job.status == 'video_ripping'  # unchanged
