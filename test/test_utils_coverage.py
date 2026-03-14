"""Additional tests for arm/ripper/utils.py — covering missing lines.

Covers: bash_notify(), _build_job_env(), _move_to_shared_storage(),
transcoder_notify(), scan_emby(), notify_entry(), job_dupe_check(),
is_ripping_paused(), get_drive_mode(), clean_old_jobs(),
save_disc_poster(), _apply_track_phases(), _update_music_tracks(),
arm_setup(), duplicate_run_check().
"""
import datetime
import os
import unittest.mock

import pytest


class TestBuildJobEnv:
    """Test _build_job_env() environment variable construction."""

    def test_builds_env_dict(self):
        from arm.ripper.utils import _build_job_env

        job = unittest.mock.MagicMock()
        job.job_id = 42
        job.title = "Test Movie"
        job.title_auto = "Test Movie"
        job.year = "2024"
        job.video_type = "movie"
        job.disctype = "bluray"
        job.label = "TEST"
        job.status = "active"
        job.path = "/home/arm/media/completed/movies/Test Movie"
        job.raw_path = "/home/arm/media/raw/Test Movie"
        job.transcode_path = "/home/arm/media/transcode/Test Movie"
        job.config.RAW_PATH = "/home/arm/media/raw"
        job.config.COMPLETED_PATH = "/home/arm/media/completed"

        env = _build_job_env(job)
        assert env['ARM_JOB_ID'] == '42'
        assert env['ARM_TITLE'] == 'Test Movie'
        assert env['ARM_DISCTYPE'] == 'bluray'
        assert env['ARM_RAW_PATH_BASE'] == '/home/arm/media/raw'

    def test_handles_none_values(self):
        from arm.ripper.utils import _build_job_env

        job = unittest.mock.MagicMock()
        job.job_id = None
        job.title = None
        job.title_auto = None
        job.year = None
        job.video_type = None
        job.disctype = None
        job.label = None
        job.status = None
        job.path = None
        job.raw_path = None
        job.transcode_path = None
        job.config = None

        env = _build_job_env(job)
        assert env['ARM_JOB_ID'] == ''
        assert env['ARM_TITLE'] == ''


class TestBashNotify:
    """Test bash_notify() subprocess execution (lines 135-136)."""

    def test_calls_bash_script(self):
        from arm.ripper.utils import bash_notify

        cfg = {'BASH_SCRIPT': '/usr/local/bin/notify.sh'}
        job = unittest.mock.MagicMock()
        job.job_id = 1
        job.title = "Test"
        job.config = None

        with unittest.mock.patch('subprocess.run') as mock_run, \
             unittest.mock.patch('arm.ripper.utils._build_job_env', return_value={}):
            bash_notify(cfg, "Title", "Body", job)
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert '/usr/local/bin/notify.sh' in call_args
        assert 'Title' in call_args
        assert 'Body' in call_args

    def test_empty_script_does_nothing(self):
        from arm.ripper.utils import bash_notify

        cfg = {'BASH_SCRIPT': ''}
        with unittest.mock.patch('subprocess.run') as mock_run:
            bash_notify(cfg, "Title", "Body")
        mock_run.assert_not_called()

    def test_exception_caught(self):
        from arm.ripper.utils import bash_notify

        cfg = {'BASH_SCRIPT': '/bad/script.sh'}
        with unittest.mock.patch('subprocess.run', side_effect=OSError("not found")):
            # Should not raise
            bash_notify(cfg, "Title", "Body")


class TestMoveToSharedStorage:
    """Test _move_to_shared_storage() file movement (lines 145-153)."""

    def test_moves_directory(self, tmp_path):
        from arm.ripper.utils import _move_to_shared_storage

        local_raw = str(tmp_path / "local")
        shared_raw = str(tmp_path / "shared")
        os.makedirs(os.path.join(local_raw, "movie"))
        (tmp_path / "local" / "movie" / "file.mkv").write_bytes(b"data")

        cfg = {'LOCAL_RAW_PATH': local_raw, 'SHARED_RAW_PATH': shared_raw}
        _move_to_shared_storage(cfg, "movie")
        assert os.path.isdir(os.path.join(shared_raw, "movie"))

    def test_no_config_does_nothing(self, tmp_path):
        from arm.ripper.utils import _move_to_shared_storage

        cfg = {'LOCAL_RAW_PATH': '', 'SHARED_RAW_PATH': ''}
        _move_to_shared_storage(cfg, "movie")  # Should not raise

    def test_no_basename_does_nothing(self, tmp_path):
        from arm.ripper.utils import _move_to_shared_storage

        cfg = {'LOCAL_RAW_PATH': '/home/arm/media/local', 'SHARED_RAW_PATH': '/home/arm/media/shared'}
        _move_to_shared_storage(cfg, "")  # Should not raise


class TestTranscoderNotify:
    """Test transcoder_notify() webhook sending (lines 217, 221, 229-232)."""

    def test_no_job_returns_early(self):
        from arm.ripper.utils import transcoder_notify

        cfg = {'TRANSCODER_URL': 'http://localhost:5000/webhook'}
        with unittest.mock.patch('httpx.Client') as mock_client:
            transcoder_notify(cfg, "Title", "Body", None)
        mock_client.assert_not_called()

    def test_no_transcoder_url_returns_early(self):
        from arm.ripper.utils import transcoder_notify

        cfg = {'TRANSCODER_URL': ''}
        job = unittest.mock.MagicMock()
        job.job_id = 1

        with unittest.mock.patch('httpx.Client') as mock_client:
            transcoder_notify(cfg, "Title", "Body", job)
        mock_client.assert_not_called()

    def test_sends_webhook(self, app_context):
        from arm.ripper.utils import transcoder_notify

        cfg = {'TRANSCODER_URL': 'http://localhost:5000/webhook',
               'TRANSCODER_WEBHOOK_SECRET': 'test-secret',
               'SHARED_RAW_PATH': '', 'LOCAL_RAW_PATH': ''}
        job = unittest.mock.MagicMock()
        job.job_id = 1
        job.raw_path = '/home/arm/media/raw/Movie'
        job.video_type = 'movie'
        job.year = '2024'
        job.disctype = 'bluray'
        job.status = 'active'
        job.poster_url = ''
        job.title = 'Movie'
        job.multi_title = False
        job.transcode_overrides = None

        mock_resp = unittest.mock.MagicMock()
        mock_resp.status_code = 200

        with unittest.mock.patch('httpx.Client') as mock_client_cls, \
             unittest.mock.patch('arm.ripper.utils._build_webhook_payload',
                                 return_value={"title": "test"}), \
             unittest.mock.patch('arm.ripper.utils.db'):
            mock_client = mock_client_cls.return_value.__enter__.return_value
            mock_client.post.return_value = mock_resp
            transcoder_notify(cfg, "Title", "Body", job)
        mock_client.post.assert_called_once()


class TestScanEmby:
    """Test scan_emby() HTTP request (lines 91-92, 96-100)."""

    def test_scan_when_enabled(self):
        from arm.ripper.utils import scan_emby
        import arm.config.config as cfg

        old_refresh = cfg.arm_config.get('EMBY_REFRESH')
        old_server = cfg.arm_config.get('EMBY_SERVER')
        old_port = cfg.arm_config.get('EMBY_PORT')
        old_key = cfg.arm_config.get('EMBY_API_KEY')

        cfg.arm_config['EMBY_REFRESH'] = True
        cfg.arm_config['EMBY_SERVER'] = 'localhost'
        cfg.arm_config['EMBY_PORT'] = '8096'
        cfg.arm_config['EMBY_API_KEY'] = 'test-key'

        try:
            mock_resp = unittest.mock.MagicMock()
            mock_resp.status_code = 200
            with unittest.mock.patch('requests.post', return_value=mock_resp) as mock_post:
                scan_emby()
            mock_post.assert_called_once()
        finally:
            cfg.arm_config['EMBY_REFRESH'] = old_refresh
            cfg.arm_config['EMBY_SERVER'] = old_server
            cfg.arm_config['EMBY_PORT'] = old_port
            cfg.arm_config['EMBY_API_KEY'] = old_key

    def test_scan_disabled(self):
        from arm.ripper.utils import scan_emby
        import arm.config.config as cfg

        old = cfg.arm_config.get('EMBY_REFRESH')
        cfg.arm_config['EMBY_REFRESH'] = False
        try:
            with unittest.mock.patch('requests.post') as mock_post:
                scan_emby()
            mock_post.assert_not_called()
        finally:
            cfg.arm_config['EMBY_REFRESH'] = old

    def test_scan_http_error(self):
        from arm.ripper.utils import scan_emby
        import arm.config.config as cfg
        import requests

        old_refresh = cfg.arm_config.get('EMBY_REFRESH')
        cfg.arm_config['EMBY_REFRESH'] = True
        cfg.arm_config['EMBY_SERVER'] = 'localhost'
        cfg.arm_config['EMBY_PORT'] = '8096'
        cfg.arm_config['EMBY_API_KEY'] = 'test-key'

        try:
            mock_resp = unittest.mock.MagicMock()
            mock_resp.status_code = 500
            mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("500")
            with unittest.mock.patch('requests.post', return_value=mock_resp):
                # Should not raise
                scan_emby()
        finally:
            cfg.arm_config['EMBY_REFRESH'] = old_refresh


class TestNotifyEntry:
    """Test notify_entry() disc type notification routing."""

    def test_video_disc_notification(self, app_context, sample_job):
        from arm.ripper.utils import notify_entry
        import arm.config.config as cfg

        old = cfg.arm_config.get('UI_BASE_URL')
        cfg.arm_config['UI_BASE_URL'] = ''
        try:
            with unittest.mock.patch('arm.ripper.utils.notify') as mock_notify, \
                 unittest.mock.patch('arm.ripper.utils.database_adder'), \
                 unittest.mock.patch('arm.ripper.utils.check_ip', return_value='127.0.0.1'):
                notify_entry(sample_job)
            mock_notify.assert_called_once()
            call_body = mock_notify.call_args[0][2]
            assert 'Found disc' in call_body
        finally:
            if old is not None:
                cfg.arm_config['UI_BASE_URL'] = old

    def test_music_disc_notification(self, app_context, sample_job):
        from arm.ripper.utils import notify_entry

        sample_job.disctype = 'music'
        with unittest.mock.patch('arm.ripper.utils.notify') as mock_notify, \
             unittest.mock.patch('arm.ripper.utils.database_adder'):
            notify_entry(sample_job)
        call_body = mock_notify.call_args[0][2]
        assert 'music CD' in call_body

    def test_data_disc_notification(self, app_context, sample_job):
        from arm.ripper.utils import notify_entry

        sample_job.disctype = 'data'
        with unittest.mock.patch('arm.ripper.utils.notify') as mock_notify, \
             unittest.mock.patch('arm.ripper.utils.database_adder'):
            notify_entry(sample_job)
        call_body = mock_notify.call_args[0][2]
        assert 'data disc' in call_body

    def test_unknown_disc_raises(self, app_context, sample_job):
        from arm.ripper.utils import notify_entry, RipperException

        sample_job.disctype = 'unknown'
        with unittest.mock.patch('arm.ripper.utils.database_adder'), \
             pytest.raises(RipperException, match="Could not determine"):
            notify_entry(sample_job)


class TestJobDupeCheck:
    """Test job_dupe_check() duplicate detection."""

    def test_none_label_returns_false(self, app_context, sample_job):
        from arm.ripper.utils import job_dupe_check

        sample_job.label = None
        result = job_dupe_check(sample_job)
        assert result is False

    def test_no_previous_rips(self, app_context, sample_job):
        from arm.ripper.utils import job_dupe_check

        sample_job.label = "UNIQUE_LABEL"
        result = job_dupe_check(sample_job)
        assert result is False


class TestIsRippingPaused:
    """Test is_ripping_paused() database query."""

    def test_returns_false_by_default(self, app_context):
        from arm.ripper.utils import is_ripping_paused
        # No app_state row exists
        result = is_ripping_paused()
        assert result is False

    def test_returns_false_on_exception(self, app_context):
        from arm.ripper.utils import is_ripping_paused
        from arm.database import db

        with unittest.mock.patch.object(db.engine, 'connect',
                                        side_effect=RuntimeError("db error")):
            result = is_ripping_paused()
        assert result is False


class TestGetDriveMode:
    """Test get_drive_mode() database lookup."""

    def test_returns_auto_when_no_drive(self, app_context):
        from arm.ripper.utils import get_drive_mode

        result = get_drive_mode('/dev/sr99')
        assert result == 'auto'


class TestCleanOldJobs:
    """Test clean_old_jobs() zombie job cleanup."""

    def test_cleans_abandoned_jobs(self, app_context, sample_job):
        from arm.ripper.utils import clean_old_jobs
        from arm.database import db

        sample_job.status = 'active'
        sample_job.pid = 99999999  # Non-existent PID
        db.session.commit()

        with unittest.mock.patch('psutil.pid_exists', return_value=False):
            clean_old_jobs()

        db.session.refresh(sample_job)
        assert sample_job.status == 'fail'

    def test_skips_running_jobs(self, app_context, sample_job):
        from arm.ripper.utils import clean_old_jobs
        from arm.database import db

        sample_job.status = 'active'
        sample_job.pid = os.getpid()
        sample_job.pid_hash = hash(unittest.mock.MagicMock())
        db.session.commit()

        with unittest.mock.patch('psutil.pid_exists', return_value=True), \
             unittest.mock.patch('psutil.Process') as mock_proc:
            mock_proc.return_value.__hash__ = lambda self: sample_job.pid_hash
            clean_old_jobs()

        db.session.refresh(sample_job)
        assert sample_job.status == 'active'


class TestApplyTrackPhases:
    """Test _apply_track_phases() per-track status updates."""

    def test_updates_track_statuses(self, app_context, sample_job):
        from arm.ripper.utils import _apply_track_phases, put_track
        from arm.models.track import Track

        # Create test tracks
        put_track(sample_job, 1, 300, "16:9", 24.0, False, "abcde")
        put_track(sample_job, 2, 300, "16:9", 24.0, False, "abcde")
        put_track(sample_job, 3, 300, "16:9", 24.0, False, "abcde")

        grabbing = {1, 2, 3}
        encoding = {1, 2}
        tagging = {1}

        _apply_track_phases(sample_job, grabbing, encoding, tagging)

        tracks = Track.query.filter_by(job_id=sample_job.job_id).order_by(Track.track_number).all()
        assert tracks[0].status == "success"
        assert tracks[0].ripped is True
        assert tracks[1].status == "encoding"
        assert tracks[1].ripped is True
        assert tracks[2].status == "ripping"


class TestUpdateMusicTracks:
    """Test _update_music_tracks() bulk update."""

    def test_updates_all_tracks(self, app_context, sample_job):
        from arm.ripper.utils import _update_music_tracks, put_track
        from arm.models.track import Track

        put_track(sample_job, 1, 200, "16:9", 24.0, False, "abcde")
        put_track(sample_job, 2, 200, "16:9", 24.0, False, "abcde")

        _update_music_tracks(sample_job, ripped=True, status="success")

        tracks = Track.query.filter_by(job_id=sample_job.job_id).all()
        for t in tracks:
            assert t.ripped is True
            assert t.status == "success"


class TestSaveDiscPoster:
    """Test save_disc_poster() poster extraction."""

    def test_skips_non_dvd(self):
        from arm.ripper.utils import save_disc_poster
        import arm.config.config as cfg

        job = unittest.mock.MagicMock()
        job.disctype = 'bluray'

        with unittest.mock.patch('subprocess.run') as mock_run:
            save_disc_poster('/home/arm/media/raw', job)
        mock_run.assert_not_called()

    def test_skips_when_disabled(self):
        from arm.ripper.utils import save_disc_poster
        import arm.config.config as cfg

        old = cfg.arm_config.get('RIP_POSTER')
        cfg.arm_config['RIP_POSTER'] = False
        try:
            job = unittest.mock.MagicMock()
            job.disctype = 'dvd'
            with unittest.mock.patch('subprocess.run') as mock_run:
                save_disc_poster('/home/arm/media/raw', job)
            mock_run.assert_not_called()
        finally:
            if old is not None:
                cfg.arm_config['RIP_POSTER'] = old


class TestArmSetup:
    """Test arm_setup() directory and permission checks."""

    def test_creates_directories(self, tmp_path):
        from arm.ripper.utils import arm_setup
        import arm.config.config as cfg

        raw = str(tmp_path / 'raw')
        completed = str(tmp_path / 'completed')
        logpath = str(tmp_path / 'logs')

        old_raw = cfg.arm_config.get('RAW_PATH')
        old_completed = cfg.arm_config.get('COMPLETED_PATH')
        old_logpath = cfg.arm_config.get('LOGPATH')
        old_db = cfg.arm_config.get('DBFILE')

        cfg.arm_config['RAW_PATH'] = raw
        cfg.arm_config['COMPLETED_PATH'] = completed
        cfg.arm_config['LOGPATH'] = logpath
        cfg.arm_config['DBFILE'] = str(tmp_path / 'test.db')

        mock_logger = unittest.mock.MagicMock()

        try:
            arm_setup(mock_logger)
            assert os.path.isdir(raw)
            assert os.path.isdir(completed)
            assert os.path.isdir(logpath)
            assert os.path.isdir(os.path.join(logpath, 'progress'))
        finally:
            cfg.arm_config['RAW_PATH'] = old_raw
            cfg.arm_config['COMPLETED_PATH'] = old_completed
            cfg.arm_config['LOGPATH'] = old_logpath
            cfg.arm_config['DBFILE'] = old_db
