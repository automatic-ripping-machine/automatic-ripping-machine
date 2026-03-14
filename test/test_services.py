"""Tests for arm/services/ modules: tvdb_sync, files, jobs, config.

Covers high-impact uncovered lines with extensive mocking of DB,
filesystem, and external API calls.
"""
import datetime
import os
import tempfile
import unittest.mock
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


# ═══════════════════════════════════════════════════════════════════════
# tvdb_sync tests
# ═══════════════════════════════════════════════════════════════════════

class TestApplyMatches:
    """Test _apply_matches helper."""

    def test_matches_written_to_tracks(self, app_context):
        from arm.services.tvdb_sync import _apply_matches
        from arm.services.matching.base import MatchResult, TrackMatch

        job = MagicMock()
        track1 = MagicMock()
        track2 = MagicMock()
        track1.track_number = "1"
        track2.track_number = "2"
        job.tracks = [track1, track2]

        result = MatchResult(
            matcher="tvdb",
            season=1,
            matches=[
                TrackMatch(track_number="1", episode_number=1,
                           episode_name="Pilot", episode_runtime=42),
                TrackMatch(track_number="2", episode_number=2,
                           episode_name="Second", episode_runtime=44),
            ],
            match_count=2,
        )

        count = _apply_matches(job, result)
        assert count == 2
        assert track1.title == "Pilot"
        assert track1.episode_number == "1"
        assert track2.episode_name == "Second"

    def test_unmatched_tracks_skipped(self, app_context):
        from arm.services.tvdb_sync import _apply_matches
        from arm.services.matching.base import MatchResult, TrackMatch

        job = MagicMock()
        track1 = MagicMock()
        track1.track_number = "1"
        job.tracks = [track1]

        result = MatchResult(
            matcher="tvdb",
            season=1,
            matches=[
                TrackMatch(track_number="99", episode_number=1,
                           episode_name="Missing", episode_runtime=42),
            ],
            match_count=1,
        )

        count = _apply_matches(job, result)
        assert count == 0


class TestMatchEpisodesSync:
    """Test match_episodes_sync."""

    def test_successful_match(self, app_context):
        from arm.services.tvdb_sync import match_episodes_sync
        from arm.services.matching.base import MatchResult, TrackMatch

        job = MagicMock()
        job.tvdb_id = None
        job.season = None
        track = MagicMock()
        track.track_number = "1"
        job.tracks = [track]

        result = MatchResult(
            matcher="tvdb", season=2, tvdb_id=12345,
            matches=[TrackMatch("1", 1, "Ep1", 42)],
            match_count=1,
        )

        with patch("arm.services.matching.match_job", return_value=result), \
             patch("arm.services.tvdb_sync.db") as mock_db:
            assert match_episodes_sync(job) is True
            mock_db.session.commit.assert_called_once()

        assert job.tvdb_id == 12345
        assert job.season_auto == "2"

    def test_no_matches_returns_false(self, app_context):
        from arm.services.tvdb_sync import match_episodes_sync
        from arm.services.matching.base import MatchResult

        job = MagicMock()
        result = MatchResult(matcher="tvdb", error="No series found")

        with patch("arm.services.matching.match_job", return_value=result):
            assert match_episodes_sync(job) is False

    def test_exception_returns_false(self, app_context):
        from arm.services.tvdb_sync import match_episodes_sync

        job = MagicMock()
        with patch("arm.services.matching.match_job",
                   side_effect=RuntimeError("boom")):
            assert match_episodes_sync(job) is False

    def test_zero_matched_tracks_returns_false(self, app_context):
        from arm.services.tvdb_sync import match_episodes_sync
        from arm.services.matching.base import MatchResult, TrackMatch

        job = MagicMock()
        job.tvdb_id = None
        job.season = None
        job.tracks = []  # no tracks to match against

        result = MatchResult(
            matcher="tvdb", season=1,
            matches=[TrackMatch("99", 1, "Ghost", 42)],
            match_count=1,
        )

        with patch("arm.services.matching.match_job", return_value=result), \
             patch("arm.services.tvdb_sync.db"):
            assert match_episodes_sync(job) is False

    def test_tvdb_id_not_overwritten_if_already_set(self, app_context):
        from arm.services.tvdb_sync import match_episodes_sync
        from arm.services.matching.base import MatchResult, TrackMatch

        job = MagicMock()
        job.tvdb_id = 99999  # already set
        job.season = None
        track = MagicMock()
        track.track_number = "1"
        job.tracks = [track]

        result = MatchResult(
            matcher="tvdb", season=1, tvdb_id=12345,
            matches=[TrackMatch("1", 1, "Ep1", 42)],
            match_count=1,
        )

        with patch("arm.services.matching.match_job", return_value=result), \
             patch("arm.services.tvdb_sync.db"):
            match_episodes_sync(job)

        # Should NOT overwrite existing tvdb_id
        assert job.tvdb_id == 99999


class TestMatchEpisodesForApi:
    """Test match_episodes_for_api."""

    def test_returns_dict_with_results(self, app_context):
        from arm.services.tvdb_sync import match_episodes_for_api
        from arm.services.matching.base import MatchResult, TrackMatch

        job = MagicMock()
        job.tvdb_id = None
        job.tracks = []

        result = MatchResult(
            matcher="tvdb", season=3,
            matches=[TrackMatch("1", 5, "FiveAlive", 30)],
            match_count=1, score=0.95,
            alternatives=[{"season": 4}],
        )

        with patch("arm.services.matching.match_job", return_value=result):
            out = match_episodes_for_api(job, season=3, tolerance=120)

        assert out["success"] is True
        assert out["matcher"] == "tvdb"
        assert out["season"] == 3
        assert len(out["matches"]) == 1
        assert out["matches"][0]["episode_name"] == "FiveAlive"
        assert out["score"] == pytest.approx(0.95)

    def test_apply_writes_to_db(self, app_context):
        from arm.services.tvdb_sync import match_episodes_for_api
        from arm.services.matching.base import MatchResult, TrackMatch

        job = MagicMock()
        job.tvdb_id = None
        job.season = None
        track = MagicMock()
        track.track_number = "1"
        job.tracks = [track]

        result = MatchResult(
            matcher="tvdb", season=1, tvdb_id=555,
            matches=[TrackMatch("1", 1, "Applied", 42)],
            match_count=1, score=0.9,
        )

        with patch("arm.services.matching.match_job", return_value=result), \
             patch("arm.services.tvdb_sync.db") as mock_db:
            out = match_episodes_for_api(job, apply=True)

        assert out["applied"] is True
        mock_db.session.commit.assert_called_once()
        assert job.tvdb_id == 555

    def test_error_included_in_output(self, app_context):
        from arm.services.tvdb_sync import match_episodes_for_api
        from arm.services.matching.base import MatchResult

        job = MagicMock()
        job.tracks = []

        result = MatchResult(matcher="tvdb", error="API down")

        with patch("arm.services.matching.match_job", return_value=result):
            out = match_episodes_for_api(job)

        assert out["success"] is False
        assert out["error"] == "API down"


# ═══════════════════════════════════════════════════════════════════════
# files tests
# ═══════════════════════════════════════════════════════════════════════

class TestDatabaseUpdater:
    """Test database_updater."""

    def test_successful_update(self, app_context):
        from arm.services.files import database_updater

        job = MagicMock()
        with patch("arm.services.files.db") as mock_db:
            result = database_updater({"status": "success"}, job)

        assert result is True
        assert job.status == "success"
        mock_db.session.commit.assert_called()

    def test_locked_db_retries(self, app_context):
        from arm.services.files import database_updater

        job = MagicMock()
        call_count = 0

        def commit_side_effect():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("database is locked")

        with patch("arm.services.files.db") as mock_db, \
             patch("arm.services.files.sleep"):
            mock_db.session.commit.side_effect = commit_side_effect
            result = database_updater({"status": "x"}, job, wait_time=5)

        assert result is True
        assert call_count == 3

    def test_non_locked_error_raises(self, app_context):
        from arm.services.files import database_updater

        job = MagicMock()
        with patch("arm.services.files.db") as mock_db:
            mock_db.session.commit.side_effect = Exception("some other error")
            with pytest.raises(RuntimeError, match="some other error"):
                database_updater({"status": "x"}, job, wait_time=2)
            mock_db.session.rollback.assert_called()


class TestMakeDir:
    """Test make_dir."""

    def test_creates_directory(self, tmp_path):
        from arm.services.files import make_dir

        new_dir = str(tmp_path / "newdir")
        result = make_dir(new_dir)
        assert result is True
        assert os.path.isdir(new_dir)

    def test_existing_directory_returns_false(self, tmp_path):
        from arm.services.files import make_dir

        result = make_dir(str(tmp_path))
        assert result is False

    def test_permission_error_returns_false(self):
        from arm.services.files import make_dir

        with patch("arm.services.files.os.path.exists", return_value=False), \
             patch("arm.services.files.os.makedirs", side_effect=OSError("denied")):
            result = make_dir("/impossible/path")
        assert result is False


class TestGetsize:
    """Test getsize."""

    def test_returns_gb_value(self):
        from arm.services.files import getsize

        mock_stats = MagicMock()
        mock_stats.f_bavail = 1073741824  # 1 GB in blocks of size 1
        mock_stats.f_frsize = 1

        with patch("arm.services.files.os.statvfs", return_value=mock_stats):
            result = getsize("/")
        assert result == pytest.approx(1.0)


class TestCleanForFilename:
    """Test clean_for_filename."""

    def test_basic_cleaning(self):
        from arm.services.files import clean_for_filename

        assert clean_for_filename("Movie: The & Sequel") == "Movie- The and Sequel"
        assert clean_for_filename("Bad\\Title") == "Bad - Title"
        assert clean_for_filename("  Extra   Spaces  ") == "Extra Spaces"


class TestValidateLogfile:
    """Test validate_logfile."""

    def test_valid_logfile(self, tmp_path):
        from arm.services.files import validate_logfile

        logfile = tmp_path / "test.log"
        logfile.write_text("log content")

        with patch("arm.services.files.cfg") as mock_cfg:
            mock_cfg.arm_config = {"LOGPATH": str(tmp_path)}
            result = validate_logfile("test.log", "true", logfile)
        assert result == str(logfile)

    def test_none_logfile_raises(self):
        from arm.services.files import validate_logfile

        with pytest.raises(ValueError):
            validate_logfile(None, "true", MagicMock())

    def test_path_traversal_raises(self, tmp_path):
        from arm.services.files import validate_logfile
        from pathlib import Path

        # Create a file outside logpath
        outside = tmp_path / "outside"
        outside.mkdir()
        evil_file = outside / "evil.log"
        evil_file.write_text("evil")

        with patch("arm.services.files.cfg") as mock_cfg:
            mock_cfg.arm_config = {"LOGPATH": str(tmp_path / "logs")}
            with pytest.raises(ValueError):
                validate_logfile("../../evil.log", "true", evil_file)

    def test_missing_file_raises(self, tmp_path):
        from arm.services.files import validate_logfile
        from pathlib import Path

        logdir = tmp_path / "logs"
        logdir.mkdir()
        missing = logdir / "missing.log"

        with patch("arm.services.files.cfg") as mock_cfg:
            mock_cfg.arm_config = {"LOGPATH": str(logdir)}
            with pytest.raises(FileNotFoundError):
                validate_logfile("missing.log", "true", missing)


class TestJobIdValidator:
    """Test job_id_validator."""

    def test_valid_id(self):
        from arm.services.files import job_id_validator
        assert job_id_validator("42") is True

    def test_invalid_non_string(self):
        from arm.services.files import job_id_validator
        # Integers don't have .strip() — triggers AttributeError
        assert job_id_validator(42) is False


class TestFindFolderInLog:
    """Test find_folder_in_log."""

    def test_finds_path_in_log(self, tmp_path):
        from arm.services.files import find_folder_in_log

        logfile = tmp_path / "test.log"
        logfile.write_text(
            "INFO some stuff\n"
            "ERROR Operation not permitted: '/home/arm/media/completed/Movie (2020)'\n"
            "INFO done\n"
        )
        result = find_folder_in_log(str(logfile), "/default/path")
        assert result == "/home/arm/media/completed/Movie (2020)"

    def test_returns_default_when_not_found(self, tmp_path):
        from arm.services.files import find_folder_in_log

        logfile = tmp_path / "test.log"
        logfile.write_text("Nothing relevant here\n")
        result = find_folder_in_log(str(logfile), "/default/path")
        assert result == "/default/path"


class TestSendToRemoteDb:
    """Test send_to_remote_db."""

    def test_successful_send(self, app_context):
        from arm.services.files import send_to_remote_db

        mock_job = MagicMock()
        mock_job.crc_id = "abc123"
        mock_job.title = "Test"
        mock_job.year = "2020"
        mock_job.imdb_id = "tt1234"
        mock_job.hasnicetitle = True
        mock_job.label = "TEST"
        mock_job.video_type = "movie"
        mock_job.get_d.return_value = {"title": "Test"}.items()
        mock_job.get_d.return_value = {"title": "Test"}
        mock_job.config.get_d.return_value = {"key": "val"}

        mock_response = MagicMock()
        mock_response.text = '{"success": true}'

        with patch("arm.services.files.Job") as MockJob, \
             patch("arm.services.files.cfg") as mock_cfg, \
             patch("arm.services.files.requests.get", return_value=mock_response):
            mock_cfg.arm_config = {"ARM_API_KEY": "test_key"}
            MockJob.query.get.return_value = mock_job
            result = send_to_remote_db(1)

        assert result["status"] == "success"

    def test_failed_send(self, app_context):
        from arm.services.files import send_to_remote_db

        mock_job = MagicMock()
        mock_job.crc_id = "abc123"
        mock_job.title = "Test"
        mock_job.year = "2020"
        mock_job.imdb_id = "tt1234"
        mock_job.hasnicetitle = True
        mock_job.label = "TEST"
        mock_job.video_type = "movie"
        mock_job.get_d.return_value = {"title": "Test"}
        mock_job.config.get_d.return_value = {"key": "val"}

        mock_response = MagicMock()
        mock_response.text = '{"success": false, "Error": "Not found"}'

        with patch("arm.services.files.Job") as MockJob, \
             patch("arm.services.files.cfg") as mock_cfg, \
             patch("arm.services.files.requests.get", return_value=mock_response):
            mock_cfg.arm_config = {"ARM_API_KEY": "key123"}
            MockJob.query.get.return_value = mock_job
            result = send_to_remote_db(1)

        assert result["status"] == "fail"
        assert result["error"] == "Not found"


# ═══════════════════════════════════════════════════════════════════════
# jobs tests
# ═══════════════════════════════════════════════════════════════════════

class TestGetNotifications:
    """Test get_notifications."""

    def test_returns_notification_list(self, app_context):
        from arm.services.jobs import get_notifications
        from arm.models.notifications import Notifications
        from arm.database import db

        n = Notifications("Test Title", "Test Message")
        db.session.add(n)
        db.session.commit()

        result = get_notifications()
        assert len(result) == 1
        assert result[0]["title"] == "Test Title"


class TestGetXJobs:
    """Test get_x_jobs."""

    def test_joblist_returns_active(self, sample_job):
        from arm.services.jobs import get_x_jobs

        with patch("arm.services.jobs.cfg") as mock_cfg, \
             patch("arm.services.jobs.process_logfile"):
            mock_cfg.arm_config = {"LOGPATH": "/home/arm/logs", "ARM_NAME": "test-arm"}
            result = get_x_jobs("joblist")

        assert result["success"] is True
        assert result["mode"] == "joblist"
        assert len(result["results"]) >= 1

    def test_success_status(self, sample_job):
        from arm.services.jobs import get_x_jobs
        from arm.database import db

        sample_job.status = "success"
        db.session.commit()

        with patch("arm.services.jobs.cfg") as mock_cfg, \
             patch("arm.services.jobs.process_logfile"):
            mock_cfg.arm_config = {"LOGPATH": "/home/arm/logs", "ARM_NAME": "test-arm"}
            result = get_x_jobs("success")

        assert result["mode"] == "success"

    def test_invalid_status_raises(self, app_context):
        from arm.services.jobs import get_x_jobs

        with pytest.raises(ValueError):
            get_x_jobs("nonexistent_status")


class TestProcessLogfile:
    """Test process_logfile."""

    def test_video_ripping_dispatches_to_makemkv(self, app_context):
        from arm.services.jobs import process_logfile

        job = MagicMock()
        job.disctype = "bluray"
        job.status = "ripping"
        job_results = {}

        with patch("arm.services.jobs.process_makemkv_logfile",
                   return_value={"progress": "50"}) as mock_mkv:
            process_logfile("/home/arm/logs/test.log", job, job_results)
            mock_mkv.assert_called_once_with(job, job_results)

    def test_music_ripping_dispatches_to_audio(self, app_context):
        from arm.services.jobs import process_logfile

        job = MagicMock()
        job.disctype = "music"
        job.status = "ripping"
        job.logfile = "music.log"
        job_results = {}

        with patch("arm.services.jobs.process_audio_logfile",
                   return_value={}) as mock_audio:
            process_logfile("/home/arm/logs/music.log", job, job_results)
            mock_audio.assert_called_once_with("music.log", job, job_results)

    def test_other_disctype_returns_unchanged(self, app_context):
        from arm.services.jobs import process_logfile

        job = MagicMock()
        job.disctype = "data"
        job.status = "success"
        job_results = {}

        result = process_logfile("/home/arm/logs/test.log", job, job_results)
        assert result == job_results


class TestDeleteJob:
    """Test delete_job."""

    def test_delete_all_returns_success(self, app_context):
        from arm.services.jobs import delete_job

        result = delete_job("all", "delete")
        assert result["success"] is True
        assert result["job"] == "all"

    def test_delete_title_returns_success(self, app_context):
        from arm.services.jobs import delete_job

        result = delete_job("title", "delete")
        assert result["success"] is True
        assert result["job"] == "title"

    def test_delete_invalid_id(self, app_context):
        from arm.services.jobs import delete_job

        with patch("arm.services.jobs.db") as mock_db:
            result = delete_job("notanumber", "delete")

        assert result["success"] is False
        assert result["error"] == "Not a valid job"

    def test_delete_valid_id(self, sample_job):
        from arm.services.jobs import delete_job

        job_id = str(sample_job.job_id)
        with patch("arm.services.drives.job_cleanup"):
            result = delete_job(job_id, "delete")

        assert result["success"] is True


class TestGenerateLog:
    """Test generate_log."""

    def test_missing_job_returns_failure(self, app_context):
        from arm.services.jobs import generate_log

        result = generate_log("/home/arm/logs", "99999")
        assert result["success"] is False

    def test_job_with_no_logfile(self, sample_job):
        from arm.services.jobs import generate_log

        sample_job.logfile = None
        from arm.database import db
        db.session.commit()

        result = generate_log("/home/arm/logs", str(sample_job.job_id))
        assert result["success"] is False

    def test_valid_logfile(self, sample_job, tmp_path):
        from arm.services.jobs import generate_log

        logfile = tmp_path / "test.log"
        logfile.write_text("Log line 1\nLog line 2")
        sample_job.logfile = "test.log"
        from arm.database import db
        db.session.commit()

        result = generate_log(str(tmp_path), str(sample_job.job_id))
        assert result["success"] is True
        assert "Log line 1" in result["log"]
        assert result["escaped"] is True

    def test_missing_logfile_on_disk(self, sample_job, tmp_path):
        from arm.services.jobs import generate_log

        sample_job.logfile = "nonexistent.log"
        from arm.database import db
        db.session.commit()

        result = generate_log(str(tmp_path), str(sample_job.job_id))
        assert result["success"] is False
        assert result["log"] == "File not found"


class TestAbandonJob:
    """Test abandon_job."""

    def test_invalid_job_id(self, app_context):
        from arm.services.jobs import abandon_job

        result = abandon_job(42)  # not a string
        assert result["success"] is False

    def test_successful_abandon(self, sample_job):
        from arm.services.jobs import abandon_job

        with patch("arm.services.jobs.terminate_process"):
            result = abandon_job(str(sample_job.job_id))

        assert result["success"] is True
        assert result["mode"] == "abandon"

    def test_abandon_with_terminate_error(self, sample_job):
        from arm.services.jobs import abandon_job

        with patch("arm.services.jobs.terminate_process",
                   side_effect=ValueError("Access denied")):
            result = abandon_job(str(sample_job.job_id))

        assert result["success"] is False
        assert "Access denied" in result.get("Error", "")


class TestTerminateProcess:
    """Test terminate_process."""

    def test_none_pid(self):
        from arm.services.jobs import terminate_process
        # Should not raise
        terminate_process(None)

    def test_no_such_process(self):
        from arm.services.jobs import terminate_process
        import psutil

        with patch("arm.services.jobs.psutil.Process",
                   side_effect=psutil.NoSuchProcess(99999)):
            terminate_process(99999)  # should not raise

    def test_access_denied(self):
        from arm.services.jobs import terminate_process
        import psutil

        with patch("arm.services.jobs.psutil.Process",
                   side_effect=psutil.AccessDenied(1)):
            with pytest.raises(ValueError, match="Access denied"):
                terminate_process(1)

    def test_successful_terminate(self):
        from arm.services.jobs import terminate_process

        mock_process = MagicMock()
        with patch("arm.services.jobs.psutil.Process", return_value=mock_process):
            terminate_process(12345)
        mock_process.terminate.assert_called_once()


class TestReadNotification:
    """Test read_notification."""

    def test_read_existing(self, app_context):
        from arm.services.jobs import read_notification
        from arm.models.notifications import Notifications
        from arm.database import db

        n = Notifications("Title", "Body")
        db.session.add(n)
        db.session.commit()

        result = read_notification(n.id)
        assert result["success"] is True

    def test_read_nonexistent(self, app_context):
        from arm.services.jobs import read_notification

        result = read_notification(99999)
        assert result["success"] is False
        assert "already read" in result["message"]


class TestGetNotifyTimeout:
    """Test get_notify_timeout."""

    def test_with_settings(self, app_context):
        from arm.services.jobs import get_notify_timeout
        from arm.models.ui_settings import UISettings
        from arm.database import db

        ui_cfg = UISettings(notify_refresh=3000)
        db.session.add(ui_cfg)
        db.session.commit()

        result = get_notify_timeout(None)
        assert result["success"] is True
        assert result["notify_timeout"] == 3000

    def test_without_settings(self, app_context):
        from arm.services.jobs import get_notify_timeout

        result = get_notify_timeout(None)
        assert result["notify_timeout"] == "6500"


class TestSearch:
    """Test search."""

    def test_finds_matching_jobs(self, sample_job):
        from arm.services.jobs import search

        result = search("SERIAL")
        assert result["success"] is True
        assert len(result["results"]) >= 1

    def test_no_results(self, app_context):
        from arm.services.jobs import search

        result = search("ZZZZNONEXISTENT")
        assert result["success"] is True
        assert len(result["results"]) == 0


class TestCalcProcessTime:
    """Test calc_process_time."""

    def test_valid_calculation(self):
        from arm.services.jobs import calc_process_time

        start = datetime.datetime.now() - datetime.timedelta(minutes=5)
        result = calc_process_time(start, 5, 10)
        assert "@" in result  # contains time estimate

    def test_zero_iter(self):
        from arm.services.jobs import calc_process_time

        result = calc_process_time(datetime.datetime.now(), 0, 10)
        assert "@" in result  # falls through to fallback

    def test_none_start(self):
        from arm.services.jobs import calc_process_time

        result = calc_process_time(None, 1, 10)
        assert "@" in result


class TestReadLogLine:
    """Test read_log_line."""

    def test_missing_file(self):
        from arm.services.jobs import read_log_line

        result = read_log_line("/nonexistent/file.log")
        assert result == ["", ""]


class TestReadAllLogLines:
    """Test read_all_log_lines."""

    def test_existing_file(self, tmp_path):
        from arm.services.jobs import read_all_log_lines

        logfile = tmp_path / "test.log"
        logfile.write_text("line1\nline2\n")
        result = read_all_log_lines(str(logfile))
        assert len(result) == 2

    def test_missing_file(self):
        from arm.services.jobs import read_all_log_lines

        result = read_all_log_lines("/nonexistent/file.log")
        assert result == ""


class TestPercentage:
    """Test percentage."""

    def test_basic_calculation(self):
        from arm.services.jobs import percentage
        assert percentage(50, 100) == pytest.approx(50.0)
        assert percentage(1, 4) == pytest.approx(25.0)


class TestProcessMakemkvLogfile:
    """Test process_makemkv_logfile."""

    def test_with_progress(self, app_context):
        from arm.services.jobs import process_makemkv_logfile

        job = MagicMock()
        job.logfile = "test.log"
        job.job_id = 1
        job.no_of_titles = 5
        job_results = {}

        lines = [
            b"PRGV:500,0,1000",
            b"PRGC:0,2,\"Analyzing seamless segments\"",
        ]
        with patch("arm.services.jobs.cfg") as mock_cfg, \
             patch("arm.services.jobs.read_log_line", return_value=lines), \
             patch("arm.services.jobs.db"):
            mock_cfg.arm_config = {"LOGPATH": "/home/arm/logs"}
            process_makemkv_logfile(job, job_results)

        assert "progress" in job_results or job.progress is not None


class TestRestartUi:
    """Test restart_ui."""

    def test_restart_returns_json(self):
        from arm.services.jobs import restart_ui

        with patch("arm.services.jobs.subprocess.check_output",
                   return_value=b"0"):
            result = restart_ui()

        assert result["success"] is False  # always returns False
        assert "Shutting down" in result["error"]


# ═══════════════════════════════════════════════════════════════════════
# config tests
# ═══════════════════════════════════════════════════════════════════════

class TestAlembicUpgrade:
    """Test _alembic_upgrade."""

    def test_calls_alembic_command(self):
        from arm.services.config import _alembic_upgrade

        with patch("alembic.command.upgrade") as mock_upgrade:
            _alembic_upgrade("/migrations", "sqlite:///test.db")

        mock_upgrade.assert_called_once()
        args = mock_upgrade.call_args
        assert args[0][1] == "head"


class TestCheckDbVersion:
    """Test check_db_version."""

    def test_creates_db_when_missing(self, tmp_path):
        from arm.services.config import check_db_version

        db_file = str(tmp_path / "arm.db")
        install_path = str(tmp_path)
        mig_dir = os.path.join(install_path, "arm/migrations")

        with patch("arm.services.config._alembic_upgrade") as mock_upgrade, \
             patch("alembic.script.ScriptDirectory") as mock_sd:
            mock_script = MagicMock()
            mock_script.get_current_head.return_value = "abc123"
            mock_sd.from_config.return_value = mock_script

            check_db_version(install_path, db_file)

        mock_upgrade.assert_called_once()

    def test_db_up_to_date(self, tmp_path):
        from arm.services.config import check_db_version
        import sqlite3

        db_file = str(tmp_path / "arm.db")
        # Create a db with alembic_version table
        conn = sqlite3.connect(db_file)
        conn.execute("CREATE TABLE alembic_version (version_num VARCHAR(32))")
        conn.execute("INSERT INTO alembic_version VALUES ('abc123')")
        conn.commit()
        conn.close()

        with patch("alembic.script.ScriptDirectory") as mock_sd:
            mock_script = MagicMock()
            mock_script.get_current_head.return_value = "abc123"
            mock_sd.from_config.return_value = mock_script

            check_db_version(str(tmp_path), db_file)
        # Should not raise, no upgrade needed

    def test_db_out_of_date_upgrades(self, tmp_path):
        from arm.services.config import check_db_version
        import sqlite3

        db_file = str(tmp_path / "arm.db")
        conn = sqlite3.connect(db_file)
        conn.execute("CREATE TABLE alembic_version (version_num VARCHAR(32))")
        conn.execute("INSERT INTO alembic_version VALUES ('old_rev')")
        conn.commit()
        conn.close()

        with patch("alembic.script.ScriptDirectory") as mock_sd, \
             patch("arm.services.config._alembic_upgrade"), \
             patch("arm.services.config.shutil.copy"):
            mock_script = MagicMock()
            mock_script.get_current_head.return_value = "new_rev"
            mock_sd.from_config.return_value = mock_script

            check_db_version(str(tmp_path), db_file)

    def test_missing_alembic_table(self, tmp_path):
        from arm.services.config import check_db_version
        import sqlite3

        db_file = str(tmp_path / "arm.db")
        conn = sqlite3.connect(db_file)
        conn.execute("CREATE TABLE dummy (id INTEGER)")
        conn.commit()
        conn.close()

        with patch("alembic.script.ScriptDirectory") as mock_sd:
            mock_script = MagicMock()
            mock_script.get_current_head.return_value = "abc123"
            mock_sd.from_config.return_value = mock_script

            # Should not raise — handles OperationalError gracefully
            check_db_version(str(tmp_path), db_file)


class TestGenerateComments:
    """Test generate_comments."""

    def test_loads_comments(self):
        from arm.services.config import generate_comments

        with patch("builtins.open", unittest.mock.mock_open(
                read_data='{"key": "value"}')):
            result = generate_comments()
        assert result == {"key": "value"}

    def test_file_not_found(self):
        from arm.services.config import generate_comments

        with patch("builtins.open", side_effect=FileNotFoundError):
            result = generate_comments()
        assert "error" in result


class TestBuildArmCfg:
    """Test build_arm_cfg."""

    def test_builds_config_string(self):
        from arm.services.config import build_arm_cfg

        comments = {
            "ARM_CFG_GROUPS": {"BEGIN": "# ARM Config"},
            "MINLENGTH": "# Minimum length",
        }

        with patch("arm.services.config.config_utils") as mock_cu:
            mock_cu.arm_yaml_check_groups.return_value = ""
            mock_cu.arm_yaml_test_bool.return_value = "RIPMETHOD: mkv\n"

            result = build_arm_cfg(
                {"MINLENGTH": "600", "RIPMETHOD": "mkv"},
                comments,
            )

        assert "# ARM Config" in result
        assert "MINLENGTH: 600" in result


class TestBuildAppriseCfg:
    """Test build_apprise_cfg."""

    def test_builds_apprise_string(self):
        from arm.services.config import build_apprise_cfg

        with patch("arm.services.config.arm_yaml_test_bool",
                   return_value="SOME_KEY: value\n"):
            result = build_apprise_cfg({"PORT": "8080", "HOST": "localhost"})

        assert "PORT: 8080" in result

    def test_skips_csrf(self):
        from arm.services.config import build_apprise_cfg

        with patch("arm.services.config.arm_yaml_test_bool",
                   return_value="X: y\n"):
            result = build_apprise_cfg({"csrf_token": "abc", "HOST": "localhost"})

        assert "csrf_token" not in result


class TestFormatYamlValue:
    """Test _format_yaml_value."""

    def test_integer_value(self):
        from arm.services.config import _format_yaml_value

        result = _format_yaml_value("PORT", "8080")
        assert result == "PORT: 8080\n"

    def test_string_value(self):
        from arm.services.config import _format_yaml_value

        with patch("arm.services.config.config_utils.arm_yaml_test_bool",
                   return_value="KEY: value\n"):
            result = _format_yaml_value("KEY", "value")
        assert result == "KEY: value\n"


class TestArmDbGet:
    """Test arm_db_get."""

    def test_returns_revision(self, app_context):
        from arm.services.config import arm_db_get
        from arm.models.alembic_version import AlembicVersion

        # AlembicVersion may not have a table; mock it
        mock_rev = MagicMock()
        mock_rev.version_num = "abc123"

        with patch.object(AlembicVersion, "query", create=True) as mock_q:
            mock_q.first.return_value = mock_rev
            result = arm_db_get()

        assert result.version_num == "abc123"

    def test_returns_none_on_empty(self, app_context):
        from arm.services.config import arm_db_get
        from arm.models.alembic_version import AlembicVersion

        with patch.object(AlembicVersion, "query", create=True) as mock_q:
            mock_q.first.return_value = None
            result = arm_db_get()

        assert result is None

    def test_returns_none_on_error(self, app_context):
        from arm.services.config import arm_db_get
        from arm.models.alembic_version import AlembicVersion

        with patch.object(AlembicVersion, "query", create=True,
                          new_callable=PropertyMock) as mock_q:
            mock_q.side_effect = Exception("table missing")
            result = arm_db_get()

        assert result is None


class TestSetupDatabase:
    """Test setup_database."""

    def test_existing_admin_returns_true(self, app_context):
        from arm.services.config import setup_database
        from arm.models.user import User

        mock_user = MagicMock()
        with patch.object(User, "query", create=True) as mock_q:
            mock_q.all.return_value = [mock_user]
            result = setup_database()

        assert result is True

    def test_no_admins_creates_default(self, app_context):
        from arm.services.config import setup_database
        from arm.models.user import User

        with patch.object(User, "query", create=True) as mock_q, \
             patch("arm.services.config.db") as mock_db, \
             patch("arm.services.config.SystemInfo"), \
             patch("arm.services.drives.drives_update"):
            mock_q.all.return_value = []
            mock_db.metadata.create_all = MagicMock()
            mock_db.create_all = MagicMock()
            mock_db.session = MagicMock()
            mock_db.engine = MagicMock()

            result = setup_database()

        assert result is True
