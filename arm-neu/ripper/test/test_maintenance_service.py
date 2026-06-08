"""Tests for arm/services/maintenance.py — orphan detection and cleanup."""
import os
import unittest.mock

import pytest

from arm.database import db
from arm.models.job import Job


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

    def test_returns_roots(self, app_context, sample_job, tmp_media):
        """Result includes both scanned roots for parity with orphan-logs."""
        mock_cfg = {
            "RAW_PATH": tmp_media["raw"],
            "COMPLETED_PATH": tmp_media["completed"],
        }
        with unittest.mock.patch("arm.config.config.arm_config", mock_cfg):
            from arm.services.maintenance import get_orphan_folders
            result = get_orphan_folders()

        assert result["roots"] == [tmp_media["raw"], tmp_media["completed"]]

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


class TestDeleteShapeInvariants:
    """Wire shapes for delete_log/delete_folder must be invariant across success/failure."""

    def test_delete_log_success_includes_error_none(self, app_context, tmp_logs):
        with unittest.mock.patch("arm.config.config.arm_config", {"LOGPATH": str(tmp_logs)}):
            from arm.services.maintenance import delete_log
            result = delete_log("orphan1.log")

        assert result["success"] is True
        assert result["path"] == "orphan1.log"
        assert result["error"] is None
        assert set(result.keys()) == {"success", "path", "error"}

    def test_delete_log_failure_keys_match(self, app_context, tmp_logs):
        with unittest.mock.patch("arm.config.config.arm_config", {"LOGPATH": str(tmp_logs)}):
            from arm.services.maintenance import delete_log
            result = delete_log("does-not-exist.log")

        assert result["success"] is False
        assert isinstance(result["error"], str)
        assert set(result.keys()) == {"success", "path", "error"}

    def test_delete_folder_success_includes_error_none(self, app_context, tmp_media):
        mock_cfg = {
            "RAW_PATH": tmp_media["raw"],
            "COMPLETED_PATH": tmp_media["completed"],
        }
        with unittest.mock.patch("arm.config.config.arm_config", mock_cfg):
            from arm.services.maintenance import delete_folder
            result = delete_folder("Orphan Movie")

        assert result["success"] is True
        assert result["error"] is None
        assert set(result.keys()) == {"success", "path", "error"}


class TestBulkDeleteShapeInvariants:
    """Bulk endpoints carry success: bool for sibling consistency."""

    def test_bulk_delete_logs_all_success(self, app_context, tmp_logs):
        with unittest.mock.patch("arm.config.config.arm_config", {"LOGPATH": str(tmp_logs)}):
            from arm.services.maintenance import bulk_delete_logs
            result = bulk_delete_logs(["orphan1.log", "orphan2.log"])

        assert result["success"] is True
        assert result["removed"] == ["orphan1.log", "orphan2.log"]
        assert result["errors"] == []
        assert set(result.keys()) == {"success", "removed", "errors"}

    def test_bulk_delete_logs_partial_failure(self, app_context, tmp_logs):
        with unittest.mock.patch("arm.config.config.arm_config", {"LOGPATH": str(tmp_logs)}):
            from arm.services.maintenance import bulk_delete_logs
            result = bulk_delete_logs(["orphan1.log", "missing.log"])

        assert result["success"] is False
        assert result["removed"] == ["orphan1.log"]
        assert len(result["errors"]) == 1

    def test_bulk_delete_folders_all_success(self, app_context, tmp_media):
        mock_cfg = {
            "RAW_PATH": tmp_media["raw"],
            "COMPLETED_PATH": tmp_media["completed"],
        }
        with unittest.mock.patch("arm.config.config.arm_config", mock_cfg):
            from arm.services.maintenance import bulk_delete_folders
            result = bulk_delete_folders(["Orphan Movie"])

        assert result["success"] is True
        assert "Orphan Movie" in result["removed"]
        assert result["errors"] == []


class TestClearRawDirectories:
    def test_clears_files_and_dirs(self, tmp_path):
        """Should remove all contents of RAW_PATH and report counts."""
        raw = tmp_path / "raw"
        raw.mkdir()
        (raw / "file1.mkv").write_bytes(b"x" * 1000)
        (raw / "file2.mkv").write_bytes(b"y" * 2000)
        subdir = raw / "job_123"
        subdir.mkdir()
        (subdir / "track.mkv").write_bytes(b"z" * 500)

        with unittest.mock.patch("arm.config.config.arm_config", {"RAW_PATH": str(raw)}):
            from arm.services.maintenance import clear_raw_directories
            result = clear_raw_directories()

        assert result["success"] is True
        assert result["cleared"] == 3  # 2 files + 1 dir
        assert result["freed_bytes"] == 3500
        assert result["path"] == str(raw)
        assert result["errors"] == []
        assert result["error"] is None
        # Directory itself still exists, but empty
        assert raw.is_dir()
        assert list(raw.iterdir()) == []

    def test_empty_raw_succeeds(self, tmp_path):
        """Empty RAW_PATH should succeed with zero counts."""
        raw = tmp_path / "raw"
        raw.mkdir()

        with unittest.mock.patch("arm.config.config.arm_config", {"RAW_PATH": str(raw)}):
            from arm.services.maintenance import clear_raw_directories
            result = clear_raw_directories()

        assert result["success"] is True
        assert result["cleared"] == 0
        assert result["freed_bytes"] == 0

    def test_missing_raw_path_fails(self):
        """Non-existent RAW_PATH should return error - with full-shape invariant."""
        with unittest.mock.patch("arm.config.config.arm_config", {"RAW_PATH": "/nonexistent/path"}):
            from arm.services.maintenance import clear_raw_directories
            result = clear_raw_directories()

        assert result["success"] is False
        assert "not configured" in result["error"]
        # Failure path emits the full success-shape with zero defaults
        assert result["cleared"] == 0
        assert result["freed_bytes"] == 0
        assert result["errors"] == []
        assert result["path"] == "/nonexistent/path"
        assert set(result.keys()) == {"success", "cleared", "freed_bytes", "errors", "path", "error"}
