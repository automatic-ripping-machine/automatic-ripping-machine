"""Additional tests for arm/ripper/identify.py — covering missing lines.

Covers: _find_mountpoint(), _drive_status(), _drive_has_disc(),
_wait_for_drive_ready(), resolve_disc_label(), _search_metadata(),
_apply_label_as_title(), _identify_video_title(), identify() branching,
_detect_track_99(), identify_bluray() key error path.
"""
import json
import subprocess
import unittest.mock

import pytest


class TestFindMountpoint:
    """Test _find_mountpoint() direct subprocess call (lines 39-47)."""

    def test_returns_mountpoint_on_success(self, tmp_path):
        from arm.ripper.identify import _find_mountpoint

        mount_target = str(tmp_path)
        findmnt_json = json.dumps({
            "filesystems": [{"target": mount_target}]
        })
        mock_result = unittest.mock.MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = findmnt_json

        with unittest.mock.patch('subprocess.run', return_value=mock_result):
            result = _find_mountpoint('/dev/sr0')
        assert result == mount_target

    def test_returns_none_on_failure(self):
        from arm.ripper.identify import _find_mountpoint

        mock_result = unittest.mock.MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with unittest.mock.patch('subprocess.run', return_value=mock_result):
            result = _find_mountpoint('/dev/sr0')
        assert result is None

    def test_returns_none_when_not_readable(self, tmp_path):
        from arm.ripper.identify import _find_mountpoint

        findmnt_json = json.dumps({
            "filesystems": [{"target": "/nonexistent/path"}]
        })
        mock_result = unittest.mock.MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = findmnt_json

        with unittest.mock.patch('subprocess.run', return_value=mock_result):
            result = _find_mountpoint('/dev/sr0')
        assert result is None


class TestDriveStatus:
    """Test _drive_status() ioctl wrapper (lines 57-64)."""

    def test_returns_disc_ok(self):
        from arm.ripper.identify import _drive_status

        with unittest.mock.patch('os.open', return_value=3), \
             unittest.mock.patch('fcntl.ioctl', return_value=4), \
             unittest.mock.patch('os.close'):
            result = _drive_status('/dev/sr0')
        assert result == 4

    def test_returns_minus_one_on_error(self):
        from arm.ripper.identify import _drive_status

        with unittest.mock.patch('os.open', side_effect=OSError("no device")):
            result = _drive_status('/dev/sr0')
        assert result == -1

    def test_close_called_on_success(self):
        from arm.ripper.identify import _drive_status

        with unittest.mock.patch('os.open', return_value=5), \
             unittest.mock.patch('fcntl.ioctl', return_value=4), \
             unittest.mock.patch('os.close') as mock_close:
            _drive_status('/dev/sr0')
        mock_close.assert_called_once_with(5)


class TestDriveHasDisc:
    """Test _drive_has_disc() convenience function (line 74)."""

    def test_disc_ok(self):
        from arm.ripper.identify import _drive_has_disc
        with unittest.mock.patch('arm.ripper.identify._drive_status', return_value=4):
            assert _drive_has_disc('/dev/sr0') is True

    def test_no_disc(self):
        from arm.ripper.identify import _drive_has_disc
        with unittest.mock.patch('arm.ripper.identify._drive_status', return_value=1):
            assert _drive_has_disc('/dev/sr0') is False

    def test_tray_open(self):
        from arm.ripper.identify import _drive_has_disc
        with unittest.mock.patch('arm.ripper.identify._drive_status', return_value=2):
            assert _drive_has_disc('/dev/sr0') is False

    def test_error(self):
        from arm.ripper.identify import _drive_has_disc
        with unittest.mock.patch('arm.ripper.identify._drive_status', return_value=-1):
            assert _drive_has_disc('/dev/sr0') is False

    def test_not_ready_treated_as_has_disc(self):
        from arm.ripper.identify import _drive_has_disc
        # NOT_READY (3) is not in the definitive ejection list
        with unittest.mock.patch('arm.ripper.identify._drive_status', return_value=3):
            assert _drive_has_disc('/dev/sr0') is True


class TestWaitForDriveReady:
    """Test _wait_for_drive_ready() polling logic (lines 104-133)."""

    def test_immediately_ready(self):
        from arm.ripper.identify import _wait_for_drive_ready

        with unittest.mock.patch('arm.ripper.identify._drive_status', return_value=4):
            result = _wait_for_drive_ready('/dev/sr0', timeout=10)
        assert result is True

    def test_becomes_ready_after_polling(self):
        from arm.ripper.identify import _wait_for_drive_ready

        # NOT_READY -> NOT_READY -> DISC_OK
        with unittest.mock.patch('arm.ripper.identify._drive_status',
                                 side_effect=[3, 3, 4]), \
             unittest.mock.patch('time.sleep'):
            result = _wait_for_drive_ready('/dev/sr0', timeout=30)
        assert result is True

    def test_disc_ejected_returns_false(self):
        from arm.ripper.identify import _wait_for_drive_ready

        with unittest.mock.patch('arm.ripper.identify._drive_status', return_value=1), \
             unittest.mock.patch('time.sleep'):
            result = _wait_for_drive_ready('/dev/sr0', timeout=10)
        assert result is False

    def test_tray_open_returns_false(self):
        from arm.ripper.identify import _wait_for_drive_ready

        with unittest.mock.patch('arm.ripper.identify._drive_status', return_value=2), \
             unittest.mock.patch('time.sleep'):
            result = _wait_for_drive_ready('/dev/sr0', timeout=10)
        assert result is False

    def test_timeout_returns_false(self):
        from arm.ripper.identify import _wait_for_drive_ready

        with unittest.mock.patch('arm.ripper.identify._drive_status', return_value=3), \
             unittest.mock.patch('time.sleep'):
            result = _wait_for_drive_ready('/dev/sr0', timeout=3)
        assert result is False


class TestResolveDiscLabel:
    """Test resolve_disc_label() label resolution from multiple sources."""

    def test_already_has_label(self):
        from arm.ripper.identify import resolve_disc_label

        job = unittest.mock.MagicMock()
        job.label = "EXISTING_LABEL"
        resolve_disc_label(job)
        # Should not change anything

    def test_fallback_to_blkid(self):
        from arm.ripper.identify import resolve_disc_label

        job = unittest.mock.MagicMock()
        job.label = None
        job.devpath = '/dev/sr0'

        with unittest.mock.patch('arm.ripper.identify._label_from_blkid',
                                 return_value="BLKID_LABEL"):
            resolve_disc_label(job)
        assert job.label == "BLKID_LABEL"

    def test_fallback_to_lsdvd_for_dvd(self):
        from arm.ripper.identify import resolve_disc_label

        job = unittest.mock.MagicMock()
        job.label = None
        job.devpath = '/dev/sr0'
        job.disctype = 'dvd'

        with unittest.mock.patch('arm.ripper.identify._label_from_blkid', return_value=None), \
             unittest.mock.patch('arm.ripper.identify._label_from_lsdvd',
                                 return_value="LSDVD_TITLE"):
            resolve_disc_label(job)
        assert job.label == "LSDVD_TITLE"

    def test_fallback_to_xml_for_bluray(self):
        from arm.ripper.identify import resolve_disc_label

        job = unittest.mock.MagicMock()
        job.label = None
        job.devpath = '/dev/sr0'
        job.disctype = 'bluray'
        job.mountpoint = '/mnt/sr0'

        with unittest.mock.patch('arm.ripper.identify._label_from_blkid', return_value=None), \
             unittest.mock.patch('arm.ripper.identify._label_from_bluray_xml',
                                 return_value="XML_TITLE"):
            resolve_disc_label(job)
        assert job.label == "XML_TITLE"

    def test_no_source_found(self):
        from arm.ripper.identify import resolve_disc_label

        job = unittest.mock.MagicMock()
        job.label = None
        job.devpath = '/dev/sr0'
        job.disctype = 'data'

        with unittest.mock.patch('arm.ripper.identify._label_from_blkid', return_value=None):
            resolve_disc_label(job)
        assert job.label is None


class TestApplyLabelAsTitle:
    """Test _apply_label_as_title() last-resort title setting."""

    def test_with_label(self, app_context):
        from arm.ripper.identify import _apply_label_as_title

        job = unittest.mock.MagicMock()
        job.label = "SOME_DISC_TITLE"
        _apply_label_as_title(job)
        assert job.title == "Some Disc Title"
        assert job.hasnicetitle is False

    def test_without_label(self, app_context):
        from arm.ripper.identify import _apply_label_as_title

        job = unittest.mock.MagicMock()
        job.label = None
        _apply_label_as_title(job)
        assert job.title == ""
        assert job.year == ""
        assert job.hasnicetitle is False


class TestSearchMetadata:
    """Test _search_metadata() metadata lookup orchestration."""

    def test_no_title_or_label(self):
        from arm.ripper.identify import _search_metadata

        job = unittest.mock.MagicMock()
        job.title = None
        job.label = None

        with unittest.mock.patch('arm.ripper.identify.metadata_selector') as mock_sel:
            _search_metadata(job)
        mock_sel.assert_not_called()

    def test_title_none_uses_label(self):
        from arm.ripper.identify import _search_metadata

        job = unittest.mock.MagicMock()
        job.title = "None"
        job.label = "DISC_LABEL"
        job.year = "2020"

        with unittest.mock.patch('arm.ripper.identify.metadata_selector') as mock_sel, \
             unittest.mock.patch('arm.ripper.identify.identify_loop'):
            mock_sel.return_value = None
            _search_metadata(job)
        # Should have been called with cleaned label
        assert mock_sel.called

    def test_strips_16x9_and_sku(self):
        from arm.ripper.identify import _search_metadata

        job = unittest.mock.MagicMock()
        job.title = "Movie 16x9 SKU Edition"
        job.label = None
        job.year = ""

        with unittest.mock.patch('arm.ripper.identify.metadata_selector') as mock_sel, \
             unittest.mock.patch('arm.ripper.identify.identify_loop'):
            mock_sel.return_value = None
            _search_metadata(job)
        call_title = mock_sel.call_args[0][1]
        assert "16x9" not in call_title
        assert "SKU" not in call_title

    def test_exception_caught(self):
        from arm.ripper.identify import _search_metadata

        job = unittest.mock.MagicMock()
        job.title = "Test"
        job.label = None
        job.year = ""

        with unittest.mock.patch('arm.ripper.identify.metadata_selector',
                                 side_effect=RuntimeError("API failure")):
            # Should not raise
            _search_metadata(job)


class TestDetectTrack99:
    """Test _detect_track_99() lsdvd track counting (lines 497)."""

    def _build_lsdvd_output(self, num_tracks):
        """Build lsdvd -Oy style output with the given number of tracks.

        The output format is a Python dict literal preceded by 'lsdvd = '.
        The regex ``^.*\\{`` in _detect_track_99 is greedy and replaces
        everything up to the LAST '{' on the line, so track values must
        be simple (no nested dicts). Use integers like real lsdvd output.
        """
        track_list = list(range(num_tracks))
        return f"lsdvd = {{'track': {track_list}}}"

    def test_99_tracks_sets_flag(self):
        from arm.ripper.identify import _detect_track_99
        import arm.config.config as cfg

        job = unittest.mock.MagicMock()
        job.devpath = '/dev/sr0'
        job.has_track_99 = False

        lsdvd_output = self._build_lsdvd_output(99)

        old = cfg.arm_config.get('PREVENT_99')
        cfg.arm_config['PREVENT_99'] = False
        try:
            with unittest.mock.patch('arm.ripper.identify.arm_subprocess',
                                     return_value=lsdvd_output):
                _detect_track_99(job)
            assert job.has_track_99 is True
        finally:
            if old is not None:
                cfg.arm_config['PREVENT_99'] = old

    def test_99_tracks_prevent_raises(self):
        from arm.ripper.identify import _detect_track_99
        from arm.ripper.utils import RipperException
        import arm.config.config as cfg

        job = unittest.mock.MagicMock()
        job.devpath = '/dev/sr0'
        job.has_track_99 = False

        lsdvd_output = self._build_lsdvd_output(99)

        old = cfg.arm_config.get('PREVENT_99')
        cfg.arm_config['PREVENT_99'] = True
        try:
            with unittest.mock.patch('arm.ripper.identify.arm_subprocess',
                                     return_value=lsdvd_output), \
                 pytest.raises(RipperException, match="Track 99"):
                _detect_track_99(job)
        finally:
            if old is not None:
                cfg.arm_config['PREVENT_99'] = old

    def test_bad_lsdvd_output(self):
        from arm.ripper.identify import _detect_track_99

        job = unittest.mock.MagicMock()
        job.devpath = '/dev/sr0'
        job.has_track_99 = False

        with unittest.mock.patch('arm.ripper.identify.arm_subprocess',
                                 return_value="garbage output {{{}"):
            # Should not raise — catches SyntaxError
            _detect_track_99(job)

    def test_no_output(self):
        from arm.ripper.identify import _detect_track_99

        job = unittest.mock.MagicMock()
        job.devpath = '/dev/sr0'
        job.has_track_99 = False

        with unittest.mock.patch('arm.ripper.identify.arm_subprocess', return_value=None):
            _detect_track_99(job)
        assert job.has_track_99 is False


class TestIdentifyVideoTitle:
    """Test _identify_video_title() orchestration."""

    def test_auto_enables_multi_title_for_series(self, app_context):
        from arm.ripper.identify import _identify_video_title

        job = unittest.mock.MagicMock()
        job.disctype = 'dvd'
        job.video_type = 'series'
        job.multi_title = False
        job.hasnicetitle = True
        job.title = "Test Show"
        job.year = "2020"

        with unittest.mock.patch('arm.ripper.identify.resolve_disc_label'), \
             unittest.mock.patch('arm.ripper.identify.identify_dvd'), \
             unittest.mock.patch('arm.ripper.identify._search_metadata'), \
             unittest.mock.patch('arm.ripper.identify.db'):
            _identify_video_title(job)
        assert job.multi_title is True

    def test_bluray_calls_identify_bluray(self, app_context):
        from arm.ripper.identify import _identify_video_title

        job = unittest.mock.MagicMock()
        job.disctype = 'bluray'
        job.video_type = 'movie'
        job.multi_title = True  # already true, no change
        job.hasnicetitle = True
        job.title = "Test Movie"
        job.year = "2020"

        with unittest.mock.patch('arm.ripper.identify.resolve_disc_label'), \
             unittest.mock.patch('arm.ripper.identify.identify_bluray') as mock_br, \
             unittest.mock.patch('arm.ripper.identify._search_metadata'), \
             unittest.mock.patch('arm.ripper.identify.db'):
            _identify_video_title(job)
        mock_br.assert_called_once_with(job)

    def test_calls_search_metadata_when_no_nice_title(self, app_context):
        from arm.ripper.identify import _identify_video_title

        job = unittest.mock.MagicMock()
        job.disctype = 'dvd'
        job.video_type = 'movie'
        job.multi_title = False
        job.hasnicetitle = False
        job.title = "Test"
        job.year = "2020"

        with unittest.mock.patch('arm.ripper.identify.resolve_disc_label'), \
             unittest.mock.patch('arm.ripper.identify.identify_dvd'), \
             unittest.mock.patch('arm.ripper.identify._search_metadata') as mock_search, \
             unittest.mock.patch('arm.ripper.identify.db'):
            _identify_video_title(job)
        mock_search.assert_called_once_with(job)


class TestIdentifyEntryPoint:
    """Test identify() main entry point branching."""

    def test_music_skips_identification(self):
        from arm.ripper.identify import identify

        job = unittest.mock.MagicMock()
        job.disctype = 'music'

        with unittest.mock.patch('arm.ripper.identify.check_mount') as mock_mount:
            identify(job)
        mock_mount.assert_not_called()

    def test_unmounted_none_disctype_raises(self):
        from arm.ripper.identify import identify
        from arm.ripper.utils import RipperException

        job = unittest.mock.MagicMock()
        job.devpath = '/dev/sr0'
        job.disctype = None

        with unittest.mock.patch('arm.ripper.identify.check_mount', return_value=False), \
             unittest.mock.patch('subprocess.run'), \
             pytest.raises(RipperException, match="Could not mount"):
            identify(job)

    def test_video_disc_identifies_and_unmounts(self):
        from arm.ripper.identify import identify
        import arm.config.config as cfg

        job = unittest.mock.MagicMock()
        job.devpath = '/dev/sr0'
        job.disctype = 'dvd'
        job.mountpoint = '/mnt/sr0'

        old = cfg.arm_config.get('GET_VIDEO_TITLE')
        cfg.arm_config['GET_VIDEO_TITLE'] = True
        try:
            with unittest.mock.patch('arm.ripper.identify.check_mount', return_value=True), \
                 unittest.mock.patch('arm.ripper.identify._identify_video_title') as mock_id, \
                 unittest.mock.patch('subprocess.run') as mock_run:
                identify(job)
            mock_id.assert_called_once_with(job)
            mock_run.assert_called_once()  # umount
        finally:
            if old is not None:
                cfg.arm_config['GET_VIDEO_TITLE'] = old


class TestIdentifyBlurayKeyError:
    """Test identify_bluray() KeyError path (lines 412-415, 418)."""

    def _make_job(self):
        job = unittest.mock.MagicMock()
        job.disctype = 'bluray'
        job.mountpoint = '/mnt/dev/sr0'
        job.label = None
        return job

    def test_missing_di_name_key_falls_back_to_label(self, tmp_path):
        from arm.ripper.identify import identify_bluray

        job = self._make_job()
        job.mountpoint = str(tmp_path)
        job.label = "FALLBACK_LABEL"

        xml_dir = tmp_path / 'BDMV' / 'META' / 'DL'
        xml_dir.mkdir(parents=True)
        xml_file = xml_dir / 'bdmt_eng.xml'
        # Valid XML with di:title having content but no di:name child
        # This triggers KeyError on doc['disclib']['di:discinfo']['di:title']['di:name']
        xml_file.write_text(
            '<?xml version="1.0"?>'
            '<disclib xmlns:di="urn:BDA:bdmv;discinfo">'
            '<di:discinfo><di:title><di:other>stuff</di:other></di:title></di:discinfo>'
            '</disclib>'
        )

        with unittest.mock.patch('arm.ripper.identify.db'):
            result = identify_bluray(job)
        # Falls back to label via KeyError path (line 414)
        assert result is True

    def test_empty_title_and_no_label_returns_false(self, tmp_path):
        from arm.ripper.identify import identify_bluray

        job = self._make_job()
        job.mountpoint = str(tmp_path)
        job.label = None

        xml_dir = tmp_path / 'BDMV' / 'META' / 'DL'
        xml_dir.mkdir(parents=True)
        xml_file = xml_dir / 'bdmt_eng.xml'
        # Valid XML with empty title
        xml_file.write_text(
            '<?xml version="1.0"?>'
            '<disclib xmlns:di="urn:BDA:bdmv;discinfo">'
            '<di:discinfo><di:title><di:name></di:name></di:title></di:discinfo>'
            '</disclib>'
        )

        result = identify_bluray(job)
        assert result is False
