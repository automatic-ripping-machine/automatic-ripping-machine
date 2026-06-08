"""Tests for arm_ripper.py dispatch logic and notification functions."""
import unittest.mock


class TestNotifyExit:
    """Test notify_exit() publishes JobTranscodeCompleteEvent."""

    def test_success_publishes_transcode_complete(self):
        from arm.ripper.arm_ripper import notify_exit
        from arm_contracts import JobTranscodeCompleteEvent

        job = unittest.mock.MagicMock()
        job.job_id = 7
        job.title = "Serial Mom"
        job.disctype = "bluray"
        job.imdb_id = None
        job.errors = None
        job.start_time = None
        job.path = "/home/arm/media/completed/Serial Mom (1994)"

        with unittest.mock.patch('arm.ripper.arm_ripper.publish_event') as mock_publish:
            notify_exit(job)
            mock_publish.assert_called_once()
            published = mock_publish.call_args[0][0]
            assert isinstance(published, JobTranscodeCompleteEvent)
            assert published.job_id == 7
            assert published.job_title == "Serial Mom"

    def test_error_still_publishes_transcode_complete(self):
        """Even when job.errors is populated we publish — the dedicated
        job.failed event (emitted at the FAILURE state set site) carries
        the error narrative for subscribers."""
        from arm.ripper.arm_ripper import notify_exit
        from arm_contracts import JobTranscodeCompleteEvent

        job = unittest.mock.MagicMock()
        job.job_id = 8
        job.title = "Serial Mom"
        job.disctype = "bluray"
        job.imdb_id = None
        job.errors = "title_03.mkv, title_07.mkv"
        job.start_time = None
        job.path = ""

        with unittest.mock.patch('arm.ripper.arm_ripper.publish_event') as mock_publish:
            notify_exit(job)
            mock_publish.assert_called_once()
            published = mock_publish.call_args[0][0]
            assert isinstance(published, JobTranscodeCompleteEvent)

    def test_publishes_even_when_legacy_flag_would_have_been_false(self):
        """The legacy NOTIFY_TRANSCODE per-job guard is gone — channels
        filter on subscribed_events instead, so publish_event always
        fires regardless of the (now-ignored) job.config attribute."""
        from arm.ripper.arm_ripper import notify_exit

        job = unittest.mock.MagicMock()
        job.job_id = 9
        job.title = "Movie"
        job.disctype = "dvd"
        job.imdb_id = None
        job.errors = None
        job.start_time = None
        job.path = ""
        job.config.NOTIFY_TRANSCODE = False  # historical; now ignored

        with unittest.mock.patch('arm.ripper.arm_ripper.publish_event') as mock_publish:
            notify_exit(job)
            mock_publish.assert_called_once()


class TestRipVisualMedia:
    """Test simplified rip_visual_media() flow: rip -> persist -> publish."""

    def _make_job(self, **overrides):
        """Build a mock job with configurable attributes."""
        job = unittest.mock.MagicMock()
        job.job_id = overrides.get('job_id', 1)
        job.title = overrides.get('title', 'Test Movie')
        job.disctype = overrides.get('disctype', 'bluray')
        job.imdb_id = overrides.get('imdb_id', None)
        job.config.NOTIFY_RIP = overrides.get('notify_rip', True)
        job.config.NOTIFY_TRANSCODE = overrides.get('notify_transcode', True)
        job.config.MAINFEATURE = overrides.get('mainfeature', False)
        job.errors = overrides.get('errors', None)
        job.start_time = overrides.get('start_time', None)
        job.path = overrides.get('path', '')
        job.tracks.count.return_value = overrides.get('track_count', 1)
        job.build_final_path.return_value = '/home/arm/media/completed/movies/Test Movie (2024)'
        return job

    def test_rip_calls_makemkv(self):
        from arm.ripper.arm_ripper import rip_visual_media

        job = self._make_job()

        with unittest.mock.patch('arm.ripper.arm_ripper.utils') as mock_utils, \
             unittest.mock.patch('arm.ripper.arm_ripper.makemkv') as mock_mkv, \
             unittest.mock.patch('arm.ripper.arm_ripper.publish_event'), \
             unittest.mock.patch('arm.ripper.arm_ripper.db'):
            mock_utils.check_for_dupe_folder.return_value = '/home/arm/media/completed/movies/Test Movie (2024)'
            mock_mkv.makemkv.return_value = '/home/arm/media/raw/Test Movie (2024)'

            rip_visual_media(False, job, "test.log", 0)

            mock_mkv.makemkv.assert_called_once_with(job)

    def test_rip_persists_raw_path(self):
        from arm.ripper.arm_ripper import rip_visual_media

        job = self._make_job()
        raw_path = '/home/arm/media/raw/Test Movie (2024)'

        with unittest.mock.patch('arm.ripper.arm_ripper.utils') as mock_utils, \
             unittest.mock.patch('arm.ripper.arm_ripper.makemkv') as mock_mkv, \
             unittest.mock.patch('arm.ripper.arm_ripper.publish_event'), \
             unittest.mock.patch('arm.ripper.arm_ripper.db'):
            mock_utils.check_for_dupe_folder.return_value = '/home/arm/media/completed/movies/Test Movie (2024)'
            mock_mkv.makemkv.return_value = raw_path

            rip_visual_media(False, job, "test.log", 0)

            # Verify raw_path was persisted to DB
            raw_path_calls = [
                c for c in mock_utils.database_updater.call_args_list
                if 'raw_path' in c[0][0]
            ]
            assert len(raw_path_calls) == 1
            assert raw_path_calls[0][0][0]['raw_path'] == raw_path

    def test_rip_publishes_rip_complete_and_transcode_complete(self):
        """Happy path: a JobRipCompleteEvent (from _post_rip_handoff)
        and a JobTranscodeCompleteEvent (from notify_exit) are both
        published, in that order."""
        from arm.ripper.arm_ripper import rip_visual_media
        from arm_contracts import JobRipCompleteEvent, JobTranscodeCompleteEvent

        job = self._make_job(notify_rip=True)

        with unittest.mock.patch('arm.ripper.arm_ripper.utils') as mock_utils, \
             unittest.mock.patch('arm.ripper.arm_ripper.makemkv') as mock_mkv, \
             unittest.mock.patch('arm.ripper.arm_ripper.publish_event') as mock_publish, \
             unittest.mock.patch('arm.ripper.arm_ripper.db'):
            mock_utils.check_for_dupe_folder.return_value = '/home/arm/media/completed/movies/Test Movie (2024)'
            mock_mkv.makemkv.return_value = '/home/arm/media/raw/Test Movie (2024)'

            rip_visual_media(False, job, "test.log", 0)

            published_types = [type(c[0][0]) for c in mock_publish.call_args_list]
            assert JobRipCompleteEvent in published_types
            assert JobTranscodeCompleteEvent in published_types

    def test_makemkv_error_raises_ripper_exception(self):
        from arm.ripper.arm_ripper import rip_visual_media
        from arm.ripper.utils import RipperException
        from arm.ripper.makemkv import UpdateKeyRunTimeError

        job = self._make_job()

        with unittest.mock.patch('arm.ripper.arm_ripper.utils') as mock_utils, \
             unittest.mock.patch('arm.ripper.arm_ripper.makemkv') as mock_mkv, \
             unittest.mock.patch('arm.ripper.arm_ripper.publish_event'), \
             unittest.mock.patch('arm.ripper.arm_ripper.db'):
            mock_utils.check_for_dupe_folder.return_value = '/home/arm/media/completed/movies/Test Movie (2024)'
            mock_utils.RipperException = RipperException
            mock_mkv.UpdateKeyRunTimeError = UpdateKeyRunTimeError
            mock_mkv.makemkv.side_effect = RuntimeError("MakeMKV crashed")

            try:
                rip_visual_media(False, job, "test.log", 0)
                assert False, "Expected RipperException"
            except RipperException:
                pass

    def test_rip_complete_publishes_regardless_of_legacy_notify_rip_flag(self):
        """NOTIFY_RIP per-job guard is gone — publish_event fires for
        rip_complete unconditionally on the happy path. Channels filter
        on subscribed_events."""
        from arm.ripper.arm_ripper import rip_visual_media
        from arm_contracts import JobRipCompleteEvent

        job = self._make_job(notify_rip=False)

        with unittest.mock.patch('arm.ripper.arm_ripper.utils') as mock_utils, \
             unittest.mock.patch('arm.ripper.arm_ripper.makemkv') as mock_mkv, \
             unittest.mock.patch('arm.ripper.arm_ripper.publish_event') as mock_publish, \
             unittest.mock.patch('arm.ripper.arm_ripper.db'):
            mock_utils.check_for_dupe_folder.return_value = '/home/arm/media/completed/movies/Test Movie (2024)'
            mock_mkv.makemkv.return_value = '/home/arm/media/raw/Test Movie (2024)'

            rip_visual_media(False, job, "test.log", 0)

            rip_complete_publishes = [
                c for c in mock_publish.call_args_list
                if isinstance(c[0][0], JobRipCompleteEvent)
            ]
            assert len(rip_complete_publishes) == 1


class TestSkipTranscode:
    """Test _post_rip_handoff() SKIP_TRANSCODE decision logic."""

    def _make_job(self, skip_transcode=None, notify_rip=False):
        job = unittest.mock.MagicMock()
        job.job_id = 1
        job.title = "Test Movie"
        job.disctype = "bluray"
        job.imdb_id = None
        job.errors = None
        job.start_time = None
        job.path = ""
        job.config.SKIP_TRANSCODE = skip_transcode
        job.config.NOTIFY_RIP = notify_rip
        job.tracks.count.return_value = 1
        return job

    def test_skip_transcode_true_finalizes_locally(self):
        from arm.ripper.arm_ripper import _post_rip_handoff

        job = self._make_job(skip_transcode=True)

        with unittest.mock.patch('arm.ripper.arm_ripper.db'), \
             unittest.mock.patch('arm.ripper.arm_ripper.utils') as mock_utils, \
             unittest.mock.patch('arm.ripper.arm_ripper.publish_event'), \
             unittest.mock.patch('arm.config.config.arm_config', {'TRANSCODER_URL': 'http://transcoder:5000/webhook/arm', 'SKIP_TRANSCODE': False}), \
             unittest.mock.patch('arm.ripper.naming.finalize_output') as mock_finalize:
            _post_rip_handoff(job)
            mock_finalize.assert_called_once_with(job)
            mock_utils.transcoder_notify.assert_not_called()

    def test_skip_transcode_false_notifies_transcoder(self):
        from arm.ripper.arm_ripper import _post_rip_handoff

        job = self._make_job(skip_transcode=False)

        with unittest.mock.patch('arm.ripper.arm_ripper.db'), \
             unittest.mock.patch('arm.ripper.arm_ripper.utils') as mock_utils, \
             unittest.mock.patch('arm.ripper.arm_ripper.publish_event'), \
             unittest.mock.patch('arm.config.config.arm_config', {'TRANSCODER_URL': 'http://transcoder:5000/webhook/arm', 'SKIP_TRANSCODE': False}), \
             unittest.mock.patch('arm.ripper.naming.finalize_output') as mock_finalize:
            _post_rip_handoff(job)
            mock_finalize.assert_not_called()
            mock_utils.transcoder_notify.assert_called_once()

    def test_skip_transcode_no_url_finalizes_locally(self):
        from arm.ripper.arm_ripper import _post_rip_handoff

        job = self._make_job(skip_transcode=False)

        with unittest.mock.patch('arm.ripper.arm_ripper.db'), \
             unittest.mock.patch('arm.ripper.arm_ripper.utils') as mock_utils, \
             unittest.mock.patch('arm.ripper.arm_ripper.publish_event'), \
             unittest.mock.patch('arm.config.config.arm_config', {'TRANSCODER_URL': '', 'SKIP_TRANSCODE': False}), \
             unittest.mock.patch('arm.ripper.naming.finalize_output') as mock_finalize:
            _post_rip_handoff(job)
            mock_finalize.assert_called_once_with(job)
            mock_utils.transcoder_notify.assert_not_called()

    def test_per_job_override_skip(self):
        from arm.ripper.arm_ripper import _post_rip_handoff

        # Global says don't skip, but per-job says skip
        job = self._make_job(skip_transcode=True)

        with unittest.mock.patch('arm.ripper.arm_ripper.db'), \
             unittest.mock.patch('arm.ripper.arm_ripper.utils') as mock_utils, \
             unittest.mock.patch('arm.ripper.arm_ripper.publish_event'), \
             unittest.mock.patch('arm.config.config.arm_config', {'TRANSCODER_URL': 'http://transcoder:5000/webhook/arm', 'SKIP_TRANSCODE': False}), \
             unittest.mock.patch('arm.ripper.naming.finalize_output') as mock_finalize:
            _post_rip_handoff(job)
            mock_finalize.assert_called_once_with(job)
            mock_utils.transcoder_notify.assert_not_called()
