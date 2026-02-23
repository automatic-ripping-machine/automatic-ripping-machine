"""Tests for disc identification — README Feature: Video Metadata Retrieval.

Covers identify.py functions: find_mount(), identify_bluray(), update_job(),
metadata_selector(), identify_loop(), try_with_year(), try_without_year().
Also covers arm/ui/metadata.py: call_omdb_api() fallback for short titles.
"""
import json
import subprocess
import unittest.mock

import pytest


class TestFindMount:
    """Test find_mount() parsing of findmnt JSON output."""

    def test_returns_mountpoint(self, tmp_path):
        """Returns the target from findmnt JSON when accessible."""
        from arm.ripper.identify import find_mount

        mount_target = str(tmp_path)
        findmnt_output = json.dumps({
            "filesystems": [{"target": mount_target, "source": "/dev/sr0"}]
        })
        with unittest.mock.patch('arm.ripper.identify.arm_subprocess', return_value=findmnt_output):
            result = find_mount('/dev/sr0')
        assert result == mount_target

    def test_returns_none_when_no_output(self):
        """Returns None when findmnt produces no output."""
        from arm.ripper.identify import find_mount

        with unittest.mock.patch('arm.ripper.identify.arm_subprocess', return_value=None):
            result = find_mount('/dev/sr0')
        assert result is None

    def test_skips_inaccessible_mountpoint(self, tmp_path):
        """Skips mountpoints that aren't readable."""
        from arm.ripper.identify import find_mount

        findmnt_output = json.dumps({
            "filesystems": [{"target": "/nonexistent/path", "source": "/dev/sr0"}]
        })
        with unittest.mock.patch('arm.ripper.identify.arm_subprocess', return_value=findmnt_output):
            result = find_mount('/dev/sr0')
        assert result is None

    def test_multiple_mountpoints_returns_first_accessible(self, tmp_path):
        """Returns first accessible mountpoint from multiple entries."""
        from arm.ripper.identify import find_mount

        findmnt_output = json.dumps({
            "filesystems": [
                {"target": "/nonexistent", "source": "/dev/sr0"},
                {"target": str(tmp_path), "source": "/dev/sr0"},
            ]
        })
        with unittest.mock.patch('arm.ripper.identify.arm_subprocess', return_value=findmnt_output):
            result = find_mount('/dev/sr0')
        assert result == str(tmp_path)


class TestCheckMount:
    """Test check_mount() mount-or-find logic."""

    def test_already_mounted(self, tmp_path):
        """If disc is already mounted, returns True and sets mountpoint."""
        from arm.ripper.identify import check_mount

        job = unittest.mock.MagicMock()
        job.devpath = '/dev/sr0'
        with unittest.mock.patch('arm.ripper.identify.find_mount', return_value=str(tmp_path)):
            result = check_mount(job)
        assert result is True
        assert job.mountpoint == str(tmp_path)

    def test_mount_attempt_succeeds(self, tmp_path):
        """If not mounted, tries mount and succeeds on second find_mount call."""
        from arm.ripper.identify import check_mount

        job = unittest.mock.MagicMock()
        job.devpath = '/dev/sr0'
        # First call: not mounted; second call after mount: found
        with unittest.mock.patch('arm.ripper.identify.find_mount',
                                 side_effect=[None, str(tmp_path)]), \
             unittest.mock.patch('arm.ripper.identify.arm_subprocess'):
            result = check_mount(job)
        assert result is True

    def test_mount_fails(self):
        """If mount fails, returns False."""
        from arm.ripper.identify import check_mount

        job = unittest.mock.MagicMock()
        job.devpath = '/dev/sr0'
        with unittest.mock.patch('arm.ripper.identify.find_mount', return_value=None), \
             unittest.mock.patch('arm.ripper.identify.arm_subprocess'):
            result = check_mount(job)
        assert result is False


class TestIdentifyBluray:
    """Test identify_bluray() XML parsing for Blu-ray discs."""

    def _make_job(self):
        """Create a minimal mock job for bluray identification."""
        from arm.models.job import Job
        with unittest.mock.patch.object(Job, 'parse_udev'), \
             unittest.mock.patch.object(Job, 'get_pid'):
            job = Job('/dev/sr0')
        job.disctype = 'bluray'
        job.label = 'SERIAL_MOM'
        job.title = None
        job.title_auto = None
        job.year = None
        job.year_auto = None
        return job

    def test_parses_xml_title(self, app_context, tmp_path):
        """Extracts title from bdmt_eng.xml."""
        from arm.ripper.identify import identify_bluray

        job = self._make_job()
        job.mountpoint = str(tmp_path)

        # Create bdmt_eng.xml structure
        xml_dir = tmp_path / 'BDMV' / 'META' / 'DL'
        xml_dir.mkdir(parents=True)
        xml_file = xml_dir / 'bdmt_eng.xml'
        xml_file.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<disclib xmlns:di="urn:BDA:bdmv;discinfo">'
            '<di:discinfo><di:title><di:name>Serial Mom</di:name></di:title></di:discinfo>'
            '</disclib>'
        )

        result = identify_bluray(job)
        assert result is True
        assert 'Serial-Mom' in job.title or 'Serial Mom' in job.title

    def test_xml_missing_returns_false(self, app_context, tmp_path):
        """When bdmt_eng.xml is missing, returns False — caller handles fallback."""
        from arm.ripper.identify import identify_bluray

        job = self._make_job()
        job.mountpoint = str(tmp_path)
        # No XML file exists

        result = identify_bluray(job)
        assert result is False

    def test_xml_missing_empty_label(self, app_context, tmp_path):
        """When XML is missing AND label is empty, returns False."""
        from arm.ripper.identify import identify_bluray

        job = self._make_job()
        job.mountpoint = str(tmp_path)
        job.label = ""

        result = identify_bluray(job)
        assert result is False

    def test_strips_bluray_tm_suffix(self, app_context, tmp_path):
        """Strips ' - Blu-rayTM' from extracted title."""
        from arm.ripper.identify import identify_bluray

        job = self._make_job()
        job.mountpoint = str(tmp_path)

        xml_dir = tmp_path / 'BDMV' / 'META' / 'DL'
        xml_dir.mkdir(parents=True)
        xml_file = xml_dir / 'bdmt_eng.xml'
        xml_file.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<disclib xmlns:di="urn:BDA:bdmv;discinfo">'
            '<di:discinfo><di:title><di:name>Serial Mom - Blu-rayTM</di:name></di:title></di:discinfo>'
            '</disclib>'
        )

        identify_bluray(job)
        assert 'Blu-ray' not in job.title
        assert 'Serial' in job.title


class TestUpdateJob:
    """Test update_job() search result processing with disc matcher."""

    def test_valid_search_results(self, app_context, sample_job):
        """Valid OMDb-format search results update the job via matcher."""
        from arm.ripper.identify import update_job

        search_results = {
            'Search': [{
                'Title': 'Serial Mom',
                'Year': '1994',
                'Type': 'movie',
                'imdbID': 'tt0111127',
                'Poster': 'https://example.com/poster.jpg',
            }]
        }
        result = update_job(sample_job, search_results)
        assert result is True
        assert 'Serial-Mom' in sample_job.title or 'Serial Mom' in sample_job.title
        assert sample_job.year == '1994'
        assert sample_job.video_type == 'movie'
        assert sample_job.imdb_id == 'tt0111127'
        assert sample_job.hasnicetitle is True

    def test_no_search_key_returns_none(self, app_context, sample_job):
        """Missing 'Search' key returns None."""
        from arm.ripper.identify import update_job

        result = update_job(sample_job, {'Response': 'False', 'Error': 'Not found'})
        assert result is None

    def test_empty_search_list_returns_none(self, app_context, sample_job):
        """Empty 'Search' list returns None (matcher handles gracefully)."""
        from arm.ripper.identify import update_job

        result = update_job(sample_job, {'Search': []})
        assert result is None

    def test_picks_best_match_not_first(self, app_context, sample_job):
        """Matcher should pick the best-scoring result, not Search[0]."""
        from arm.ripper.identify import update_job

        # sample_job.label = 'SERIAL_MOM'
        search_results = {
            'Search': [
                {
                    'Title': 'Serial Killer Mom',
                    'Year': '2020',
                    'Type': 'movie',
                    'imdbID': 'tt9999999',
                    'Poster': 'N/A',
                },
                {
                    'Title': 'Serial Mom',
                    'Year': '1994',
                    'Type': 'movie',
                    'imdbID': 'tt0111127',
                    'Poster': 'https://example.com/poster.jpg',
                },
            ]
        }
        result = update_job(sample_job, search_results)
        assert result is True
        # Should pick "Serial Mom" (index 1), not "Serial Killer Mom" (index 0)
        assert sample_job.imdb_id == 'tt0111127'

    def test_rejects_low_confidence(self, app_context, sample_job):
        """Matcher rejects results that don't match the disc label well."""
        from arm.ripper.identify import update_job

        # sample_job.label = 'SERIAL_MOM'
        search_results = {
            'Search': [{
                'Title': 'Finding Nemo',
                'Year': '2003',
                'Type': 'movie',
                'imdbID': 'tt0266543',
                'Poster': 'https://example.com/nemo.jpg',
            }]
        }
        result = update_job(sample_job, search_results)
        # Finding Nemo shouldn't match SERIAL_MOM
        assert result is None

    def test_poster_na_normalized(self, app_context, sample_job):
        """OMDb 'N/A' poster should be stored as empty string."""
        from arm.ripper.identify import update_job

        search_results = {
            'Search': [{
                'Title': 'Serial Mom',
                'Year': '1994',
                'Type': 'movie',
                'imdbID': 'tt0111127',
                'Poster': 'N/A',
            }]
        }
        update_job(sample_job, search_results)
        # Matcher normalizes N/A to None, update_job converts to ''
        assert sample_job.poster_url == ''


class TestMetadataSelector:
    """Test metadata_selector() provider switching."""

    def _make_job(self):
        from arm.models.job import Job
        with unittest.mock.patch.object(Job, 'parse_udev'), \
             unittest.mock.patch.object(Job, 'get_pid'):
            job = Job('/dev/sr0')
        job.title = 'TEST'
        job.label = 'TEST'
        return job

    def test_omdb_provider(self):
        """When METADATA_PROVIDER=omdb, calls call_omdb_api."""
        from arm.ripper.identify import metadata_selector
        import arm.config.config as cfg

        job = self._make_job()
        original = cfg.arm_config.get('METADATA_PROVIDER')
        cfg.arm_config['METADATA_PROVIDER'] = 'omdb'
        try:
            # Return None to avoid update_job being called
            with unittest.mock.patch('arm.ripper.identify.ui_utils.call_omdb_api',
                                     return_value=None) as mock_omdb:
                metadata_selector(job, 'Serial Mom', '1994')
                mock_omdb.assert_called_once()
        finally:
            if original is not None:
                cfg.arm_config['METADATA_PROVIDER'] = original

    def test_tmdb_provider(self):
        """When METADATA_PROVIDER=tmdb, calls tmdb_search."""
        from arm.ripper.identify import metadata_selector
        import arm.config.config as cfg

        job = self._make_job()
        original = cfg.arm_config.get('METADATA_PROVIDER')
        cfg.arm_config['METADATA_PROVIDER'] = 'tmdb'
        try:
            with unittest.mock.patch('arm.ripper.identify.ui_utils.tmdb_search',
                                     return_value=None) as mock_tmdb:
                metadata_selector(job, 'Serial Mom', '1994')
                mock_tmdb.assert_called_once()
        finally:
            if original is not None:
                cfg.arm_config['METADATA_PROVIDER'] = original

    def test_unknown_provider_returns_none(self):
        """Unknown METADATA_PROVIDER returns None."""
        from arm.ripper.identify import metadata_selector
        import arm.config.config as cfg

        job = self._make_job()
        original = cfg.arm_config.get('METADATA_PROVIDER')
        cfg.arm_config['METADATA_PROVIDER'] = 'invalid_provider'
        try:
            result = metadata_selector(job, 'Serial Mom', '1994')
            assert result is None
        finally:
            if original is not None:
                cfg.arm_config['METADATA_PROVIDER'] = original

    def test_returns_none_when_matcher_rejects(self):
        """When API returns results but matcher isn't confident, return None
        so identify_loop retries with simplified queries."""
        from arm.ripper.identify import metadata_selector
        import arm.config.config as cfg

        job = self._make_job()
        # label = 'TEST' but API returns unrelated result
        original = cfg.arm_config.get('METADATA_PROVIDER')
        cfg.arm_config['METADATA_PROVIDER'] = 'omdb'
        try:
            bad_results = {
                'Search': [{
                    'Title': 'Completely Unrelated Movie',
                    'Year': '2020',
                    'Type': 'movie',
                    'imdbID': 'tt9999999',
                    'Poster': 'N/A',
                }],
                'Response': 'True',
            }
            with unittest.mock.patch('arm.ripper.identify.ui_utils.call_omdb_api',
                                     return_value=bad_results):
                result = metadata_selector(job, 'TEST', '2020')
            # Should return None because matcher rejected the results
            assert result is None
        finally:
            if original is not None:
                cfg.arm_config['METADATA_PROVIDER'] = original


class TestTryWithYear:
    """Test try_with_year() metadata retry with year variations."""

    def test_returns_existing_response(self):
        """If response is already set, returns it unchanged."""
        from arm.ripper.identify import try_with_year

        existing = {'Search': [{'Title': 'Test'}]}
        result = try_with_year(None, existing, 'Test', '2020')
        assert result is existing

    def test_tries_with_year(self):
        """When response is None and year given, calls metadata_selector."""
        from arm.ripper.identify import try_with_year

        mock_result = {'Search': [{'Title': 'Test'}]}
        with unittest.mock.patch('arm.ripper.identify.metadata_selector',
                                 return_value=mock_result) as mock_ms:
            result = try_with_year(None, None, 'Test', '2020')
            assert result == mock_result
            mock_ms.assert_called_once_with(None, 'Test', '2020')

    def test_subtracts_year_on_failure(self):
        """If first try fails, subtracts 1 year and tries again."""
        from arm.ripper.identify import try_with_year

        mock_result = {'Search': [{'Title': 'Test'}]}
        with unittest.mock.patch('arm.ripper.identify.metadata_selector',
                                 side_effect=[None, mock_result]) as mock_ms:
            result = try_with_year(None, None, 'Test', '2020')
            assert result == mock_result
            assert mock_ms.call_count == 2
            # Second call with year-1
            assert mock_ms.call_args_list[1][0][2] == '2019'

    def test_no_year_skips(self):
        """If year is falsy, skips metadata_selector call."""
        from arm.ripper.identify import try_with_year

        with unittest.mock.patch('arm.ripper.identify.metadata_selector') as mock_ms:
            result = try_with_year(None, None, 'Test', None)
            mock_ms.assert_not_called()
            assert result is None


class TestTryWithoutYear:
    """Test try_without_year() metadata retry without year."""

    def test_calls_when_response_none(self):
        """Calls metadata_selector without year when response is None."""
        from arm.ripper.identify import try_without_year

        mock_result = {'Search': [{'Title': 'Test'}]}
        with unittest.mock.patch('arm.ripper.identify.metadata_selector',
                                 return_value=mock_result) as mock_ms:
            result = try_without_year(None, None, 'Test')
            mock_ms.assert_called_once_with(None, 'Test')
            assert result == mock_result

    def test_skips_when_response_exists(self):
        """Does nothing when response already has a value."""
        from arm.ripper.identify import try_without_year

        existing = {'Search': [{'Title': 'Existing'}]}
        with unittest.mock.patch('arm.ripper.identify.metadata_selector') as mock_ms:
            result = try_without_year(None, existing, 'Test')
            mock_ms.assert_not_called()
            assert result is existing


class TestIdentifyLoop:
    """Test identify_loop() progressive title slicing retry logic."""

    def test_with_existing_response_does_nothing(self):
        """When response is provided, no metadata_selector calls are made."""
        from arm.ripper.identify import identify_loop

        existing = {'Search': [{'Title': 'Test'}]}
        with unittest.mock.patch('arm.ripper.identify.metadata_selector'), \
             unittest.mock.patch('arm.ripper.identify.try_with_year', return_value=existing), \
             unittest.mock.patch('arm.ripper.identify.try_without_year', return_value=existing):
            identify_loop(None, existing, 'Test', '2020')
            # When response is not None, the function should return early

    def test_slices_title_on_hyphen(self):
        """When response is None, tries slicing title on hyphens."""
        from arm.ripper.identify import identify_loop

        call_count = 0
        titles_tried = []

        def mock_selector(job, title, year=None):
            nonlocal call_count
            titles_tried.append(title)
            call_count += 1
            if call_count >= 2:
                return {'Search': [{'Title': 'Found'}]}
            return None

        with unittest.mock.patch('arm.ripper.identify.metadata_selector',
                                 side_effect=mock_selector), \
             unittest.mock.patch('arm.ripper.identify.try_with_year', return_value=None), \
             unittest.mock.patch('arm.ripper.identify.try_without_year', return_value=None):
            identify_loop(None, None, 'Title-Part-Extra', '2020')
        # Should have tried "Title-Part" (sliced off "-Extra")
        assert any('Title-Part' in t for t in titles_tried)

    def test_slices_title_on_plus(self):
        """When hyphens exhausted, tries slicing on plus signs."""
        from arm.ripper.identify import identify_loop

        titles_tried = []

        def mock_selector(job, title, year=None):
            titles_tried.append(title)
            # Return None for first several tries, then succeed
            if title == 'Title':
                return {'Search': [{'Title': 'Found'}]}
            return None

        with unittest.mock.patch('arm.ripper.identify.metadata_selector',
                                 side_effect=mock_selector), \
             unittest.mock.patch('arm.ripper.identify.try_with_year', return_value=None), \
             unittest.mock.patch('arm.ripper.identify.try_without_year', return_value=None):
            identify_loop(None, None, 'Title+Extra+Words', '2020')
        # Should eventually try 'Title' (sliced off '+Extra+Words')
        assert 'Title' in titles_tried


class TestMalformedBlurayXml:
    """Test identify_bluray() handles malformed XML gracefully (#1650)."""

    def _make_job(self):
        from arm.models.job import Job
        with unittest.mock.patch.object(Job, 'parse_udev'), \
             unittest.mock.patch.object(Job, 'get_pid'):
            job = Job('/dev/sr0')
        job.disctype = 'bluray'
        job.label = 'SERIAL_MOM'
        job.title = None
        job.title_auto = None
        job.year = None
        job.year_auto = None
        return job

    def test_malformed_xml_returns_false(self, app_context, tmp_path):
        """Malformed XML returns False — caller handles fallback."""
        from arm.ripper.identify import identify_bluray

        job = self._make_job()
        job.mountpoint = str(tmp_path)

        xml_dir = tmp_path / 'BDMV' / 'META' / 'DL'
        xml_dir.mkdir(parents=True)
        xml_file = xml_dir / 'bdmt_eng.xml'
        xml_file.write_text('<<<not valid xml>>>')

        result = identify_bluray(job)
        assert result is False

    def test_malformed_xml_empty_label(self, app_context, tmp_path):
        """Malformed XML with empty label returns False."""
        from arm.ripper.identify import identify_bluray

        job = self._make_job()
        job.mountpoint = str(tmp_path)
        job.label = ""

        xml_dir = tmp_path / 'BDMV' / 'META' / 'DL'
        xml_dir.mkdir(parents=True)
        xml_file = xml_dir / 'bdmt_eng.xml'
        xml_file.write_text('<<<not valid xml>>>')

        result = identify_bluray(job)
        assert result is False

    def test_none_label_does_not_produce_string_none(self, app_context, tmp_path):
        """When label is None and XML is malformed, title must NOT become 'None'."""
        from arm.ripper.identify import identify_bluray

        job = self._make_job()
        job.mountpoint = str(tmp_path)
        job.label = None

        xml_dir = tmp_path / 'BDMV' / 'META' / 'DL'
        xml_dir.mkdir(parents=True)
        xml_file = xml_dir / 'bdmt_eng.xml'
        xml_file.write_text('<<<not valid xml>>>')

        result = identify_bluray(job)
        assert result is False
        # identify_bluray must not set title to the literal string "None"
        assert job.title != "None"

    def test_truncated_xml_returns_false(self, app_context, tmp_path):
        """Truncated/incomplete XML returns False — caller handles fallback."""
        from arm.ripper.identify import identify_bluray

        job = self._make_job()
        job.mountpoint = str(tmp_path)

        xml_dir = tmp_path / 'BDMV' / 'META' / 'DL'
        xml_dir.mkdir(parents=True)
        xml_file = xml_dir / 'bdmt_eng.xml'
        xml_file.write_bytes(b'<?xml version="1.0"?><disclib><di:discinfo')  # truncated

        result = identify_bluray(job)
        assert result is False


class TestIdentifyUnmount:
    """Test identify() always unmounts the disc (#1664)."""

    def test_umount_called_on_success(self):
        """umount is called after successful identification."""
        from arm.ripper.identify import identify

        job = unittest.mock.MagicMock()
        job.devpath = '/dev/sr0'
        job.disctype = 'music'  # skip video identification

        with unittest.mock.patch('arm.ripper.identify.check_mount', return_value=True), \
             unittest.mock.patch('arm.ripper.identify.subprocess.run') as mock_run:
            identify(job)
            mock_run.assert_called_once_with(
                ["umount", "/dev/sr0"], stderr=subprocess.PIPE, text=True
            )

    def test_umount_called_on_exception(self):
        """umount is called even when identification raises an exception."""
        from arm.ripper.identify import identify

        job = unittest.mock.MagicMock()
        job.devpath = '/dev/sr0'
        job.disctype = 'bluray'

        with unittest.mock.patch('arm.ripper.identify.check_mount', return_value=True), \
             unittest.mock.patch('arm.ripper.identify.cfg') as mock_cfg, \
             unittest.mock.patch('arm.ripper.identify.subprocess.run') as mock_run:
            mock_cfg.arm_config = {"GET_VIDEO_TITLE": True}
            # identify_bluray will fail because job is a MagicMock without a real mountpoint
            with unittest.mock.patch('arm.ripper.identify.identify_bluray',
                                     side_effect=RuntimeError("test error")):
                with pytest.raises(RuntimeError):
                    identify(job)
            # umount should still have been called
            mock_run.assert_called_once_with(
                ["umount", "/dev/sr0"], stderr=subprocess.PIPE, text=True
            )

    def test_umount_called_when_not_mounted(self):
        """umount is called even if disc was not successfully mounted."""
        from arm.ripper.identify import identify

        job = unittest.mock.MagicMock()
        job.devpath = '/dev/sr0'
        job.disctype = 'data'

        with unittest.mock.patch('arm.ripper.identify.check_mount', return_value=False), \
             unittest.mock.patch('arm.ripper.identify.subprocess.run') as mock_run:
            identify(job)
            mock_run.assert_called_once()


class TestMatcherIntegration:
    """End-to-end integration tests: create jobs with matching-relevant
    fields only, feed mock search results through update_job(), and
    verify the matcher picks the correct result."""

    TMDB = "https://image.tmdb.org/t/p/original"

    def _make_job(self, app_context, *, label, year_auto=None, video_type_auto=None):
        """Create a minimal Job with only the fields used by the matcher."""
        from arm.database import db
        from arm.models.job import Job

        with unittest.mock.patch.object(Job, 'parse_udev'), \
             unittest.mock.patch.object(Job, 'get_pid'):
            job = Job('/dev/sr0')

        job.label = label
        job.title = label.replace('_', ' ').title()
        job.title_auto = job.title
        job.year = year_auto or ""
        job.year_auto = year_auto or ""
        job.video_type = video_type_auto or ""
        job.video_type_auto = video_type_auto or ""
        job.imdb_id = ""
        job.imdb_id_auto = ""
        job.poster_url = ""
        job.poster_url_auto = ""
        job.hasnicetitle = False
        job.disctype = "bluray"

        db.session.add(job)
        db.session.flush()
        return job

    # -- LOTR: the original production bug --

    def test_lotr_picks_fellowship_over_parody(self, app_context):
        """LOTR label must pick Fellowship (2001), not 'Pronouns of Power' parody at [0]."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="LOTR_FELLOWSHIP_OF_THE_RING_P1",
                             year_auto="2001", video_type_auto="movie")
        result = update_job(job, {'Search': [
            {'Title': 'LOTR: the Pronouns of Power', 'Year': '2022',
             'imdbID': 'tt22262280', 'Type': 'movie', 'Poster': 'N/A'},
            {'Title': 'The Lord of the Rings: The Fellowship of the Ring', 'Year': '2001',
             'imdbID': 'tt0120737', 'Type': 'movie', 'Poster': f'{self.TMDB}/lotr.jpg'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt0120737'
        assert job.year == '2001'
        assert job.hasnicetitle is True

    # -- Sequel disambiguation --

    def test_hotel_transylvania_3_not_2(self, app_context):
        """'3' in title must be preserved — must match HT3 over HT2 or HT1."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="HOTEL_TRANSYLVANIA_3",
                             year_auto="2018", video_type_auto="movie")
        result = update_job(job, {'Search': [
            {'Title': 'Hotel Transylvania 2', 'Year': '2015',
             'imdbID': 'tt2510894', 'Type': 'movie', 'Poster': 'N/A'},
            {'Title': 'Hotel Transylvania 3: Summer Vacation', 'Year': '2018',
             'imdbID': 'tt5220122', 'Type': 'movie', 'Poster': 'N/A'},
            {'Title': 'Hotel Transylvania', 'Year': '2012',
             'imdbID': 'tt0837562', 'Type': 'movie', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt5220122'

    def test_godfather_part_2_not_part_1(self, app_context):
        """'PART 2' stays in title and picks Godfather Part II."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="THE_GODFATHER_PART_2",
                             year_auto="1974", video_type_auto="movie")
        result = update_job(job, {'Search': [
            {'Title': 'The Godfather', 'Year': '1972',
             'imdbID': 'tt0068646', 'Type': 'movie', 'Poster': 'N/A'},
            {'Title': 'The Godfather Part II', 'Year': '1974',
             'imdbID': 'tt0071562', 'Type': 'movie', 'Poster': 'N/A'},
            {'Title': 'The Godfather Part III', 'Year': '1990',
             'imdbID': 'tt0099674', 'Type': 'movie', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt0071562'

    # -- Year-like numbers in titles --

    def test_blade_runner_2049_not_1982(self, app_context):
        """2049 in title must NOT be treated as year — match the correct sequel."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="BLADE_RUNNER_2049",
                             year_auto="2017", video_type_auto="movie")
        result = update_job(job, {'Search': [
            {'Title': 'Blade Runner', 'Year': '1982',
             'imdbID': 'tt0083658', 'Type': 'movie', 'Poster': 'N/A'},
            {'Title': 'Blade Runner 2049', 'Year': '2017',
             'imdbID': 'tt1856101', 'Type': 'movie', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt1856101'

    def test_2001_space_odyssey(self, app_context):
        """2001 in title is title content, not a year."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="2001_A_SPACE_ODYSSEY",
                             year_auto="1968", video_type_auto="movie")
        result = update_job(job, {'Search': [
            {'Title': '2010: The Year We Make Contact', 'Year': '1984',
             'imdbID': 'tt0086837', 'Type': 'movie', 'Poster': 'N/A'},
            {'Title': '2001: A Space Odyssey', 'Year': '1968',
             'imdbID': 'tt0062622', 'Type': 'movie', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt0062622'

    # -- Compound word matching --

    def test_antman_compound_word(self, app_context):
        """ANTMAN (no separator) must match 'Ant-Man'."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="ANTMAN",
                             year_auto="2015", video_type_auto="movie")
        result = update_job(job, {'Search': [
            {'Title': 'Ant-Man', 'Year': '2015',
             'imdbID': 'tt0478970', 'Type': 'movie', 'Poster': 'N/A'},
            {'Title': 'Ant-Man and the Wasp', 'Year': '2018',
             'imdbID': 'tt5095030', 'Type': 'movie', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt0478970'

    def test_faceoff_compound_word(self, app_context):
        """FACEOFF must match 'Face/Off'."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="FACEOFF",
                             year_auto="1997", video_type_auto="movie")
        result = update_job(job, {'Search': [
            {'Title': 'Face/Off', 'Year': '1997',
             'imdbID': 'tt0119094', 'Type': 'movie', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt0119094'

    # -- Multi-disc suffix stripping --

    def test_disc_suffix_p1_stripped(self, app_context):
        """_P1 is a disc suffix — stripped before matching."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="BACK_TO_THE_FUTURE_P1",
                             year_auto="1985", video_type_auto="movie")
        result = update_job(job, {'Search': [
            {'Title': 'Back to the Future', 'Year': '1985',
             'imdbID': 'tt0088763', 'Type': 'movie', 'Poster': 'N/A'},
            {'Title': 'Back to the Future Part II', 'Year': '1989',
             'imdbID': 'tt0096874', 'Type': 'movie', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt0088763'

    def test_disc_suffix_disc_1_stripped(self, app_context):
        """_DISC_1 is a disc suffix — stripped before matching."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="BACK_TO_THE_FUTURE_DISC_1",
                             year_auto="1985", video_type_auto="movie")
        result = update_job(job, {'Search': [
            {'Title': 'Back to the Future', 'Year': '1985',
             'imdbID': 'tt0088763', 'Type': 'movie', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt0088763'

    def test_disc_suffix_d2_stripped(self, app_context):
        """_D2 is a disc suffix — stripped before matching."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="STAR_WARS_EP_IV_D2",
                             year_auto="1977", video_type_auto="movie")
        result = update_job(job, {'Search': [
            {'Title': 'Star Wars: Episode IV - A New Hope', 'Year': '1977',
             'imdbID': 'tt0076759', 'Type': 'movie', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt0076759'

    # -- PART preserved in title --

    def test_dune_part_two_preserved(self, app_context):
        """PART_TWO must stay in title — it's 'Dune: Part Two', not disc 2."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="DUNE_PART_TWO",
                             year_auto="2024", video_type_auto="movie")
        result = update_job(job, {'Search': [
            {'Title': 'Dune', 'Year': '2021',
             'imdbID': 'tt1160419', 'Type': 'movie', 'Poster': 'N/A'},
            {'Title': 'Dune: Part Two', 'Year': '2024',
             'imdbID': 'tt15239678', 'Type': 'movie', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt15239678'

    # -- Type hint tie-breaking --

    def test_fargo_movie_over_series(self, app_context):
        """Type hint 'movie' + year 1996 picks Fargo movie over TV series."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="FARGO",
                             year_auto="1996", video_type_auto="movie")
        result = update_job(job, {'Search': [
            {'Title': 'Fargo', 'Year': '2014–', 'imdbID': 'tt2802850',
             'Type': 'series', 'Poster': 'N/A'},
            {'Title': 'Fargo', 'Year': '1996', 'imdbID': 'tt0116282',
             'Type': 'movie', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt0116282'

    def test_fargo_series_over_movie(self, app_context):
        """Type hint 'series' + year 2014 picks Fargo series over movie."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="FARGO",
                             year_auto="2014", video_type_auto="series")
        result = update_job(job, {'Search': [
            {'Title': 'Fargo', 'Year': '2014–', 'imdbID': 'tt2802850',
             'Type': 'series', 'Poster': 'N/A'},
            {'Title': 'Fargo', 'Year': '1996', 'imdbID': 'tt0116282',
             'Type': 'movie', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt2802850'

    # -- Rejection / no-match --

    def test_rejects_all_unrelated(self, app_context):
        """All unrelated results should be rejected — returns None."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="SERIAL_MOM",
                             year_auto="1994", video_type_auto="movie")
        result = update_job(job, {'Search': [
            {'Title': 'Finding Nemo', 'Year': '2003',
             'imdbID': 'tt0266543', 'Type': 'movie', 'Poster': 'N/A'},
            {'Title': 'The Avengers', 'Year': '2012',
             'imdbID': 'tt0848228', 'Type': 'movie', 'Poster': 'N/A'},
        ]})
        assert result is None
        assert job.hasnicetitle is False

    def test_no_search_key_returns_none(self, app_context):
        """API error response (no 'Search' key) returns None."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="THE_MATRIX",
                             year_auto="1999", video_type_auto="movie")
        result = update_job(job, {'Response': 'False', 'Error': 'Movie not found!'})
        assert result is None

    def test_empty_search_returns_none(self, app_context):
        """Empty Search array returns None."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="THE_MATRIX",
                             year_auto="1999", video_type_auto="movie")
        result = update_job(job, {'Search': []})
        assert result is None

    # -- Poster normalization --

    def test_poster_na_becomes_empty_string(self, app_context):
        """OMDb 'N/A' poster stored as empty string on job."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="THE_MATRIX",
                             year_auto="1999", video_type_auto="movie")
        update_job(job, {'Search': [
            {'Title': 'The Matrix', 'Year': '1999',
             'imdbID': 'tt0133093', 'Type': 'movie', 'Poster': 'N/A'},
        ]})
        assert job.poster_url == ''
        assert job.poster_url_auto == ''

    def test_poster_url_preserved(self, app_context):
        """Real poster URL is stored as-is."""
        from arm.ripper.identify import update_job

        poster = f'{self.TMDB}/matrix.jpg'
        job = self._make_job(app_context, label="THE_MATRIX",
                             year_auto="1999", video_type_auto="movie")
        update_job(job, {'Search': [
            {'Title': 'The Matrix', 'Year': '1999',
             'imdbID': 'tt0133093', 'Type': 'movie', 'Poster': poster},
        ]})
        assert job.poster_url == poster

    # -- Label cleaning applied to stored title --

    def test_title_cleaned_for_filename(self, app_context):
        """Matched title is run through clean_for_filename before storing."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="LOTR_FELLOWSHIP_OF_THE_RING_P1",
                             year_auto="2001", video_type_auto="movie")
        update_job(job, {'Search': [
            {'Title': 'The Lord of the Rings: The Fellowship of the Ring', 'Year': '2001',
             'imdbID': 'tt0120737', 'Type': 'movie', 'Poster': 'N/A'},
        ]})
        # clean_for_filename replaces colons with hyphens and spaces with hyphens
        assert ':' not in job.title
        assert 'Fellowship' in job.title

    # -- No prior year/type (auto fields empty) --

    def test_no_year_hint_still_matches(self, app_context):
        """Without year_auto, title similarity alone drives the match."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="THE_MATRIX")
        result = update_job(job, {'Search': [
            {'Title': 'The Matrix', 'Year': '1999',
             'imdbID': 'tt0133093', 'Type': 'movie', 'Poster': 'N/A'},
            {'Title': 'The Matrix Reloaded', 'Year': '2003',
             'imdbID': 'tt0234215', 'Type': 'movie', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt0133093'

    # -- Aspect ratio / SKU cleaning --

    def test_16x9_stripped(self, app_context):
        """16x9 aspect ratio marker stripped from label before matching."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="ALIEN_16x9",
                             year_auto="1979", video_type_auto="movie")
        result = update_job(job, {'Search': [
            {'Title': 'Alien', 'Year': '1979',
             'imdbID': 'tt0078748', 'Type': 'movie', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt0078748'

    def test_sku_stripped(self, app_context):
        """SKU suffix stripped from label before matching."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="OCEAN_S_ELEVEN_SKU1234",
                             year_auto="2001", video_type_auto="movie")
        result = update_job(job, {'Search': [
            {"Title": "Ocean's Eleven", 'Year': '2001',
             'imdbID': 'tt0240772', 'Type': 'movie', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt0240772'

    # -- Year proximity: DVD release ±1 year from movie release --

    def test_year_off_by_one_still_matches(self, app_context):
        """Disc year 2009 should still match a 2008 movie (DVD ±1 year)."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="THE_DARK_KNIGHT",
                             year_auto="2009", video_type_auto="movie")
        result = update_job(job, {'Search': [
            {'Title': 'The Dark Knight', 'Year': '2008',
             'imdbID': 'tt0468569', 'Type': 'movie', 'Poster': 'N/A'},
            {'Title': 'The Dark Knight Rises', 'Year': '2012',
             'imdbID': 'tt1345836', 'Type': 'movie', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt0468569'

    # -- TV Series: basic season suffix stripping --

    def test_series_game_of_thrones_s1(self, app_context):
        """GAME_OF_THRONES_S1 — S suffix stripped, matches series."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="GAME_OF_THRONES_S1",
                             video_type_auto="series")
        result = update_job(job, {'Search': [
            {'Title': 'Game of Thrones', 'Year': '2011–2019',
             'imdbID': 'tt0944947', 'Type': 'series', 'Poster': 'N/A'},
            {'Title': 'Game of Thrones: The Last Watch', 'Year': '2019',
             'imdbID': 'tt10731768', 'Type': 'movie', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt0944947'
        assert job.hasnicetitle is True

    def test_series_breaking_bad_s1d1(self, app_context):
        """BREAKING_BAD_S1D1 — combined season+disc stripped."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="BREAKING_BAD_S1D1",
                             video_type_auto="series")
        result = update_job(job, {'Search': [
            {'Title': 'Breaking Bad', 'Year': '2008–2013',
             'imdbID': 'tt0903747', 'Type': 'series', 'Poster': 'N/A'},
            {'Title': 'El Camino: A Breaking Bad Movie', 'Year': '2019',
             'imdbID': 'tt9243946', 'Type': 'movie', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt0903747'

    def test_series_stranger_things_s1(self, app_context):
        """STRANGER_THINGS_S1 — S suffix."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="STRANGER_THINGS_S1",
                             video_type_auto="series")
        result = update_job(job, {'Search': [
            {'Title': 'Stranger Things', 'Year': '2016–',
             'imdbID': 'tt4574334', 'Type': 'series', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt4574334'

    # -- TV Series: short titles (most likely to fail without season stripping) --

    def test_series_friends_season_3_disc_2(self, app_context):
        """FRIENDS_SEASON_3_DISC_2 — short title with SEASON keyword + disc."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="FRIENDS_SEASON_3_DISC_2",
                             video_type_auto="series")
        result = update_job(job, {'Search': [
            {'Title': 'Friends', 'Year': '1994–2004',
             'imdbID': 'tt0108778', 'Type': 'series', 'Poster': 'N/A'},
            {'Title': 'Friends with Benefits', 'Year': '2011',
             'imdbID': 'tt1632708', 'Type': 'movie', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt0108778'

    def test_series_lost_season_1_disc_1(self, app_context):
        """LOST_SEASON_1_DISC_1 — very short title with full SEASON+DISC."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="LOST_SEASON_1_DISC_1",
                             video_type_auto="series")
        result = update_job(job, {'Search': [
            {'Title': 'Lost', 'Year': '2004–2010',
             'imdbID': 'tt0411008', 'Type': 'series', 'Poster': 'N/A'},
            {'Title': 'Lost in Translation', 'Year': '2003',
             'imdbID': 'tt0335266', 'Type': 'movie', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt0411008'

    def test_series_er_s1(self, app_context):
        """ER_S1 — two-letter title, shortest possible."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="ER_S1",
                             video_type_auto="series")
        result = update_job(job, {'Search': [
            {'Title': 'ER', 'Year': '1994–2009',
             'imdbID': 'tt0108757', 'Type': 'series', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt0108757'

    # -- TV Series: SEASON keyword variants --

    def test_series_office_season_keyword(self, app_context):
        """THE_OFFICE_SEASON_1 — SEASON keyword with separator."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="THE_OFFICE_SEASON_1",
                             year_auto="2005", video_type_auto="series")
        result = update_job(job, {'Search': [
            {'Title': 'The Office', 'Year': '2005–2013',
             'imdbID': 'tt0386676', 'Type': 'series', 'Poster': 'N/A'},
            {'Title': 'The Office', 'Year': '2001–2003',
             'imdbID': 'tt0290978', 'Type': 'series', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt0386676'

    def test_series_sopranos_season1_no_separator(self, app_context):
        """SOPRANOS_SEASON1 — SEASON keyword with no separator before number."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="SOPRANOS_SEASON1",
                             video_type_auto="series")
        result = update_job(job, {'Search': [
            {'Title': 'The Sopranos', 'Year': '1999–2007',
             'imdbID': 'tt0141842', 'Type': 'series', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt0141842'

    # -- TV Series: zero-padded season/disc --

    def test_series_walking_dead_s01(self, app_context):
        """THE_WALKING_DEAD_S01 — zero-padded season."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="THE_WALKING_DEAD_S01",
                             video_type_auto="series")
        result = update_job(job, {'Search': [
            {'Title': 'The Walking Dead', 'Year': '2010–2022',
             'imdbID': 'tt1520211', 'Type': 'series', 'Poster': 'N/A'},
            {'Title': 'Fear the Walking Dead', 'Year': '2015–2023',
             'imdbID': 'tt3743822', 'Type': 'series', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt1520211'

    def test_series_friends_s03d02(self, app_context):
        """FRIENDS_S03D02 — zero-padded combined season+disc."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="FRIENDS_S03D02",
                             video_type_auto="series")
        result = update_job(job, {'Search': [
            {'Title': 'Friends', 'Year': '1994–2004',
             'imdbID': 'tt0108778', 'Type': 'series', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt0108778'

    # -- TV Series: numeric titles --

    def test_series_24_s1_d1(self, app_context):
        """24_S1_D1 — single-number title is a series."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="24_S1_D1",
                             video_type_auto="series")
        result = update_job(job, {'Search': [
            {'Title': '24', 'Year': '2001–2014',
             'imdbID': 'tt0285331', 'Type': 'series', 'Poster': 'N/A'},
            {'Title': '24: Legacy', 'Year': '2017',
             'imdbID': 'tt4939064', 'Type': 'series', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt0285331'

    def test_series_1883_s1(self, app_context):
        """1883_S1 — numeric title (Yellowstone prequel)."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="1883_S1",
                             video_type_auto="series")
        result = update_job(job, {'Search': [
            {'Title': '1883', 'Year': '2021–2022',
             'imdbID': 'tt13991232', 'Type': 'series', 'Poster': 'N/A'},
            {'Title': '1923', 'Year': '2022–',
             'imdbID': 'tt15299712', 'Type': 'series', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt13991232'

    # -- TV Series: disambiguation --

    def test_series_fargo_s1_over_movie(self, app_context):
        """FARGO_S1 with series type hint picks the series, not the movie."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="FARGO_S1",
                             video_type_auto="series")
        result = update_job(job, {'Search': [
            {'Title': 'Fargo', 'Year': '2014–', 'imdbID': 'tt2802850',
             'Type': 'series', 'Poster': 'N/A'},
            {'Title': 'Fargo', 'Year': '1996', 'imdbID': 'tt0116282',
             'Type': 'movie', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt2802850'

    def test_series_dexter_not_lab(self, app_context):
        """DEXTER_S1 matches Dexter, not Dexter's Laboratory."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="DEXTER_S1",
                             video_type_auto="series")
        result = update_job(job, {'Search': [
            {'Title': 'Dexter', 'Year': '2006–2013',
             'imdbID': 'tt0773262', 'Type': 'series', 'Poster': 'N/A'},
            {"Title": "Dexter's Laboratory", 'Year': '1996–2003',
             'imdbID': 'tt0115157', 'Type': 'series', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt0773262'

    def test_series_walking_dead_not_fear(self, app_context):
        """THE_WALKING_DEAD_S1 picks main show over Fear the Walking Dead."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="THE_WALKING_DEAD_S1",
                             video_type_auto="series")
        result = update_job(job, {'Search': [
            {'Title': 'Fear the Walking Dead', 'Year': '2015–2023',
             'imdbID': 'tt3743822', 'Type': 'series', 'Poster': 'N/A'},
            {'Title': 'The Walking Dead', 'Year': '2010–2022',
             'imdbID': 'tt1520211', 'Type': 'series', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt1520211'

    # -- TV Series: S-ending titles not misinterpreted --

    def test_series_alias_no_season_suffix(self, app_context):
        """ALIAS — trailing S is NOT a season indicator."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="ALIAS",
                             video_type_auto="series")
        result = update_job(job, {'Search': [
            {'Title': 'Alias', 'Year': '2001–2006',
             'imdbID': 'tt0285333', 'Type': 'series', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt0285333'

    def test_series_ncis_no_season_suffix(self, app_context):
        """NCIS — acronym ending in S, not a season indicator."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="NCIS",
                             video_type_auto="series")
        result = update_job(job, {'Search': [
            {'Title': 'NCIS', 'Year': '2003–',
             'imdbID': 'tt0364845', 'Type': 'series', 'Poster': 'N/A'},
            {'Title': 'NCIS: Los Angeles', 'Year': '2009–2023',
             'imdbID': 'tt1378167', 'Type': 'series', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt0364845'

    def test_series_ncis_with_season(self, app_context):
        """NCIS_S1 — S1 IS a season suffix, NCIS title preserved."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="NCIS_S1",
                             video_type_auto="series")
        result = update_job(job, {'Search': [
            {'Title': 'NCIS', 'Year': '2003–',
             'imdbID': 'tt0364845', 'Type': 'series', 'Poster': 'N/A'},
            {'Title': 'NCIS: Los Angeles', 'Year': '2009–2023',
             'imdbID': 'tt1378167', 'Type': 'series', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt0364845'

    # -- TV Series: mini series (disc only, no season) --

    def test_series_chernobyl_d1(self, app_context):
        """CHERNOBYL_D1 — limited series, disc only."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="CHERNOBYL_D1",
                             video_type_auto="series")
        result = update_job(job, {'Search': [
            {'Title': 'Chernobyl', 'Year': '2019',
             'imdbID': 'tt7366338', 'Type': 'series', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt7366338'

    def test_series_band_of_brothers_d1(self, app_context):
        """BAND_OF_BROTHERS_D1 — mini series, disc only."""
        from arm.ripper.identify import update_job

        job = self._make_job(app_context, label="BAND_OF_BROTHERS_D1",
                             video_type_auto="series")
        result = update_job(job, {'Search': [
            {'Title': 'Band of Brothers', 'Year': '2001',
             'imdbID': 'tt0185906', 'Type': 'series', 'Poster': 'N/A'},
        ]})
        assert result is True
        assert job.imdb_id == 'tt0185906'

    # -- metadata_selector retry behavior --

    def test_metadata_selector_returns_none_on_reject(self, app_context):
        """metadata_selector returns None when matcher rejects — enables retry."""
        from arm.ripper.identify import metadata_selector
        import arm.config.config as cfg

        job = self._make_job(app_context, label="SERIAL_MOM",
                             year_auto="1994", video_type_auto="movie")

        bad_results = {'Search': [
            {'Title': 'Completely Wrong Movie', 'Year': '2020',
             'imdbID': 'tt9999999', 'Type': 'movie', 'Poster': 'N/A'},
        ], 'Response': 'True'}

        original = cfg.arm_config.get('METADATA_PROVIDER')
        cfg.arm_config['METADATA_PROVIDER'] = 'omdb'
        try:
            with unittest.mock.patch('arm.ripper.identify.ui_utils.call_omdb_api',
                                     return_value=bad_results):
                result = metadata_selector(job, 'Serial+Mom', '1994')
            assert result is None
        finally:
            if original is not None:
                cfg.arm_config['METADATA_PROVIDER'] = original


class TestOmdbShortTitleFallback:
    """Test call_omdb_api() fallback to ?t= for short/numeric titles (#1430)."""

    def _mock_urlopen(self, responses):
        """Create a mock urlopen that returns different responses per call."""
        call_count = [0]

        def side_effect(url, **kwargs):
            idx = min(call_count[0], len(responses) - 1)
            call_count[0] += 1
            mock_resp = unittest.mock.MagicMock()
            mock_resp.read.return_value = json.dumps(responses[idx]).encode()
            return mock_resp

        return side_effect

    @unittest.mock.patch.dict('arm.config.config.arm_config', {'OMDB_API_KEY': 'test_key'})
    def test_search_failure_falls_back_to_exact_title(self):
        """When ?s= returns 'Too many results', ?t= is tried."""
        from arm.ui.metadata import call_omdb_api

        search_error = {"Response": "False", "Error": "Too many results."}
        exact_match = {
            "Response": "True",
            "Title": "9",
            "Year": "2009",
            "Type": "movie",
            "imdbID": "tt0472033",
            "Poster": "https://example.com/9.jpg",
        }
        mock_open = self._mock_urlopen([search_error, exact_match])
        with unittest.mock.patch('arm.ui.metadata.urllib.request.urlopen', side_effect=mock_open):
            result = call_omdb_api(title="9", year="2009")

        assert result is not None
        assert result['Search'][0]['Title'] == '9'
        assert result['Search'][0]['imdbID'] == 'tt0472033'

    @unittest.mock.patch.dict('arm.config.config.arm_config', {'OMDB_API_KEY': 'test_key'})
    def test_both_search_and_exact_fail_returns_none(self):
        """When both ?s= and ?t= fail, returns None."""
        from arm.ui.metadata import call_omdb_api

        error_resp = {"Response": "False", "Error": "Movie not found!"}
        mock_open = self._mock_urlopen([error_resp, error_resp])
        with unittest.mock.patch('arm.ui.metadata.urllib.request.urlopen', side_effect=mock_open):
            result = call_omdb_api(title="xyznonexistent", year="2020")

        assert result is None

    @unittest.mock.patch.dict('arm.config.config.arm_config', {'OMDB_API_KEY': 'test_key'})
    def test_search_succeeds_no_fallback_needed(self):
        """When ?s= succeeds, no fallback is triggered."""
        from arm.ui.metadata import call_omdb_api

        search_success = {
            "Response": "True",
            "Search": [{"Title": "The Matrix", "Year": "1999", "imdbID": "tt0133093",
                        "Type": "movie", "Poster": "https://example.com/matrix.jpg"}]
        }
        mock_open = self._mock_urlopen([search_success])
        with unittest.mock.patch('arm.ui.metadata.urllib.request.urlopen', side_effect=mock_open):
            result = call_omdb_api(title="The Matrix", year="1999")

        assert result is not None
        assert result['Search'][0]['Title'] == 'The Matrix'

    @unittest.mock.patch.dict('arm.config.config.arm_config', {'OMDB_API_KEY': 'test_key'})
    def test_fallback_network_error_returns_none(self):
        """When ?s= fails and ?t= raises a network error, returns None gracefully (#1430)."""
        from arm.ui.metadata import call_omdb_api

        call_count = [0]

        def mock_urlopen(url, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call (?s=) returns error response
                mock_resp = unittest.mock.MagicMock()
                mock_resp.read.return_value = json.dumps(
                    {"Response": "False", "Error": "Too many results."}
                ).encode()
                return mock_resp
            # Second call (?t=) raises network error
            raise urllib.error.URLError("DNS lookup failed")

        import urllib.error
        with unittest.mock.patch('arm.ui.metadata.urllib.request.urlopen',
                                 side_effect=mock_urlopen):
            result = call_omdb_api(title="9", year="2009")

        assert result is None


class TestResolveDiscLabel:
    """Test resolve_disc_label() multi-source label recovery."""

    def test_already_set_from_pyudev(self):
        """If label is already set, returns immediately without probing."""
        from arm.ripper.identify import resolve_disc_label

        job = unittest.mock.MagicMock()
        job.label = "EXISTING_LABEL"
        job.devpath = "/dev/sr0"

        with unittest.mock.patch('arm.ripper.identify._label_from_blkid') as mock_blkid:
            resolve_disc_label(job)
            mock_blkid.assert_not_called()
        assert job.label == "EXISTING_LABEL"

    def test_blkid_recovery(self):
        """Falls back to blkid when pyudev label is missing."""
        from arm.ripper.identify import resolve_disc_label

        job = unittest.mock.MagicMock()
        job.label = ""
        job.devpath = "/dev/sr0"

        with unittest.mock.patch('arm.ripper.identify._label_from_blkid',
                                 return_value="BLKID_LABEL"):
            resolve_disc_label(job)
        assert job.label == "BLKID_LABEL"

    def test_lsdvd_recovery_for_dvd(self):
        """Falls back to lsdvd for DVD when blkid fails."""
        from arm.ripper.identify import resolve_disc_label

        job = unittest.mock.MagicMock()
        job.label = ""
        job.devpath = "/dev/sr0"
        job.disctype = "dvd"

        with unittest.mock.patch('arm.ripper.identify._label_from_blkid',
                                 return_value=None), \
             unittest.mock.patch('arm.ripper.identify._label_from_lsdvd',
                                 return_value="LSDVD_LABEL"):
            resolve_disc_label(job)
        assert job.label == "LSDVD_LABEL"

    def test_bluray_xml_recovery(self):
        """Falls back to bdmt_eng.xml for Blu-ray when blkid fails."""
        from arm.ripper.identify import resolve_disc_label

        job = unittest.mock.MagicMock()
        job.label = ""
        job.devpath = "/dev/sr0"
        job.disctype = "bluray"
        job.mountpoint = "/mnt/disc"

        with unittest.mock.patch('arm.ripper.identify._label_from_blkid',
                                 return_value=None), \
             unittest.mock.patch('arm.ripper.identify._label_from_bluray_xml',
                                 return_value="XML_TITLE"):
            resolve_disc_label(job)
        assert job.label == "XML_TITLE"

    def test_all_sources_fail(self):
        """When all sources fail, label remains empty."""
        from arm.ripper.identify import resolve_disc_label

        job = unittest.mock.MagicMock()
        job.label = ""
        job.devpath = "/dev/sr0"
        job.disctype = "dvd"

        with unittest.mock.patch('arm.ripper.identify._label_from_blkid',
                                 return_value=None), \
             unittest.mock.patch('arm.ripper.identify._label_from_lsdvd',
                                 return_value=None):
            resolve_disc_label(job)
        assert job.label == ""

    def test_none_label_treated_as_missing(self):
        """None label triggers fallback chain."""
        from arm.ripper.identify import resolve_disc_label

        job = unittest.mock.MagicMock()
        job.label = None
        job.devpath = "/dev/sr0"

        with unittest.mock.patch('arm.ripper.identify._label_from_blkid',
                                 return_value="RECOVERED"):
            resolve_disc_label(job)
        assert job.label == "RECOVERED"

    def test_lsdvd_skipped_for_bluray(self):
        """lsdvd is not tried for Blu-ray discs."""
        from arm.ripper.identify import resolve_disc_label

        job = unittest.mock.MagicMock()
        job.label = ""
        job.devpath = "/dev/sr0"
        job.disctype = "bluray"
        job.mountpoint = "/mnt/disc"

        with unittest.mock.patch('arm.ripper.identify._label_from_blkid',
                                 return_value=None), \
             unittest.mock.patch('arm.ripper.identify._label_from_lsdvd') as mock_lsdvd, \
             unittest.mock.patch('arm.ripper.identify._label_from_bluray_xml',
                                 return_value=None):
            resolve_disc_label(job)
            mock_lsdvd.assert_not_called()


class TestLabelHelpers:
    """Test individual label recovery helpers."""

    def test_blkid_returns_label(self):
        """blkid parses filesystem label."""
        from arm.ripper.identify import _label_from_blkid

        with unittest.mock.patch('arm.ripper.identify.arm_subprocess',
                                 return_value="THE_BABYSITTER\n"):
            assert _label_from_blkid("/dev/sr0") == "THE_BABYSITTER"

    def test_blkid_returns_none_on_empty(self):
        """blkid returns None for empty output."""
        from arm.ripper.identify import _label_from_blkid

        with unittest.mock.patch('arm.ripper.identify.arm_subprocess',
                                 return_value=""):
            assert _label_from_blkid("/dev/sr0") is None

    def test_blkid_returns_none_on_failure(self):
        """blkid returns None when subprocess fails."""
        from arm.ripper.identify import _label_from_blkid

        with unittest.mock.patch('arm.ripper.identify.arm_subprocess',
                                 return_value=None):
            assert _label_from_blkid("/dev/sr0") is None

    def test_lsdvd_parses_disc_title(self):
        """lsdvd extracts Disc Title from output."""
        from arm.ripper.identify import _label_from_lsdvd

        lsdvd_output = "Disc Title: THE_BABYSITTER\nTitle: 01, Length: 01:30:00\n"
        with unittest.mock.patch('arm.ripper.identify.arm_subprocess',
                                 return_value=lsdvd_output):
            assert _label_from_lsdvd("/dev/sr0") == "THE_BABYSITTER"

    def test_lsdvd_returns_none_on_no_title(self):
        """lsdvd returns None when no Disc Title line present."""
        from arm.ripper.identify import _label_from_lsdvd

        with unittest.mock.patch('arm.ripper.identify.arm_subprocess',
                                 return_value="Title: 01, Length: 01:30:00\n"):
            assert _label_from_lsdvd("/dev/sr0") is None

    def test_lsdvd_returns_none_on_failure(self):
        """lsdvd returns None when subprocess fails."""
        from arm.ripper.identify import _label_from_lsdvd

        with unittest.mock.patch('arm.ripper.identify.arm_subprocess',
                                 return_value=None):
            assert _label_from_lsdvd("/dev/sr0") is None

    def test_bluray_xml_reads_title(self, tmp_path):
        """Extracts title from well-formed bdmt_eng.xml."""
        from arm.ripper.identify import _label_from_bluray_xml

        xml_dir = tmp_path / 'BDMV' / 'META' / 'DL'
        xml_dir.mkdir(parents=True)
        (xml_dir / 'bdmt_eng.xml').write_text(
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<disclib xmlns:di="urn:BDA:bdmv;discinfo">'
            '<di:discinfo><di:title><di:name>Serial Mom</di:name></di:title></di:discinfo>'
            '</disclib>'
        )
        assert _label_from_bluray_xml(str(tmp_path)) == "Serial Mom"

    def test_bluray_xml_returns_none_on_missing(self, tmp_path):
        """Returns None when bdmt_eng.xml doesn't exist."""
        from arm.ripper.identify import _label_from_bluray_xml

        assert _label_from_bluray_xml(str(tmp_path)) is None

    def test_bluray_xml_returns_none_on_malformed(self, tmp_path):
        """Returns None when bdmt_eng.xml is malformed."""
        from arm.ripper.identify import _label_from_bluray_xml

        xml_dir = tmp_path / 'BDMV' / 'META' / 'DL'
        xml_dir.mkdir(parents=True)
        (xml_dir / 'bdmt_eng.xml').write_text('<<<not valid xml>>>')
        assert _label_from_bluray_xml(str(tmp_path)) is None


class TestSearchMetadata:
    """Test _search_metadata() metadata API search wrapper."""

    def test_uses_title_when_available(self):
        """Searches with job.title when set."""
        from arm.ripper.identify import _search_metadata

        job = unittest.mock.MagicMock()
        job.title = "Serial Mom"
        job.label = "SERIAL_MOM"
        job.year = "1994"
        job.hasnicetitle = False

        with unittest.mock.patch('arm.ripper.identify.metadata_selector',
                                 return_value=None) as mock_ms, \
             unittest.mock.patch('arm.ripper.identify.identify_loop'):
            _search_metadata(job)
            mock_ms.assert_called_once()
            args = mock_ms.call_args[0]
            assert "Serial+Mom" in args[1]

    def test_falls_back_to_label(self):
        """Uses job.label when job.title is None."""
        from arm.ripper.identify import _search_metadata

        job = unittest.mock.MagicMock()
        job.title = None
        job.label = "THE_BABYSITTER"
        job.year = None

        with unittest.mock.patch('arm.ripper.identify.metadata_selector',
                                 return_value=None) as mock_ms, \
             unittest.mock.patch('arm.ripper.identify.identify_loop'):
            _search_metadata(job)
            mock_ms.assert_called_once()
            args = mock_ms.call_args[0]
            assert "THE+BABYSITTER" in args[1]

    def test_skips_when_no_title_or_label(self):
        """Does nothing when both title and label are empty."""
        from arm.ripper.identify import _search_metadata

        job = unittest.mock.MagicMock()
        job.title = None
        job.label = None

        with unittest.mock.patch('arm.ripper.identify.metadata_selector') as mock_ms:
            _search_metadata(job)
            mock_ms.assert_not_called()

    def test_strips_16x9_and_sku(self):
        """Strips 16x9 and SKU markers from search query."""
        from arm.ripper.identify import _search_metadata

        job = unittest.mock.MagicMock()
        job.title = None
        job.label = "ALIEN_16x9"
        job.year = None

        with unittest.mock.patch('arm.ripper.identify.metadata_selector',
                                 return_value=None) as mock_ms, \
             unittest.mock.patch('arm.ripper.identify.identify_loop'):
            _search_metadata(job)
            args = mock_ms.call_args[0]
            assert "16x9" not in args[1]

    def test_title_string_none_falls_back_to_label(self):
        """String 'None' in title treated as missing, falls back to label."""
        from arm.ripper.identify import _search_metadata

        job = unittest.mock.MagicMock()
        job.title = "None"
        job.label = "SERIAL_MOM"
        job.year = None

        with unittest.mock.patch('arm.ripper.identify.metadata_selector',
                                 return_value=None) as mock_ms, \
             unittest.mock.patch('arm.ripper.identify.identify_loop'):
            _search_metadata(job)
            args = mock_ms.call_args[0]
            assert "SERIAL+MOM" in args[1]


class TestApplyLabelAsTitle:
    """Test _apply_label_as_title() last-resort title assignment."""

    def test_cleans_label_as_title(self, app_context):
        """Cleans underscored label into title-cased title."""
        from arm.ripper.identify import _apply_label_as_title
        from arm.models.job import Job

        with unittest.mock.patch.object(Job, 'parse_udev'), \
             unittest.mock.patch.object(Job, 'get_pid'):
            job = Job('/dev/sr0')
        job.label = "THE_BABYSITTER"
        job.title = None
        job.title_auto = None
        job.hasnicetitle = True  # should be reset to False

        _apply_label_as_title(job)
        assert job.title == "The Babysitter"
        assert job.title_auto == "The Babysitter"
        assert job.hasnicetitle is False

    def test_empty_label(self, app_context):
        """Empty label sets empty title and year."""
        from arm.ripper.identify import _apply_label_as_title
        from arm.models.job import Job

        with unittest.mock.patch.object(Job, 'parse_udev'), \
             unittest.mock.patch.object(Job, 'get_pid'):
            job = Job('/dev/sr0')
        job.label = ""
        job.title = None
        job.year = None

        _apply_label_as_title(job)
        assert job.title == ""
        assert job.year == ""
        assert job.hasnicetitle is False

    def test_none_label(self, app_context):
        """None label sets empty title and year."""
        from arm.ripper.identify import _apply_label_as_title
        from arm.models.job import Job

        with unittest.mock.patch.object(Job, 'parse_udev'), \
             unittest.mock.patch.object(Job, 'get_pid'):
            job = Job('/dev/sr0')
        job.label = None
        job.title = None
        job.year = None

        _apply_label_as_title(job)
        assert job.title == ""
        assert job.year == ""
        assert job.hasnicetitle is False


class TestDetectTrack99:
    """Test _detect_track_99() DVD track 99 detection."""

    @staticmethod
    def _lsdvd_output(num_tracks):
        """Create lsdvd -Oy style multiline output for testing."""
        tracks = [{'ix': i + 1} for i in range(num_tracks)]
        return "lsdvd = {\n'track': " + repr(tracks) + "\n}"

    def test_detects_99_tracks(self):
        """Sets has_track_99 when exactly 99 tracks detected."""
        from arm.ripper.identify import _detect_track_99

        job = unittest.mock.MagicMock()
        job.devpath = "/dev/sr0"
        job.has_track_99 = False

        with unittest.mock.patch('arm.ripper.identify.arm_subprocess',
                                 return_value=self._lsdvd_output(99)), \
             unittest.mock.patch('arm.ripper.identify.cfg') as mock_cfg:
            mock_cfg.arm_config = {"PREVENT_99": False}
            _detect_track_99(job)
        assert job.has_track_99 is True

    def test_normal_track_count(self):
        """Does not flag normal track counts."""
        from arm.ripper.identify import _detect_track_99

        job = unittest.mock.MagicMock()
        job.devpath = "/dev/sr0"
        job.has_track_99 = False

        with unittest.mock.patch('arm.ripper.identify.arm_subprocess',
                                 return_value=self._lsdvd_output(15)):
            _detect_track_99(job)
        # has_track_99 should not have been set to True
        assert job.has_track_99 is False

    def test_prevent_99_raises(self):
        """Raises RipperException when PREVENT_99 is enabled."""
        from arm.ripper.identify import _detect_track_99
        from arm.ripper.utils import RipperException

        job = unittest.mock.MagicMock()
        job.devpath = "/dev/sr0"
        job.has_track_99 = False

        with unittest.mock.patch('arm.ripper.identify.arm_subprocess',
                                 return_value=self._lsdvd_output(99)), \
             unittest.mock.patch('arm.ripper.identify.cfg') as mock_cfg:
            mock_cfg.arm_config = {"PREVENT_99": True}
            with pytest.raises(RipperException):
                _detect_track_99(job)

    def test_no_output(self):
        """Handles missing lsdvd output gracefully."""
        from arm.ripper.identify import _detect_track_99

        job = unittest.mock.MagicMock()
        job.devpath = "/dev/sr0"

        with unittest.mock.patch('arm.ripper.identify.arm_subprocess',
                                 return_value=None):
            _detect_track_99(job)  # should not raise
