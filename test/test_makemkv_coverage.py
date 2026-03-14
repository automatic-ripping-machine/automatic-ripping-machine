"""Tests to improve coverage for arm/ripper/makemkv.py.

Covers: parse_content, parse_line, dataclass constructors, convert_to_seconds,
MakeMKVOutputChecker, TrackInfoProcessor, setup_rawpath, progress_log,
_strip_track_suffix, _prefix_match_pass, _positional_match_pass,
DriveVisible, DriveType, Drive, OutputType, and error classes.
"""
import dataclasses
import os
import unittest.mock

import pytest


class TestParseContent:
    """Test parse_content() CSV parsing with quoted strings."""

    def test_msg_line(self):
        from arm.ripper.makemkv import parse_content
        msg = '1005,0,1,"MakeMKV v1.17.8 linux(x64-release) started","%1 started","MakeMKV v1.17.8 linux(x64-release)"'
        result = list(parse_content(msg, 3, -1))
        assert result[0] == '1005'
        assert result[1] == '0'
        assert result[2] == '1'
        assert 'MakeMKV v1.17.8' in result[3]

    def test_tcount_line(self):
        from arm.ripper.makemkv import parse_content
        result = list(parse_content('0', 0, 0))
        assert result == ['0']

    def test_drv_line(self):
        from arm.ripper.makemkv import parse_content
        msg = '6,256,999,0,"BD-Drive","THE TITLE","/dev/sr0"'
        result = list(parse_content(msg, 4, 2))
        assert result[0] == '6'
        assert result[-1] == '/dev/sr0'

    def test_cinfo_line(self):
        from arm.ripper.makemkv import parse_content
        msg = '1,6209,"Blu-ray disc"'
        result = list(parse_content(msg, 2, 0))
        assert result == ['1', '6209', 'Blu-ray disc']

    def test_tinfo_with_comma_in_value(self):
        from arm.ripper.makemkv import parse_content
        msg = '1,26,0,"155,156,157"'
        result = list(parse_content(msg, 3, 0))
        assert result[0] == '1'
        assert result[3] == '155,156,157'

    def test_sinfo_line(self):
        from arm.ripper.makemkv import parse_content
        msg = '0,0,28,0,"ger"'
        result = list(parse_content(msg, 4, 0))
        assert result == ['0', '0', '28', '0', 'ger']


class TestParseLine:
    """Test parse_line() full line parsing dispatch."""

    def test_tcount(self):
        from arm.ripper.makemkv import parse_line, OutputType, Titles
        msg_type, data = parse_line("TCOUNT:5")
        assert msg_type == OutputType.TCOUNT
        assert isinstance(data, Titles)
        assert data.count == 5

    def test_cinfo(self):
        from arm.ripper.makemkv import parse_line, OutputType, CInfo
        msg_type, data = parse_line('CINFO:1,6209,"Blu-ray disc"')
        assert msg_type == OutputType.CINFO
        assert isinstance(data, CInfo)
        assert data.id == 1
        assert data.code == 6209

    def test_tinfo(self):
        from arm.ripper.makemkv import parse_line, OutputType, TInfo
        msg_type, data = parse_line('TINFO:0,27,0,"title00.mkv"')
        assert msg_type == OutputType.TINFO
        assert isinstance(data, TInfo)
        assert data.tid == 0

    def test_sinfo(self):
        from arm.ripper.makemkv import parse_line, OutputType, SInfo
        msg_type, data = parse_line('SINFO:0,0,1,6201,"Video"')
        assert msg_type == OutputType.SINFO
        assert isinstance(data, SInfo)
        assert data.tid == 0
        assert data.sid == 0

    def test_prgv(self):
        from arm.ripper.makemkv import parse_line, OutputType, ProgressBarValues
        msg_type, data = parse_line("PRGV:100,200,65536")
        assert msg_type == OutputType.PRGV
        assert isinstance(data, ProgressBarValues)
        assert data.current == 100
        assert data.total == 200
        assert data.maximum == 65536

    def test_prgc(self):
        from arm.ripper.makemkv import parse_line, OutputType, ProgressBarCurrent
        msg_type, data = parse_line('PRGC:5003,0,"Analyzing"')
        assert msg_type == OutputType.PRGC
        assert isinstance(data, ProgressBarCurrent)
        assert data.code == 5003

    def test_prgt(self):
        from arm.ripper.makemkv import parse_line, OutputType, ProgressBarTotal
        msg_type, data = parse_line('PRGT:5004,0,"Total progress"')
        assert msg_type == OutputType.PRGT
        assert isinstance(data, ProgressBarTotal)

    def test_drv(self):
        from arm.ripper.makemkv import parse_line, OutputType, Drive
        msg_type, data = parse_line('DRV:0,2,999,1,"BD-RE PIONEER","DISC","/dev/sr0"')
        assert msg_type == OutputType.DRV
        assert isinstance(data, Drive)
        assert data.mount == '/dev/sr0'

    def test_msg(self):
        from arm.ripper.makemkv import parse_line, OutputType, MakeMKVMessage
        line = 'MSG:1005,0,1,"MakeMKV started","%1 started","MakeMKV"'
        msg_type, data = parse_line(line)
        assert msg_type == OutputType.MSG
        assert isinstance(data, MakeMKVMessage)

    def test_no_colon_raises(self):
        from arm.ripper.makemkv import parse_line, MakeMkvParserError
        with pytest.raises(MakeMkvParserError, match="No Message Type"):
            parse_line("garbage no colon here")

    def test_unknown_type_raises(self):
        from arm.ripper.makemkv import parse_line, MakeMkvParserError
        with pytest.raises(MakeMkvParserError, match="Cannot parse"):
            parse_line("FOOBAR:1,2,3")


class TestConvertToSeconds:
    """Test convert_to_seconds() time parsing."""

    def test_standard(self):
        from arm.ripper.makemkv import convert_to_seconds
        assert convert_to_seconds("1:30:00") == 5400

    def test_zero(self):
        from arm.ripper.makemkv import convert_to_seconds
        assert convert_to_seconds("0:00:00") == 0

    def test_seconds_only(self):
        from arm.ripper.makemkv import convert_to_seconds
        assert convert_to_seconds("0:00:45") == 45

    def test_minutes_and_seconds(self):
        from arm.ripper.makemkv import convert_to_seconds
        assert convert_to_seconds("0:05:30") == 330

    def test_large_hours(self):
        from arm.ripper.makemkv import convert_to_seconds
        assert convert_to_seconds("10:00:00") == 36000


class TestDataclasses:
    """Test dataclass constructors and __post_init__ logic."""

    def test_titles_post_init(self):
        from arm.ripper.makemkv import Titles
        t = Titles("5")
        assert t.count == 5

    def test_cinfo_post_init(self):
        from arm.ripper.makemkv import CInfo
        c = CInfo("1", "6209", "Blu-ray disc")
        assert c.id == 1
        assert c.code == 6209
        assert c.value == "Blu-ray disc"

    def test_tinfo_post_init(self):
        from arm.ripper.makemkv import TInfo
        t = TInfo("27", "0", "title00.mkv", "0")
        assert t.tid == 0
        assert t.id == 27

    def test_sinfo_post_init(self):
        from arm.ripper.makemkv import SInfo
        s = SInfo("1", "6201", "Video", "0", "0")
        assert s.tid == 0
        assert s.sid == 0

    def test_progress_bar_values(self):
        from arm.ripper.makemkv import ProgressBarValues
        p = ProgressBarValues("100", "200", "65536")
        assert p.current == 100
        assert p.total == 200
        assert p.maximum == 65536

    def test_makemkv_message(self):
        from arm.ripper.makemkv import MakeMKVMessage
        m = MakeMKVMessage("1005", "0", "1", "test message", ["param1"])
        assert m.code == 1005
        assert m.flags == 0
        assert m.count == 1

    def test_makemkv_error_message(self):
        from arm.ripper.makemkv import MakeMKVErrorMessage
        m = MakeMKVErrorMessage("2003", "0", "2", "Error msg", ["ignored", "err_detail", "param"], "")
        assert m.error == "err_detail"

    def test_makemkv_error_message_short_sprintf_raises(self):
        from arm.ripper.makemkv import MakeMKVErrorMessage
        with pytest.raises(ValueError):
            MakeMKVErrorMessage("2003", "0", "1", "Error", ["x"], "")


class TestDriveEnums:
    """Test DriveVisible and DriveType enum _missing_ fallbacks."""

    def test_drive_visible_unknown_returns_not_attached(self):
        from arm.ripper.makemkv import DriveVisible
        assert DriveVisible(999) == DriveVisible.NOT_ATTACHED

    def test_drive_type_unknown_returns_cd(self):
        from arm.ripper.makemkv import DriveType
        assert DriveType(999) == DriveType.CD

    def test_drive_loaded_states(self):
        from arm.ripper.makemkv import Drive
        # Test LOADED state (visible=2)
        d = Drive("/dev/sr0", "DISC", "Pioneer", "1", "999", "2", "0")
        assert d.loaded is True
        assert d.media_dvd is True

    def test_drive_open_state(self):
        from arm.ripper.makemkv import Drive
        d = Drive("/dev/sr0", "", "Pioneer", "0", "999", "1", "0")
        assert d.open is True
        assert d.media_cd is True

    def test_drive_empty_state(self):
        from arm.ripper.makemkv import Drive
        d = Drive("/dev/sr0", "", "Pioneer", "0", "999", "0", "0")
        assert d.loaded is False

    def test_drive_bd_type1(self):
        from arm.ripper.makemkv import Drive
        d = Drive("/dev/sr0", "DISC", "Pioneer", "12", "999", "2", "0")
        assert d.media_bd is True

    def test_drive_bd_type2(self):
        from arm.ripper.makemkv import Drive
        d = Drive("/dev/sr0", "DISC", "Pioneer", "28", "999", "2", "0")
        assert d.media_bd is True

    def test_drive_not_attached(self):
        from arm.ripper.makemkv import Drive
        d = Drive("", "", "", "0", "999", "256", "0")
        assert d.attached is False

    def test_drive_loading(self):
        from arm.ripper.makemkv import Drive
        d = Drive("/dev/sr0", "DISC", "Pioneer", "1", "999", "3", "0")
        assert d.loaded is True


class TestOutputChecker:
    """Test MakeMKVOutputChecker message processing."""

    def _msg(self, code, message="test", sprintf=None):
        from arm.ripper.makemkv import MakeMKVMessage
        if sprintf is None:
            sprintf = ["param0", "param1", "param2"]
        return MakeMKVMessage(code, 0, 1, message, sprintf)

    def test_check_requires_message_type(self):
        from arm.ripper.makemkv import MakeMKVOutputChecker
        with pytest.raises(TypeError):
            MakeMKVOutputChecker("not a message")

    def test_rip_title_error_raises(self):
        from arm.ripper.makemkv import MakeMKVOutputChecker, MessageID, MakeMkvRuntimeError
        msg = self._msg(MessageID.RIP_TITLE_ERROR)
        checker = MakeMKVOutputChecker(msg)
        with pytest.raises(MakeMkvRuntimeError):
            checker.check()

    def test_rip_completed_zero_saved_raises(self):
        from arm.ripper.makemkv import MakeMKVOutputChecker, MessageID, MakeMkvRuntimeError
        msg = self._msg(MessageID.RIP_COMPLETED, sprintf=["ignored", "0", "1"])
        checker = MakeMKVOutputChecker(msg)
        with pytest.raises(MakeMkvRuntimeError):
            checker.check()

    def test_rip_completed_nonzero_saved(self):
        from arm.ripper.makemkv import MakeMKVOutputChecker, MessageID
        msg = self._msg(MessageID.RIP_COMPLETED, sprintf=["ignored", "3", "0"])
        checker = MakeMKVOutputChecker(msg)
        # Should not raise
        result = checker.check()
        assert result is None  # zero_saved_files returns None when saved > 0

    def test_read_error_known(self):
        from arm.ripper.makemkv import (MakeMKVOutputChecker, MessageID,
                                         MakeMKVErrorMessage, ERROR_MESSAGE_TRAY_OPEN)
        msg = self._msg(MessageID.READ_ERROR, sprintf=["ignored", ERROR_MESSAGE_TRAY_OPEN, "extra"])
        checker = MakeMKVOutputChecker(msg)
        result = checker.check()
        assert isinstance(result, MakeMKVErrorMessage)

    def test_read_error_unknown(self):
        from arm.ripper.makemkv import MakeMKVOutputChecker, MessageID, MakeMKVErrorMessage
        msg = self._msg(MessageID.READ_ERROR, sprintf=["ignored", "unknown error msg", "extra"])
        checker = MakeMKVOutputChecker(msg)
        result = checker.check()
        assert isinstance(result, MakeMKVErrorMessage)

    def test_write_error_posix(self):
        from arm.ripper.makemkv import MakeMKVOutputChecker, MessageID, MakeMKVErrorMessage
        msg = self._msg(MessageID.WRITE_ERROR,
                        sprintf=["ignored", "Posix error - No such file or directory", "extra"])
        checker = MakeMKVOutputChecker(msg)
        result = checker.check()
        assert isinstance(result, MakeMKVErrorMessage)

    def test_write_error_other(self):
        from arm.ripper.makemkv import MakeMKVOutputChecker, MessageID, MakeMKVErrorMessage
        msg = self._msg(MessageID.WRITE_ERROR, sprintf=["ignored", "some other error", "extra"])
        checker = MakeMKVOutputChecker(msg)
        result = checker.check()
        assert isinstance(result, MakeMKVErrorMessage)

    def test_special_error_code(self):
        from arm.ripper.makemkv import MakeMKVOutputChecker, MessageID, MakeMKVErrorMessage
        msg = self._msg(MessageID.EVALUATION_PERIOD_EXPIRED_APP_TOO_OLD,
                        sprintf=["ignored", "expired", "extra"])
        checker = MakeMKVOutputChecker(msg)
        result = checker.check()
        assert isinstance(result, MakeMKVErrorMessage)

    def test_log_only_code(self):
        from arm.ripper.makemkv import MakeMKVOutputChecker, MessageID, MakeMKVMessage
        msg = self._msg(MessageID.RIP_DISC_OPEN_ERROR)
        checker = MakeMKVOutputChecker(msg)
        result = checker.check()
        assert isinstance(result, MakeMKVMessage)

    def test_default_returns_data(self):
        from arm.ripper.makemkv import MakeMKVOutputChecker, MakeMKVMessage
        # Use a code not in any special map (e.g. VERSION_INFO=1005)
        msg = self._msg(1005)
        checker = MakeMKVOutputChecker(msg)
        result = checker.check()
        assert isinstance(result, MakeMKVMessage)


class TestStripTrackSuffix:
    """Test _strip_track_suffix() filename normalization."""

    def test_standard(self):
        from arm.ripper.makemkv import _strip_track_suffix
        assert _strip_track_suffix("C1_t04.mkv") == "C1"

    def test_no_suffix(self):
        from arm.ripper.makemkv import _strip_track_suffix
        assert _strip_track_suffix("title.mkv") == "title"

    def test_complex_name(self):
        from arm.ripper.makemkv import _strip_track_suffix
        assert _strip_track_suffix("Last Vermeer, The-B1_t00.mkv") == "Last Vermeer, The-B1"


class TestPrefixMatchPass:
    """Test _prefix_match_pass() filename reconciliation."""

    def test_matches_by_prefix(self):
        from arm.ripper.makemkv import _prefix_match_pass

        track = unittest.mock.MagicMock()
        track.track_id = 1
        track.track_number = "0"
        track.filename = "Movie_t00.mkv"

        actual_files = ["Movie_t00.mkv", "Movie_t01.mkv"]
        claimed = set()
        matched_ids = set()
        # Since "Movie_t00.mkv" is not claimed, prefix "Movie" maps to both files
        # so single-candidate check fails — no match
        result = _prefix_match_pass([track], actual_files, claimed, matched_ids)
        assert result is False

    def test_single_candidate_matches(self):
        from arm.ripper.makemkv import _prefix_match_pass

        track = unittest.mock.MagicMock()
        track.track_id = 1
        track.track_number = "0"
        track.filename = "C1_t00.mkv"

        actual_files = ["C1_t01.mkv"]  # prefix "C1" only matches one file
        claimed = set()
        matched_ids = set()
        result = _prefix_match_pass([track], actual_files, claimed, matched_ids)
        assert result is True
        assert track.filename == "C1_t01.mkv"


class TestPositionalMatchPass:
    """Test _positional_match_pass() fallback filename matching."""

    def test_matches_by_position(self):
        from arm.ripper.makemkv import _positional_match_pass

        t1 = unittest.mock.MagicMock()
        t1.track_id = 1
        t1.track_number = "0"
        t2 = unittest.mock.MagicMock()
        t2.track_id = 2
        t2.track_number = "1"

        actual_files = ["file_a.mkv", "file_b.mkv"]
        matched_ids = set()
        claimed = set()
        result = _positional_match_pass([t1, t2], actual_files, matched_ids, claimed)
        assert result is True
        assert t1.filename == "file_a.mkv"
        assert t2.filename == "file_b.mkv"

    def test_mismatch_count_returns_false(self):
        from arm.ripper.makemkv import _positional_match_pass

        t1 = unittest.mock.MagicMock()
        t1.track_id = 1
        t1.track_number = "0"

        result = _positional_match_pass([t1], ["a.mkv", "b.mkv"], set(), set())
        assert result is False


class TestSetupRawpath:
    """Test setup_rawpath() directory creation."""

    def test_creates_new_path(self, tmp_path):
        from arm.ripper.makemkv import setup_rawpath

        job = unittest.mock.MagicMock()
        job.title = "TestMovie"
        raw = str(tmp_path / "raw" / "TestMovie")
        result = setup_rawpath(job, raw)
        assert result == raw
        assert os.path.isdir(raw)

    def test_existing_path_gets_timestamp(self, tmp_path):
        from arm.ripper.makemkv import setup_rawpath

        raw = str(tmp_path / "raw" / "TestMovie")
        os.makedirs(raw)

        job = unittest.mock.MagicMock()
        job.title = "TestMovie"
        job.config.RAW_PATH = str(tmp_path / "raw")

        result = setup_rawpath(job, raw)
        assert result != raw
        assert os.path.isdir(result)
        assert "TestMovie_" in result


class TestProgressLog:
    """Test progress_log() path construction."""

    def test_returns_quoted_path(self):
        from arm.ripper.makemkv import progress_log

        job = unittest.mock.MagicMock()
        job.job_id = 42
        job.config.LOGPATH = "/tmp/logs"

        result = progress_log(job)
        assert "42.log" in result
        assert "progress" in result


class TestErrorClasses:
    """Test MakeMkvRuntimeError and UpdateKeyRunTimeError."""

    def test_makemkv_runtime_error(self):
        from arm.ripper.makemkv import MakeMkvRuntimeError
        err = MakeMkvRuntimeError(1, ["makemkvcon", "mkv"], output="test output")
        assert "code: 1" in err.message

    def test_makemkv_runtime_error_with_stderr(self):
        from arm.ripper.makemkv import MakeMkvRuntimeError
        err = MakeMkvRuntimeError(2, ["cmd"], stderr="stderr data")
        assert "code: 2" in err.message

    def test_update_key_error_known_code(self):
        from arm.ripper.makemkv import UpdateKeyRunTimeError, UpdateKeyErrorCodes
        err = UpdateKeyRunTimeError(40, ["bash", "update_key.sh", "ABCD-1234"])
        assert "URL_ERROR" in err.message

    def test_update_key_error_unknown_code(self):
        from arm.ripper.makemkv import UpdateKeyRunTimeError
        err = UpdateKeyRunTimeError(99, ["bash", "script.sh"])
        assert "UNDEFINED_ERROR" in err.message

    def test_update_key_masks_key(self):
        from arm.ripper.makemkv import UpdateKeyRunTimeError
        # When cmd has 3 elements, the key (index 2) is masked
        err = UpdateKeyRunTimeError(1, ["bash", "script.sh", "SECRET_KEY_12345"])
        # Should not expose full key in error message
        assert "SECRET_KEY_12345" not in err.message


class TestRunTypeChecks:
    """Test run() input validation."""

    def test_options_not_list_raises(self):
        from arm.ripper.makemkv import run, OutputType
        with pytest.raises(TypeError):
            list(run("not a list", OutputType.MSG))

    def test_select_not_output_type_raises(self):
        from arm.ripper.makemkv import run
        with pytest.raises(TypeError):
            list(run([], "not an OutputType"))


class TestTrackInfoProcessor:
    """Test TrackInfoProcessor message handling."""

    def test_handle_tinfo_filename(self, app_context, sample_job):
        from arm.ripper.makemkv import TrackInfoProcessor, TInfo, TrackID

        processor = TrackInfoProcessor(sample_job, 0)
        msg = TInfo(str(TrackID.FILENAME), "0", '"title_t00.mkv"', "0")
        processor._process_message(msg)
        assert processor.filename == "title_t00.mkv"

    def test_handle_tinfo_duration(self, app_context, sample_job):
        from arm.ripper.makemkv import TrackInfoProcessor, TInfo, TrackID

        processor = TrackInfoProcessor(sample_job, 0)
        msg = TInfo(str(TrackID.DURATION), "0", "1:30:00", "0")
        processor._process_message(msg)
        assert processor.seconds == 5400

    def test_handle_tinfo_chapters(self, app_context, sample_job):
        from arm.ripper.makemkv import TrackInfoProcessor, TInfo, TrackID

        processor = TrackInfoProcessor(sample_job, 0)
        msg = TInfo(str(TrackID.CHAPTERS), "0", "24", "0")
        processor._process_message(msg)
        assert processor.chapters == 24

    def test_handle_tinfo_filesize(self, app_context, sample_job):
        from arm.ripper.makemkv import TrackInfoProcessor, TInfo, TrackID

        processor = TrackInfoProcessor(sample_job, 0)
        msg = TInfo(str(TrackID.FILESIZE), "0", "1073741824", "0")
        processor._process_message(msg)
        assert processor.filesize == 1073741824

    def test_handle_sinfo_video_type(self, app_context, sample_job):
        from arm.ripper.makemkv import (TrackInfoProcessor, SInfo, StreamID,
                                         MAKEMKV_STREAM_CODE_TYPE_VIDEO)

        processor = TrackInfoProcessor(sample_job, 0)
        # First set stream type to video
        type_msg = SInfo(str(StreamID.TYPE), str(MAKEMKV_STREAM_CODE_TYPE_VIDEO), "Video", "0", "0")
        processor._process_message(type_msg)
        assert processor.stream_type == MAKEMKV_STREAM_CODE_TYPE_VIDEO

        # Then set aspect ratio
        aspect_msg = SInfo(str(StreamID.ASPECT), "0", "16:9", "0", "0")
        processor._process_message(aspect_msg)
        assert processor.aspect == "16:9"

    def test_handle_sinfo_fps(self, app_context, sample_job):
        from arm.ripper.makemkv import (TrackInfoProcessor, SInfo, StreamID,
                                         MAKEMKV_STREAM_CODE_TYPE_VIDEO)

        processor = TrackInfoProcessor(sample_job, 0)
        type_msg = SInfo(str(StreamID.TYPE), str(MAKEMKV_STREAM_CODE_TYPE_VIDEO), "Video", "0", "0")
        processor._process_message(type_msg)

        fps_msg = SInfo(str(StreamID.FPS), "0", "23.976 (24000/1001)", "0", "0")
        processor._process_message(fps_msg)
        assert abs(processor.fps - 23.976) < 0.001

    def test_handle_titles_message(self, app_context, sample_job):
        from arm.ripper.makemkv import TrackInfoProcessor, Titles

        processor = TrackInfoProcessor(sample_job, 0)
        msg = Titles("5")
        processor._process_message(msg)
        # Should have called database_updater
        assert sample_job.no_of_titles == 5

    def test_add_track(self, app_context, sample_job):
        from arm.ripper.makemkv import TrackInfoProcessor
        from arm.models.track import Track

        processor = TrackInfoProcessor(sample_job, 0)
        processor.track_id = 0
        processor.seconds = 3600
        processor.aspect = "16:9"
        processor.fps = 24.0
        processor.filename = "title_t00.mkv"
        processor.chapters = 15
        processor.filesize = 5000000

        processor._add_track()

        tracks = Track.query.filter_by(job_id=sample_job.job_id).all()
        assert len(tracks) == 1
        assert tracks[0].length == 3600
        assert tracks[0].filename == "title_t00.mkv"

    def test_add_track_resets_state(self, app_context, sample_job):
        from arm.ripper.makemkv import TrackInfoProcessor

        processor = TrackInfoProcessor(sample_job, 0)
        processor.track_id = 0
        processor.seconds = 3600
        processor.filename = "test.mkv"
        processor._add_track()

        assert processor.seconds == 0
        assert processor.filename == ""

    def test_new_track_triggers_add(self, app_context, sample_job):
        """When tid changes, previous track is added."""
        from arm.ripper.makemkv import TrackInfoProcessor, TInfo, TrackID
        from arm.models.track import Track

        processor = TrackInfoProcessor(sample_job, 0)
        # First track
        msg1 = TInfo(str(TrackID.FILENAME), "0", '"track0.mkv"', "0")
        processor._process_message(msg1)
        assert processor.track_id == 0

        # Second track with different tid triggers add of first
        msg2 = TInfo(str(TrackID.FILENAME), "0", '"track1.mkv"', "1")
        processor._process_message(msg2)

        tracks = Track.query.filter_by(job_id=sample_job.job_id).all()
        assert len(tracks) == 1  # First track was added

    def test_chapters_bad_value(self, app_context, sample_job):
        from arm.ripper.makemkv import TrackInfoProcessor, TInfo, TrackID

        processor = TrackInfoProcessor(sample_job, 0)
        msg = TInfo(str(TrackID.CHAPTERS), "0", "not_a_number", "0")
        # Should not raise, just log warning
        processor._process_message(msg)
        assert processor.chapters == 0

    def test_filesize_bad_value(self, app_context, sample_job):
        from arm.ripper.makemkv import TrackInfoProcessor, TInfo, TrackID

        processor = TrackInfoProcessor(sample_job, 0)
        msg = TInfo(str(TrackID.FILESIZE), "0", "invalid", "0")
        processor._process_message(msg)
        assert processor.filesize == 0


class TestMakemkvInfoTypeChecks:
    """Test makemkv_info() input validation."""

    def test_options_not_list_raises(self, app_context, sample_job):
        from arm.ripper.makemkv import makemkv_info
        with pytest.raises(TypeError):
            list(makemkv_info(sample_job, options="not a list"))


class TestUpdateKeyErrorCodes:
    """Test UpdateKeyErrorCodes enum."""

    def test_known_codes(self):
        from arm.ripper.makemkv import UpdateKeyErrorCodes
        assert UpdateKeyErrorCodes(1) == UpdateKeyErrorCodes.GENERAL_ERROR
        assert UpdateKeyErrorCodes(20) == UpdateKeyErrorCodes.PARSE_ERROR
        assert UpdateKeyErrorCodes(40) == UpdateKeyErrorCodes.URL_ERROR
        assert UpdateKeyErrorCodes(50) == UpdateKeyErrorCodes.INVALID_MAKEMKV_SERIAL

    def test_unknown_code_returns_undefined(self):
        from arm.ripper.makemkv import UpdateKeyErrorCodes
        assert UpdateKeyErrorCodes(999) == UpdateKeyErrorCodes.UNDEFINED_ERROR
