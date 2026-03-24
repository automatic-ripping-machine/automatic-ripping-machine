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

    @patch("arm.api.v1.folder.threading")
    @patch("arm.api.v1.folder.db")
    @patch("arm.api.v1.folder.validate_ingress_path")
    @patch("arm.api.v1.folder.Job")
    @patch("arm.api.v1.folder.cfg")
    def test_create_success(self, mock_cfg, mock_job_cls, mock_validate, mock_db, mock_threading):
        mock_cfg.arm_config = {"INGRESS_PATH": "/ingress", "VIDEOTYPE": "auto"}

        mock_job = MagicMock()
        mock_job.job_id = 42
        mock_job.status = "identifying"
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
        assert data["status"] == "identifying"
        # Prescan thread launched in background
        mock_threading.Thread.assert_called_once()
        mock_threading.Thread.return_value.start.assert_called_once()
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

    @patch("arm.api.v1.folder.threading")
    @patch("arm.api.v1.folder.db")
    @patch("arm.api.v1.folder.validate_ingress_path")
    @patch("arm.api.v1.folder.Job")
    @patch("arm.api.v1.folder.cfg")
    def test_create_with_season_and_disc_fields(
        self, mock_cfg, mock_job_cls, mock_validate, mock_db, mock_threading
    ):
        """season, disc_number, disc_total are stored on the job."""
        mock_cfg.arm_config = {"INGRESS_PATH": "/ingress", "VIDEOTYPE": "auto"}

        mock_job = MagicMock()
        mock_job.job_id = 55
        mock_job.status = "identifying"
        mock_job.source_type = "folder"
        mock_job.source_path = "/ingress/tv_show"
        mock_job_cls.from_folder.return_value = mock_job
        mock_job_cls.query.filter.return_value.first.return_value = None

        from fastapi.testclient import TestClient
        from arm.app import app
        client = TestClient(app)

        resp = client.post("/api/v1/jobs/folder", json={
            "source_path": "/ingress/tv_show",
            "title": "My TV Show",
            "year": "2025",
            "video_type": "series",
            "disctype": "bluray",
            "season": 1,
            "disc_number": 4,
            "disc_total": 4,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["success"] is True
        assert data["job_id"] == 55
        # Verify season fields
        assert mock_job.season == "1"
        assert mock_job.season_manual == "1"
        # Verify disc fields
        assert mock_job.disc_number == 4
        assert mock_job.disc_total == 4


class TestPrescanAndWait:
    """Test _prescan_and_wait background function."""

    @patch("arm.api.v1.folder.db")
    @patch("arm.api.v1.folder.Job")
    def test_prescan_success(self, mock_job_cls, mock_db):
        """Job transitions from IDENTIFYING to MANUAL_WAIT_STARTED on success."""
        from arm.api.v1.folder import _prescan_and_wait

        mock_job = MagicMock()
        mock_job.job_id = 10
        mock_job.tracks = [MagicMock(), MagicMock()]
        mock_job_cls.query.get.return_value = mock_job

        with patch("arm.ripper.makemkv.prep_mkv") as mock_prep, \
             patch("arm.ripper.makemkv.prescan_track_info") as mock_prescan:
            _prescan_and_wait(10)

        mock_prep.assert_called_once()
        mock_prescan.assert_called_once_with(mock_job)
        assert mock_job.status == "waiting"
        mock_db.session.commit.assert_called()

    @patch("arm.api.v1.folder.db")
    @patch("arm.api.v1.folder.Job")
    def test_prescan_failure_still_transitions(self, mock_job_cls, mock_db):
        """On failure, job gets error message and still transitions to MANUAL_WAIT_STARTED."""
        from arm.api.v1.folder import _prescan_and_wait

        mock_job = MagicMock()
        mock_job.job_id = 11
        mock_job.errors = None
        mock_job_cls.query.get.return_value = mock_job

        with patch("arm.ripper.makemkv.prep_mkv"), \
             patch("arm.ripper.makemkv.prescan_track_info",
                   side_effect=RuntimeError("MakeMKV crashed")):
            _prescan_and_wait(11)

        assert mock_job.status == "waiting"
        assert "Prescan failed" in mock_job.errors
        assert "MakeMKV crashed" in mock_job.errors
        mock_db.session.commit.assert_called()

    @patch("arm.api.v1.folder.db")
    @patch("arm.api.v1.folder.Job")
    def test_prescan_job_not_found(self, mock_job_cls, mock_db):
        """When job is not found, logs error and returns gracefully."""
        from arm.api.v1.folder import _prescan_and_wait

        mock_job_cls.query.get.return_value = None

        # Should not raise
        _prescan_and_wait(999)

        # DB commit should NOT be called since there's no job to update
        mock_db.session.commit.assert_not_called()
