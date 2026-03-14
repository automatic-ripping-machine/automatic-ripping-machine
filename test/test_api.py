"""Tests for the REST API layer (arm/api/v1/)."""
import unittest.mock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(app_context):
    """FastAPI test client."""
    from arm.app import app
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client


class TestApiJobsList:
    """Test GET /api/v1/jobs endpoint."""

    def test_list_jobs_returns_json(self, client):
        response = client.get('/api/v1/jobs')
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_list_jobs_with_status_filter(self, client):
        response = client.get('/api/v1/jobs?status=success')
        assert response.status_code == 200

    def test_list_jobs_fail_status(self, client):
        response = client.get('/api/v1/jobs?status=fail')
        assert response.status_code == 200

    def test_list_jobs_search(self, client):
        response = client.get('/api/v1/jobs?q=serial')
        assert response.status_code == 200


class TestApiJobDelete:
    """Test DELETE /api/v1/jobs/<id> endpoint."""

    def test_delete_nonexistent_job(self, client):
        response = client.delete('/api/v1/jobs/99999')
        assert response.status_code in (200, 404)


class TestApiJobAbandon:
    """Test POST /api/v1/jobs/<id>/abandon endpoint."""

    def test_abandon_nonexistent_raises(self, client):
        """Upstream svc_jobs.abandon_job doesn't handle missing jobs gracefully."""
        # abandon_job tries to set attrs on None (Job.query.get returns None)
        with pytest.raises(AttributeError):
            client.post('/api/v1/jobs/99999/abandon')

    def test_abandon_with_mock(self, client):
        with unittest.mock.patch('arm.api.v1.jobs.svc_jobs') as mock_api:
            mock_api.abandon_job.return_value = {"success": True}
            response = client.post('/api/v1/jobs/1/abandon')
            assert response.status_code == 200


class TestApiJobPause:
    """Test POST /api/v1/jobs/<id>/pause endpoint."""

    def test_pause_nonexistent_job(self, client):
        response = client.post('/api/v1/jobs/99999/pause')
        assert response.status_code == 404
        assert response.json()["success"] is False

    def test_pause_job_not_waiting(self, client, sample_job, app_context):
        """Can only pause jobs in MANUAL_WAIT_STARTED status."""
        from arm.ripper.utils import database_updater
        database_updater({"status": "active"}, sample_job)
        response = client.post(f'/api/v1/jobs/{sample_job.job_id}/pause')
        assert response.status_code == 409

    def test_pause_toggles_on(self, client, sample_job, app_context):
        from arm.ripper.utils import database_updater
        from arm.database import db
        database_updater({"status": "waiting"}, sample_job)
        response = client.post(f'/api/v1/jobs/{sample_job.job_id}/pause')
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["paused"] is True
        db.session.refresh(sample_job)
        assert sample_job.manual_pause is True

    def test_pause_toggles_off(self, client, sample_job, app_context):
        from arm.ripper.utils import database_updater
        from arm.database import db
        database_updater({"status": "waiting", "manual_pause": True}, sample_job)
        response = client.post(f'/api/v1/jobs/{sample_job.job_id}/pause')
        assert response.status_code == 200
        data = response.json()
        assert data["paused"] is False
        db.session.refresh(sample_job)
        assert sample_job.manual_pause is False


class TestApiJobConfig:
    """Test PATCH /api/v1/jobs/<id>/config endpoint."""

    def test_change_config_nonexistent(self, client):
        response = client.patch(
            '/api/v1/jobs/99999/config',
            json={"RIPMETHOD": "mkv"},
        )
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False

    def test_change_config_empty_body(self, client, sample_job, app_context):
        response = client.patch(
            f'/api/v1/jobs/{sample_job.job_id}/config',
            json={},
        )
        assert response.status_code == 400

    def test_change_config_invalid_ripmethod(self, client, sample_job, app_context):
        response = client.patch(
            f'/api/v1/jobs/{sample_job.job_id}/config',
            json={"RIPMETHOD": "invalid"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "RIPMETHOD" in data["error"]

    def test_change_config_success(self, client, sample_job, app_context):
        response = client.patch(
            f'/api/v1/jobs/{sample_job.job_id}/config',
            json={"RIPMETHOD": "backup", "MAINFEATURE": True, "MINLENGTH": 600},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["job_id"] == sample_job.job_id


class TestApiJobFixPermissions:
    """Test POST /api/v1/jobs/<id>/fix-permissions endpoint."""

    def test_fix_permissions_with_mock(self, client):
        with unittest.mock.patch('arm.api.v1.jobs.svc_files') as mock_utils:
            mock_utils.fix_permissions.return_value = {"success": True}
            response = client.post('/api/v1/jobs/1/fix-permissions')
            assert response.status_code == 200


class TestApiJobSend:
    """Test POST /api/v1/jobs/<id>/send endpoint."""

    def test_send_with_mock(self, client):
        with unittest.mock.patch('arm.api.v1.jobs.svc_files') as mock_utils:
            mock_utils.send_to_remote_db.return_value = {"success": True}
            response = client.post('/api/v1/jobs/1/send')
            assert response.status_code == 200


class TestApiJobLog:
    """Test GET /api/v1/jobs/<id>/log endpoint."""

    def test_get_log_nonexistent_job(self, client):
        response = client.get('/api/v1/jobs/99999/log')
        assert response.status_code in (200, 404)


class TestApiNotifications:
    """Test PATCH /api/v1/notifications/<id> endpoint."""

    def test_read_notification(self, client):
        response = client.patch('/api/v1/notifications/99999')
        assert response.status_code in (200, 404)


class TestApiNotifyTimeout:
    """Test GET /api/v1/settings/notify-timeout endpoint."""

    def test_get_notify_timeout(self, client):
        response = client.get('/api/v1/settings/notify-timeout')
        assert response.status_code == 200
        data = response.json()
        assert data is not None


class TestApiSystemRestart:
    """Test POST /api/v1/system/restart endpoint."""

    def test_restart_returns_response(self, client):
        with unittest.mock.patch('arm.api.v1.system.svc_jobs') as mock_api:
            mock_api.restart_ui.return_value = {"success": True}
            response = client.post('/api/v1/system/restart')
            assert response.status_code == 200


class TestApiSystemVersion:
    """Test GET /api/v1/system/version endpoint."""

    def _patch_version(self, client, *, arm_version="1.0.0",
                       makemkv_output="MakeMKV v1.18.3",
                       db_file="/tmp/arm.db", install_path="/opt/arm",
                       db_row=("abc123",), head="def456",
                       version_file_error=None, db_file_exists=True):
        """Call the version endpoint with all dependencies mocked."""
        import unittest.mock as m

        config = {"INSTALLPATH": install_path, "DBFILE": db_file}
        proc = m.Mock(stdout=makemkv_output, stderr="")
        mock_script = m.Mock()
        mock_script.get_current_head.return_value = head
        mock_cursor = m.Mock()
        mock_cursor.fetchone.return_value = db_row
        mock_conn = m.Mock()
        mock_conn.cursor.return_value = mock_cursor

        open_side = version_file_error if version_file_error else None
        open_mock = m.mock_open(read_data=arm_version) if not version_file_error else None

        with (
            m.patch("arm.api.v1.system.cfg.arm_config", config),
            m.patch("arm.api.v1.system.subprocess.run", return_value=proc),
            m.patch("arm.api.v1.system.os.path.isfile", return_value=db_file_exists),
            m.patch("alembic.script.ScriptDirectory.from_config", return_value=mock_script),
            m.patch("sqlite3.connect", return_value=mock_conn),
            m.patch("builtins.open", open_mock or m.Mock(side_effect=open_side)),
        ):
            return client.get('/api/v1/system/version')

    def test_version_returns_all_fields(self, client):
        """All four version keys are present in the response."""
        response = self._patch_version(client)
        assert response.status_code == 200
        data = response.json()
        assert data["arm_version"] == "1.0.0"
        assert data["makemkv_version"] == "1.18.3"
        assert data["db_version"] == "abc123"
        assert data["db_head"] == "def456"

    def test_version_arm_unknown_when_file_missing(self, client):
        """arm_version is 'unknown' when VERSION file does not exist."""
        response = self._patch_version(client, version_file_error=OSError("not found"))
        assert response.status_code == 200
        assert response.json()["arm_version"] == "unknown"

    def test_version_db_version_from_sqlite(self, client):
        """db_version matches the revision returned by sqlite."""
        response = self._patch_version(client, db_row=("rev_99x",))
        assert response.status_code == 200
        assert response.json()["db_version"] == "rev_99x"

    def test_version_db_unknown_when_no_dbfile(self, client):
        """db_version is 'unknown' when DBFILE is empty or file does not exist."""
        response = self._patch_version(client, db_file="", db_file_exists=False)
        assert response.status_code == 200
        assert response.json()["db_version"] == "unknown"


class TestApiJobTitleUpdate:
    """Test PUT /api/v1/jobs/<id>/title endpoint."""

    def test_update_title_basic(self, client, sample_job, app_context):
        response = client.put(
            f'/api/v1/jobs/{sample_job.job_id}/title',
            json={"title": "New Title", "year": "2020"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["updated"]["title"] == "New Title"
        assert data["updated"]["year"] == "2020"

    def test_update_nonexistent_job(self, client):
        response = client.put(
            '/api/v1/jobs/99999/title',
            json={"title": "Test"},
        )
        assert response.status_code == 404

    def test_update_empty_body(self, client, sample_job, app_context):
        response = client.put(
            f'/api/v1/jobs/{sample_job.job_id}/title',
            json={},
        )
        assert response.status_code == 400

    def test_update_structured_fields_music(self, client, sample_job, app_context):
        """Sending artist/album stores them and re-renders the title."""
        response = client.put(
            f'/api/v1/jobs/{sample_job.job_id}/title',
            json={
                "artist": "The Beatles",
                "album": "Abbey Road",
                "year": "1969",
                "video_type": "music",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["updated"]["artist"] == "The Beatles"
        assert data["updated"]["album"] == "Abbey Road"
        # Title should be auto-rendered from the music pattern
        assert data["updated"]["title"] == "The Beatles - Abbey Road"

    def test_update_structured_fields_series(self, client, sample_job, app_context):
        """Sending season/episode stores them and re-renders the title."""
        # First set title and type so the pattern has something to work with
        sample_job.title = "Breaking Bad"
        sample_job.video_type = "series"
        from arm.database import db
        db.session.commit()

        response = client.put(
            f'/api/v1/jobs/{sample_job.job_id}/title',
            json={
                "season": "2",
                "episode": "5",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["updated"]["season"] == "2"
        assert data["updated"]["episode"] == "5"
        # Title re-rendered from TV pattern
        assert data["updated"]["title"] == "Breaking Bad S02E05"

    def test_explicit_title_not_overridden(self, client, sample_job, app_context):
        """When title is explicitly set alongside structured fields, it's not overridden."""
        response = client.put(
            f'/api/v1/jobs/{sample_job.job_id}/title',
            json={
                "title": "Custom Title",
                "artist": "Queen",
                "album": "Jazz",
                "video_type": "music",
            },
        )
        assert response.status_code == 200
        data = response.json()
        # Title should be the explicit value, not the pattern-rendered one
        assert data["updated"]["title"] == "Custom Title"

    def test_update_invalid_disctype(self, client, sample_job, app_context):
        response = client.put(
            f'/api/v1/jobs/{sample_job.job_id}/title',
            json={"disctype": "invalid"},
        )
        assert response.status_code == 400


class TestApiNamingPreview:
    """Test POST /api/v1/naming/preview endpoint."""

    def test_preview_basic(self, client):
        response = client.post(
            '/api/v1/naming/preview',
            json={
                "pattern": "{artist} - {album} ({year})",
                "variables": {"artist": "Queen", "album": "Jazz", "year": "1978"},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["rendered"] == "Queen - Jazz (1978)"

    def test_preview_missing_variable(self, client):
        response = client.post(
            '/api/v1/naming/preview',
            json={
                "pattern": "{title} ({year})",
                "variables": {"title": "Inception"},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["rendered"] == "Inception"

    def test_preview_empty_pattern(self, client):
        response = client.post(
            '/api/v1/naming/preview',
            json={"pattern": "", "variables": {}},
        )
        assert response.status_code == 400

    def test_preview_tv_pattern(self, client):
        response = client.post(
            '/api/v1/naming/preview',
            json={
                "pattern": "{title} S{season}E{episode}",
                "variables": {"title": "Lost", "season": "03", "episode": "12"},
            },
        )
        assert response.status_code == 200
        assert response.json()["rendered"] == "Lost S03E12"


class TestApiDrivesRescan:
    """Test POST /api/v1/drives/rescan endpoint."""

    def test_rescan_success(self, client, app_context):
        with unittest.mock.patch("arm.services.drives.drives_update", return_value=0), \
             unittest.mock.patch("arm.api.v1.drives.SystemDrives") as mock_sd:
            mock_sd.query.count.side_effect = [2, 2]
            response = client.post('/api/v1/drives/rescan')
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "drive_count" in data

    def test_rescan_failure(self, client, app_context):
        with unittest.mock.patch(
            "arm.services.drives.drives_update", side_effect=RuntimeError("scan failed")
        ), unittest.mock.patch("arm.api.v1.drives.SystemDrives") as mock_sd:
            mock_sd.query.count.return_value = 0
            response = client.post('/api/v1/drives/rescan')
        assert response.status_code == 500
        assert response.json()["success"] is False


class TestApiDriveScan:
    """Test POST /api/v1/drives/{drive_id}/scan endpoint."""

    def test_scan_not_found(self, client, app_context):
        with unittest.mock.patch("arm.api.v1.drives.SystemDrives") as mock_sd:
            mock_sd.query.get.return_value = None
            response = client.post('/api/v1/drives/1/scan')
        assert response.status_code == 404

    def test_scan_no_mount(self, client, app_context):
        mock_drive = unittest.mock.MagicMock()
        mock_drive.mount = None
        with unittest.mock.patch("arm.api.v1.drives.SystemDrives") as mock_sd:
            mock_sd.query.get.return_value = mock_drive
            response = client.post('/api/v1/drives/1/scan')
        assert response.status_code == 400

    def test_scan_success(self, client, app_context):
        mock_drive = unittest.mock.MagicMock()
        mock_drive.mount = "/dev/sr0"
        with unittest.mock.patch("arm.api.v1.drives.SystemDrives") as mock_sd, \
             unittest.mock.patch("arm.api.v1.drives.subprocess.Popen") as mock_popen:
            mock_sd.query.get.return_value = mock_drive
            response = client.post('/api/v1/drives/1/scan')
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_scan_popen_fails(self, client, app_context):
        mock_drive = unittest.mock.MagicMock()
        mock_drive.mount = "/dev/sr0"
        with unittest.mock.patch("arm.api.v1.drives.SystemDrives") as mock_sd, \
             unittest.mock.patch(
                 "arm.api.v1.drives.subprocess.Popen",
                 side_effect=OSError("script missing"),
             ):
            mock_sd.query.get.return_value = mock_drive
            response = client.post('/api/v1/drives/1/scan')
        assert response.status_code == 500


class TestApiDriveDelete:
    """Test DELETE /api/v1/drives/{drive_id} endpoint."""

    def test_delete_not_found(self, client, app_context):
        with unittest.mock.patch("arm.api.v1.drives.SystemDrives") as mock_sd:
            mock_sd.query.get.return_value = None
            response = client.delete('/api/v1/drives/1')
        assert response.status_code == 404

    def test_delete_active_job(self, client, app_context):
        mock_drive = unittest.mock.MagicMock()
        mock_drive.processing = True
        with unittest.mock.patch("arm.api.v1.drives.SystemDrives") as mock_sd:
            mock_sd.query.get.return_value = mock_drive
            response = client.delete('/api/v1/drives/1')
        assert response.status_code == 409

    def test_delete_success(self, client, app_context):
        mock_drive = unittest.mock.MagicMock()
        mock_drive.processing = False
        mock_drive.name = "Test Drive"
        mock_drive.mount = "/dev/sr0"
        with unittest.mock.patch("arm.api.v1.drives.SystemDrives") as mock_sd, \
             unittest.mock.patch("arm.api.v1.drives.db") as mock_db:
            mock_sd.query.get.return_value = mock_drive
            response = client.delete('/api/v1/drives/1')
        assert response.status_code == 200
        assert response.json()["success"] is True


class TestApiDriveUpdate:
    """Test PATCH /api/v1/drives/{drive_id} endpoint."""

    def test_update_not_found(self, client, app_context):
        with unittest.mock.patch("arm.api.v1.drives.SystemDrives") as mock_sd:
            mock_sd.query.get.return_value = None
            response = client.patch('/api/v1/drives/1', json={"name": "My Drive"})
        assert response.status_code == 404

    def test_update_empty_body(self, client, app_context):
        mock_drive = unittest.mock.MagicMock()
        with unittest.mock.patch("arm.api.v1.drives.SystemDrives") as mock_sd:
            mock_sd.query.get.return_value = mock_drive
            response = client.patch('/api/v1/drives/1', json={})
        assert response.status_code == 400

    def test_update_name(self, client, app_context):
        mock_drive = unittest.mock.MagicMock()
        mock_drive.drive_id = 1
        with unittest.mock.patch("arm.api.v1.drives.SystemDrives") as mock_sd, \
             unittest.mock.patch("arm.api.v1.drives.db"):
            mock_sd.query.get.return_value = mock_drive
            response = client.patch('/api/v1/drives/1', json={"name": "My Drive"})
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_update_description_and_uhd(self, client, app_context):
        mock_drive = unittest.mock.MagicMock()
        mock_drive.drive_id = 1
        with unittest.mock.patch("arm.api.v1.drives.SystemDrives") as mock_sd, \
             unittest.mock.patch("arm.api.v1.drives.db"):
            mock_sd.query.get.return_value = mock_drive
            response = client.patch(
                '/api/v1/drives/1',
                json={"description": "Main drive", "uhd_capable": True},
            )
        assert response.status_code == 200

    def test_update_no_valid_fields(self, client, app_context):
        mock_drive = unittest.mock.MagicMock()
        with unittest.mock.patch("arm.api.v1.drives.SystemDrives") as mock_sd:
            mock_sd.query.get.return_value = mock_drive
            response = client.patch('/api/v1/drives/1', json={"invalid_field": "value"})
        assert response.status_code == 400


class TestApiSettingsConfig:
    """Test GET /api/v1/settings/config endpoint."""

    def test_config_includes_naming_variables(self, client):
        response = client.get('/api/v1/settings/config')
        assert response.status_code == 200
        data = response.json()
        assert "naming_variables" in data
        nv = data["naming_variables"]
        assert isinstance(nv, dict)
        assert "title" in nv
        assert "year" in nv
        assert "artist" in nv
        assert "album" in nv
        assert "season" in nv
        assert "episode" in nv

    def test_naming_variables_match_engine(self, client):
        from arm.ripper.naming import PATTERN_VARIABLES
        response = client.get('/api/v1/settings/config')
        data = response.json()
        assert data["naming_variables"] == PATTERN_VARIABLES


# ── Drive diagnostic endpoint tests ──────────────────────────────────────


class TestApiDriveDiagnostic:
    """Test GET /api/v1/drives/diagnostic endpoint."""

    def _mock_proc_listdir(self, entries):
        """Return a side_effect for os.listdir that handles /proc specially."""
        def _listdir(path):
            if path == "/proc":
                return entries
            raise FileNotFoundError(path)
        return _listdir

    def test_diagnostic_no_drives(self, client, app_context):
        """Diagnostic with no drives found anywhere."""
        with unittest.mock.patch("arm.api.v1.drives.os.listdir", return_value=[]), \
             unittest.mock.patch("arm.api.v1.drives.glob.glob", return_value=[]), \
             unittest.mock.patch("arm.api.v1.drives.SystemDrives") as mock_sd, \
             unittest.mock.patch("builtins.open", side_effect=FileNotFoundError):
            mock_sd.query.all.return_value = []
            response = client.get('/api/v1/drives/diagnostic')
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert any("No optical drives found" in i for i in data["issues"])

    def test_diagnostic_udevd_running(self, client, app_context):
        """Diagnostic detects udevd running."""
        mock_comm_open = unittest.mock.mock_open(read_data="systemd-udevd\n")
        original_open = open

        def _open_side_effect(path, *args, **kwargs):
            if isinstance(path, str) and path.startswith("/proc/") and path.endswith("/comm"):
                return mock_comm_open(path, *args, **kwargs)
            if isinstance(path, str) and path == "/proc/sys/dev/cdrom/info":
                raise FileNotFoundError
            return original_open(path, *args, **kwargs)

        with unittest.mock.patch("arm.api.v1.drives.os.listdir", return_value=["1", "42", "abc"]), \
             unittest.mock.patch("arm.api.v1.drives.glob.glob", return_value=[]), \
             unittest.mock.patch("arm.api.v1.drives.SystemDrives") as mock_sd, \
             unittest.mock.patch("builtins.open", side_effect=_open_side_effect):
            mock_sd.query.all.return_value = []
            response = client.get('/api/v1/drives/diagnostic')
        data = response.json()
        assert data["udevd_running"] is True

    def test_diagnostic_udevd_not_running(self, client, app_context):
        """Diagnostic detects udevd NOT running."""
        mock_comm_open = unittest.mock.mock_open(read_data="bash\n")
        original_open = open

        def _open_side_effect(path, *args, **kwargs):
            if isinstance(path, str) and path.startswith("/proc/") and path.endswith("/comm"):
                return mock_comm_open(path, *args, **kwargs)
            if isinstance(path, str) and path == "/proc/sys/dev/cdrom/info":
                raise FileNotFoundError
            return original_open(path, *args, **kwargs)

        with unittest.mock.patch("arm.api.v1.drives.os.listdir", return_value=["1"]), \
             unittest.mock.patch("arm.api.v1.drives.glob.glob", return_value=[]), \
             unittest.mock.patch("arm.api.v1.drives.SystemDrives") as mock_sd, \
             unittest.mock.patch("builtins.open", side_effect=_open_side_effect):
            mock_sd.query.all.return_value = []
            response = client.get('/api/v1/drives/diagnostic')
        data = response.json()
        assert data["udevd_running"] is False
        assert any("udevd is not running" in i for i in data["issues"])

    def test_diagnostic_with_drive(self, client, app_context):
        """Diagnostic with one drive detected from kernel cdrom info."""
        cdrom_info = "drive name:\tsr0\n"

        def _open_side_effect(path, *args, **kwargs):
            if isinstance(path, str) and path.startswith("/proc/") and path.endswith("/comm"):
                raise FileNotFoundError
            if isinstance(path, str) and path == "/proc/sys/dev/cdrom/info":
                return unittest.mock.mock_open(read_data=cdrom_info)(path, *args, **kwargs)
            if isinstance(path, str) and path.startswith("/sys/block/"):
                raise FileNotFoundError
            raise FileNotFoundError(path)

        with unittest.mock.patch("arm.api.v1.drives.os.listdir", return_value=[]), \
             unittest.mock.patch("arm.api.v1.drives.glob.glob", return_value=[]), \
             unittest.mock.patch("arm.api.v1.drives.SystemDrives") as mock_sd, \
             unittest.mock.patch("arm.api.v1.drives.os.path.exists", return_value=False), \
             unittest.mock.patch("arm.api.v1.drives.os.path.isdir", return_value=False), \
             unittest.mock.patch("arm.api.v1.drives.subprocess.run",
                                 side_effect=FileNotFoundError("udevadm")), \
             unittest.mock.patch("builtins.open", side_effect=_open_side_effect):
            mock_sd.query.all.return_value = []
            response = client.get('/api/v1/drives/diagnostic')
        data = response.json()
        assert data["success"] is True
        assert data["kernel_drives"] == ["sr0"]
        assert len(data["drives"]) == 1
        assert data["drives"][0]["devname"] == "sr0"

    def test_diagnostic_drive_with_db_entry(self, client, app_context):
        """Diagnostic shows DB info for a known drive."""
        mock_drive = unittest.mock.MagicMock()
        mock_drive.mount = "/dev/sr0"
        mock_drive.name = "Pioneer BDR"
        mock_drive.maker = "Pioneer"
        mock_drive.model = "BDR-S12J"
        mock_drive.connection = "usb"

        def _open_side_effect(path, *args, **kwargs):
            if isinstance(path, str) and path.startswith("/proc/") and path.endswith("/comm"):
                raise FileNotFoundError
            if isinstance(path, str) and path == "/proc/sys/dev/cdrom/info":
                return unittest.mock.mock_open(read_data="drive name:\tsr0\n")(path)
            if isinstance(path, str) and path.startswith("/sys/block/"):
                raise FileNotFoundError
            raise FileNotFoundError(path)

        with unittest.mock.patch("arm.api.v1.drives.os.listdir", return_value=[]), \
             unittest.mock.patch("arm.api.v1.drives.glob.glob", return_value=[]), \
             unittest.mock.patch("arm.api.v1.drives.SystemDrives") as mock_sd, \
             unittest.mock.patch("arm.api.v1.drives.os.path.exists", return_value=False), \
             unittest.mock.patch("arm.api.v1.drives.os.path.isdir", return_value=False), \
             unittest.mock.patch("arm.api.v1.drives.subprocess.run",
                                 side_effect=FileNotFoundError("udevadm")), \
             unittest.mock.patch("builtins.open", side_effect=_open_side_effect):
            mock_sd.query.all.return_value = [mock_drive]
            response = client.get('/api/v1/drives/diagnostic')
        data = response.json()
        assert data["success"] is True
        drive = data["drives"][0]
        assert drive["db_name"] == "Pioneer BDR"
        assert drive["in_database"] is True


# ── File browser API endpoint tests ──────────────────────────────────────


class TestApiFilesRoots:
    """Test GET /api/v1/files/roots endpoint."""

    def test_get_roots(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.get_roots",
                                 return_value=[{"key": "raw", "label": "Raw", "path": "/tmp"}]):
            response = client.get('/api/v1/files/roots')
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert data[0]["key"] == "raw"


class TestApiFilesList:
    """Test GET /api/v1/files/list endpoint."""

    def test_list_success(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.list_directory",
                                 return_value={"path": "/tmp", "parent": None, "entries": []}):
            response = client.get('/api/v1/files/list?path=/tmp')
        assert response.status_code == 200
        assert response.json()["entries"] == []

    def test_list_access_denied(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.list_directory",
                                 side_effect=ValueError("not allowed")):
            response = client.get('/api/v1/files/list?path=/etc')
        assert response.status_code == 403

    def test_list_not_found(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.list_directory",
                                 side_effect=FileNotFoundError):
            response = client.get('/api/v1/files/list?path=/nonexistent')
        assert response.status_code == 404

    def test_list_not_a_directory(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.list_directory",
                                 side_effect=NotADirectoryError):
            response = client.get('/api/v1/files/list?path=/tmp/file.txt')
        assert response.status_code == 400

    def test_list_os_error(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.list_directory",
                                 side_effect=OSError("disk failure")):
            response = client.get('/api/v1/files/list?path=/tmp')
        assert response.status_code == 500


class TestApiFilesRename:
    """Test POST /api/v1/files/rename endpoint."""

    def test_rename_success(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.rename_item",
                                 return_value={"success": True, "new_path": "/tmp/new.mkv"}):
            response = client.post('/api/v1/files/rename',
                                   json={"path": "/tmp/old.mkv", "new_name": "new.mkv"})
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_rename_missing_fields(self, client, app_context):
        response = client.post('/api/v1/files/rename', json={"path": "/tmp/old.mkv"})
        assert response.status_code == 400

    def test_rename_access_denied(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.rename_item",
                                 side_effect=ValueError):
            response = client.post('/api/v1/files/rename',
                                   json={"path": "/etc/passwd", "new_name": "x"})
        assert response.status_code == 403

    def test_rename_not_found(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.rename_item",
                                 side_effect=FileNotFoundError):
            response = client.post('/api/v1/files/rename',
                                   json={"path": "/tmp/gone.mkv", "new_name": "x"})
        assert response.status_code == 404

    def test_rename_already_exists(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.rename_item",
                                 side_effect=FileExistsError):
            response = client.post('/api/v1/files/rename',
                                   json={"path": "/tmp/a.mkv", "new_name": "b.mkv"})
        assert response.status_code == 409

    def test_rename_os_error(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.rename_item",
                                 side_effect=OSError("io error")):
            response = client.post('/api/v1/files/rename',
                                   json={"path": "/tmp/a.mkv", "new_name": "b.mkv"})
        assert response.status_code == 500


class TestApiFilesMove:
    """Test POST /api/v1/files/move endpoint."""

    def test_move_success(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.move_item",
                                 return_value={"success": True, "new_path": "/tmp/dest/file.mkv"}):
            response = client.post('/api/v1/files/move',
                                   json={"path": "/tmp/file.mkv", "destination": "/tmp/dest"})
        assert response.status_code == 200

    def test_move_missing_fields(self, client, app_context):
        response = client.post('/api/v1/files/move', json={"path": "/tmp/file.mkv"})
        assert response.status_code == 400

    def test_move_access_denied(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.move_item",
                                 side_effect=ValueError):
            response = client.post('/api/v1/files/move',
                                   json={"path": "/tmp/a", "destination": "/etc"})
        assert response.status_code == 403

    def test_move_not_found(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.move_item",
                                 side_effect=FileNotFoundError):
            response = client.post('/api/v1/files/move',
                                   json={"path": "/tmp/gone", "destination": "/tmp/dest"})
        assert response.status_code == 404

    def test_move_conflict(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.move_item",
                                 side_effect=FileExistsError):
            response = client.post('/api/v1/files/move',
                                   json={"path": "/tmp/a", "destination": "/tmp/b"})
        assert response.status_code == 409

    def test_move_os_error(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.move_item",
                                 side_effect=OSError("io")):
            response = client.post('/api/v1/files/move',
                                   json={"path": "/tmp/a", "destination": "/tmp/b"})
        assert response.status_code == 500


class TestApiFilesMkdir:
    """Test POST /api/v1/files/mkdir endpoint."""

    def test_mkdir_success(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.create_directory",
                                 return_value={"success": True, "new_path": "/tmp/newdir"}):
            response = client.post('/api/v1/files/mkdir',
                                   json={"path": "/tmp", "name": "newdir"})
        assert response.status_code == 200

    def test_mkdir_missing_fields(self, client, app_context):
        response = client.post('/api/v1/files/mkdir', json={"path": "/tmp"})
        assert response.status_code == 400

    def test_mkdir_access_denied(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.create_directory",
                                 side_effect=ValueError):
            response = client.post('/api/v1/files/mkdir',
                                   json={"path": "/etc", "name": "nope"})
        assert response.status_code == 403

    def test_mkdir_not_found(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.create_directory",
                                 side_effect=FileNotFoundError):
            response = client.post('/api/v1/files/mkdir',
                                   json={"path": "/nonexistent", "name": "dir"})
        assert response.status_code == 404

    def test_mkdir_already_exists(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.create_directory",
                                 side_effect=FileExistsError):
            response = client.post('/api/v1/files/mkdir',
                                   json={"path": "/tmp", "name": "existing"})
        assert response.status_code == 409

    def test_mkdir_os_error(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.create_directory",
                                 side_effect=OSError("fail")):
            response = client.post('/api/v1/files/mkdir',
                                   json={"path": "/tmp", "name": "dir"})
        assert response.status_code == 500


class TestApiFilesFixPermissions:
    """Test POST /api/v1/files/fix-permissions endpoint."""

    def test_fix_perms_success(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.fix_item_permissions",
                                 return_value={"success": True, "fixed": 5}):
            response = client.post('/api/v1/files/fix-permissions',
                                   json={"path": "/tmp/media"})
        assert response.status_code == 200
        assert response.json()["fixed"] == 5

    def test_fix_perms_missing_path(self, client, app_context):
        response = client.post('/api/v1/files/fix-permissions', json={})
        assert response.status_code == 400

    def test_fix_perms_access_denied(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.fix_item_permissions",
                                 side_effect=ValueError):
            response = client.post('/api/v1/files/fix-permissions',
                                   json={"path": "/etc"})
        assert response.status_code == 403

    def test_fix_perms_not_found(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.fix_item_permissions",
                                 side_effect=FileNotFoundError):
            response = client.post('/api/v1/files/fix-permissions',
                                   json={"path": "/tmp/gone"})
        assert response.status_code == 404

    def test_fix_perms_os_error(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.fix_item_permissions",
                                 side_effect=OSError("perm denied")):
            response = client.post('/api/v1/files/fix-permissions',
                                   json={"path": "/tmp/media"})
        assert response.status_code == 500


class TestApiFilesDelete:
    """Test DELETE /api/v1/files/delete endpoint."""

    def test_delete_success(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.delete_item",
                                 return_value={"success": True}):
            response = client.request('DELETE', '/api/v1/files/delete',
                                      json={"path": "/tmp/file.mkv"})
        assert response.status_code == 200

    def test_delete_missing_path(self, client, app_context):
        response = client.request('DELETE', '/api/v1/files/delete', json={})
        assert response.status_code == 400

    def test_delete_access_denied(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.delete_item",
                                 side_effect=ValueError):
            response = client.request('DELETE', '/api/v1/files/delete',
                                      json={"path": "/etc/passwd"})
        assert response.status_code == 403

    def test_delete_not_found(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.delete_item",
                                 side_effect=FileNotFoundError):
            response = client.request('DELETE', '/api/v1/files/delete',
                                      json={"path": "/tmp/gone"})
        assert response.status_code == 404

    def test_delete_os_error(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.delete_item",
                                 side_effect=OSError("io")):
            response = client.request('DELETE', '/api/v1/files/delete',
                                      json={"path": "/tmp/file"})
        assert response.status_code == 500


# ── System endpoint tests ────────────────────────────────────────────────


class TestApiSystemInfo:
    """Test GET /api/v1/system/info endpoint."""

    def test_system_info_returns_cpu_and_memory(self, client):
        mock_mem = unittest.mock.MagicMock()
        mock_mem.total = 17179869184  # 16 GB
        with unittest.mock.patch("arm.api.v1.system.psutil.virtual_memory",
                                 return_value=mock_mem), \
             unittest.mock.patch("arm.api.v1.system._detect_cpu",
                                 return_value="Intel Xeon E5"):
            response = client.get('/api/v1/system/info')
        assert response.status_code == 200
        data = response.json()
        assert data["cpu"] == "Intel Xeon E5"
        assert data["memory_total_gb"] == 16.0


class TestApiSystemStats:
    """Test GET /api/v1/system/stats endpoint."""

    def test_stats_returns_all_sections(self, client):
        mock_mem = unittest.mock.MagicMock()
        mock_mem.total = 17179869184
        mock_mem.used = 8589934592
        mock_mem.available = 8589934592
        mock_mem.percent = 50.0

        mock_disk = unittest.mock.MagicMock()
        mock_disk.total = 1099511627776
        mock_disk.used = 549755813888
        mock_disk.free = 549755813888
        mock_disk.percent = 50.0

        config = {
            "RAW_PATH": "/tmp/raw",
            "TRANSCODE_PATH": "",
            "COMPLETED_PATH": "/tmp/completed",
        }

        with unittest.mock.patch("arm.api.v1.system.psutil.cpu_percent", return_value=25.0), \
             unittest.mock.patch("arm.api.v1.system.psutil.sensors_temperatures",
                                 return_value={}), \
             unittest.mock.patch("arm.api.v1.system.psutil.virtual_memory",
                                 return_value=mock_mem), \
             unittest.mock.patch("arm.api.v1.system.psutil.disk_usage",
                                 return_value=mock_disk), \
             unittest.mock.patch("arm.api.v1.system.cfg.arm_config", config):
            response = client.get('/api/v1/system/stats')
        assert response.status_code == 200
        data = response.json()
        assert data["cpu_percent"] == 25.0
        assert data["memory"]["percent"] == 50.0
        assert len(data["storage"]) == 2  # RAW_PATH and COMPLETED_PATH

    def test_stats_with_cpu_temp(self, client):
        mock_mem = unittest.mock.MagicMock()
        mock_mem.total = 17179869184
        mock_mem.used = 8589934592
        mock_mem.available = 8589934592
        mock_mem.percent = 50.0

        temp_entry = unittest.mock.MagicMock()
        temp_entry.current = 65.0

        with unittest.mock.patch("arm.api.v1.system.psutil.cpu_percent", return_value=10.0), \
             unittest.mock.patch("arm.api.v1.system.psutil.sensors_temperatures",
                                 return_value={"coretemp": [temp_entry]}), \
             unittest.mock.patch("arm.api.v1.system.psutil.virtual_memory",
                                 return_value=mock_mem), \
             unittest.mock.patch("arm.api.v1.system.cfg.arm_config",
                                 {"RAW_PATH": "", "TRANSCODE_PATH": "", "COMPLETED_PATH": ""}):
            response = client.get('/api/v1/system/stats')
        data = response.json()
        assert data["cpu_temp"] == 65.0

    def test_stats_disk_not_found(self, client):
        """Storage paths that don't exist are silently skipped."""
        mock_mem = unittest.mock.MagicMock()
        mock_mem.total = 17179869184
        mock_mem.used = 0
        mock_mem.available = 17179869184
        mock_mem.percent = 0.0

        with unittest.mock.patch("arm.api.v1.system.psutil.cpu_percent", return_value=0.0), \
             unittest.mock.patch("arm.api.v1.system.psutil.sensors_temperatures",
                                 return_value={}), \
             unittest.mock.patch("arm.api.v1.system.psutil.virtual_memory",
                                 return_value=mock_mem), \
             unittest.mock.patch("arm.api.v1.system.psutil.disk_usage",
                                 side_effect=FileNotFoundError), \
             unittest.mock.patch("arm.api.v1.system.cfg.arm_config",
                                 {"RAW_PATH": "/no/such/path", "TRANSCODE_PATH": "",
                                  "COMPLETED_PATH": ""}):
            response = client.get('/api/v1/system/stats')
        assert response.status_code == 200
        assert response.json()["storage"] == []


class TestApiSystemPaths:
    """Test GET /api/v1/system/paths endpoint."""

    def test_paths_returns_list(self, client):
        config = {
            "RAW_PATH": "/tmp",
            "COMPLETED_PATH": "/tmp",
            "TRANSCODE_PATH": "",
            "LOGPATH": "",
            "DBFILE": "",
            "INSTALLPATH": "",
        }
        with unittest.mock.patch("arm.api.v1.system.cfg.arm_config", config):
            response = client.get('/api/v1/system/paths')
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Only RAW_PATH and COMPLETED_PATH have values
        assert len(data) == 2
        assert all("setting" in entry for entry in data)
        assert all("exists" in entry for entry in data)

    def test_paths_empty_config(self, client):
        config = {
            "RAW_PATH": "", "COMPLETED_PATH": "", "TRANSCODE_PATH": "",
            "LOGPATH": "", "DBFILE": "", "INSTALLPATH": "",
        }
        with unittest.mock.patch("arm.api.v1.system.cfg.arm_config", config):
            response = client.get('/api/v1/system/paths')
        assert response.status_code == 200
        assert response.json() == []


class TestApiRippingEnabled:
    """Test GET/POST /api/v1/system/ripping-enabled endpoint."""

    def test_get_ripping_enabled(self, client, app_context):
        from arm.models.app_state import AppState
        from arm.database import db
        # Ensure AppState row exists
        state = AppState(id=1, ripping_paused=False)
        db.session.add(state)
        db.session.commit()

        response = client.get('/api/v1/system/ripping-enabled')
        assert response.status_code == 200
        assert response.json()["ripping_enabled"] is True

    def test_set_ripping_enabled(self, client, app_context):
        from arm.models.app_state import AppState
        from arm.database import db
        state = AppState(id=1, ripping_paused=False)
        db.session.add(state)
        db.session.commit()

        response = client.post('/api/v1/system/ripping-enabled',
                               json={"enabled": False})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["ripping_enabled"] is False

    def test_set_ripping_enabled_missing_field(self, client, app_context):
        response = client.post('/api/v1/system/ripping-enabled', json={})
        assert response.status_code == 400

    def test_toggle_ripping_back_on(self, client, app_context):
        from arm.models.app_state import AppState
        from arm.database import db
        state = AppState(id=1, ripping_paused=True)
        db.session.add(state)
        db.session.commit()

        response = client.post('/api/v1/system/ripping-enabled',
                               json={"enabled": True})
        assert response.status_code == 200
        assert response.json()["ripping_enabled"] is True
