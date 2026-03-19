"""Tests for drive controls and system controls endpoints."""

from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(app_context):
    """FastAPI test client."""
    from arm.app import app
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client


def _make_drive(db_obj, **overrides):
    """Create a test drive in the DB."""
    from arm.models.system_drives import SystemDrives
    drive = SystemDrives()
    drive.name = overrides.get('name', 'Test Drive')
    drive.mount = overrides.get('mount', '/dev/sr0')
    drive.drive_mode = overrides.get('drive_mode', 'auto')
    db_obj.session.add(drive)
    db_obj.session.commit()
    return drive


def _make_job(db_obj, **overrides):
    """Create a test job in the DB by inserting directly."""
    from sqlalchemy import text
    title = overrides.get('title', 'Test')
    status = overrides.get('status', 'success')
    video_type = overrides.get('video_type', 'movie')
    db_obj.session.execute(text(
        "INSERT INTO job (title, status, video_type, devpath) VALUES (:t, :s, :v, :d)"
    ), {"t": title, "s": status, "v": video_type, "d": "/dev/sr0"})
    return None


class TestDriveEject:
    """Test POST /api/v1/drives/{drive_id}/eject endpoint."""

    def test_eject_drive_not_found(self, client):
        response = client.post('/api/v1/drives/99999/eject', json={"method": "eject"})
        assert response.status_code == 404

    def test_eject_invalid_method(self, client, app_context):
        _, db_obj = app_context
        drive = _make_drive(db_obj)
        response = client.post(f'/api/v1/drives/{drive.drive_id}/eject', json={"method": "invalid"})
        assert response.status_code == 400

    def test_eject_default_toggle(self, client, app_context):
        _, db_obj = app_context
        drive = _make_drive(db_obj)
        from arm.models.system_drives import SystemDrives
        with patch.object(SystemDrives, 'eject') as mock_eject:
            response = client.post(f'/api/v1/drives/{drive.drive_id}/eject')
            assert response.status_code == 200
            assert response.json()["method"] == "toggle"
            mock_eject.assert_called_once_with(method="toggle")

    def test_eject_method_eject(self, client, app_context):
        _, db_obj = app_context
        drive = _make_drive(db_obj)
        from arm.models.system_drives import SystemDrives
        with patch.object(SystemDrives, 'eject') as mock_eject:
            response = client.post(f'/api/v1/drives/{drive.drive_id}/eject', json={"method": "eject"})
            assert response.status_code == 200
            assert response.json()["success"] is True

    def test_eject_failure(self, client, app_context):
        _, db_obj = app_context
        drive = _make_drive(db_obj)
        from arm.models.system_drives import SystemDrives
        with patch.object(SystemDrives, 'eject', side_effect=RuntimeError("eject failed")):
            response = client.post(f'/api/v1/drives/{drive.drive_id}/eject', json={"method": "eject"})
            assert response.status_code == 500


class TestDriveModeUpdate:
    """Test PATCH /api/v1/drives/{drive_id} with drive_mode."""

    def test_update_drive_mode_auto(self, client, app_context):
        _, db_obj = app_context
        drive = _make_drive(db_obj, drive_mode="manual")
        response = client.patch(f'/api/v1/drives/{drive.drive_id}', json={"drive_mode": "auto"})
        assert response.status_code == 200
        db_obj.session.refresh(drive)
        assert drive.drive_mode == "auto"

    def test_update_drive_mode_manual(self, client, app_context):
        _, db_obj = app_context
        drive = _make_drive(db_obj, drive_mode="auto")
        response = client.patch(f'/api/v1/drives/{drive.drive_id}', json={"drive_mode": "manual"})
        assert response.status_code == 200
        db_obj.session.refresh(drive)
        assert drive.drive_mode == "manual"

    def test_update_drive_mode_invalid(self, client, app_context):
        _, db_obj = app_context
        drive = _make_drive(db_obj)
        response = client.patch(f'/api/v1/drives/{drive.drive_id}', json={"drive_mode": "turbo"})
        assert response.status_code == 400


class TestJobStats:
    """Test GET /api/v1/system/stats/jobs endpoint."""

    def test_job_stats_empty(self, client):
        response = client.get('/api/v1/system/stats/jobs')
        assert response.status_code == 200
        data = response.json()
        assert "by_status" in data
        assert "by_type" in data
        assert data["total"] == 0

    def test_job_stats_with_jobs(self, client, app_context):
        _, db_obj = app_context
        _make_job(db_obj, title="M1", status="success", video_type="movie")
        _make_job(db_obj, title="M2", status="success", video_type="movie")
        _make_job(db_obj, title="S1", status="fail", video_type="series")
        db_obj.session.commit()

        response = client.get('/api/v1/system/stats/jobs')
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert data["by_status"].get("success") == 2
        assert data["by_status"].get("fail") == 1
        assert data["by_type"].get("movie") == 2
        assert data["by_type"].get("series") == 1
