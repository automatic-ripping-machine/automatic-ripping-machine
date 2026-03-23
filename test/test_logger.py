"""Tests for arm.ripper.logger — structlog-based structured logging."""

import json
import logging
import os
import unittest.mock

import pytest
import structlog

from arm.ripper import logger


@pytest.fixture(autouse=True)
def _clean_handlers():
    """Remove all handlers from root + ARM loggers after each test."""
    yield
    for name in (None, "ARM"):
        log = logging.getLogger(name)
        log.handlers.clear()
    structlog.contextvars.clear_contextvars()


@pytest.fixture
def log_dir(tmp_path):
    """Provide a temp log directory and patch LOGPATH."""
    with unittest.mock.patch.dict(
        "arm.config.config.arm_config",
        {"LOGPATH": str(tmp_path), "LOGLEVEL": "DEBUG"},
    ):
        yield tmp_path


def test_json_file_output(log_dir):
    """FileHandler produces valid JSON lines with expected keys."""
    arm_logger = logger.create_early_logger(stdout=False, syslog=False, file=True)
    arm_logger.info("test message")

    log_file = log_dir / "arm.log"
    assert log_file.exists()

    lines = [l for l in log_file.read_text().splitlines() if l.strip()]
    assert len(lines) >= 1

    parsed = json.loads(lines[-1])
    assert parsed["event"] == "test message"
    assert parsed["level"] == "info"
    assert "timestamp" in parsed


def test_console_stdout(log_dir, capsys):
    """StreamHandler produces human-readable output (not JSON)."""
    arm_logger = logger.create_early_logger(stdout=True, syslog=False, file=False)
    arm_logger.info("console test")

    captured = capsys.readouterr()
    assert "console test" in captured.err  # StreamHandler defaults to stderr


def test_contextvars_binding(log_dir):
    """After binding contextvars, job_id/label/devpath appear in JSON output."""
    arm_logger = logger.create_early_logger(stdout=False, syslog=False, file=True)

    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        job_id=42, label="LOTR", devpath="/dev/sr0"
    )
    arm_logger.info("ripping title 1")

    log_file = log_dir / "arm.log"
    lines = [l for l in log_file.read_text().splitlines() if l.strip()]
    parsed = json.loads(lines[-1])

    assert parsed["job_id"] == 42
    assert parsed["label"] == "LOTR"
    assert parsed["devpath"] == "/dev/sr0"
    assert parsed["event"] == "ripping title 1"


def test_setup_job_log_swaps_handler(log_dir):
    """setup_job_log() replaces FileHandler with per-job file."""
    arm_logger = logger.create_early_logger(stdout=False, syslog=False, file=True)

    # Create a mock job
    job = unittest.mock.MagicMock()
    job.label = "TEST_DISC"
    job.stage = "rip"
    job.disctype = "bluray"
    job.job_id = 7
    job.devpath = "/dev/sr1"

    log_full = logger.setup_job_log(job)

    assert job.logfile == "TEST_DISC.log"
    assert log_full == os.path.join(str(log_dir), "TEST_DISC.log")

    # Now log something — should go to the per-job file, not arm.log
    arm_logger.info("per-job message")

    job_log = log_dir / "TEST_DISC.log"
    assert job_log.exists()

    lines = [l for l in job_log.read_text().splitlines() if l.strip()]
    assert len(lines) >= 1

    parsed = json.loads(lines[-1])
    assert parsed["event"] == "per-job message"
    assert parsed["job_id"] == 7
    assert parsed["label"] == "TEST_DISC"


def test_stdlib_compatibility(log_dir):
    """Standard logging.getLogger(__name__).info() calls produce structured JSON."""
    logger.create_early_logger(stdout=False, syslog=False, file=True)

    # Simulate what a random ARM module does
    stdlib_logger = logging.getLogger("arm.ripper.makemkv")
    stdlib_logger.info("Ripping title 3")

    log_file = log_dir / "arm.log"
    lines = [l for l in log_file.read_text().splitlines() if l.strip()]
    assert len(lines) >= 1

    parsed = json.loads(lines[-1])
    assert parsed["event"] == "Ripping title 3"
    assert parsed["level"] == "info"
    assert "logger" in parsed


def test_log_filename_format():
    """log_filename() returns JOB_{id}_Rip.log"""
    from arm.ripper.logger import log_filename
    assert log_filename(42) == "JOB_42_Rip.log"
    assert log_filename(1) == "JOB_1_Rip.log"
    assert log_filename(9999) == "JOB_9999_Rip.log"


def test_clean_up_logs(log_dir):
    """clean_up_logs() deletes old files, keeps recent ones."""
    old_log = log_dir / "old_job.log"
    old_log.write_text("old data")
    # Set mtime to 100 days ago
    old_time = os.path.getmtime(str(old_log)) - (100 * 86400)
    os.utime(str(old_log), (old_time, old_time))

    new_log = log_dir / "new_job.log"
    new_log.write_text("new data")

    logger.create_early_logger(stdout=False, syslog=False, file=False)
    result = logger.clean_up_logs(str(log_dir), loglife=30)

    assert result is True
    assert not old_log.exists()
    assert new_log.exists()


def test_clean_up_logs_disabled(log_dir):
    """clean_up_logs() with loglife=0 does nothing."""
    log_file = log_dir / "keep.log"
    log_file.write_text("keep me")

    logger.create_early_logger(stdout=False, syslog=False, file=False)
    result = logger.clean_up_logs(str(log_dir), loglife=0)

    assert result is False
    assert log_file.exists()
