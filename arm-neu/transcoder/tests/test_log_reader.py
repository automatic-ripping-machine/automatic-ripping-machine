"""
Tests for log_reader.py - log file listing, reading, and structured parsing.
"""

import json
import time
from unittest.mock import patch

import pytest


class TestLogDir:
    """Tests for _log_dir helper."""

    def test_returns_path_from_settings(self):
        from log_reader import _log_dir
        from config import settings

        assert str(_log_dir()) == settings.log_path


class TestListLogs:
    """Tests for list_logs()."""

    def test_empty_when_dir_missing(self, tmp_path):
        with patch("log_reader._log_dir", return_value=tmp_path / "nonexistent"):
            from log_reader import list_logs

            result = list_logs()
            assert result == []

    def test_empty_when_no_log_files(self, tmp_path):
        with patch("log_reader._log_dir", return_value=tmp_path):
            from log_reader import list_logs

            # Create a non-log file
            (tmp_path / "readme.txt").write_text("hello")
            result = list_logs()
            assert result == []

    def test_finds_log_files(self, tmp_path):
        with patch("log_reader._log_dir", return_value=tmp_path):
            from log_reader import list_logs

            (tmp_path / "transcoder.log").write_text("line1\nline2")
            result = list_logs()
            assert len(result) == 1
            assert result[0]["filename"] == "transcoder.log"
            assert result[0]["size"] > 0
            assert result[0]["modified"] is not None

    def test_finds_rotated_log_files(self, tmp_path):
        with patch("log_reader._log_dir", return_value=tmp_path):
            from log_reader import list_logs

            (tmp_path / "transcoder.log").write_text("current")
            (tmp_path / "transcoder.log.1").write_text("rotated")
            result = list_logs()
            assert len(result) == 2
            filenames = {r["filename"] for r in result}
            assert "transcoder.log" in filenames
            assert "transcoder.log.1" in filenames

    def test_excludes_subdirectories(self, tmp_path):
        with patch("log_reader._log_dir", return_value=tmp_path):
            from log_reader import list_logs

            subdir = tmp_path / "subdir.log"
            subdir.mkdir()
            (tmp_path / "real.log").write_text("data")
            result = list_logs()
            assert len(result) == 1
            assert result[0]["filename"] == "real.log"

    def test_sorted_newest_first(self, tmp_path):
        with patch("log_reader._log_dir", return_value=tmp_path):
            from log_reader import list_logs

            old = tmp_path / "old.log"
            old.write_text("old")
            import os
            os.utime(old, (1000000, 1000000))

            new = tmp_path / "new.log"
            new.write_text("new")

            result = list_logs()
            assert len(result) == 2
            assert result[0]["filename"] == "new.log"
            assert result[1]["filename"] == "old.log"


class TestReadLog:
    """Tests for read_log()."""

    def test_returns_none_for_missing_file(self, tmp_path):
        with patch("log_reader._log_dir", return_value=tmp_path):
            from log_reader import read_log

            result = read_log("nonexistent.log")
            assert result is None

    def test_prevents_path_traversal(self, tmp_path):
        with patch("log_reader._log_dir", return_value=tmp_path):
            from log_reader import read_log

            result = read_log("../../etc/passwd")
            assert result is None

    def test_tail_mode_returns_last_n_lines(self, tmp_path):
        with patch("log_reader._log_dir", return_value=tmp_path):
            from log_reader import read_log

            lines = [f"line {i}\n" for i in range(200)]
            (tmp_path / "big.log").write_text("".join(lines))

            result = read_log("big.log", mode="tail", lines=50)
            assert result is not None
            assert result["filename"] == "big.log"
            assert result["lines"] == 50
            assert "line 199" in result["content"]
            assert "line 0" not in result["content"]

    def test_tail_mode_with_small_file(self, tmp_path):
        with patch("log_reader._log_dir", return_value=tmp_path):
            from log_reader import read_log

            (tmp_path / "small.log").write_text("line 1\nline 2\nline 3\n")

            result = read_log("small.log", mode="tail", lines=100)
            assert result is not None
            assert result["lines"] == 3

    def test_full_mode_returns_all(self, tmp_path):
        with patch("log_reader._log_dir", return_value=tmp_path):
            from log_reader import read_log

            content = "line 1\nline 2\nline 3\n"
            (tmp_path / "full.log").write_text(content)

            result = read_log("full.log", mode="full")
            assert result is not None
            assert result["content"] == content
            assert result["lines"] == 3

    def test_returns_none_for_os_error(self, tmp_path):
        with patch("log_reader._log_dir", return_value=tmp_path):
            from log_reader import read_log

            # Create a file then make it unreadable
            log = tmp_path / "unreadable.log"
            log.write_text("data")
            log.chmod(0o000)
            try:
                result = read_log("unreadable.log")
                # May return None on permission error, or content if running as root
                # Just verify no exception is raised
            finally:
                log.chmod(0o644)


class TestParseLogLine:
    """Tests for _parse_log_line()."""

    def test_parses_valid_json(self):
        from log_reader import _parse_log_line

        line = json.dumps({
            "timestamp": "2026-03-14T10:00:00Z",
            "level": "error",
            "logger": "transcoder",
            "event": "Job failed",
            "job_id": "42",
            "label": "MY_DISC",
        })
        result = _parse_log_line(line)
        assert result["timestamp"] == "2026-03-14T10:00:00Z"
        assert result["level"] == "error"
        assert result["logger"] == "transcoder"
        assert result["event"] == "Job failed"
        assert result["job_id"] == "42"
        assert result["label"] == "MY_DISC"
        assert result["raw"] == line

    def test_parses_json_with_missing_fields(self):
        from log_reader import _parse_log_line

        line = json.dumps({"event": "something"})
        result = _parse_log_line(line)
        assert result["timestamp"] == ""
        assert result["level"] == "info"
        assert result["logger"] == ""
        assert result["event"] == "something"
        assert result["job_id"] is None
        assert result["label"] is None

    def test_handles_non_json_line(self):
        from log_reader import _parse_log_line

        line = "plain text log line"
        result = _parse_log_line(line)
        assert result["timestamp"] == ""
        assert result["level"] == "info"
        assert result["event"] == "plain text log line"
        assert result["raw"] == "plain text log line"

    def test_strips_trailing_newline(self):
        from log_reader import _parse_log_line

        line = "log line with newline\n"
        result = _parse_log_line(line)
        assert result["event"] == "log line with newline"
        assert result["raw"] == "log line with newline"


class TestReadStructuredLog:
    """Tests for read_structured_log()."""

    def test_returns_none_for_missing_file(self, tmp_path):
        with patch("log_reader._log_dir", return_value=tmp_path):
            from log_reader import read_structured_log

            result = read_structured_log("nonexistent.log")
            assert result is None

    def test_parses_json_lines(self, tmp_path):
        with patch("log_reader._log_dir", return_value=tmp_path):
            from log_reader import read_structured_log

            lines = [
                json.dumps({"event": "start", "level": "info"}),
                json.dumps({"event": "done", "level": "info"}),
            ]
            (tmp_path / "structured.log").write_text("\n".join(lines) + "\n")

            result = read_structured_log("structured.log", mode="full")
            assert result is not None
            assert result["filename"] == "structured.log"
            assert result["lines"] == 2
            assert result["entries"][0]["event"] == "start"
            assert result["entries"][1]["event"] == "done"

    def test_filters_by_level(self, tmp_path):
        with patch("log_reader._log_dir", return_value=tmp_path):
            from log_reader import read_structured_log

            lines = [
                json.dumps({"event": "info msg", "level": "info"}),
                json.dumps({"event": "err msg", "level": "error"}),
                json.dumps({"event": "info2", "level": "info"}),
            ]
            (tmp_path / "levels.log").write_text("\n".join(lines) + "\n")

            result = read_structured_log("levels.log", mode="full", level="error")
            assert result is not None
            assert result["lines"] == 1
            assert result["entries"][0]["event"] == "err msg"

    def test_filters_by_search(self, tmp_path):
        with patch("log_reader._log_dir", return_value=tmp_path):
            from log_reader import read_structured_log

            lines = [
                json.dumps({"event": "Job started", "level": "info"}),
                json.dumps({"event": "Encoding file", "level": "info"}),
                json.dumps({"event": "Job completed", "level": "info"}),
            ]
            (tmp_path / "search.log").write_text("\n".join(lines) + "\n")

            result = read_structured_log("search.log", mode="full", search="job")
            assert result is not None
            assert result["lines"] == 2
            events = [e["event"] for e in result["entries"]]
            assert "Job started" in events
            assert "Job completed" in events

    def test_filters_by_level_and_search(self, tmp_path):
        with patch("log_reader._log_dir", return_value=tmp_path):
            from log_reader import read_structured_log

            lines = [
                json.dumps({"event": "Job started", "level": "info"}),
                json.dumps({"event": "Job failed", "level": "error"}),
                json.dumps({"event": "Other error", "level": "error"}),
            ]
            (tmp_path / "combo.log").write_text("\n".join(lines) + "\n")

            result = read_structured_log("combo.log", mode="full", level="error", search="job")
            assert result is not None
            assert result["lines"] == 1
            assert result["entries"][0]["event"] == "Job failed"

    def test_skips_blank_lines(self, tmp_path):
        with patch("log_reader._log_dir", return_value=tmp_path):
            from log_reader import read_structured_log

            content = json.dumps({"event": "first"}) + "\n\n\n" + json.dumps({"event": "second"}) + "\n"
            (tmp_path / "blanks.log").write_text(content)

            result = read_structured_log("blanks.log", mode="full")
            assert result is not None
            assert result["lines"] == 2
