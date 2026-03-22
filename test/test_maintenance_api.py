"""Tests for arm/api/v1/maintenance.py — maintenance REST endpoints."""
import os
import unittest.mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from arm.database import db
from arm.models.job import Job


@pytest.fixture
def maint_client(app_context):
    from arm.api.v1.maintenance import router
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as c:
        yield c


class TestMaintenanceCountsEndpoint:
    def test_returns_counts(self, app_context, sample_job, tmp_logs, maint_client):
        sample_job.logfile = "referenced.log"
        db.session.commit()

        mock_cfg = {"LOGPATH": str(tmp_logs), "RAW_PATH": "/nonexistent", "COMPLETED_PATH": "/nonexistent"}
        with unittest.mock.patch("arm.config.config.arm_config", mock_cfg):
            resp = maint_client.get("/api/v1/maintenance/counts")

        assert resp.status_code == 200
        data = resp.json()
        assert "orphan_logs" in data
        assert "orphan_folders" in data


class TestOrphanEndpoints:
    def test_get_orphan_logs(self, app_context, sample_job, tmp_logs, maint_client):
        sample_job.logfile = "referenced.log"
        db.session.commit()

        with unittest.mock.patch("arm.config.config.arm_config", {"LOGPATH": str(tmp_logs)}):
            resp = maint_client.get("/api/v1/maintenance/orphan-logs")

        assert resp.status_code == 200
        data = resp.json()
        assert "files" in data
        names = [f["relative_path"] for f in data["files"]]
        assert "orphan1.log" in names

    def test_get_orphan_folders(self, app_context, sample_job, tmp_media, maint_client):
        mock_cfg = {"RAW_PATH": tmp_media["raw"], "COMPLETED_PATH": tmp_media["completed"]}
        with unittest.mock.patch("arm.config.config.arm_config", mock_cfg):
            resp = maint_client.get("/api/v1/maintenance/orphan-folders")

        assert resp.status_code == 200
        data = resp.json()
        names = [f["name"] for f in data["folders"]]
        assert "Orphan Movie" in names


class TestDeleteEndpoints:
    def test_delete_log_success(self, app_context, tmp_logs, maint_client):
        target = tmp_logs / "orphan1.log"
        with unittest.mock.patch("arm.config.config.arm_config", {"LOGPATH": str(tmp_logs)}):
            resp = maint_client.post("/api/v1/maintenance/delete-log", json={"path": str(target)})
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        assert not target.exists()

    def test_delete_log_outside_root(self, app_context, tmp_logs, tmp_path, maint_client):
        outside = tmp_path / "evil.log"
        outside.write_text("x")
        with unittest.mock.patch("arm.config.config.arm_config", {"LOGPATH": str(tmp_logs)}):
            resp = maint_client.post("/api/v1/maintenance/delete-log", json={"path": str(outside)})
        assert resp.status_code == 403

    def test_delete_folder_success(self, app_context, tmp_media, maint_client):
        target = os.path.join(tmp_media["raw"], "Orphan Movie")
        mock_cfg = {"RAW_PATH": tmp_media["raw"], "COMPLETED_PATH": tmp_media["completed"]}
        with unittest.mock.patch("arm.config.config.arm_config", mock_cfg):
            resp = maint_client.post("/api/v1/maintenance/delete-folder", json={"path": target})
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_bulk_delete_logs(self, app_context, tmp_logs, maint_client):
        paths = [str(tmp_logs / "orphan1.log"), str(tmp_logs / "orphan2.log"), str(tmp_logs / "nonexistent.log")]
        with unittest.mock.patch("arm.config.config.arm_config", {"LOGPATH": str(tmp_logs)}):
            resp = maint_client.post("/api/v1/maintenance/bulk-delete-logs", json={"paths": paths})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["removed"]) == 2
        assert len(data["errors"]) == 1
