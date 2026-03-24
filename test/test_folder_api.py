"""Tests for folder import API endpoints."""
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def client():
    """Create a FastAPI TestClient with mocked config."""
    with patch("arm.config.config.arm_config", {
        "DBFILE": ":memory:",
        "INGRESS_PATH": "/ingress",
        "TRANSCODER_URL": "",
    }):
        # Mock the db engine init to avoid real database
        with patch("arm.database.db") as mock_db:
            mock_db.init_engine = MagicMock()
            mock_db.session = MagicMock()

            from fastapi.testclient import TestClient
            from arm.app import app
            yield TestClient(app)


class TestFolderScan:
    """Test POST /api/v1/jobs/folder/scan."""

    @patch("arm.api.v1.folder.cfg")
    @patch("arm.api.v1.folder.scan_folder")
    def test_scan_success(self, mock_scan, mock_cfg):
        mock_cfg.arm_config = {"INGRESS_PATH": "/ingress"}
        mock_scan.return_value = {
            "disc_type": "bluray",
            "label": "TEST MOVIE",
            "title_suggestion": "Test Movie",
            "year_suggestion": "2024",
            "folder_size_bytes": 1024,
            "stream_count": 1,
        }

        from fastapi.testclient import TestClient
        from arm.app import app
        client = TestClient(app)

        resp = client.post("/api/v1/jobs/folder/scan", json={"path": "/ingress/movie"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["disc_type"] == "bluray"
        mock_scan.assert_called_once_with("/ingress/movie", "/ingress")

    @patch("arm.api.v1.folder.cfg")
    def test_scan_no_ingress_configured(self, mock_cfg):
        mock_cfg.arm_config = {"INGRESS_PATH": ""}

        from fastapi.testclient import TestClient
        from arm.app import app
        client = TestClient(app)

        resp = client.post("/api/v1/jobs/folder/scan", json={"path": "/some/path"})
        assert resp.status_code == 400
        assert "INGRESS_PATH" in resp.json()["error"]

    @patch("arm.api.v1.folder.cfg")
    @patch("arm.api.v1.folder.scan_folder", side_effect=FileNotFoundError("Path does not exist"))
    def test_scan_file_not_found(self, mock_scan, mock_cfg):
        mock_cfg.arm_config = {"INGRESS_PATH": "/ingress"}

        from fastapi.testclient import TestClient
        from arm.app import app
        client = TestClient(app)

        resp = client.post("/api/v1/jobs/folder/scan", json={"path": "/ingress/missing"})
        assert resp.status_code == 400

    @patch("arm.api.v1.folder.cfg")
    @patch("arm.api.v1.folder.scan_folder", side_effect=ValueError("No disc structure"))
    def test_scan_invalid_structure(self, mock_scan, mock_cfg):
        mock_cfg.arm_config = {"INGRESS_PATH": "/ingress"}

        from fastapi.testclient import TestClient
        from arm.app import app
        client = TestClient(app)

        resp = client.post("/api/v1/jobs/folder/scan", json={"path": "/ingress/bad"})
        assert resp.status_code == 422


class TestFolderCreate:
    """Test POST /api/v1/jobs/folder."""

    @patch("arm.api.v1.folder.db")
    @patch("arm.api.v1.folder.validate_ingress_path")
    @patch("arm.api.v1.folder.Job")
    @patch("arm.api.v1.folder.cfg")
    def test_create_success(self, mock_cfg, mock_job_cls, mock_validate, mock_db):
        mock_cfg.arm_config = {"INGRESS_PATH": "/ingress", "VIDEOTYPE": "auto"}

        mock_job = MagicMock()
        mock_job.job_id = 42
        mock_job.status = "waiting"
        mock_job.source_type = "folder"
        mock_job.source_path = "/ingress/movie"
        mock_job_cls.from_folder.return_value = mock_job
        mock_job_cls.query.filter.return_value.first.return_value = None

        from fastapi.testclient import TestClient
        from arm.app import app
        client = TestClient(app)

        resp = client.post("/api/v1/jobs/folder", json={
            "source_path": "/ingress/movie",
            "title": "Test Movie",
            "year": "2024",
            "video_type": "movie",
            "disctype": "bluray",
            "imdb_id": "tt1234567",
            "poster_url": "https://example.com/poster.jpg",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["success"] is True
        assert data["job_id"] == 42
        assert data["source_type"] == "folder"
        assert data["status"] == "waiting"
        # No background thread launched — job waits for review
        # Verify optional fields were set on the job object
        assert mock_job.imdb_id == "tt1234567"
        assert mock_job.poster_url == "https://example.com/poster.jpg"

    @patch("arm.api.v1.folder.cfg")
    def test_create_no_ingress_configured(self, mock_cfg):
        mock_cfg.arm_config = {"INGRESS_PATH": ""}

        from fastapi.testclient import TestClient
        from arm.app import app
        client = TestClient(app)

        resp = client.post("/api/v1/jobs/folder", json={
            "source_path": "/some/path",
            "title": "Test",
            "video_type": "movie",
            "disctype": "bluray",
        })
        assert resp.status_code == 400

    @patch("arm.api.v1.folder.validate_ingress_path", side_effect=ValueError("outside ingress"))
    @patch("arm.api.v1.folder.cfg")
    def test_create_path_outside_ingress(self, mock_cfg, mock_validate):
        mock_cfg.arm_config = {"INGRESS_PATH": "/ingress"}

        from fastapi.testclient import TestClient
        from arm.app import app
        client = TestClient(app)

        resp = client.post("/api/v1/jobs/folder", json={
            "source_path": "/etc/passwd",
            "title": "Evil",
            "video_type": "movie",
            "disctype": "bluray",
        })
        assert resp.status_code == 400

    @patch("arm.api.v1.folder.db")
    @patch("arm.api.v1.folder.validate_ingress_path")
    @patch("arm.api.v1.folder.Job")
    @patch("arm.api.v1.folder.cfg")
    def test_create_duplicate_job(self, mock_cfg, mock_job_cls, mock_validate, mock_db):
        mock_cfg.arm_config = {"INGRESS_PATH": "/ingress"}

        existing = MagicMock()
        existing.job_id = 10
        mock_job_cls.query.filter.return_value.first.return_value = existing

        from fastapi.testclient import TestClient
        from arm.app import app
        client = TestClient(app)

        resp = client.post("/api/v1/jobs/folder", json={
            "source_path": "/ingress/movie",
            "title": "Test",
            "video_type": "movie",
            "disctype": "bluray",
        })
        assert resp.status_code == 409
        assert "Active job already exists" in resp.json()["error"]

    @patch("arm.api.v1.folder.validate_ingress_path", side_effect=FileNotFoundError("not found"))
    @patch("arm.api.v1.folder.cfg")
    def test_create_source_not_found(self, mock_cfg, mock_validate):
        """FileNotFoundError from validate_ingress_path returns 400 (line 74)."""
        mock_cfg.arm_config = {"INGRESS_PATH": "/ingress"}

        from fastapi.testclient import TestClient
        from arm.app import app
        client = TestClient(app)

        resp = client.post("/api/v1/jobs/folder", json={
            "source_path": "/ingress/missing_folder",
            "title": "Ghost",
            "video_type": "movie",
            "disctype": "bluray",
        })
        assert resp.status_code == 400
        assert "Source folder not found" in resp.json()["error"]
