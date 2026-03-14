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
                       db_file="/home/arm/db/arm.db", install_path="/opt/arm",
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

        async def mock_create_subprocess(*args, **kwargs):
            return unittest.mock.MagicMock()

        with unittest.mock.patch("arm.api.v1.drives.SystemDrives") as mock_sd, \
             unittest.mock.patch("arm.api.v1.drives.asyncio.create_subprocess_exec",
                                 side_effect=mock_create_subprocess):
            mock_sd.query.get.return_value = mock_drive
            response = client.post('/api/v1/drives/1/scan')
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_scan_popen_fails(self, client, app_context):
        mock_drive = unittest.mock.MagicMock()
        mock_drive.mount = "/dev/sr0"
        with unittest.mock.patch("arm.api.v1.drives.SystemDrives") as mock_sd, \
             unittest.mock.patch(
                 "arm.api.v1.drives.asyncio.create_subprocess_exec",
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
                                 return_value=[{"key": "raw", "label": "Raw", "path": "/home/arm/media/raw"}]):
            response = client.get('/api/v1/files/roots')
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert data[0]["key"] == "raw"


class TestApiFilesList:
    """Test GET /api/v1/files/list endpoint."""

    def test_list_success(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.list_directory",
                                 return_value={"path": "/home/arm/media", "parent": None, "entries": []}):
            response = client.get('/api/v1/files/list?path=/home/arm/media')
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
            response = client.get('/api/v1/files/list?path=/home/arm/media/file.txt')
        assert response.status_code == 400

    def test_list_os_error(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.list_directory",
                                 side_effect=OSError("disk failure")):
            response = client.get('/api/v1/files/list?path=/home/arm/media')
        assert response.status_code == 500


class TestApiFilesRename:
    """Test POST /api/v1/files/rename endpoint."""

    def test_rename_success(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.rename_item",
                                 return_value={"success": True, "new_path": "/home/arm/media/new.mkv"}):
            response = client.post('/api/v1/files/rename',
                                   json={"path": "/home/arm/media/old.mkv", "new_name": "new.mkv"})
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_rename_missing_fields(self, client, app_context):
        response = client.post('/api/v1/files/rename', json={"path": "/home/arm/media/old.mkv"})
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
                                   json={"path": "/home/arm/media/gone.mkv", "new_name": "x"})
        assert response.status_code == 404

    def test_rename_already_exists(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.rename_item",
                                 side_effect=FileExistsError):
            response = client.post('/api/v1/files/rename',
                                   json={"path": "/home/arm/media/a.mkv", "new_name": "b.mkv"})
        assert response.status_code == 409

    def test_rename_os_error(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.rename_item",
                                 side_effect=OSError("io error")):
            response = client.post('/api/v1/files/rename',
                                   json={"path": "/home/arm/media/a.mkv", "new_name": "b.mkv"})
        assert response.status_code == 500


class TestApiFilesMove:
    """Test POST /api/v1/files/move endpoint."""

    def test_move_success(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.move_item",
                                 return_value={"success": True, "new_path": "/home/arm/media/dest/file.mkv"}):
            response = client.post('/api/v1/files/move',
                                   json={"path": "/home/arm/media/file.mkv", "destination": "/home/arm/media/dest"})
        assert response.status_code == 200

    def test_move_missing_fields(self, client, app_context):
        response = client.post('/api/v1/files/move', json={"path": "/home/arm/media/file.mkv"})
        assert response.status_code == 400

    def test_move_access_denied(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.move_item",
                                 side_effect=ValueError):
            response = client.post('/api/v1/files/move',
                                   json={"path": "/home/arm/media/a", "destination": "/etc"})
        assert response.status_code == 403

    def test_move_not_found(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.move_item",
                                 side_effect=FileNotFoundError):
            response = client.post('/api/v1/files/move',
                                   json={"path": "/home/arm/media/gone", "destination": "/home/arm/media/dest"})
        assert response.status_code == 404

    def test_move_conflict(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.move_item",
                                 side_effect=FileExistsError):
            response = client.post('/api/v1/files/move',
                                   json={"path": "/home/arm/media/a", "destination": "/home/arm/media/b"})
        assert response.status_code == 409

    def test_move_os_error(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.move_item",
                                 side_effect=OSError("io")):
            response = client.post('/api/v1/files/move',
                                   json={"path": "/home/arm/media/a", "destination": "/home/arm/media/b"})
        assert response.status_code == 500


class TestApiFilesMkdir:
    """Test POST /api/v1/files/mkdir endpoint."""

    def test_mkdir_success(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.create_directory",
                                 return_value={"success": True, "new_path": "/home/arm/media/newdir"}):
            response = client.post('/api/v1/files/mkdir',
                                   json={"path": "/home/arm/media", "name": "newdir"})
        assert response.status_code == 200

    def test_mkdir_missing_fields(self, client, app_context):
        response = client.post('/api/v1/files/mkdir', json={"path": "/home/arm/media"})
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
                                   json={"path": "/home/arm/media", "name": "existing"})
        assert response.status_code == 409

    def test_mkdir_os_error(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.create_directory",
                                 side_effect=OSError("fail")):
            response = client.post('/api/v1/files/mkdir',
                                   json={"path": "/home/arm/media", "name": "dir"})
        assert response.status_code == 500


class TestApiFilesFixPermissions:
    """Test POST /api/v1/files/fix-permissions endpoint."""

    def test_fix_perms_success(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.fix_item_permissions",
                                 return_value={"success": True, "fixed": 5}):
            response = client.post('/api/v1/files/fix-permissions',
                                   json={"path": "/home/arm/media/media"})
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
                                   json={"path": "/home/arm/media/gone"})
        assert response.status_code == 404

    def test_fix_perms_os_error(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.fix_item_permissions",
                                 side_effect=OSError("perm denied")):
            response = client.post('/api/v1/files/fix-permissions',
                                   json={"path": "/home/arm/media/media"})
        assert response.status_code == 500


class TestApiFilesDelete:
    """Test DELETE /api/v1/files/delete endpoint."""

    def test_delete_success(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.delete_item",
                                 return_value={"success": True}):
            response = client.request('DELETE', '/api/v1/files/delete',
                                      json={"path": "/home/arm/media/file.mkv"})
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
                                      json={"path": "/home/arm/media/gone"})
        assert response.status_code == 404

    def test_delete_os_error(self, client, app_context):
        with unittest.mock.patch("arm.services.file_browser.delete_item",
                                 side_effect=OSError("io")):
            response = client.request('DELETE', '/api/v1/files/delete',
                                      json={"path": "/home/arm/media/file"})
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
        assert data["memory_total_gb"] == pytest.approx(16.0)


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
            "RAW_PATH": "/home/arm/media/raw",
            "TRANSCODE_PATH": "",
            "COMPLETED_PATH": "/home/arm/media/completed",
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
        assert data["cpu_percent"] == pytest.approx(25.0)
        assert data["memory"]["percent"] == pytest.approx(50.0)
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
        assert data["cpu_temp"] == pytest.approx(65.0)

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
            "RAW_PATH": "/home/arm/media",
            "COMPLETED_PATH": "/home/arm/media",
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


# ── Drive diagnostic helper function unit tests ──────────────────────────


class TestCheckUdevd:
    """Test _check_udevd() helper directly."""

    def test_udevd_found_as_systemd_udevd(self):
        from arm.api.v1.drives import _check_udevd

        original_open = open

        def _mock_listdir(path):
            if path == "/proc":
                return ["1", "42", "abc", "300"]
            raise FileNotFoundError(path)

        def _mock_open(path, *args, **kwargs):
            if isinstance(path, str) and path == "/proc/42/comm":
                return unittest.mock.mock_open(read_data="systemd-udevd\n")(path)
            if isinstance(path, str) and path.startswith("/proc/") and path.endswith("/comm"):
                return unittest.mock.mock_open(read_data="bash\n")(path)
            return original_open(path, *args, **kwargs)

        with unittest.mock.patch("arm.api.v1.drives.os.listdir", side_effect=_mock_listdir), \
             unittest.mock.patch("builtins.open", side_effect=_mock_open):
            assert _check_udevd() is True

    def test_udevd_not_found(self):
        from arm.api.v1.drives import _check_udevd

        original_open = open

        def _mock_open(path, *args, **kwargs):
            if isinstance(path, str) and path.startswith("/proc/") and path.endswith("/comm"):
                return unittest.mock.mock_open(read_data="python3\n")(path)
            return original_open(path, *args, **kwargs)

        with unittest.mock.patch("arm.api.v1.drives.os.listdir", return_value=["1", "2"]), \
             unittest.mock.patch("builtins.open", side_effect=_mock_open):
            assert _check_udevd() is False

    def test_udevd_skips_non_digit_pids(self):
        from arm.api.v1.drives import _check_udevd

        with unittest.mock.patch("arm.api.v1.drives.os.listdir",
                                 return_value=["self", "bus", "net"]):
            assert _check_udevd() is False

    def test_udevd_handles_file_not_found(self):
        from arm.api.v1.drives import _check_udevd

        def _mock_open(path, *args, **kwargs):
            raise FileNotFoundError(path)

        with unittest.mock.patch("arm.api.v1.drives.os.listdir", return_value=["1", "2"]), \
             unittest.mock.patch("builtins.open", side_effect=_mock_open):
            assert _check_udevd() is False

    def test_udevd_handles_ioerror(self):
        from arm.api.v1.drives import _check_udevd

        def _mock_open(path, *args, **kwargs):
            raise IOError("permission denied")

        with unittest.mock.patch("arm.api.v1.drives.os.listdir", return_value=["1"]), \
             unittest.mock.patch("builtins.open", side_effect=_mock_open):
            assert _check_udevd() is False


class TestReadKernelCdromInfo:
    """Test _read_kernel_cdrom_info() helper directly."""

    def test_reads_two_drives(self):
        from arm.api.v1.drives import _read_kernel_cdrom_info

        content = "CD-ROM information, Id: cdrom.c 3.20 2003/12/17\n\ndrive name:\tsr0\tsr1\n"

        with unittest.mock.patch("builtins.open",
                                 unittest.mock.mock_open(read_data=content)):
            exists, drives = _read_kernel_cdrom_info()
        assert exists is True
        assert drives == ["sr0", "sr1"]

    def test_reads_single_drive(self):
        from arm.api.v1.drives import _read_kernel_cdrom_info

        content = "drive name:\tsr0\n"
        with unittest.mock.patch("builtins.open",
                                 unittest.mock.mock_open(read_data=content)):
            exists, drives = _read_kernel_cdrom_info()
        assert exists is True
        assert drives == ["sr0"]

    def test_file_not_found(self):
        from arm.api.v1.drives import _read_kernel_cdrom_info

        with unittest.mock.patch("builtins.open", side_effect=FileNotFoundError):
            exists, drives = _read_kernel_cdrom_info()
        assert exists is False
        assert drives == []

    def test_no_drive_name_line(self):
        from arm.api.v1.drives import _read_kernel_cdrom_info

        content = "CD-ROM information, Id: cdrom.c 3.20\n\nsome other info\n"
        with unittest.mock.patch("builtins.open",
                                 unittest.mock.mock_open(read_data=content)):
            exists, drives = _read_kernel_cdrom_info()
        assert exists is True
        assert drives == []


class TestRunDriveDiagnostic:
    """Test _run_drive_diagnostic() helper directly."""

    def test_drive_with_sysfs_and_major_minor(self):
        from arm.api.v1.drives import _run_drive_diagnostic

        original_open = open

        def _mock_open(path, *args, **kwargs):
            if isinstance(path, str) and path == "/sys/block/sr0/dev":
                return unittest.mock.mock_open(read_data="11:0\n")(path)
            return original_open(path, *args, **kwargs)

        with unittest.mock.patch("arm.api.v1.drives.os.path.exists", return_value=True), \
             unittest.mock.patch("arm.api.v1.drives.os.path.isdir", return_value=True), \
             unittest.mock.patch("builtins.open", side_effect=_mock_open), \
             unittest.mock.patch("arm.api.v1.drives.os.open", return_value=3), \
             unittest.mock.patch("arm.api.v1.drives.fcntl.ioctl", return_value=4), \
             unittest.mock.patch("arm.api.v1.drives.os.close"), \
             unittest.mock.patch("arm.api.v1.drives.subprocess.run") as mock_run:
            mock_result = unittest.mock.MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "ID_CDROM=1\nID_CDROM_DVD=1\n"
            mock_run.return_value = mock_result

            issues = []
            checks = _run_drive_diagnostic({}, {"sr0"}, ["sr0"], issues)

        assert len(checks) == 1
        assert checks[0]["major_minor"] == "11:0"
        assert checks[0]["tray_status"] == 4
        assert checks[0]["tray_status_name"] == "DISC_OK"
        assert checks[0]["udevadm"]["ID_CDROM"] == "1"

    def test_drive_not_in_kernel_cdrom(self):
        from arm.api.v1.drives import _run_drive_diagnostic

        with unittest.mock.patch("arm.api.v1.drives.os.path.exists", return_value=False), \
             unittest.mock.patch("arm.api.v1.drives.os.path.isdir", return_value=False), \
             unittest.mock.patch("builtins.open", side_effect=FileNotFoundError), \
             unittest.mock.patch("arm.api.v1.drives.subprocess.run",
                                 side_effect=FileNotFoundError("udevadm")):
            issues = []
            checks = _run_drive_diagnostic({}, {"sr0"}, [], issues)

        assert checks[0]["in_kernel_cdrom"] is False
        assert any("not listed" in i for i in checks[0]["issues"])

    def test_drive_ioctl_oserror(self):
        from arm.api.v1.drives import _run_drive_diagnostic

        with unittest.mock.patch("arm.api.v1.drives.os.path.exists", return_value=True), \
             unittest.mock.patch("arm.api.v1.drives.os.path.isdir", return_value=False), \
             unittest.mock.patch("builtins.open", side_effect=FileNotFoundError), \
             unittest.mock.patch("arm.api.v1.drives.os.open", return_value=3), \
             unittest.mock.patch("arm.api.v1.drives.fcntl.ioctl",
                                 side_effect=OSError("ioctl failed")), \
             unittest.mock.patch("arm.api.v1.drives.os.close"), \
             unittest.mock.patch("arm.api.v1.drives.subprocess.run",
                                 side_effect=FileNotFoundError("udevadm")):
            issues = []
            checks = _run_drive_diagnostic({}, {"sr0"}, ["sr0"], issues)

        assert "ioctl failed" in checks[0]["tray_status_name"]
        assert any("Cannot read tray status" in i for i in checks[0]["issues"])

    def test_drive_open_oserror(self):
        from arm.api.v1.drives import _run_drive_diagnostic

        with unittest.mock.patch("arm.api.v1.drives.os.path.exists", return_value=True), \
             unittest.mock.patch("arm.api.v1.drives.os.path.isdir", return_value=False), \
             unittest.mock.patch("builtins.open", side_effect=FileNotFoundError), \
             unittest.mock.patch("arm.api.v1.drives.os.open",
                                 side_effect=OSError("open failed")), \
             unittest.mock.patch("arm.api.v1.drives.subprocess.run",
                                 side_effect=FileNotFoundError("udevadm")):
            issues = []
            checks = _run_drive_diagnostic({}, {"sr0"}, ["sr0"], issues)

        assert "open failed" in checks[0]["tray_status_name"]
        assert any("Cannot open" in i for i in checks[0]["issues"])

    def test_udevadm_nonzero_returncode(self):
        from arm.api.v1.drives import _run_drive_diagnostic

        with unittest.mock.patch("arm.api.v1.drives.os.path.exists", return_value=False), \
             unittest.mock.patch("arm.api.v1.drives.os.path.isdir", return_value=False), \
             unittest.mock.patch("builtins.open", side_effect=FileNotFoundError), \
             unittest.mock.patch("arm.api.v1.drives.subprocess.run") as mock_run:
            mock_result = unittest.mock.MagicMock()
            mock_result.returncode = 1
            mock_result.stderr = "error message"
            mock_run.return_value = mock_result

            issues = []
            checks = _run_drive_diagnostic({}, {"sr0"}, ["sr0"], issues)

        assert any("udevadm info failed" in i for i in checks[0]["issues"])

    def test_udevadm_timeout(self):
        import subprocess
        from arm.api.v1.drives import _run_drive_diagnostic

        with unittest.mock.patch("arm.api.v1.drives.os.path.exists", return_value=False), \
             unittest.mock.patch("arm.api.v1.drives.os.path.isdir", return_value=False), \
             unittest.mock.patch("builtins.open", side_effect=FileNotFoundError), \
             unittest.mock.patch("arm.api.v1.drives.subprocess.run",
                                 side_effect=subprocess.TimeoutExpired("udevadm", 5)):
            issues = []
            checks = _run_drive_diagnostic({}, {"sr0"}, ["sr0"], issues)

        assert any("timed out" in i for i in checks[0]["issues"])

    def test_udevadm_no_cdrom_properties(self):
        from arm.api.v1.drives import _run_drive_diagnostic

        with unittest.mock.patch("arm.api.v1.drives.os.path.exists", return_value=False), \
             unittest.mock.patch("arm.api.v1.drives.os.path.isdir", return_value=False), \
             unittest.mock.patch("builtins.open", side_effect=FileNotFoundError), \
             unittest.mock.patch("arm.api.v1.drives.subprocess.run") as mock_run:
            mock_result = unittest.mock.MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "DEVPATH=/dev/sr0\nSUBSYSTEM=block\n"
            mock_run.return_value = mock_result

            issues = []
            checks = _run_drive_diagnostic({}, {"sr0"}, ["sr0"], issues)

        assert checks[0]["udevadm"] == {}
        assert any("no CDROM properties" in i for i in checks[0]["issues"])

    def test_flock_arm_processing(self):
        from arm.api.v1.drives import _run_drive_diagnostic

        with unittest.mock.patch("arm.api.v1.drives.os.path.exists") as mock_exists, \
             unittest.mock.patch("arm.api.v1.drives.os.path.isdir", return_value=False), \
             unittest.mock.patch("builtins.open", side_effect=FileNotFoundError), \
             unittest.mock.patch("arm.api.v1.drives.os.open", return_value=3), \
             unittest.mock.patch("arm.api.v1.drives.fcntl.flock",
                                 side_effect=BlockingIOError("locked")), \
             unittest.mock.patch("arm.api.v1.drives.os.close"), \
             unittest.mock.patch("arm.api.v1.drives.subprocess.run",
                                 side_effect=FileNotFoundError("udevadm")):
            def exists_side_effect(path):
                if path == "/home/arm/.arm_sr0.lock":
                    return True
                return False
            mock_exists.side_effect = exists_side_effect

            issues = []
            checks = _run_drive_diagnostic({}, {"sr0"}, ["sr0"], issues)

        assert checks[0]["arm_processing"] is True

    def test_flock_not_locked(self):
        from arm.api.v1.drives import _run_drive_diagnostic

        with unittest.mock.patch("arm.api.v1.drives.os.path.exists") as mock_exists, \
             unittest.mock.patch("arm.api.v1.drives.os.path.isdir", return_value=False), \
             unittest.mock.patch("builtins.open", side_effect=FileNotFoundError), \
             unittest.mock.patch("arm.api.v1.drives.os.open", return_value=3), \
             unittest.mock.patch("arm.api.v1.drives.fcntl.flock"), \
             unittest.mock.patch("arm.api.v1.drives.os.close"), \
             unittest.mock.patch("arm.api.v1.drives.subprocess.run",
                                 side_effect=FileNotFoundError("udevadm")):
            def exists_side_effect(path):
                if path == "/home/arm/.arm_sr0.lock":
                    return True
                return False
            mock_exists.side_effect = exists_side_effect

            issues = []
            checks = _run_drive_diagnostic({}, {"sr0"}, ["sr0"], issues)

        assert checks[0]["arm_processing"] is False

    def test_flock_oserror(self):
        from arm.api.v1.drives import _run_drive_diagnostic

        with unittest.mock.patch("arm.api.v1.drives.os.path.exists") as mock_exists, \
             unittest.mock.patch("arm.api.v1.drives.os.path.isdir", return_value=False), \
             unittest.mock.patch("builtins.open", side_effect=FileNotFoundError), \
             unittest.mock.patch("arm.api.v1.drives.os.open",
                                 side_effect=OSError("can't open")), \
             unittest.mock.patch("arm.api.v1.drives.subprocess.run",
                                 side_effect=FileNotFoundError("udevadm")):
            def exists_side_effect(path):
                if path == "/home/arm/.arm_sr0.lock":
                    return True
                return False
            mock_exists.side_effect = exists_side_effect

            issues = []
            checks = _run_drive_diagnostic({}, {"sr0"}, ["sr0"], issues)

        assert checks[0]["arm_processing"] is False

    def test_drive_with_db_entry(self):
        from arm.api.v1.drives import _run_drive_diagnostic

        mock_db_drive = unittest.mock.MagicMock()
        mock_db_drive.name = "Pioneer BDR"
        mock_db_drive.maker = "Pioneer"
        mock_db_drive.model = "BDR-S12J"
        mock_db_drive.connection = "usb"

        with unittest.mock.patch("arm.api.v1.drives.os.path.exists", return_value=False), \
             unittest.mock.patch("arm.api.v1.drives.os.path.isdir", return_value=False), \
             unittest.mock.patch("builtins.open", side_effect=FileNotFoundError), \
             unittest.mock.patch("arm.api.v1.drives.subprocess.run",
                                 side_effect=FileNotFoundError("udevadm")):
            issues = []
            checks = _run_drive_diagnostic(
                {"sr0": mock_db_drive}, {"sr0"}, ["sr0"], issues
            )

        assert checks[0]["db_name"] == "Pioneer BDR"
        assert checks[0]["db_model"] == "Pioneer BDR-S12J"
        assert checks[0]["db_connection"] == "usb"
        assert checks[0]["in_database"] is True

    def test_drive_not_in_database(self):
        from arm.api.v1.drives import _run_drive_diagnostic

        with unittest.mock.patch("arm.api.v1.drives.os.path.exists", return_value=False), \
             unittest.mock.patch("arm.api.v1.drives.os.path.isdir", return_value=False), \
             unittest.mock.patch("builtins.open", side_effect=FileNotFoundError), \
             unittest.mock.patch("arm.api.v1.drives.subprocess.run",
                                 side_effect=FileNotFoundError("udevadm")):
            issues = []
            checks = _run_drive_diagnostic({}, {"sr0"}, ["sr0"], issues)

        assert checks[0]["in_database"] is False
        assert any("not found in ARM database" in i for i in checks[0]["issues"])


# ── Additional API job endpoint tests ────────────────────────────────────


class TestApiJobStart:
    """Test POST /api/v1/jobs/<id>/start endpoint."""

    def test_start_nonexistent_job(self, client):
        response = client.post('/api/v1/jobs/99999/start')
        assert response.status_code == 404

    def test_start_job_not_waiting(self, client, sample_job, app_context):
        from arm.ripper.utils import database_updater
        database_updater({"status": "active"}, sample_job)
        response = client.post(f'/api/v1/jobs/{sample_job.job_id}/start')
        assert response.status_code == 409

    def test_start_waiting_job_success(self, client, sample_job, app_context):
        from arm.ripper.utils import database_updater
        database_updater({"status": "waiting"}, sample_job)
        with unittest.mock.patch("arm.api.v1.jobs.svc_files.database_updater"):
            response = client.post(f'/api/v1/jobs/{sample_job.job_id}/start')
        assert response.status_code == 200
        assert response.json()["success"] is True


class TestApiJobCancel:
    """Test POST /api/v1/jobs/<id>/cancel endpoint."""

    def test_cancel_nonexistent_job(self, client):
        response = client.post('/api/v1/jobs/99999/cancel')
        assert response.status_code == 404

    def test_cancel_not_waiting(self, client, sample_job, app_context):
        from arm.ripper.utils import database_updater
        database_updater({"status": "active"}, sample_job)
        response = client.post(f'/api/v1/jobs/{sample_job.job_id}/cancel')
        assert response.status_code == 409

    def test_cancel_waiting_job_success(self, client, sample_job, app_context):
        from arm.ripper.utils import database_updater
        database_updater({"status": "waiting"}, sample_job)
        with unittest.mock.patch("arm.api.v1.jobs.svc_files.database_updater"):
            response = client.post(f'/api/v1/jobs/{sample_job.job_id}/cancel')
        assert response.status_code == 200
        assert response.json()["success"] is True


class TestApiJobConfig:
    """Test PATCH /api/v1/jobs/<id>/config endpoint."""

    def test_config_not_found(self, client):
        response = client.patch('/api/v1/jobs/99999/config', json={"RIPMETHOD": "mkv"})
        assert response.status_code == 404

    def test_config_empty_body(self, client, sample_job, app_context):
        response = client.patch(f'/api/v1/jobs/{sample_job.job_id}/config', json={})
        assert response.status_code == 400

    def test_config_invalid_ripmethod(self, client, sample_job, app_context):
        response = client.patch(
            f'/api/v1/jobs/{sample_job.job_id}/config',
            json={"RIPMETHOD": "invalid"}
        )
        assert response.status_code == 400

    def test_config_invalid_disctype(self, client, sample_job, app_context):
        response = client.patch(
            f'/api/v1/jobs/{sample_job.job_id}/config',
            json={"DISCTYPE": "invalid"}
        )
        assert response.status_code == 400

    def test_config_valid_ripmethod(self, client, sample_job, app_context):
        with unittest.mock.patch("arm.api.v1.jobs.svc_files.database_updater"):
            response = client.patch(
                f'/api/v1/jobs/{sample_job.job_id}/config',
                json={"RIPMETHOD": "backup"}
            )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_config_maxlength(self, client, sample_job, app_context):
        with unittest.mock.patch("arm.api.v1.jobs.svc_files.database_updater"):
            response = client.patch(
                f'/api/v1/jobs/{sample_job.job_id}/config',
                json={"MAXLENGTH": 7200}
            )
        assert response.status_code == 200

    def test_config_minlength(self, client, sample_job, app_context):
        with unittest.mock.patch("arm.api.v1.jobs.svc_files.database_updater"):
            response = client.patch(
                f'/api/v1/jobs/{sample_job.job_id}/config',
                json={"MINLENGTH": 300}
            )
        assert response.status_code == 200

    def test_config_audio_format_valid(self, client, sample_job, app_context):
        with unittest.mock.patch("arm.api.v1.jobs.svc_files.database_updater"):
            response = client.patch(
                f'/api/v1/jobs/{sample_job.job_id}/config',
                json={"AUDIO_FORMAT": "flac"}
            )
        assert response.status_code == 200

    def test_config_audio_format_invalid(self, client, sample_job, app_context):
        response = client.patch(
            f'/api/v1/jobs/{sample_job.job_id}/config',
            json={"AUDIO_FORMAT": "invalid_format"}
        )
        assert response.status_code == 400

    def test_config_speed_profile_valid(self, client, sample_job, app_context):
        with unittest.mock.patch("arm.api.v1.jobs.svc_files.database_updater"):
            response = client.patch(
                f'/api/v1/jobs/{sample_job.job_id}/config',
                json={"RIP_SPEED_PROFILE": "fast"}
            )
        assert response.status_code == 200

    def test_config_speed_profile_invalid(self, client, sample_job, app_context):
        response = client.patch(
            f'/api/v1/jobs/{sample_job.job_id}/config',
            json={"RIP_SPEED_PROFILE": "ludicrous"}
        )
        assert response.status_code == 400

    def test_config_disctype_valid(self, client, sample_job, app_context):
        with unittest.mock.patch("arm.api.v1.jobs.svc_files.database_updater"):
            response = client.patch(
                f'/api/v1/jobs/{sample_job.job_id}/config',
                json={"DISCTYPE": "dvd"}
            )
        assert response.status_code == 200

    def test_config_mainfeature(self, client, sample_job, app_context):
        with unittest.mock.patch("arm.api.v1.jobs.svc_files.database_updater"):
            response = client.patch(
                f'/api/v1/jobs/{sample_job.job_id}/config',
                json={"MAINFEATURE": True}
            )
        assert response.status_code == 200

    def test_config_no_valid_fields(self, client, sample_job, app_context):
        response = client.patch(
            f'/api/v1/jobs/{sample_job.job_id}/config',
            json={"UNKNOWN_FIELD": "value"}
        )
        assert response.status_code == 400

    def test_config_disc_folder_pattern_valid(self, client, sample_job, app_context):
        with unittest.mock.patch("arm.api.v1.jobs.svc_files.database_updater"):
            response = client.patch(
                f'/api/v1/jobs/{sample_job.job_id}/config',
                json={"MUSIC_DISC_FOLDER_PATTERN": "Disc {num}"}
            )
        assert response.status_code == 200

    def test_config_disc_folder_pattern_invalid(self, client, sample_job, app_context):
        response = client.patch(
            f'/api/v1/jobs/{sample_job.job_id}/config',
            json={"MUSIC_DISC_FOLDER_PATTERN": "no_num_placeholder"}
        )
        assert response.status_code == 400


class TestApiJobTracks:
    """Test PUT /api/v1/jobs/<id>/tracks endpoint."""

    def test_set_tracks_not_found(self, client):
        response = client.put('/api/v1/jobs/99999/tracks',
                               json={"tracks": []})
        assert response.status_code == 404

    def test_set_tracks_invalid_type(self, client, sample_job, app_context):
        response = client.put(
            f'/api/v1/jobs/{sample_job.job_id}/tracks',
            json={"tracks": "not a list"}
        )
        assert response.status_code == 400

    def test_set_tracks_success(self, client, sample_job, app_context):
        tracks_data = [
            {"track_number": "1", "title": "Track 1", "length_ms": 240000},
            {"track_number": "2", "title": "Track 2", "length_ms": 180000},
        ]
        response = client.put(
            f'/api/v1/jobs/{sample_job.job_id}/tracks',
            json={"tracks": tracks_data}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["tracks_count"] == 2


class TestApiJobMultiTitle:
    """Test POST /api/v1/jobs/<id>/multi-title endpoint."""

    def test_multi_title_not_found(self, client):
        response = client.post('/api/v1/jobs/99999/multi-title',
                                json={"enabled": True})
        assert response.status_code == 404

    def test_multi_title_toggle(self, client, sample_job, app_context):
        with unittest.mock.patch("arm.api.v1.jobs.svc_files.database_updater"):
            response = client.post(
                f'/api/v1/jobs/{sample_job.job_id}/multi-title',
                json={"enabled": True}
            )
        assert response.status_code == 200
        assert response.json()["multi_title"] is True


class TestApiTrackTitle:
    """Test PUT/DELETE /api/v1/jobs/<id>/tracks/<track_id>/title endpoints."""

    def _create_track(self, sample_job):
        from arm.models.track import Track
        from arm.database import db

        track = Track(
            job_id=sample_job.job_id,
            track_number="0",
            length=3600,
            aspect_ratio="16:9",
            fps=23.976,
            main_feature=True,
            source="MakeMKV",
            basename="title_t00.mkv",
            filename="title_t00.mkv",
        )
        db.session.add(track)
        db.session.commit()
        return track

    def test_update_track_title_not_found_job(self, client):
        response = client.put('/api/v1/jobs/99999/tracks/1/title',
                               json={"title": "Test"})
        assert response.status_code == 404

    def test_update_track_title_not_found_track(self, client, sample_job, app_context):
        response = client.put(
            f'/api/v1/jobs/{sample_job.job_id}/tracks/99999/title',
            json={"title": "Test"}
        )
        assert response.status_code == 404

    def test_update_track_title_success(self, client, sample_job, app_context):
        track = self._create_track(sample_job)
        response = client.put(
            f'/api/v1/jobs/{sample_job.job_id}/tracks/{track.track_id}/title',
            json={"title": "My Movie", "year": "2024", "video_type": "movie"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["updated"]["title"] == "My Movie"

    def test_update_track_no_fields(self, client, sample_job, app_context):
        track = self._create_track(sample_job)
        response = client.put(
            f'/api/v1/jobs/{sample_job.job_id}/tracks/{track.track_id}/title',
            json={}
        )
        assert response.status_code == 400

    def test_clear_track_title_success(self, client, sample_job, app_context):
        track = self._create_track(sample_job)
        track.title = "Custom"
        from arm.database import db
        db.session.commit()

        response = client.delete(
            f'/api/v1/jobs/{sample_job.job_id}/tracks/{track.track_id}/title'
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_clear_track_title_not_found(self, client, sample_job, app_context):
        response = client.delete(
            f'/api/v1/jobs/{sample_job.job_id}/tracks/99999/title'
        )
        assert response.status_code == 404


class TestApiTranscodeConfig:
    """Test PATCH /api/v1/jobs/<id>/transcode-config endpoint."""

    def test_transcode_config_not_found(self, client):
        response = client.patch('/api/v1/jobs/99999/transcode-config',
                                 json={"video_encoder": "x265"})
        assert response.status_code == 404

    def test_transcode_config_empty_body(self, client, sample_job, app_context):
        response = client.patch(
            f'/api/v1/jobs/{sample_job.job_id}/transcode-config',
            json=""
        )
        assert response.status_code == 400

    def test_transcode_config_unknown_key(self, client, sample_job, app_context):
        response = client.patch(
            f'/api/v1/jobs/{sample_job.job_id}/transcode-config',
            json={"bad_key": "value"}
        )
        assert response.status_code == 400

    def test_transcode_config_valid(self, client, sample_job, app_context):
        response = client.patch(
            f'/api/v1/jobs/{sample_job.job_id}/transcode-config',
            json={"video_encoder": "nvenc_h265", "video_quality": "22"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["overrides"]["video_encoder"] == "nvenc_h265"
        assert data["overrides"]["video_quality"] == 22


class TestApiTranscodeCallback:
    """Test POST /api/v1/jobs/<id>/transcode-callback endpoint."""

    def test_callback_not_found(self, client):
        response = client.post('/api/v1/jobs/99999/transcode-callback',
                                json={"status": "completed"})
        assert response.status_code == 404

    def test_callback_unknown_status(self, client, sample_job, app_context):
        response = client.post(
            f'/api/v1/jobs/{sample_job.job_id}/transcode-callback',
            json={"status": "invalid_status"}
        )
        assert response.status_code == 400

    def test_callback_transcoding(self, client, sample_job, app_context):
        response = client.post(
            f'/api/v1/jobs/{sample_job.job_id}/transcode-callback',
            json={"status": "transcoding"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "transcoding"

    def test_callback_completed(self, client, sample_job, app_context):
        response = client.post(
            f'/api/v1/jobs/{sample_job.job_id}/transcode-callback',
            json={"status": "completed"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    def test_callback_failed(self, client, sample_job, app_context):
        response = client.post(
            f'/api/v1/jobs/{sample_job.job_id}/transcode-callback',
            json={"status": "failed", "error": "codec error"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "fail"

    def test_callback_partial(self, client, sample_job, app_context):
        response = client.post(
            f'/api/v1/jobs/{sample_job.job_id}/transcode-callback',
            json={"status": "partial", "error": "Some tracks failed"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    def test_callback_with_track_results(self, client, sample_job, app_context):
        from arm.models.track import Track
        from arm.database import db

        track = Track(
            job_id=sample_job.job_id, track_number="1", length=3600,
            aspect_ratio="16:9", fps=23.976, main_feature=True,
            source="MakeMKV", basename="t.mkv", filename="t.mkv",
        )
        db.session.add(track)
        db.session.commit()

        response = client.post(
            f'/api/v1/jobs/{sample_job.job_id}/transcode-callback',
            json={
                "status": "completed",
                "track_results": [
                    {"track_number": "1", "status": "completed", "output_path": "/out/t.mkv"},
                ],
            }
        )
        assert response.status_code == 200
        db.session.refresh(track)
        assert track.status == "transcoded"

    def test_callback_track_failed(self, client, sample_job, app_context):
        from arm.models.track import Track
        from arm.database import db

        track = Track(
            job_id=sample_job.job_id, track_number="2", length=3600,
            aspect_ratio="16:9", fps=23.976, main_feature=True,
            source="MakeMKV", basename="t.mkv", filename="t.mkv",
        )
        db.session.add(track)
        db.session.commit()

        response = client.post(
            f'/api/v1/jobs/{sample_job.job_id}/transcode-callback',
            json={
                "status": "failed",
                "error": "codec problem",
                "track_results": [
                    {"track_number": "2", "status": "failed", "error": "codec error"},
                ],
            }
        )
        assert response.status_code == 200
        db.session.refresh(track)
        assert "transcode_failed" in track.status


class TestApiTvdbMatch:
    """Test POST /api/v1/jobs/<id>/tvdb-match endpoint."""

    def test_tvdb_match_not_found(self, client):
        response = client.post('/api/v1/jobs/99999/tvdb-match',
                                json={"season": 1})
        assert response.status_code == 404

    def test_tvdb_match_success(self, client, sample_job, app_context):
        mock_result = {"success": True, "matches": [], "season": 1}
        with unittest.mock.patch("arm.services.tvdb_sync.match_episodes_for_api",
                                  return_value=mock_result):
            response = client.post(
                f'/api/v1/jobs/{sample_job.job_id}/tvdb-match',
                json={"season": 1, "tolerance": 120, "apply": False}
            )
        assert response.status_code == 200
        assert response.json()["success"] is True


class TestApiTvdbEpisodes:
    """Test GET /api/v1/jobs/<id>/tvdb-episodes endpoint."""

    def test_tvdb_episodes_not_found(self, client):
        response = client.get('/api/v1/jobs/99999/tvdb-episodes?season=1')
        assert response.status_code == 404

    def test_tvdb_episodes_no_tvdb_id(self, client, sample_job, app_context):
        response = client.get(
            f'/api/v1/jobs/{sample_job.job_id}/tvdb-episodes?season=1'
        )
        assert response.status_code == 400

    def test_tvdb_episodes_success(self, client, sample_job, app_context):
        from arm.database import db
        sample_job.tvdb_id = 12345
        db.session.commit()

        mock_episodes = [{"number": 1, "name": "Pilot", "runtime": 3300}]
        with unittest.mock.patch("arm.services.matching._async_compat.run_async",
                                  return_value=mock_episodes):
            response = client.get(
                f'/api/v1/jobs/{sample_job.job_id}/tvdb-episodes?season=1'
            )
        assert response.status_code == 200
        data = response.json()
        assert data["tvdb_id"] == 12345
        assert len(data["episodes"]) == 1


class TestApiCleanForFilename:
    """Test _clean_for_filename helper in jobs.py."""

    def test_colons_replaced(self):
        from arm.api.v1.jobs import _clean_for_filename
        assert _clean_for_filename("Movie: Subtitle") == "Movie- Subtitle"

    def test_ampersand_replaced(self):
        from arm.api.v1.jobs import _clean_for_filename
        assert _clean_for_filename("Tom & Jerry") == "Tom and Jerry"

    def test_backslash_replaced(self):
        from arm.api.v1.jobs import _clean_for_filename
        assert _clean_for_filename("A\\B") == "A - B"

    def test_special_chars_removed(self):
        from arm.api.v1.jobs import _clean_for_filename
        result = _clean_for_filename("Movie! (2024) #1")
        assert "!" not in result
        assert "#" not in result


class TestApiAutoFlagTracks:
    """Test _auto_flag_tracks helper."""

    def test_mainfeature_single_type(self, app_context):
        from arm.api.v1.jobs import _auto_flag_tracks
        from arm.models.track import Track
        from arm.models.job import Job
        from arm.database import db

        with unittest.mock.patch.object(Job, 'parse_udev'), \
             unittest.mock.patch.object(Job, 'get_pid'):
            job = Job('/dev/sr0')
        job.video_type = "movie"
        job.multi_title = False
        db.session.add(job)
        db.session.flush()

        t1 = Track(job_id=job.job_id, track_number="0", length=7200,
                    aspect_ratio="16:9", fps=23.976, main_feature=True,
                    source="MakeMKV", basename="t.mkv", filename="t.mkv",
                    chapters=20, filesize=10000000)
        t2 = Track(job_id=job.job_id, track_number="1", length=120,
                    aspect_ratio="16:9", fps=23.976, main_feature=False,
                    source="MakeMKV", basename="t2.mkv", filename="t2.mkv",
                    chapters=1, filesize=100)
        db.session.add_all([t1, t2])
        db.session.commit()

        _auto_flag_tracks(job, mainfeature=True)
        db.session.refresh(t1)
        db.session.refresh(t2)
        assert t1.enabled is True
        assert t2.enabled is False

    def test_mainfeature_off_enables_all(self, app_context):
        from arm.api.v1.jobs import _auto_flag_tracks
        from arm.models.track import Track
        from arm.models.job import Job
        from arm.database import db

        with unittest.mock.patch.object(Job, 'parse_udev'), \
             unittest.mock.patch.object(Job, 'get_pid'):
            job = Job('/dev/sr0')
        job.video_type = "movie"
        db.session.add(job)
        db.session.flush()

        t1 = Track(job_id=job.job_id, track_number="0", length=7200,
                    aspect_ratio="16:9", fps=23.976, main_feature=True,
                    source="MakeMKV", basename="t.mkv", filename="t.mkv")
        t1.enabled = False
        db.session.add(t1)
        db.session.commit()

        _auto_flag_tracks(job, mainfeature=False)
        db.session.refresh(t1)
        assert t1.enabled is True
