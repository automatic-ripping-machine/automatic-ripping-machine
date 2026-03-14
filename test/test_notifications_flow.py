"""Tests for notification flow and ripping dispatch — README Features:
Notifications (Apprise), Audio CD Ripping, Data Disc ISO Backup.

Covers notify(), notify_entry(), rip_music(), rip_data(),
clean_old_jobs(), and the full notification pipeline.
"""
import os
import unittest.mock

import pytest


class TestNotify:
    """Test notify() full notification pipeline."""

    def _make_job(self):
        job = unittest.mock.MagicMock()
        job.job_id = 42
        job.title = 'Serial Mom'
        job.title_auto = 'SERIAL_MOM'
        job.video_type = 'movie'
        job.disctype = 'bluray'
        job.label = 'SERIAL_MOM'
        job.status = 'active'
        job.path = None
        job.raw_path = None
        job.transcode_path = None
        job.year = '1994'
        return job

    def test_prepends_arm_name(self):
        """ARM_NAME is prepended to notification title."""
        from arm.ripper.utils import notify
        import arm.config.config as cfg

        job = self._make_job()
        original = cfg.arm_config.get('ARM_NAME', '')
        cfg.arm_config['ARM_NAME'] = 'MyARM'
        try:
            with unittest.mock.patch('arm.ripper.utils.database_adder'), \
                 unittest.mock.patch('arm.ripper.utils.bash_notify') as mock_bash, \
                 unittest.mock.patch('apprise.Apprise'):
                notify(job, 'Test Title', 'Test Body')
                call_args = mock_bash.call_args[0]
                assert '[MyARM]' in call_args[1]
        finally:
            cfg.arm_config['ARM_NAME'] = original

    def test_appends_job_id(self):
        """Job ID is appended when NOTIFY_JOBID is True."""
        from arm.ripper.utils import notify
        import arm.config.config as cfg

        job = self._make_job()
        original_name = cfg.arm_config.get('ARM_NAME', '')
        original_jobid = cfg.arm_config.get('NOTIFY_JOBID', False)
        cfg.arm_config['ARM_NAME'] = ''
        cfg.arm_config['NOTIFY_JOBID'] = True
        try:
            with unittest.mock.patch('arm.ripper.utils.database_adder'), \
                 unittest.mock.patch('arm.ripper.utils.bash_notify') as mock_bash, \
                 unittest.mock.patch('apprise.Apprise'):
                notify(job, 'Title', 'Body')
                call_args = mock_bash.call_args[0]
                assert '42' in call_args[1]
        finally:
            cfg.arm_config['ARM_NAME'] = original_name
            cfg.arm_config['NOTIFY_JOBID'] = original_jobid

    def test_creates_db_notification(self):
        """notify() creates a Notifications record in the database."""
        from arm.ripper.utils import notify
        import arm.config.config as cfg

        job = self._make_job()
        original = cfg.arm_config.get('ARM_NAME', '')
        cfg.arm_config['ARM_NAME'] = ''
        try:
            with unittest.mock.patch('arm.ripper.utils.database_adder') as mock_adder, \
                 unittest.mock.patch('arm.ripper.utils.bash_notify'), \
                 unittest.mock.patch('apprise.Apprise'):
                notify(job, 'Title', 'Body')
                mock_adder.assert_called_once()
        finally:
            cfg.arm_config['ARM_NAME'] = original

    def test_apprise_channels_configured(self):
        """Apprise adds channels for configured keys."""
        from arm.ripper.utils import notify
        import arm.config.config as cfg

        job = self._make_job()
        originals = {}
        keys = ['ARM_NAME', 'PB_KEY', 'IFTTT_KEY', 'IFTTT_EVENT',
                'PO_USER_KEY', 'PO_APP_KEY', 'JSON_URL', 'APPRISE']
        for k in keys:
            originals[k] = cfg.arm_config.get(k, '')
        cfg.arm_config['ARM_NAME'] = ''
        cfg.arm_config['PB_KEY'] = 'test_pb_key'
        cfg.arm_config['IFTTT_KEY'] = 'test_ifttt'
        cfg.arm_config['IFTTT_EVENT'] = 'arm_event'
        cfg.arm_config['PO_USER_KEY'] = 'po_user'
        cfg.arm_config['PO_APP_KEY'] = 'po_app'
        cfg.arm_config['JSON_URL'] = 'http://example.com/webhook'
        cfg.arm_config['APPRISE'] = ''
        try:
            with unittest.mock.patch('arm.ripper.utils.database_adder'), \
                 unittest.mock.patch('arm.ripper.utils.bash_notify'), \
                 unittest.mock.patch('apprise.Apprise') as MockApprise:
                mock_instance = MockApprise.return_value
                mock_instance.__len__ = lambda self: 4  # 4 services added
                notify(job, 'Title', 'Body')
                # PB_KEY, IFTTT, Pushover, JSON_URL = 4 add calls
                assert mock_instance.add.call_count == 4
                mock_instance.notify.assert_called_once()
        finally:
            for k, v in originals.items():
                cfg.arm_config[k] = v


class TestNotifyEntry:
    """Test notify_entry() per-disc-type notifications."""

    def _make_job(self, disctype='dvd'):
        job = unittest.mock.MagicMock()
        job.job_id = 1
        job.disctype = disctype
        job.title = 'Test Title'
        job.label = 'TEST_LABEL'
        job.config.MAINFEATURE = False
        job.config.WEBSERVER_PORT = 8080
        return job

    def test_dvd_notification_includes_title(self):
        """DVD/Bluray notification includes disc title and edit link."""
        from arm.ripper.utils import notify_entry
        import arm.config.config as cfg

        job = self._make_job('dvd')
        original = cfg.arm_config.get('UI_BASE_URL', '')
        cfg.arm_config['UI_BASE_URL'] = 'http://myarm:8080'
        try:
            with unittest.mock.patch('arm.ripper.utils.database_adder'), \
                 unittest.mock.patch('arm.ripper.utils.notify') as mock_notify:
                notify_entry(job)
                call_args = mock_notify.call_args[0]
                assert 'Test Title' in call_args[2]
                assert 'dvd' in call_args[2]
        finally:
            cfg.arm_config['UI_BASE_URL'] = original

    def test_music_notification(self):
        """Music CD notification mentions the label."""
        from arm.ripper.utils import notify_entry

        job = self._make_job('music')
        with unittest.mock.patch('arm.ripper.utils.database_adder'), \
             unittest.mock.patch('arm.ripper.utils.notify') as mock_notify:
            notify_entry(job)
            call_args = mock_notify.call_args[0]
            assert 'music' in call_args[2].lower()
            assert 'TEST_LABEL' in call_args[2]

    def test_data_notification(self):
        """Data disc notification mentions 'data disc'."""
        from arm.ripper.utils import notify_entry

        job = self._make_job('data')
        with unittest.mock.patch('arm.ripper.utils.database_adder'), \
             unittest.mock.patch('arm.ripper.utils.notify') as mock_notify:
            notify_entry(job)
            call_args = mock_notify.call_args[0]
            assert 'data' in call_args[2].lower()

    def test_unknown_disc_raises_ripper_exception(self):
        """Unknown disc type raises RipperException."""
        from arm.ripper.utils import notify_entry, RipperException

        job = self._make_job('unknown')
        with unittest.mock.patch('arm.ripper.utils.database_adder'), \
             unittest.mock.patch('arm.ripper.utils.notify'), \
             pytest.raises(RipperException):
            notify_entry(job)


class TestRipMusic:
    """Test rip_music() audio CD ripping dispatch."""

    def _make_job(self):
        job = unittest.mock.MagicMock()
        job.disctype = 'music'
        job.devpath = '/dev/sr0'
        job.config.LOGPATH = '/tmp'
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
        cfg.arm_config['ABCDE_CONFIG_FILE'] = '/tmp/test_abcde.conf'
        try:
            mock_proc = self._mock_popen(0)
            with unittest.mock.patch('os.path.isfile', return_value=True), \
                 unittest.mock.patch('arm.ripper.utils.database_updater'), \
                 unittest.mock.patch('arm.ripper.utils._poll_music_progress'), \
                 unittest.mock.patch('arm.ripper.utils._update_music_tracks'), \
                 unittest.mock.patch('subprocess.Popen',
                                     return_value=mock_proc) as mock_cmd:
                result = rip_music(job, 'test.log')
                assert result is True
                cmd = mock_cmd.call_args[0][0]
                assert '-c /tmp/test_abcde.conf' in cmd
        finally:
            cfg.arm_config['ABCDE_CONFIG_FILE'] = original

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
                 unittest.mock.patch('arm.ripper.utils._poll_music_progress'), \
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
        """Sets job status to 'ripping' before calling abcde."""
        from arm.ripper.utils import rip_music
        import arm.config.config as cfg

        job = self._make_job()
        original = cfg.arm_config.get('ABCDE_CONFIG_FILE', '')
        cfg.arm_config['ABCDE_CONFIG_FILE'] = ''
        try:
            mock_proc = self._mock_popen(0)
            with unittest.mock.patch('os.path.isfile', return_value=False), \
                 unittest.mock.patch('arm.ripper.utils.database_updater') as mock_updater, \
                 unittest.mock.patch('arm.ripper.utils._poll_music_progress'), \
                 unittest.mock.patch('arm.ripper.utils._update_music_tracks'), \
                 unittest.mock.patch('subprocess.Popen', return_value=mock_proc):
                rip_music(job, 'test.log')
                # First call should set status to ripping
                first_call = mock_updater.call_args_list[0][0][0]
                assert first_call['status'] == 'ripping'
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
                 unittest.mock.patch('arm.ripper.utils._poll_music_progress'), \
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
        job.status = 'ripping'
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
        job.status = 'ripping'
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
        assert job.status == 'ripping'  # unchanged
