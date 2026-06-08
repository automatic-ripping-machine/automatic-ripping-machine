"""Additional tests for arm/ripper/utils.py — covering missing lines.

Covers: _move_to_shared_storage(), transcoder_notify(), scan_emby(),
notify_entry(), job_dupe_check(), is_ripping_paused(), get_drive_mode(),
clean_old_jobs(), save_disc_poster(), _apply_track_phases(),
_update_music_tracks(), arm_setup(), duplicate_run_check().

The legacy ``bash_notify()`` and ``_build_job_env()`` helpers were
removed in N19; their tests are gone with them.
"""
import datetime
import os
import unittest.mock

import pytest


class TestMoveToSharedStorage:
    """Test _move_to_shared_storage() file copy + verify + remove."""

    def test_moves_directory(self, tmp_path):
        from arm.ripper.utils import _move_to_shared_storage

        local_raw = str(tmp_path / "local")
        shared_raw = str(tmp_path / "shared")
        os.makedirs(os.path.join(local_raw, "movie"))
        (tmp_path / "local" / "movie" / "file.mkv").write_bytes(b"data")

        cfg = {'LOCAL_RAW_PATH': local_raw, 'SHARED_RAW_PATH': shared_raw}
        _move_to_shared_storage(cfg, "movie")
        assert os.path.isfile(os.path.join(shared_raw, "movie", "file.mkv"))
        # Source should be removed after verified copy
        assert not os.path.exists(os.path.join(local_raw, "movie"))

    def test_merges_into_existing_directory(self, tmp_path):
        """When destination dir already exists (e.g. from a previous disc),
        files should merge into it rather than nesting as a subdirectory.
        This was the root cause of the disc 4 track 5 file loss."""
        from arm.ripper.utils import _move_to_shared_storage

        local_raw = str(tmp_path / "local")
        shared_raw = str(tmp_path / "shared")
        src = os.path.join(local_raw, "Show")
        dst = os.path.join(shared_raw, "Show")

        os.makedirs(src)
        os.makedirs(dst)
        # Old file from previous disc (transcoder may not have cleaned dir)
        (tmp_path / "shared" / "Show" / "old_disc3.mkv").write_bytes(b"old")
        # New disc files
        for i in range(6):
            (tmp_path / "local" / "Show" / f"disc4_t0{i}.mkv").write_bytes(b"x" * (i + 1))

        cfg = {'LOCAL_RAW_PATH': local_raw, 'SHARED_RAW_PATH': shared_raw}
        _move_to_shared_storage(cfg, "Show")

        # All 6 new files should be directly in dst (not nested)
        dst_files = os.listdir(dst)
        for i in range(6):
            assert f"disc4_t0{i}.mkv" in dst_files, f"disc4_t0{i}.mkv missing from destination"
        # Old file preserved
        assert "old_disc3.mkv" in dst_files
        # No nested subdirectory
        assert "Show" not in dst_files, "Source was nested inside destination (shutil.move bug)"
        # Source removed
        assert not os.path.exists(src)

    def test_multiple_files_all_verified(self, tmp_path):
        """All source files must arrive at destination before source is removed."""
        from arm.ripper.utils import _move_to_shared_storage

        local_raw = str(tmp_path / "local")
        shared_raw = str(tmp_path / "shared")
        src = os.path.join(local_raw, "movie")
        os.makedirs(src)
        for i in range(5):
            (tmp_path / "local" / "movie" / f"track_{i}.mkv").write_bytes(b"x" * 100)

        cfg = {'LOCAL_RAW_PATH': local_raw, 'SHARED_RAW_PATH': shared_raw}
        _move_to_shared_storage(cfg, "movie")

        dst = os.path.join(shared_raw, "movie")
        dst_files = os.listdir(dst)
        assert len(dst_files) == 5
        for i in range(5):
            assert f"track_{i}.mkv" in dst_files

    def test_no_config_does_nothing(self, tmp_path):
        from arm.ripper.utils import _move_to_shared_storage

        cfg = {'LOCAL_RAW_PATH': '', 'SHARED_RAW_PATH': ''}
        _move_to_shared_storage(cfg, "movie")  # Should not raise

    def test_no_basename_does_nothing(self, tmp_path):
        from arm.ripper.utils import _move_to_shared_storage

        cfg = {'LOCAL_RAW_PATH': '/home/arm/media/local', 'SHARED_RAW_PATH': '/home/arm/media/shared'}
        _move_to_shared_storage(cfg, "")  # Should not raise

    def test_copy_failure_raises(self, tmp_path):
        """OSError during copy should propagate (not be silently swallowed)."""
        from arm.ripper.utils import _move_to_shared_storage

        local_raw = str(tmp_path / "local")
        shared_raw = str(tmp_path / "shared")
        src = os.path.join(local_raw, "movie")
        os.makedirs(src)
        (tmp_path / "local" / "movie" / "file.mkv").write_bytes(b"data")

        cfg = {
            'LOCAL_RAW_PATH': local_raw,
            'SHARED_RAW_PATH': shared_raw,
            'LOGPATH': str(tmp_path),
        }

        # New helper streams via subprocess.Popen; simulate exit 23 (partial).
        mock_proc = unittest.mock.MagicMock()
        mock_proc.stdout = unittest.mock.MagicMock()
        mock_proc.stdout.read.side_effect = ["", ""]  # no progress output
        mock_proc.stderr = unittest.mock.MagicMock()
        mock_proc.stderr.read.return_value = "rsync: NFS write failed"
        mock_proc.returncode = 23
        mock_proc.wait.return_value = None

        with unittest.mock.patch("arm.ripper.rsync_helper.subprocess.Popen", return_value=mock_proc):
            with pytest.raises(OSError, match="rsync failed"):
                _move_to_shared_storage(cfg, "movie")


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

    def test_sends_webhook(self, app_context, transcoder_notify_job, transcoder_notify_patches):
        from arm.ripper.utils import transcoder_notify

        cfg = {'TRANSCODER_URL': 'http://localhost:5000/webhook',
               'TRANSCODER_WEBHOOK_SECRET': 'test-secret',
               'SHARED_RAW_PATH': '', 'LOCAL_RAW_PATH': ''}

        transcoder_notify(cfg, "Title", "Body", transcoder_notify_job)

        transcoder_notify_patches.post.assert_called_once()


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
    """Test notify_entry() publishes JobStartedEvent for the disc type.

    The legacy per-disctype message text now lives in channel-side
    templates rendered from the typed event, so the assertions check
    the event's ``job_disc_type`` rather than free-form body strings.
    """

    def test_video_disc_notification(self, app_context, sample_job):
        from arm.ripper.utils import notify_entry
        from arm_contracts import JobStartedEvent
        from arm_contracts.enums import Disctype

        with unittest.mock.patch('arm.notifications.publish_event') as mock_publish, \
             unittest.mock.patch('arm.ripper.utils.database_adder'):
            notify_entry(sample_job)
        mock_publish.assert_called_once()
        event = mock_publish.call_args[0][0]
        assert isinstance(event, JobStartedEvent)
        assert event.job_disc_type in (Disctype.dvd, Disctype.bluray, Disctype.bluray4k)

    def test_music_disc_notification(self, app_context, sample_job):
        from arm.ripper.utils import notify_entry
        from arm_contracts import JobStartedEvent
        from arm_contracts.enums import Disctype

        sample_job.disctype = 'music'
        with unittest.mock.patch('arm.notifications.publish_event') as mock_publish, \
             unittest.mock.patch('arm.ripper.utils.database_adder'):
            notify_entry(sample_job)
        event = mock_publish.call_args[0][0]
        assert isinstance(event, JobStartedEvent)
        assert event.job_disc_type == Disctype.music

    def test_data_disc_notification(self, app_context, sample_job):
        from arm.ripper.utils import notify_entry
        from arm_contracts import JobStartedEvent
        from arm_contracts.enums import Disctype

        sample_job.disctype = 'data'
        with unittest.mock.patch('arm.notifications.publish_event') as mock_publish, \
             unittest.mock.patch('arm.ripper.utils.database_adder'):
            notify_entry(sample_job)
        event = mock_publish.call_args[0][0]
        assert isinstance(event, JobStartedEvent)
        assert event.job_disc_type == Disctype.data

    def test_unknown_disc_raises(self, app_context, sample_job):
        from arm.ripper.utils import notify_entry, RipperException

        sample_job.disctype = 'unknown'
        with unittest.mock.patch('arm.notifications.publish_event'), \
             unittest.mock.patch('arm.ripper.utils.database_adder'), \
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

        sample_job.status='video_ripping'
        sample_job.pid = 99999999  # Non-existent PID
        db.session.commit()

        with unittest.mock.patch('psutil.pid_exists', return_value=False):
            clean_old_jobs()

        db.session.refresh(sample_job)
        assert sample_job.status == 'fail'

    def test_skips_running_jobs(self, app_context, sample_job):
        from arm.ripper.utils import clean_old_jobs
        from arm.database import db

        sample_job.status='video_ripping'
        sample_job.pid = os.getpid()
        sample_job.pid_hash = hash(unittest.mock.MagicMock())
        db.session.commit()

        with unittest.mock.patch('psutil.pid_exists', return_value=True), \
             unittest.mock.patch('psutil.Process') as mock_proc:
            mock_proc.return_value.__hash__ = lambda self: sample_job.pid_hash
            clean_old_jobs()

        db.session.refresh(sample_job)
        assert sample_job.status == 'video_ripping'


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
        assert not tracks[1].ripped  # ripped only set after tagging
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
