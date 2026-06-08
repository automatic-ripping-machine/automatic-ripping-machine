"""Tests for arm/api/v1/logs.py - log REST endpoints + log_parser service."""
import unittest.mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from arm.services import log_parser


@pytest.fixture
def logs_client(tmp_path):
    from arm.api.v1.logs import router
    app = FastAPI()
    app.include_router(router)
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    with unittest.mock.patch("arm.config.config.arm_config", {"LOGPATH": str(log_dir)}):
        with TestClient(app) as c:
            yield c, log_dir


class TestJobLog:
    """Pre-existing /jobs/{id}/log endpoint - covered here so the new
    test file owns the whole router's coverage."""

    def test_delegates_to_svc_jobs(self, logs_client):
        client, _ = logs_client
        with unittest.mock.patch(
            "arm.api.v1.logs.svc_jobs.generate_log",
            return_value={"success": True, "job": "1", "log": "ok"},
        ) as mock:
            resp = client.get("/api/v1/jobs/1/log")
        assert resp.status_code == 200
        assert resp.json()["log"] == "ok"
        mock.assert_called_once()


class TestListLogs:
    def test_lists_log_files_newest_first(self, logs_client):
        client, log_dir = logs_client
        old = log_dir / "old.log"
        new = log_dir / "new.log"
        old.write_text("aaa")
        new.write_text("bbb")
        # Force mtime ordering (filesystem may give same-second writes)
        import os
        os.utime(old, (1000, 1000))
        os.utime(new, (2000, 2000))

        resp = client.get("/api/v1/logs")
        assert resp.status_code == 200
        data = resp.json()
        names = [e["filename"] for e in data]
        assert names == ["new.log", "old.log"]
        assert data[0]["size"] == 3
        assert "modified" in data[0]

    def test_skips_non_log_files(self, logs_client):
        client, log_dir = logs_client
        (log_dir / "a.log").write_text("x")
        (log_dir / "b.txt").write_text("y")
        resp = client.get("/api/v1/logs")
        names = [e["filename"] for e in resp.json()]
        assert names == ["a.log"]

    def test_missing_logdir_returns_empty(self, tmp_path):
        from arm.api.v1.logs import router
        app = FastAPI()
        app.include_router(router)
        missing = tmp_path / "nope"
        with unittest.mock.patch("arm.config.config.arm_config", {"LOGPATH": str(missing)}):
            with TestClient(app) as c:
                resp = c.get("/api/v1/logs")
        assert resp.status_code == 200
        assert resp.json() == []


class TestReadLog:
    def test_tail_returns_last_n_lines(self, logs_client):
        client, log_dir = logs_client
        (log_dir / "x.log").write_text("\n".join(f"line{i}" for i in range(10)) + "\n")
        resp = client.get("/api/v1/logs/x.log", params={"mode": "tail", "lines": 3})
        assert resp.status_code == 200
        body = resp.json()
        assert body["filename"] == "x.log"
        assert body["lines"] == 3
        assert body["content"] == "line7\nline8\nline9\n"
        assert body["truncated"] is False

    def test_full_returns_whole_file(self, logs_client):
        client, log_dir = logs_client
        (log_dir / "x.log").write_text("a\nb\nc\n")
        resp = client.get("/api/v1/logs/x.log", params={"mode": "full"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["content"] == "a\nb\nc\n"
        assert body["truncated"] is False

    def test_full_caps_at_max_bytes(self, logs_client, monkeypatch):
        client, log_dir = logs_client
        monkeypatch.setattr(log_parser, "_FULL_MODE_MAX_BYTES", 100)
        # File is 230 bytes; we keep the last 100. The first newline inside
        # those 100 bytes splits a partial y-line away from the trailing zzz.
        big = ("x" * 200) + "\n" + ("y" * 20) + "\n" + "zzz\n"
        (log_dir / "big.log").write_text(big)
        resp = client.get("/api/v1/logs/big.log", params={"mode": "full"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["truncated"] is True
        assert "zzz" in body["content"]
        # Partial first line (some y's) is dropped, x-line never reaches us
        assert "x" * 200 not in body["content"]

    def test_missing_file_404(self, logs_client):
        client, _ = logs_client
        resp = client.get("/api/v1/logs/nope.log")
        assert resp.status_code == 404

    def test_traversal_rejected(self, logs_client, tmp_path):
        client, _ = logs_client
        outside = tmp_path / "secret.log"
        outside.write_text("sensitive")
        # The path component "../secret.log" is stripped to basename
        # "secret.log" which doesn't exist in LOGPATH.
        resp = client.get("/api/v1/logs/..%2Fsecret.log")
        assert resp.status_code == 404
        assert outside.exists()


class TestStructuredLog:
    def test_parses_arm_plain_format(self, logs_client):
        client, log_dir = logs_client
        (log_dir / "x.log").write_text(
            "02-28-2026 04:59:16 ARM: INFO: Started\n"
            "02-28-2026 04:59:17 ARM: ERROR: Crashed\n"
        )
        resp = client.get("/api/v1/logs/x.log/structured")
        assert resp.status_code == 200
        entries = resp.json()["entries"]
        assert len(entries) == 2
        assert entries[0]["level"] == "info"
        assert entries[0]["event"] == "Started"
        assert entries[1]["level"] == "error"

    def test_level_filter(self, logs_client):
        client, log_dir = logs_client
        (log_dir / "x.log").write_text(
            "02-28-2026 04:59:16 ARM: INFO: Hello\n"
            "02-28-2026 04:59:17 ARM: ERROR: Boom\n"
        )
        resp = client.get("/api/v1/logs/x.log/structured", params={"level": "error"})
        entries = resp.json()["entries"]
        assert len(entries) == 1
        assert entries[0]["event"] == "Boom"

    def test_search_filter(self, logs_client):
        client, log_dir = logs_client
        (log_dir / "x.log").write_text(
            "02-28-2026 04:59:16 ARM: INFO: ripping disc\n"
            "02-28-2026 04:59:17 ARM: INFO: ejecting drive\n"
        )
        resp = client.get("/api/v1/logs/x.log/structured", params={"search": "rip"})
        entries = resp.json()["entries"]
        assert len(entries) == 1
        assert "ripping" in entries[0]["event"]

    def test_missing_file_404(self, logs_client):
        client, _ = logs_client
        resp = client.get("/api/v1/logs/nope.log/structured")
        assert resp.status_code == 404


class TestDownloadLog:
    def test_streams_file(self, logs_client):
        client, log_dir = logs_client
        (log_dir / "x.log").write_text("hello world\n")
        resp = client.get("/api/v1/logs/x.log/download")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/plain")
        assert resp.text == "hello world\n"

    def test_missing_file_404(self, logs_client):
        client, _ = logs_client
        resp = client.get("/api/v1/logs/nope.log/download")
        assert resp.status_code == 404


class TestDeleteLog:
    def test_deletes_file(self, logs_client):
        client, log_dir = logs_client
        target = log_dir / "x.log"
        target.write_text("bye")
        resp = client.delete("/api/v1/logs/x.log")
        assert resp.status_code == 200
        assert resp.json() == {"success": True, "filename": "x.log"}
        assert not target.exists()

    def test_missing_file_404(self, logs_client):
        client, _ = logs_client
        resp = client.delete("/api/v1/logs/nope.log")
        assert resp.status_code == 404

    def test_traversal_rejected(self, logs_client, tmp_path):
        client, _ = logs_client
        outside = tmp_path / "secret.log"
        outside.write_text("sensitive")
        resp = client.delete("/api/v1/logs/..%2Fsecret.log")
        assert resp.status_code == 404
        assert outside.exists()


class TestLogParserUnit:
    def test_parse_json_line(self):
        line = '{"timestamp": "t", "level": "warning", "logger": "lg", "event": "hi"}'
        result = log_parser._parse_log_line(line)
        assert result["level"] == "warning"
        assert result["event"] == "hi"

    def test_parse_iso_bracket(self):
        line = "2026-03-20 14:24:48 [rescan_drive] No disc in /dev/sr0"
        result = log_parser._parse_log_line(line)
        assert result["timestamp"] == "2026-03-20 14:24:48"
        assert result["logger"] == "rescan_drive"
        assert result["event"] == "No disc in /dev/sr0"

    def test_parse_wrapper_bracket(self):
        line = "Sun Mar  1 04:34:15 EST 2026 [ARM] Starting ARM for DVD on sr0"
        result = log_parser._parse_log_line(line)
        assert result["logger"] == "ARM"
        assert "Starting" in result["event"]

    def test_parse_fallback(self):
        line = "totally unstructured garbage"
        result = log_parser._parse_log_line(line)
        assert result["event"] == line
        assert result["level"] == "info"

    def test_parse_wrapper_plain(self):
        """Wrapper-script format without [LOGGER] tag falls through to the plain branch."""
        line = "Sun Mar  1 04:34:15 EST 2026 Entering docker wrapper"
        result = log_parser._parse_log_line(line)
        assert result["logger"] == "wrapper"
        assert "Entering" in result["event"]

    def test_resolve_within_oserror_returns_none(self, monkeypatch, tmp_path):
        import os
        from pathlib import Path

        def boom(*a, **kw):
            raise OSError("disk gone")

        # _resolve_within now confines via arm.common.path_safety.safe_join,
        # which resolves paths with os.path.realpath rather than Path.resolve.
        monkeypatch.setattr(os.path, "realpath", boom)
        assert log_parser._resolve_within("x.log", Path(tmp_path)) is None

    def test_parse_oversized_line_skipped(self):
        """Defends the parser against catastrophic input (CodeQL py/polynomial-redos)."""
        line = "a" + " " * 50000  # leading-space ReDoS attack shape
        # Must complete instantly and return something safe.
        result = log_parser._parse_log_line(line)
        assert result["raw"] == line
        # Truncated event (the parser bails before regex)
        assert "..." in result["event"]

    def test_resolve_within_strips_traversal(self, tmp_path):
        from pathlib import Path
        result = log_parser._resolve_within("../escape", Path(tmp_path))
        # basename "escape" - file doesn't exist but resolution stays in root
        assert result is not None
        assert result.parent == tmp_path.resolve()

    def test_resolve_within_rejects_dotdot_only(self, tmp_path):
        from pathlib import Path
        assert log_parser._resolve_within("..", Path(tmp_path)) is None
        assert log_parser._resolve_within(".", Path(tmp_path)) is None
        assert log_parser._resolve_within("", Path(tmp_path)) is None

    def test_delete_oserror_returns_false(self, tmp_path, monkeypatch):
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        target = log_dir / "x.log"
        target.write_text("x")
        monkeypatch.setattr(
            "arm.config.config.arm_config", {"LOGPATH": str(log_dir)}
        )

        def boom(self):
            raise OSError("nope")

        from pathlib import Path
        monkeypatch.setattr(Path, "unlink", boom)
        assert log_parser.delete_log("x.log") is False

    def test_read_oserror_returns_none(self, tmp_path, monkeypatch):
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        target = log_dir / "x.log"
        target.write_text("x")
        monkeypatch.setattr(
            "arm.config.config.arm_config", {"LOGPATH": str(log_dir)}
        )

        import builtins
        real_open = builtins.open

        def boom(path, *a, **kw):
            if str(path).endswith("x.log"):
                raise OSError("nope")
            return real_open(path, *a, **kw)

        monkeypatch.setattr(builtins, "open", boom)
        assert log_parser.read_log("x.log") is None
