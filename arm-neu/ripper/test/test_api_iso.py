"""Tests for ISO import API endpoints."""
from unittest.mock import MagicMock, patch


class TestIsoScanEndpoint:
    """Test POST /api/v1/jobs/iso/scan."""

    @patch("arm.api.v1.iso.cfg")
    @patch("arm.api.v1.iso.prescan_iso_disc_type")
    def test_scan_success(self, mock_prescan, mock_cfg, tmp_path):
        ingress = tmp_path / "ingress"
        ingress.mkdir()
        iso = ingress / "Movie (2020).iso"
        iso.write_bytes(b"x" * 4096)
        mock_cfg.arm_config = {"INGRESS_PATH": str(ingress)}
        mock_prescan.return_value = {
            "disc_type": "bluray",
            "stream_count": 5,
            "volume_id": "MOVIE_VOL",
        }

        from fastapi.testclient import TestClient
        from arm.app import app
        client = TestClient(app)

        resp = client.post("/api/v1/jobs/iso/scan", json={"path": str(iso)})
        assert resp.status_code == 200
        data = resp.json()
        assert data["disc_type"] == "bluray"
        assert data["title_suggestion"] == "Movie"
        assert data["year_suggestion"] == "2020"
        assert data["iso_size"] == 4096
        assert data["stream_count"] == 5
        assert data["volume_id"] == "MOVIE_VOL"
        mock_prescan.assert_called_once_with(str(iso))

    @patch("arm.api.v1.iso.cfg")
    def test_scan_no_ingress_configured(self, mock_cfg):
        mock_cfg.arm_config = {"INGRESS_PATH": ""}

        from fastapi.testclient import TestClient
        from arm.app import app
        client = TestClient(app)

        resp = client.post("/api/v1/jobs/iso/scan", json={"path": "/some/path.iso"})
        assert resp.status_code == 400
        assert "INGRESS_PATH" in resp.json()["error"]

    @patch("arm.api.v1.iso.cfg")
    def test_scan_rejects_path_outside_ingress(self, mock_cfg, tmp_path):
        ingress = tmp_path / "ingress"
        ingress.mkdir()
        evil = tmp_path / "evil.iso"
        evil.write_bytes(b"\x00")
        mock_cfg.arm_config = {"INGRESS_PATH": str(ingress)}

        from fastapi.testclient import TestClient
        from arm.app import app
        client = TestClient(app)

        resp = client.post("/api/v1/jobs/iso/scan", json={"path": str(evil)})
        assert resp.status_code == 422
        # Constant string - no leakage of underlying path / exc message
        assert resp.json()["error"] == "Invalid ISO path or extension"

    @patch("arm.api.v1.iso.cfg")
    def test_scan_rejects_non_iso_extension(self, mock_cfg, tmp_path):
        ingress = tmp_path / "ingress"
        ingress.mkdir()
        notiso = ingress / "Movie.mkv"
        notiso.write_bytes(b"\x00")
        mock_cfg.arm_config = {"INGRESS_PATH": str(ingress)}

        from fastapi.testclient import TestClient
        from arm.app import app
        client = TestClient(app)

        resp = client.post("/api/v1/jobs/iso/scan", json={"path": str(notiso)})
        assert resp.status_code == 422
        assert resp.json()["error"] == "Invalid ISO path or extension"

    @patch("arm.api.v1.iso.cfg")
    def test_scan_missing_iso_returns_400(self, mock_cfg, tmp_path):
        ingress = tmp_path / "ingress"
        ingress.mkdir()
        mock_cfg.arm_config = {"INGRESS_PATH": str(ingress)}

        from fastapi.testclient import TestClient
        from arm.app import app
        client = TestClient(app)

        resp = client.post(
            "/api/v1/jobs/iso/scan",
            json={"path": str(ingress / "absent.iso")},
        )
        assert resp.status_code == 400
        # Constant string - no leakage of underlying filesystem path
        assert resp.json()["error"] == "ISO file not found"


class TestIsoCreateEndpoint:
    """Test POST /api/v1/jobs/iso."""

    @patch("arm.api.v1.iso.threading")
    @patch("arm.api.v1.iso.db")
    @patch("arm.api.v1.iso.Job")
    @patch("arm.api.v1.iso.cfg")
    def test_create_success(
        self, mock_cfg, mock_job_cls, mock_db, mock_threading, tmp_path,
    ):
        ingress = tmp_path / "ingress"
        ingress.mkdir()
        iso = ingress / "Movie.iso"
        iso.write_bytes(b"x" * 4096)
        mock_cfg.arm_config = {"INGRESS_PATH": str(ingress), "VIDEOTYPE": "auto"}

        mock_job = MagicMock()
        mock_job.job_id = 99
        mock_job.status = "identifying"
        mock_job.source_type = "iso"
        mock_job.source_path = str(iso)
        mock_job_cls.from_iso.return_value = mock_job
        mock_job_cls.query.filter.return_value.first.return_value = None

        from fastapi.testclient import TestClient
        from arm.app import app
        client = TestClient(app)

        resp = client.post("/api/v1/jobs/iso", json={
            "source_path": str(iso),
            "title": "Movie",
            "year": "2020",
            "video_type": "movie",
            "disctype": "bluray",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["success"] is True
        assert data["job_id"] == 99
        assert data["source_type"] == "iso"
        mock_threading.Thread.assert_called_once()
        mock_threading.Thread.return_value.start.assert_called_once()
        mock_job_cls.from_iso.assert_called_once_with(str(iso), "bluray")
        assert mock_job.title == "Movie"
        assert mock_job.year == "2020"

    @patch("arm.api.v1.iso.cfg")
    def test_create_no_ingress_configured(self, mock_cfg):
        mock_cfg.arm_config = {"INGRESS_PATH": ""}

        from fastapi.testclient import TestClient
        from arm.app import app
        client = TestClient(app)

        resp = client.post("/api/v1/jobs/iso", json={
            "source_path": "/some/path.iso",
            "title": "Test",
            "video_type": "movie",
            "disctype": "bluray",
        })
        assert resp.status_code == 400

    @patch("arm.api.v1.iso.cfg")
    def test_create_path_outside_ingress(self, mock_cfg, tmp_path):
        ingress = tmp_path / "ingress"
        ingress.mkdir()
        evil = tmp_path / "evil.iso"
        evil.write_bytes(b"\x00")
        mock_cfg.arm_config = {"INGRESS_PATH": str(ingress)}

        from fastapi.testclient import TestClient
        from arm.app import app
        client = TestClient(app)

        resp = client.post("/api/v1/jobs/iso", json={
            "source_path": str(evil),
            "title": "Evil",
            "video_type": "movie",
            "disctype": "bluray",
        })
        assert resp.status_code == 400
        # Constant string - no leakage of resolved path / exc message
        assert resp.json()["error"] == (
            "Path is outside the configured ingress directory or has invalid extension"
        )

    @patch("arm.api.v1.iso.db")
    @patch("arm.api.v1.iso.Job")
    @patch("arm.api.v1.iso.cfg")
    def test_create_duplicate_job(
        self, mock_cfg, mock_job_cls, mock_db, tmp_path,
    ):
        ingress = tmp_path / "ingress"
        ingress.mkdir()
        iso = ingress / "Movie.iso"
        iso.write_bytes(b"\x00")
        mock_cfg.arm_config = {"INGRESS_PATH": str(ingress)}

        existing = MagicMock()
        existing.job_id = 7
        mock_job_cls.query.filter.return_value.first.return_value = existing

        from fastapi.testclient import TestClient
        from arm.app import app
        client = TestClient(app)

        resp = client.post("/api/v1/jobs/iso", json={
            "source_path": str(iso),
            "title": "Movie",
            "video_type": "movie",
            "disctype": "bluray",
        })
        assert resp.status_code == 409
        assert "Active job already exists" in resp.json()["error"]


class TestIsoRipper:
    """Unit tests for arm.ripper.iso_ripper helpers."""

    def test_rip_iso_delegates_to_kick_off_import_rip(self, monkeypatch):
        from arm.ripper import iso_ripper
        captured = []
        monkeypatch.setattr(
            "arm.ripper.iso_ripper.kick_off_import_rip",
            lambda job: captured.append(job),
        )
        sentinel = MagicMock()
        iso_ripper.rip_iso(sentinel)
        assert captured == [sentinel]
