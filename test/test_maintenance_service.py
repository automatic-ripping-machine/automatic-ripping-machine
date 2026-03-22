"""Tests for arm/services/maintenance.py — orphan detection and cleanup."""
import os
import unittest.mock

import pytest

from arm.database import db
from arm.models.job import Job


@pytest.fixture
def tmp_logs(tmp_path):
    """Create a temporary log directory with test log files."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "orphan1.log").write_text("log content")
    (log_dir / "orphan2.log").write_text("log content")
    (log_dir / "referenced.log").write_text("log content")
    (log_dir / "not-a-log.txt").write_text("ignored")
    return log_dir


@pytest.fixture
def tmp_media(tmp_path):
    """Create temporary raw and completed directories with test folders."""
    raw = tmp_path / "raw"
    completed = tmp_path / "completed" / "movies"
    raw.mkdir()
    completed.mkdir(parents=True)
    (raw / "Orphan Movie").mkdir()
    (raw / "Orphan Movie" / "title.mkv").write_bytes(b"\x00" * 1024)
    (raw / "SERIAL_MOM").mkdir()  # matches sample_job.title
    (completed / "Another Orphan").mkdir()
    return {"raw": str(raw), "completed": str(tmp_path / "completed")}


class TestOrphanLogDetection:
    def test_finds_orphan_logs(self, app_context, sample_job, tmp_logs):
        """Logs not referenced by any job are orphans."""
        sample_job.logfile = "referenced.log"
        db.session.commit()

        with unittest.mock.patch("arm.config.config.arm_config", {"LOGPATH": str(tmp_logs)}):
            from arm.services.maintenance import get_orphan_logs
            result = get_orphan_logs()

        assert result["root"] == str(tmp_logs)
        names = [f["relative_path"] for f in result["files"]]
        assert "orphan1.log" in names
        assert "orphan2.log" in names
        assert "referenced.log" not in names
        assert "not-a-log.txt" not in names

    def test_returns_file_sizes(self, app_context, sample_job, tmp_logs):
        sample_job.logfile = "referenced.log"
        db.session.commit()

        with unittest.mock.patch("arm.config.config.arm_config", {"LOGPATH": str(tmp_logs)}):
            from arm.services.maintenance import get_orphan_logs
            result = get_orphan_logs()

        for f in result["files"]:
            assert isinstance(f["size_bytes"], int)
            assert f["size_bytes"] > 0
        assert isinstance(result["total_size_bytes"], int)

    def test_empty_log_dir(self, app_context, tmp_path):
        log_dir = tmp_path / "empty_logs"
        log_dir.mkdir()
        with unittest.mock.patch("arm.config.config.arm_config", {"LOGPATH": str(log_dir)}):
            from arm.services.maintenance import get_orphan_logs
            result = get_orphan_logs()
        assert result["files"] == []
        assert result["total_size_bytes"] == 0


class TestOrphanFolderDetection:
    def test_finds_orphan_folders(self, app_context, sample_job, tmp_media):
        """Folders not matching any job title/label/raw_path are orphans."""
        mock_cfg = {
            "RAW_PATH": tmp_media["raw"],
            "COMPLETED_PATH": tmp_media["completed"],
        }
        with unittest.mock.patch("arm.config.config.arm_config", mock_cfg):
            from arm.services.maintenance import get_orphan_folders
            result = get_orphan_folders()

        names = [f["name"] for f in result["folders"]]
        assert "Orphan Movie" in names
        assert "Another Orphan" in names
        assert "SERIAL_MOM" not in names  # matches sample_job.title

    def test_categorizes_raw_and_completed(self, app_context, sample_job, tmp_media):
        mock_cfg = {
            "RAW_PATH": tmp_media["raw"],
            "COMPLETED_PATH": tmp_media["completed"],
        }
        with unittest.mock.patch("arm.config.config.arm_config", mock_cfg):
            from arm.services.maintenance import get_orphan_folders
            result = get_orphan_folders()

        categories = {f["name"]: f["category"] for f in result["folders"]}
        assert categories.get("Orphan Movie") == "raw"
        assert categories.get("Another Orphan") == "completed"

    def test_computes_folder_sizes(self, app_context, sample_job, tmp_media):
        mock_cfg = {
            "RAW_PATH": tmp_media["raw"],
            "COMPLETED_PATH": tmp_media["completed"],
        }
        with unittest.mock.patch("arm.config.config.arm_config", mock_cfg):
            from arm.services.maintenance import get_orphan_folders
            result = get_orphan_folders()

        orphan_movie = next(f for f in result["folders"] if f["name"] == "Orphan Movie")
        assert orphan_movie["size_bytes"] >= 1024  # has a 1KB file inside
        assert isinstance(result["total_size_bytes"], int)


class TestMaintenanceCounts:
    def test_returns_counts(self, app_context, sample_job, tmp_logs, tmp_media):
        sample_job.logfile = "referenced.log"
        db.session.commit()

        mock_cfg = {
            "LOGPATH": str(tmp_logs),
            "RAW_PATH": tmp_media["raw"],
            "COMPLETED_PATH": tmp_media["completed"],
        }
        with unittest.mock.patch("arm.config.config.arm_config", mock_cfg):
            from arm.services.maintenance import get_counts
            result = get_counts()

        assert result["orphan_logs"] == 2
        assert result["orphan_folders"] >= 2  # Orphan Movie + Another Orphan
