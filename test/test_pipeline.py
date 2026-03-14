"""Tests for pipeline utilities — README Features: Video Ripping, Duplicate Detection.

Covers job_dupe_check(), check_for_dupe_folder(), find_file(), scan_emby(),
check_for_wait(), duplicate_run_check(), and MusicBrainz helper functions.
"""
import os
import unittest.mock

import pytest


class TestJobDupeCheck:
    """Test job_dupe_check() duplicate detection in database."""

    def test_no_label_returns_false(self, app_context):
        """None label returns False immediately."""
        from arm.ripper.utils import job_dupe_check
        from arm.models.job import Job

        with unittest.mock.patch.object(Job, 'parse_udev'), \
             unittest.mock.patch.object(Job, 'get_pid'):
            job = Job('/dev/sr0')
        job.label = None
        job.title = 'TEST'
        job.title_auto = 'TEST'

        result = job_dupe_check(job)
        assert result is False

    def test_no_previous_rips_returns_false(self, app_context, sample_job):
        """No matching previous rips returns False."""
        from arm.ripper.utils import job_dupe_check

        # sample_job has label 'SERIAL_MOM' but status 'active', not 'success'
        result = job_dupe_check(sample_job)
        assert result is False

    def test_one_successful_dupe_returns_true(self, app_context, sample_job):
        """One matching successful rip updates job and returns True."""
        from arm.ripper.utils import job_dupe_check
        from arm.models.job import Job
        from arm.database import db

        # Create a previous successful rip with same label
        with unittest.mock.patch.object(Job, 'parse_udev'), \
             unittest.mock.patch.object(Job, 'get_pid'):
            old_job = Job('/dev/sr0')
        old_job.title = 'Serial Mom'
        old_job.title_auto = 'Serial Mom'
        old_job.label = 'SERIAL_MOM'
        old_job.status = 'success'
        old_job.year = '1994'
        old_job.poster_url = 'https://example.com/poster.jpg'
        old_job.hasnicetitle = True
        old_job.video_type = 'movie'
        db.session.add(old_job)
        db.session.commit()

        result = job_dupe_check(sample_job)
        assert result is True

    def test_multiple_dupes_returns_false(self, app_context, sample_job):
        """Multiple matching rips returns False (too many to pick from)."""
        from arm.ripper.utils import job_dupe_check
        from arm.models.job import Job
        from arm.database import db

        for i in range(3):
            with unittest.mock.patch.object(Job, 'parse_udev'), \
                 unittest.mock.patch.object(Job, 'get_pid'):
                old_job = Job('/dev/sr0')
            old_job.title = f'Serial Mom {i}'
            old_job.title_auto = f'Serial Mom {i}'
            old_job.label = 'SERIAL_MOM'
            old_job.status = 'success'
            old_job.year = '1994'
            old_job.poster_url = ''
            old_job.hasnicetitle = True
            old_job.video_type = 'movie'
            db.session.add(old_job)
        db.session.commit()

        result = job_dupe_check(sample_job)
        assert result is False


class TestCheckForDupeFolder:
    """Test check_for_dupe_folder() directory collision handling."""

    def test_new_folder_created(self, tmp_path):
        """If folder doesn't exist, creates it and returns unchanged path."""
        from arm.ripper.utils import check_for_dupe_folder

        new_path = str(tmp_path / 'new_folder')
        job = unittest.mock.MagicMock()
        job.stage = '170750493000'

        result = check_for_dupe_folder(False, new_path, job)
        assert result == new_path
        assert os.path.isdir(new_path)

    def test_existing_folder_with_dupes_allowed(self, tmp_path):
        """Existing folder + ALLOW_DUPLICATES appends stage suffix."""
        from arm.ripper.utils import check_for_dupe_folder
        import arm.config.config as cfg

        existing = tmp_path / 'existing'
        existing.mkdir()

        original = cfg.arm_config.get('ALLOW_DUPLICATES', True)
        cfg.arm_config['ALLOW_DUPLICATES'] = True
        try:
            job = unittest.mock.MagicMock()
            job.stage = '170750493000'
            result = check_for_dupe_folder(False, str(existing), job)
            assert result.endswith('_170750493000')
            assert os.path.isdir(result)
        finally:
            cfg.arm_config['ALLOW_DUPLICATES'] = original

    def test_existing_folder_dupes_disabled_raises(self, tmp_path):
        """Existing folder + no duplicates allowed → RipperException."""
        from arm.ripper.utils import check_for_dupe_folder, RipperException
        import arm.config.config as cfg

        existing = tmp_path / 'existing'
        existing.mkdir()

        original_allow = cfg.arm_config.get('ALLOW_DUPLICATES', True)
        cfg.arm_config['ALLOW_DUPLICATES'] = False
        try:
            job = unittest.mock.MagicMock()
            job.stage = '170750493000'
            job.title = 'Test'
            with unittest.mock.patch('arm.ripper.utils.notify'), \
                 unittest.mock.patch('arm.ripper.utils.database_updater'), \
                 pytest.raises(RipperException):
                check_for_dupe_folder(True, str(existing), job)
        finally:
            cfg.arm_config['ALLOW_DUPLICATES'] = original_allow


    def test_empty_folder_from_failed_rip_is_reused(self, app_context, tmp_path):
        """Empty folder from a failed rip is cleaned up and reused."""
        from arm.ripper.utils import check_for_dupe_folder
        from arm.database import db
        from arm.models.job import Job, JobState
        from arm.models.config import Config

        existing = tmp_path / 'existing'
        existing.mkdir()

        # Create a failed job with matching label
        with unittest.mock.patch.object(Job, 'parse_udev'), \
             unittest.mock.patch.object(Job, 'get_pid'):
            prev_job = Job('/dev/sr0')
        prev_job.label = 'TEST_LABEL'
        prev_job.status = JobState.FAILURE.value
        prev_job.arm_version = 'test'
        prev_job.crc_id = ''
        prev_job.logfile = 'test.log'
        prev_job.devpath = '/dev/sr0'
        prev_job.pid = 1
        prev_job.pid_hash = 0
        db.session.add(prev_job)
        db.session.flush()
        Config({'LOGPATH': '/home/arm/logs'}, prev_job.job_id)
        db.session.commit()

        job = unittest.mock.MagicMock()
        job.label = 'TEST_LABEL'
        job.stage = '170750493000'

        result = check_for_dupe_folder(False, str(existing), job)
        assert result == str(existing)
        assert os.path.isdir(result)

    def test_nonempty_folder_from_failed_rip_not_cleaned(self, app_context, tmp_path):
        """Non-empty folder is NOT cleaned up even if last job failed."""
        from arm.ripper.utils import check_for_dupe_folder
        from arm.database import db
        from arm.models.job import Job, JobState
        from arm.models.config import Config

        existing = tmp_path / 'existing'
        existing.mkdir()
        (existing / 'movie.mkv').write_text('data')

        with unittest.mock.patch.object(Job, 'parse_udev'), \
             unittest.mock.patch.object(Job, 'get_pid'):
            prev_job = Job('/dev/sr0')
        prev_job.label = 'TEST_LABEL'
        prev_job.status = JobState.FAILURE.value
        prev_job.arm_version = 'test'
        prev_job.crc_id = ''
        prev_job.logfile = 'test.log'
        prev_job.devpath = '/dev/sr0'
        prev_job.pid = 1
        prev_job.pid_hash = 0
        db.session.add(prev_job)
        db.session.flush()
        Config({'LOGPATH': '/home/arm/logs'}, prev_job.job_id)
        db.session.commit()

        job = unittest.mock.MagicMock()
        job.label = 'TEST_LABEL'
        job.stage = '170750493000'

        # Non-empty folder should NOT be cleaned — falls through to suffix
        result = check_for_dupe_folder(False, str(existing), job)
        assert result.endswith('_170750493000')
        # Original folder still has the file
        assert (existing / 'movie.mkv').exists()


class TestFindFile:
    """Test find_file() recursive directory search."""

    def test_finds_existing_file(self, tmp_path):
        """Returns True when file exists in subdirectory."""
        from arm.ripper.utils import find_file

        subdir = tmp_path / 'sub' / 'nested'
        subdir.mkdir(parents=True)
        (subdir / 'target.txt').write_text('found')

        assert find_file('target.txt', str(tmp_path)) is True

    def test_not_found_returns_false(self, tmp_path):
        """Returns False when file doesn't exist."""
        from arm.ripper.utils import find_file

        assert find_file('nonexistent.txt', str(tmp_path)) is False

    def test_empty_directory(self, tmp_path):
        """Returns False for empty directory."""
        from arm.ripper.utils import find_file

        assert find_file('any.txt', str(tmp_path)) is False


class TestScanEmby:
    """Test scan_emby() media library refresh trigger."""

    def test_sends_request_when_enabled(self):
        """Sends POST to Emby API when EMBY_REFRESH is True."""
        from arm.ripper.utils import scan_emby
        import arm.config.config as cfg

        originals = {}
        for k in ['EMBY_REFRESH', 'EMBY_SERVER', 'EMBY_PORT', 'EMBY_API_KEY']:
            originals[k] = cfg.arm_config.get(k, '')
        cfg.arm_config['EMBY_REFRESH'] = True
        cfg.arm_config['EMBY_SERVER'] = 'localhost'
        cfg.arm_config['EMBY_PORT'] = '8096'
        cfg.arm_config['EMBY_API_KEY'] = 'test_key'
        try:
            mock_resp = unittest.mock.MagicMock()
            mock_resp.status_code = 200
            with unittest.mock.patch('requests.post', return_value=mock_resp) as mock_post:
                scan_emby()
                mock_post.assert_called_once()
                assert 'Refresh' in mock_post.call_args[0][0]
        finally:
            for k, v in originals.items():
                cfg.arm_config[k] = v

    def test_skips_when_disabled(self):
        """Does nothing when EMBY_REFRESH is False."""
        from arm.ripper.utils import scan_emby
        import arm.config.config as cfg

        original = cfg.arm_config.get('EMBY_REFRESH', False)
        cfg.arm_config['EMBY_REFRESH'] = False
        try:
            with unittest.mock.patch('requests.post') as mock_post:
                scan_emby()
                mock_post.assert_not_called()
        finally:
            cfg.arm_config['EMBY_REFRESH'] = original


class TestMusicBrainzCheckDate:
    """Test music_brainz.check_date() year extraction."""

    def test_full_date(self):
        """Extracts year from 'YYYY-MM-DD' format."""
        from arm.ripper.music_brainz import check_date

        result = check_date({'date': '1994-04-15'})
        assert result == '1994'

    def test_year_only(self):
        """Returns year from 'YYYY' format."""
        from arm.ripper.music_brainz import check_date

        result = check_date({'date': '1994'})
        assert result == '1994'

    def test_no_date(self):
        """Returns empty string when no date field."""
        from arm.ripper.music_brainz import check_date

        result = check_date({})
        assert result == ''


class TestMusicBrainzProcessTracks:
    """Test music_brainz.process_tracks() track extraction."""

    def test_processes_full_tracks(self, app_context, sample_job):
        """Processes full MusicBrainz track data."""
        from arm.ripper.music_brainz import process_tracks

        tracks = [
            {
                'number': '1',
                'recording': {'length': '240000', 'title': 'Track One'},
            },
            {
                'number': '2',
                'recording': {'length': '180000', 'title': 'Track Two'},
            },
        ]
        with unittest.mock.patch('arm.ripper.music_brainz.u.put_track') as mock_put:
            process_tracks(sample_job, tracks)
            assert mock_put.call_count == 2
            # First track
            assert mock_put.call_args_list[0][0][1] == '1'
            assert mock_put.call_args_list[0][0][2] == 240

    def test_processes_stub_tracks(self, app_context, sample_job):
        """Processes CD stub track data."""
        from arm.ripper.music_brainz import process_tracks

        tracks = [
            {'number': '1', 'length': '120000', 'title': 'Stub Track'},
        ]
        with unittest.mock.patch('arm.ripper.music_brainz.u.put_track') as mock_put:
            process_tracks(sample_job, tracks, is_stub=True)
            mock_put.assert_called_once()
            assert mock_put.call_args[0][7] == '01 - Stub Track.flac'
            assert mock_put.call_args[1]['title'] == 'Stub Track'

    def test_missing_title_uses_default(self, app_context, sample_job):
        """Stub tracks without title get 'Untitled track N'."""
        from arm.ripper.music_brainz import process_tracks

        tracks = [
            {'number': '5', 'length': '60000'},
        ]
        with unittest.mock.patch('arm.ripper.music_brainz.u.put_track') as mock_put:
            process_tracks(sample_job, tracks, is_stub=True)
            title = mock_put.call_args[0][7]
            assert 'Untitled' in title


class TestMusicBrainzCheckData:
    """Test check_musicbrainz_data() disc vs cdstub processing."""

    def test_no_disc_no_cdstub_returns_empty(self, app_context, sample_job):
        """Returns empty string when disc_info has neither key."""
        from arm.ripper.music_brainz import check_musicbrainz_data

        result = check_musicbrainz_data(sample_job, {})
        assert result == ''

    def test_cdstub_processing(self, app_context, sample_job):
        """Processes cdstub data and returns artist+title."""
        from arm.ripper.music_brainz import check_musicbrainz_data

        disc_info = {
            'cdstub': {
                'id': 'stub-123',
                'title': 'Album Title',
                'artist': 'Artist Name',
                'track-count': 10,
                'track-list': [
                    {'number': '1', 'length': '180000', 'title': 'Track 1'},
                ],
            }
        }
        with unittest.mock.patch('arm.ripper.music_brainz.u.put_track'), \
             unittest.mock.patch('arm.ripper.music_brainz.u.database_updater'):
            result = check_musicbrainz_data(sample_job, disc_info)
        assert 'Artist Name' in result
        assert 'Album Title' in result


class TestReconcileFilenames:
    """Test _reconcile_filenames() scan-to-rip filename reconciliation (#1355, #1281)."""

    def test_matching_filename_unchanged(self, app_context, sample_job, tmp_path):
        """When DB filename matches actual file, no update is made."""
        from arm.ripper.makemkv import _reconcile_filenames
        from arm.ripper.utils import put_track
        from arm.database import db

        # Create track with correct filename
        put_track(sample_job, 0, 3600, '16:9', '24.0', False, 'MakeMKV', 'title_t00.mkv')
        db.session.commit()

        # Create matching file on disk
        raw = tmp_path / 'raw'
        raw.mkdir()
        (raw / 'title_t00.mkv').write_bytes(b'\x00')

        _reconcile_filenames(sample_job, str(raw))

        track = sample_job.tracks.first()
        assert track.filename == 'title_t00.mkv'

    def test_mismatched_filename_reconciled(self, app_context, sample_job, tmp_path):
        """When scan filename differs from rip filename, DB is updated (#1281)."""
        from arm.ripper.makemkv import _reconcile_filenames
        from arm.ripper.utils import put_track
        from arm.database import db

        # Scan-time: MakeMKV reported "Last Vermeer"
        put_track(sample_job, 0, 3600, '16:9', '24.0', False, 'MakeMKV', 'Last Vermeer')
        db.session.commit()

        # Rip-time: actual file has comma and suffix
        raw = tmp_path / 'raw'
        raw.mkdir()
        (raw / 'Last Vermeer, The-B1_t00.mkv').write_bytes(b'\x00')

        _reconcile_filenames(sample_job, str(raw))

        track = sample_job.tracks.first()
        assert track.filename == 'Last Vermeer, The-B1_t00.mkv'

    def test_series_multi_track_reconciled(self, app_context, sample_job, tmp_path):
        """Multiple tracks with mismatched filenames are each reconciled (#1355)."""
        from arm.ripper.makemkv import _reconcile_filenames
        from arm.ripper.utils import put_track
        from arm.database import db

        # Scan-time filenames are just disc title
        put_track(sample_job, 0, 1800, '16:9', '24.0', False, 'MakeMKV', 'COSMOS')
        put_track(sample_job, 1, 1800, '16:9', '24.0', False, 'MakeMKV', 'COSMOS')
        db.session.commit()

        # Actual rip created episode files
        raw = tmp_path / 'raw'
        raw.mkdir()
        (raw / 'COSMOS, Season 1 Disc 1-EPL_0102_t00.mkv').write_bytes(b'\x00')
        (raw / 'COSMOS, Season 1 Disc 1-EPL_0103_t01.mkv').write_bytes(b'\x00')

        _reconcile_filenames(sample_job, str(raw))

        tracks = list(sample_job.tracks.order_by('track_number'))
        assert tracks[0].filename == 'COSMOS, Season 1 Disc 1-EPL_0102_t00.mkv'
        assert tracks[1].filename == 'COSMOS, Season 1 Disc 1-EPL_0103_t01.mkv'

    def test_no_files_on_disk_no_change(self, app_context, sample_job, tmp_path):
        """When rawpath is empty, no changes are made."""
        from arm.ripper.makemkv import _reconcile_filenames
        from arm.ripper.utils import put_track
        from arm.database import db

        put_track(sample_job, 0, 3600, '16:9', '24.0', False, 'MakeMKV', 'title.mkv')
        db.session.commit()

        raw = tmp_path / 'raw'
        raw.mkdir()

        _reconcile_filenames(sample_job, str(raw))

        track = sample_job.tracks.first()
        assert track.filename == 'title.mkv'

    def test_none_rawpath_no_error(self, app_context, sample_job):
        """None rawpath (failed rip) doesn't crash."""
        from arm.ripper.makemkv import _reconcile_filenames

        _reconcile_filenames(sample_job, None)

    # --- New tests for 3-pass reconciliation (#1475) ---

    def test_black_sails_tv_prefix_match(self, app_context, sample_job, tmp_path):
        """TV disc with unique segment IDs renumbered by MakeMKV (#1475).

        Disc title indices: C1=4, B1=5, B2=6, D2=7, D5=8
        MakeMKV sequential:  C1=0, B1=1, B2=2, D2=3, D5=4
        Pass 2 (prefix) resolves each by unique segment ID.
        """
        from arm.ripper.makemkv import _reconcile_filenames
        from arm.ripper.utils import put_track
        from arm.database import db

        # DB tracks with original disc title indices
        put_track(sample_job, 4, 2700, '16:9', '24.0', False, 'MakeMKV', 'C1_t04.mkv')
        put_track(sample_job, 5, 2700, '16:9', '24.0', False, 'MakeMKV', 'B1_t05.mkv')
        put_track(sample_job, 6, 2700, '16:9', '24.0', False, 'MakeMKV', 'B2_t06.mkv')
        put_track(sample_job, 7, 2700, '16:9', '24.0', False, 'MakeMKV', 'D2_t07.mkv')
        put_track(sample_job, 8, 2700, '16:9', '24.0', False, 'MakeMKV', 'D5_t08.mkv')
        db.session.commit()

        # Actual files renumbered sequentially
        raw = tmp_path / 'raw'
        raw.mkdir()
        for f in ['C1_t00.mkv', 'B1_t01.mkv', 'B2_t02.mkv', 'D2_t03.mkv', 'D5_t04.mkv']:
            (raw / f).write_bytes(b'\x00')

        _reconcile_filenames(sample_job, str(raw))

        tracks = {t.track_number: t.filename
                  for t in sample_job.tracks.order_by('track_number')}
        assert tracks['4'] == 'C1_t00.mkv'
        assert tracks['5'] == 'B1_t01.mkv'
        assert tracks['6'] == 'B2_t02.mkv'
        assert tracks['7'] == 'D2_t03.mkv'
        assert tracks['8'] == 'D5_t04.mkv'

    def test_movie_all_mode_positional_match(self, app_context, sample_job, tmp_path):
        """Movie ripped in all-mode; all tracks share the same prefix (#1475).

        All files share the prefix 'Movie' so prefix match can't uniquely resolve.
        Pass 3 (positional) pairs them by sorted order.
        """
        from arm.ripper.makemkv import _reconcile_filenames
        from arm.ripper.utils import put_track
        from arm.database import db

        # DB has disc title indices 5, 8, 12 — none match actual filenames
        put_track(sample_job, 5, 7200, '16:9', '24.0', True, 'MakeMKV', 'Movie_t05.mkv')
        put_track(sample_job, 8, 1200, '16:9', '24.0', False, 'MakeMKV', 'Movie_t08.mkv')
        put_track(sample_job, 12, 900, '16:9', '24.0', False, 'MakeMKV', 'Movie_t12.mkv')
        db.session.commit()

        # MakeMKV renumbered to 0, 1, 2
        raw = tmp_path / 'raw'
        raw.mkdir()
        for f in ['Movie_t00.mkv', 'Movie_t01.mkv', 'Movie_t02.mkv']:
            (raw / f).write_bytes(b'\x00')

        _reconcile_filenames(sample_job, str(raw))

        tracks = {t.track_number: t.filename
                  for t in sample_job.tracks.order_by('track_number')}
        assert tracks['5'] == 'Movie_t00.mkv'
        assert tracks['8'] == 'Movie_t01.mkv'
        assert tracks['12'] == 'Movie_t02.mkv'

    def test_mainfeature_single_track_prefix(self, app_context, sample_job, tmp_path):
        """Single MAINFEATURE track, disc index ≠ 0 — prefix match resolves it."""
        from arm.ripper.makemkv import _reconcile_filenames
        from arm.ripper.utils import put_track
        from arm.database import db

        put_track(sample_job, 3, 7200, '16:9', '24.0', True, 'MakeMKV', 'Feature_t03.mkv')
        db.session.commit()

        raw = tmp_path / 'raw'
        raw.mkdir()
        (raw / 'Feature_t00.mkv').write_bytes(b'\x00')

        _reconcile_filenames(sample_job, str(raw))

        track = sample_job.tracks.first()
        assert track.filename == 'Feature_t00.mkv'

    def test_non_contiguous_indices_positional(self, app_context, sample_job, tmp_path):
        """Non-contiguous disc indices with shared prefix — positional match (#1475)."""
        from arm.ripper.makemkv import _reconcile_filenames
        from arm.ripper.utils import put_track
        from arm.database import db

        # Disc indices 0, 3, 7 — gaps between them
        put_track(sample_job, 0, 5400, '16:9', '24.0', True, 'MakeMKV', 'Title_t00.mkv')
        put_track(sample_job, 3, 2700, '16:9', '24.0', False, 'MakeMKV', 'Title_t03.mkv')
        put_track(sample_job, 7, 1800, '16:9', '24.0', False, 'MakeMKV', 'Title_t07.mkv')
        db.session.commit()

        raw = tmp_path / 'raw'
        raw.mkdir()
        # Track 0 matches exactly; tracks 3 and 7 get renumbered
        (raw / 'Title_t00.mkv').write_bytes(b'\x00')
        (raw / 'Title_t01.mkv').write_bytes(b'\x00')
        (raw / 'Title_t02.mkv').write_bytes(b'\x00')

        _reconcile_filenames(sample_job, str(raw))

        tracks = {t.track_number: t.filename
                  for t in sample_job.tracks.order_by('track_number')}
        assert tracks['0'] == 'Title_t00.mkv'   # exact match (pass 1)
        assert tracks['3'] == 'Title_t01.mkv'    # positional (pass 3)
        assert tracks['7'] == 'Title_t02.mkv'    # positional (pass 3)

    def test_mixed_exact_and_prefix_match(self, app_context, sample_job, tmp_path):
        """Some tracks match exactly, others need prefix reconciliation."""
        from arm.ripper.makemkv import _reconcile_filenames
        from arm.ripper.utils import put_track
        from arm.database import db

        # Track 0: exact match, Track 3: needs prefix match
        put_track(sample_job, 0, 2700, '16:9', '24.0', False, 'MakeMKV', 'A1_t00.mkv')
        put_track(sample_job, 3, 2700, '16:9', '24.0', False, 'MakeMKV', 'B1_t03.mkv')
        db.session.commit()

        raw = tmp_path / 'raw'
        raw.mkdir()
        (raw / 'A1_t00.mkv').write_bytes(b'\x00')   # exact match for track 0
        (raw / 'B1_t01.mkv').write_bytes(b'\x00')   # prefix match for track 3

        _reconcile_filenames(sample_job, str(raw))

        tracks = {t.track_number: t.filename
                  for t in sample_job.tracks.order_by('track_number')}
        assert tracks['0'] == 'A1_t00.mkv'
        assert tracks['3'] == 'B1_t01.mkv'

    def test_partial_rip_no_wrong_match(self, app_context, sample_job, tmp_path):
        """File count ≠ track count — positional match refuses to guess (#1475)."""
        from arm.ripper.makemkv import _reconcile_filenames
        from arm.ripper.utils import put_track
        from arm.database import db

        # 3 tracks in DB
        put_track(sample_job, 2, 2700, '16:9', '24.0', False, 'MakeMKV', 'Ep_t02.mkv')
        put_track(sample_job, 5, 2700, '16:9', '24.0', False, 'MakeMKV', 'Ep_t05.mkv')
        put_track(sample_job, 8, 2700, '16:9', '24.0', False, 'MakeMKV', 'Ep_t08.mkv')
        db.session.commit()

        # Only 2 files on disk (partial rip / MakeMKV skipped one)
        raw = tmp_path / 'raw'
        raw.mkdir()
        (raw / 'Ep_t00.mkv').write_bytes(b'\x00')
        (raw / 'Ep_t01.mkv').write_bytes(b'\x00')

        _reconcile_filenames(sample_job, str(raw))

        # No matches should be made — filenames unchanged
        tracks = {t.track_number: t.filename
                  for t in sample_job.tracks.order_by('track_number')}
        assert tracks['2'] == 'Ep_t02.mkv'
        assert tracks['5'] == 'Ep_t05.mkv'
        assert tracks['8'] == 'Ep_t08.mkv'

    def test_scan_filename_no_suffix(self, app_context, sample_job, tmp_path):
        """Bare disc title without _tNN in DB — positional match resolves (#1475)."""
        from arm.ripper.makemkv import _reconcile_filenames
        from arm.ripper.utils import put_track
        from arm.database import db

        # Scan reported bare titles (no _tNN suffix)
        put_track(sample_job, 0, 5400, '16:9', '24.0', True, 'MakeMKV', 'My Movie')
        put_track(sample_job, 1, 1200, '16:9', '24.0', False, 'MakeMKV', 'My Movie')
        db.session.commit()

        raw = tmp_path / 'raw'
        raw.mkdir()
        (raw / 'My Movie_t00.mkv').write_bytes(b'\x00')
        (raw / 'My Movie_t01.mkv').write_bytes(b'\x00')

        _reconcile_filenames(sample_job, str(raw))

        tracks = list(sample_job.tracks.order_by('track_number'))
        assert tracks[0].filename == 'My Movie_t00.mkv'
        assert tracks[1].filename == 'My Movie_t01.mkv'

    def test_strip_track_suffix_helper(self):
        """Unit test for _strip_track_suffix() helper."""
        from arm.ripper.makemkv import _strip_track_suffix

        assert _strip_track_suffix('C1_t04.mkv') == 'C1'
        assert _strip_track_suffix('Movie_t00.mkv') == 'Movie'
        assert _strip_track_suffix('Last Vermeer, The-B1_t00.mkv') == 'Last Vermeer, The-B1'
        assert _strip_track_suffix('title.mkv') == 'title'
        assert _strip_track_suffix('My Movie') == 'My Movie'
        assert _strip_track_suffix('EP_0102_t01.mkv') == 'EP_0102'


class TestMakeMkvRunParserFragility:
    """Test that makemkv.run() skips unrecognized output lines gracefully (#1688)."""

    def test_unrecognized_lines_skipped(self):
        """Parser skips unrecognized output lines and yields only valid data."""
        from arm.ripper.makemkv import run, OutputType

        fake_stdout = [
            'TCOUNT:1\n',
            'Direct disc access mode enabled\n',       # no colon prefix
            'DEBUG:some internal makemkv message\n',    # unknown prefix
            'MSG:1005,0,1,"MakeMKV started","","""\n',  # valid MSG
        ]
        mock_proc = unittest.mock.MagicMock()
        mock_proc.stdout = iter(fake_stdout)
        mock_proc.returncode = 0
        mock_proc.pid = 12345
        mock_proc.__enter__ = lambda s: s
        mock_proc.__exit__ = unittest.mock.MagicMock(return_value=False)

        with unittest.mock.patch('shutil.which', return_value='/usr/bin/makemkvcon'), \
             unittest.mock.patch('subprocess.Popen', return_value=mock_proc):
            results = list(run(['info', 'disc:0'], OutputType.TCOUNT | OutputType.MSG))

        assert len(results) == 2  # TCOUNT + MSG parsed, debug lines skipped

    def test_nonzero_exit_raises(self):
        """When makemkvcon exits non-zero, MakeMkvRuntimeError is raised."""
        from arm.ripper.makemkv import run, OutputType, MakeMkvRuntimeError

        fake_stdout = ['Some error output\n']
        mock_proc = unittest.mock.MagicMock()
        mock_proc.stdout = iter(fake_stdout)
        mock_proc.returncode = 1
        mock_proc.pid = 12345
        mock_proc.__enter__ = lambda s: s
        mock_proc.__exit__ = unittest.mock.MagicMock(return_value=False)

        with unittest.mock.patch('shutil.which', return_value='/usr/bin/makemkvcon'), \
             unittest.mock.patch('subprocess.Popen', return_value=mock_proc):
            with pytest.raises(MakeMkvRuntimeError):
                list(run(['info', 'disc:0'], OutputType.MSG))

    def test_only_unrecognized_lines_still_succeeds(self):
        """A run with only unrecognized lines but exit code 0 succeeds with no results."""
        from arm.ripper.makemkv import run, OutputType

        fake_stdout = [
            'Direct disc access mode enabled\n',
            'Using direct disc access mode\n',
        ]
        mock_proc = unittest.mock.MagicMock()
        mock_proc.stdout = iter(fake_stdout)
        mock_proc.returncode = 0
        mock_proc.pid = 12345
        mock_proc.__enter__ = lambda s: s
        mock_proc.__exit__ = unittest.mock.MagicMock(return_value=False)

        with unittest.mock.patch('shutil.which', return_value='/usr/bin/makemkvcon'), \
             unittest.mock.patch('subprocess.Popen', return_value=mock_proc):
            results = list(run(['info', 'disc:0'], OutputType.TCOUNT))

        assert len(results) == 0
