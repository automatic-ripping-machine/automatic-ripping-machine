"""Tests for the REST API layer (arm/api/v1/)."""
import unittest.mock
from urllib.parse import urlparse

import pytest
from fastapi.testclient import TestClient

from arm.models.job import JobState


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
        """Can only pause jobs in MANUAL_PAUSED status."""
        from arm.ripper.utils import database_updater
        database_updater({"status": "video_ripping"}, sample_job)
        response = client.post(f'/api/v1/jobs/{sample_job.job_id}/pause')
        assert response.status_code == 409

    def test_pause_toggles_on(self, client, sample_job, app_context):
        from arm.ripper.utils import database_updater
        from arm.database import db
        database_updater({"status": "manual_paused"}, sample_job)
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
        database_updater({"status": "manual_paused", "manual_pause": True}, sample_job)
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


class TestSkipAndFinalize:
    """Test POST /api/v1/jobs/<id>/skip-and-finalize endpoint."""

    def test_skip_and_finalize_success(self, client, sample_job, app_context):
        """TRANSCODE_WAITING job should finalize and become SUCCESS."""
        from arm.ripper.utils import database_updater
        from arm.database import db
        database_updater({"status": "waiting_transcode"}, sample_job)

        with unittest.mock.patch('arm.ripper.naming.finalize_output'):
            response = client.post(f'/api/v1/jobs/{sample_job.job_id}/skip-and-finalize')

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "finalized" in data["message"].lower()
        db.session.refresh(sample_job)
        assert sample_job.status == "success"

    def test_skip_and_finalize_wrong_state(self, client, sample_job, app_context):
        """Job in VIDEO_RIPPING state should return 409."""
        from arm.ripper.utils import database_updater
        database_updater({"status": "video_ripping"}, sample_job)

        response = client.post(f'/api/v1/jobs/{sample_job.job_id}/skip-and-finalize')
        assert response.status_code == 409
        data = response.json()
        assert data["success"] is False

    def test_skip_and_finalize_not_found(self, client):
        """Non-existent job should return 404."""
        response = client.post('/api/v1/jobs/99999/skip-and-finalize')
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False

    def test_skip_and_finalize_transcoding_active_rejected(self, client, sample_job, app_context):
        """Skip-and-finalize MUST reject TRANSCODE_ACTIVE to avoid racing the live transcoder."""
        from arm.database import db
        sample_job.status = JobState.TRANSCODE_ACTIVE.value
        db.session.commit()

        response = client.post(f'/api/v1/jobs/{sample_job.job_id}/skip-and-finalize')

        assert response.status_code == 409
        data = response.json()
        assert data['success'] is False
        assert 'transcode_waiting' in data['error'].lower()
        # Hint at abandon for the user's actual need
        assert 'abandon' in data['error'].lower()
        # Job status must not have changed
        assert sample_job.status == JobState.TRANSCODE_ACTIVE.value

    @pytest.mark.parametrize("state", [
        JobState.VIDEO_RIPPING.value,
        JobState.TRANSCODE_ACTIVE.value,
        JobState.SUCCESS.value,
        JobState.FAILURE.value,
        JobState.MANUAL_PAUSED.value,
    ])
    def test_skip_and_finalize_rejects_non_waiting_states(self, client, sample_job, app_context, state):
        """Only TRANSCODE_WAITING is allowed - everything else 409s."""
        from arm.database import db
        sample_job.status = state
        db.session.commit()

        response = client.post(f'/api/v1/jobs/{sample_job.job_id}/skip-and-finalize')

        assert response.status_code == 409
        assert sample_job.status == state  # unchanged


class TestForceComplete:
    """Test POST /api/v1/jobs/<id>/force-complete endpoint."""

    def test_force_complete_waiting_transcode(self, client, sample_job, app_context):
        """TRANSCODE_WAITING job should be marked SUCCESS without moving files."""
        from arm.ripper.utils import database_updater
        from arm.database import db
        database_updater({"status": "waiting_transcode"}, sample_job)

        response = client.post(f'/api/v1/jobs/{sample_job.job_id}/force-complete')
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "waiting_transcode" in data["message"]
        db.session.refresh(sample_job)
        assert sample_job.status == "success"

    def test_force_complete_already_success(self, client, sample_job, app_context):
        """Already-complete job should return success without error."""
        from arm.ripper.utils import database_updater
        database_updater({"status": "success"}, sample_job)

        response = client.post(f'/api/v1/jobs/{sample_job.job_id}/force-complete')
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "already" in data["message"].lower()

    def test_force_complete_not_found(self, client):
        """Non-existent job should return 404."""
        response = client.post('/api/v1/jobs/99999/force-complete')
        assert response.status_code == 404

    def test_force_complete_failed_job(self, client, sample_job, app_context):
        """Even a failed job can be force-completed."""
        from arm.ripper.utils import database_updater
        from arm.database import db
        database_updater({"status": "fail"}, sample_job)

        response = client.post(f'/api/v1/jobs/{sample_job.job_id}/force-complete')
        assert response.status_code == 200
        db.session.refresh(sample_job)
        assert sample_job.status == "success"


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
                       version_file_error=None, db_file_exists=True,
                       db_uri=None, has_alembic_table=True):
        """Call the version endpoint with all dependencies mocked."""
        import unittest.mock as m

        config = {"INSTALLPATH": install_path, "DBFILE": db_file}
        proc = m.Mock(stdout=makemkv_output, stderr="")
        mock_script = m.Mock()
        mock_script.get_current_head.return_value = head

        # Build a mock engine + connection chain. We can't share a real
        # in-memory sqlite engine across the test client's worker thread,
        # so mock the SQLAlchemy surface used by _read_db_revisions:
        # create_engine(...) -> engine; inspect(engine).has_table(...);
        # engine.connect().__enter__() -> conn;
        # conn.execute(text(...)).fetchone() -> row.
        mock_engine = m.MagicMock()
        mock_inspector = m.MagicMock()
        mock_inspector.has_table.return_value = has_alembic_table
        mock_result = m.MagicMock()
        mock_result.fetchone.return_value = db_row
        mock_conn_ctx = m.MagicMock()
        mock_conn_ctx.execute.return_value = mock_result
        mock_engine.connect.return_value.__enter__.return_value = mock_conn_ctx

        # db_uri defaults to sqlite:///<db_file> so existing call sites
        # behave the same; tests can pass db_uri="" to force the empty
        # branch.
        if db_uri is None:
            db_uri = ('sqlite:///' + db_file) if db_file else ''

        open_side = version_file_error if version_file_error else None
        open_mock = m.mock_open(read_data=arm_version) if not version_file_error else None

        with (
            m.patch("arm.api.v1.system.cfg.arm_config", config),
            m.patch("arm.api.v1.system.cfg.get_db_uri", return_value=db_uri),
            m.patch("arm.api.v1.system.subprocess.run", return_value=proc),
            m.patch("arm.api.v1.system.os.path.isfile", return_value=db_file_exists),
            m.patch("arm.api.v1.system.ScriptDirectory.from_config", return_value=mock_script),
            m.patch("arm.api.v1.system.create_engine", return_value=mock_engine),
            m.patch("arm.api.v1.system.inspect", return_value=mock_inspector),
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
        """db_version matches the revision returned by the database."""
        response = self._patch_version(client, db_row=("rev_99x",))
        assert response.status_code == 200
        assert response.json()["db_version"] == "rev_99x"

    def test_version_db_unknown_when_no_dbfile(self, client):
        """db_version is 'unknown' when the DSN is empty."""
        response = self._patch_version(client, db_file="", db_file_exists=False, db_uri="")
        assert response.status_code == 200
        assert response.json()["db_version"] == "unknown"

    def test_version_includes_db_path_and_size(self, client):
        """The UI's settings/system-info pulls db_path + db_size_bytes from /version."""
        import unittest.mock as m
        with m.patch("arm.api.v1.system.os.path.getsize", return_value=12345):
            response = self._patch_version(client, db_file="arm.db")
        assert response.status_code == 200
        data = response.json()
        assert data["db_path"] == "arm.db"
        assert data["db_size_bytes"] == 12345

    def test_version_db_path_none_when_dbfile_missing(self, client):
        """db_path/db_size_bytes are None when DSN is empty."""
        response = self._patch_version(client, db_file="", db_file_exists=False, db_uri="")
        data = response.json()
        assert data["db_path"] is None
        assert data["db_size_bytes"] is None

    def test_version_db_version_unknown_on_db_error(self, client):
        """If create_engine or the alembic_version query raises, db_version is 'unknown'."""
        import unittest.mock as m
        from sqlalchemy.exc import OperationalError
        config = {"INSTALLPATH": "/opt/arm", "DBFILE": "arm.db"}
        mock_script = m.Mock()
        mock_script.get_current_head.return_value = "def456"
        with (
            m.patch("arm.api.v1.system.cfg.arm_config", config),
            m.patch("arm.api.v1.system.cfg.get_db_uri", return_value="sqlite:///arm.db"),
            m.patch("arm.api.v1.system.subprocess.run",
                    return_value=m.Mock(stdout="", stderr="")),
            m.patch("arm.api.v1.system.os.path.isfile", return_value=True),
            m.patch("arm.api.v1.system.ScriptDirectory.from_config", return_value=mock_script),
            m.patch("arm.api.v1.system.create_engine",
                    side_effect=OperationalError("stmt", {}, Exception("file is not a database"))),
            m.patch("builtins.open", m.mock_open(read_data="1.0.0")),
        ):
            response = client.get('/api/v1/system/version')
        assert response.status_code == 200
        data = response.json()
        assert data["db_version"] == "unknown"
        assert data["db_head"] == "def456"

    def test_version_db_path_reflects_postgres_dsn(self, client):
        """For non-sqlite DSN, db_path masks the password and db_size_bytes is None."""
        pg_uri = "postgresql://arm:secret@db.example.com:5432/arm"
        response = self._patch_version(client, db_uri=pg_uri, db_row=("rev_pg",))
        assert response.status_code == 200
        data = response.json()
        # db_path is masked: dialect/host/port/db preserved, password redacted.
        assert data["db_path"] is not None
        assert "secret" not in data["db_path"]      # password gone
        assert "arm" in data["db_path"]              # username preserved
        # host preserved - check the parsed hostname, not a substring, so the
        # assertion can't be satisfied by an attacker-style host such as
        # "db.example.com.evil.test".
        assert urlparse(data["db_path"]).hostname == "db.example.com"
        assert "postgresql" in data["db_path"]       # dialect preserved
        # db_size_bytes is None for non-sqlite (file size meaningless)
        assert data["db_size_bytes"] is None
        assert data["db_version"] == "rev_pg"

    def test_read_db_revisions_does_not_create_missing_sqlite_file(self, tmp_path):
        """Regression: pre-PR-A _read_db_revisions used os.path.isfile guard
        before connecting; the SQLAlchemy refactor inadvertently dropped that
        guard, causing inspect(engine).has_table() to side-effect-create a
        0-byte sqlite file. The fix re-adds the guard so this purely
        diagnostic endpoint never mutates the filesystem."""
        from arm.api.v1.system import _read_db_revisions
        nonexistent = tmp_path / "does_not_exist.db"
        db_uri = f"sqlite:///{nonexistent}"

        db_version, _db_head = _read_db_revisions(
            db_uri, install_path=str(tmp_path / "dummy")
        )

        assert db_version == "unknown"
        assert not nonexistent.exists(), (
            f"_read_db_revisions auto-created {nonexistent}; should not "
            f"side-effect-mutate the filesystem"
        )


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


class TestApiJobNamingUpdate:
    """Test PATCH /api/v1/jobs/<id>/naming endpoint."""

    def test_set_title_pattern(self, client, sample_job, app_context):
        response = client.patch(
            f'/api/v1/jobs/{sample_job.job_id}/naming',
            json={"title_pattern_override": "{title} ({year})"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["title_pattern_override"] == "{title} ({year})"

    def test_clear_pattern(self, client, sample_job, app_context):
        response = client.patch(
            f'/api/v1/jobs/{sample_job.job_id}/naming',
            json={"title_pattern_override": ""},
        )
        assert response.status_code == 200
        assert response.json()["title_pattern_override"] is None

    def test_invalid_variable(self, client, sample_job, app_context):
        response = client.patch(
            f'/api/v1/jobs/{sample_job.job_id}/naming',
            json={"title_pattern_override": "{bogus}"},
        )
        assert response.status_code == 400
        assert "invalid_vars" in response.json()

    def test_pattern_too_long(self, client, sample_job, app_context):
        response = client.patch(
            f'/api/v1/jobs/{sample_job.job_id}/naming',
            json={"title_pattern_override": "x" * 513},
        )
        assert response.status_code == 400
        assert "too long" in response.json()["error"]

    def test_nonexistent_job(self, client):
        response = client.patch(
            '/api/v1/jobs/99999/naming',
            json={"title_pattern_override": "{title}"},
        )
        assert response.status_code == 404


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

    def test_rescan_force_deletes_non_processing(self, client, app_context):
        d_idle = unittest.mock.MagicMock(processing=False)
        d_busy = unittest.mock.MagicMock(processing=True)
        with unittest.mock.patch("arm.services.drives.drives_update", return_value=0), \
             unittest.mock.patch("arm.api.v1.drives.SystemDrives") as mock_sd, \
             unittest.mock.patch("arm.api.v1.drives.db") as mock_db:
            mock_sd.query.all.return_value = [d_idle, d_busy]
            mock_sd.query.count.side_effect = [1, 1]
            response = client.post('/api/v1/drives/rescan?force=true')
        assert response.status_code == 200
        assert response.json()["success"] is True
        mock_db.session.delete.assert_called_once_with(d_idle)
        mock_db.session.commit.assert_called()


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

    def test_update_rip_speed(self, client, app_context):
        mock_drive = unittest.mock.MagicMock()
        mock_drive.drive_id = 1
        with unittest.mock.patch("arm.api.v1.drives.SystemDrives") as mock_sd, \
             unittest.mock.patch("arm.api.v1.drives.db"):
            mock_sd.query.get.return_value = mock_drive
            response = client.patch('/api/v1/drives/1', json={"rip_speed": 4})
        assert response.status_code == 200
        assert mock_drive.rip_speed == 4

    def test_update_rip_speed_null_clears(self, client, app_context):
        mock_drive = unittest.mock.MagicMock()
        mock_drive.drive_id = 1
        with unittest.mock.patch("arm.api.v1.drives.SystemDrives") as mock_sd, \
             unittest.mock.patch("arm.api.v1.drives.db"):
            mock_sd.query.get.return_value = mock_drive
            response = client.patch('/api/v1/drives/1', json={"rip_speed": None})
        assert response.status_code == 200
        assert mock_drive.rip_speed is None

    def test_update_rip_speed_invalid(self, client, app_context):
        mock_drive = unittest.mock.MagicMock()
        mock_drive.drive_id = 1
        with unittest.mock.patch("arm.api.v1.drives.SystemDrives") as mock_sd:
            mock_sd.query.get.return_value = mock_drive
            response = client.patch('/api/v1/drives/1', json={"rip_speed": 0})
        assert response.status_code == 400

    def test_update_rip_speed_too_high(self, client, app_context):
        mock_drive = unittest.mock.MagicMock()
        mock_drive.drive_id = 1
        with unittest.mock.patch("arm.api.v1.drives.SystemDrives") as mock_sd:
            mock_sd.query.get.return_value = mock_drive
            response = client.patch('/api/v1/drives/1', json={"rip_speed": 100})
        assert response.status_code == 400

    def test_update_prescan_cache_mb(self, client, app_context):
        mock_drive = unittest.mock.MagicMock()
        mock_drive.drive_id = 1
        with unittest.mock.patch("arm.api.v1.drives.SystemDrives") as mock_sd, \
             unittest.mock.patch("arm.api.v1.drives.db"):
            mock_sd.query.get.return_value = mock_drive
            response = client.patch('/api/v1/drives/1', json={"prescan_cache_mb": 64})
        assert response.status_code == 200
        assert mock_drive.prescan_cache_mb == 64

    def test_update_prescan_timeout(self, client, app_context):
        mock_drive = unittest.mock.MagicMock()
        mock_drive.drive_id = 1
        with unittest.mock.patch("arm.api.v1.drives.SystemDrives") as mock_sd, \
             unittest.mock.patch("arm.api.v1.drives.db"):
            mock_sd.query.get.return_value = mock_drive
            response = client.patch('/api/v1/drives/1', json={"prescan_timeout": 600})
        assert response.status_code == 200
        assert mock_drive.prescan_timeout == 600

    def test_update_prescan_retries(self, client, app_context):
        mock_drive = unittest.mock.MagicMock()
        mock_drive.drive_id = 1
        with unittest.mock.patch("arm.api.v1.drives.SystemDrives") as mock_sd, \
             unittest.mock.patch("arm.api.v1.drives.db"):
            mock_sd.query.get.return_value = mock_drive
            response = client.patch('/api/v1/drives/1', json={"prescan_retries": 5})
        assert response.status_code == 200
        assert mock_drive.prescan_retries == 5

    def test_update_disc_enum_timeout(self, client, app_context):
        mock_drive = unittest.mock.MagicMock()
        mock_drive.drive_id = 1
        with unittest.mock.patch("arm.api.v1.drives.SystemDrives") as mock_sd, \
             unittest.mock.patch("arm.api.v1.drives.db"):
            mock_sd.query.get.return_value = mock_drive
            response = client.patch('/api/v1/drives/1', json={"disc_enum_timeout": 120})
        assert response.status_code == 200
        assert mock_drive.disc_enum_timeout == 120

    def test_update_prescan_field_null_clears(self, client, app_context):
        mock_drive = unittest.mock.MagicMock()
        mock_drive.drive_id = 1
        with unittest.mock.patch("arm.api.v1.drives.SystemDrives") as mock_sd, \
             unittest.mock.patch("arm.api.v1.drives.db"):
            mock_sd.query.get.return_value = mock_drive
            response = client.patch('/api/v1/drives/1', json={"prescan_cache_mb": None})
        assert response.status_code == 200
        assert mock_drive.prescan_cache_mb is None

    def test_update_prescan_field_out_of_range(self, client, app_context):
        mock_drive = unittest.mock.MagicMock()
        mock_drive.drive_id = 1
        with unittest.mock.patch("arm.api.v1.drives.SystemDrives") as mock_sd:
            mock_sd.query.get.return_value = mock_drive
            response = client.patch('/api/v1/drives/1', json={"prescan_cache_mb": 9999})
        assert response.status_code == 400

    def test_update_prescan_field_invalid_type(self, client, app_context):
        mock_drive = unittest.mock.MagicMock()
        mock_drive.drive_id = 1
        with unittest.mock.patch("arm.api.v1.drives.SystemDrives") as mock_sd:
            mock_sd.query.get.return_value = mock_drive
            response = client.patch('/api/v1/drives/1', json={"prescan_retries": "abc"})
        assert response.status_code == 400


class TestApiDrivePrescanSerialization:
    """Test prescan fields in drive listing endpoints."""

    def test_drives_list_includes_prescan_fields(self, client, sample_drives, app_context):
        from arm.database import db
        sample_drives[0].prescan_cache_mb = 128
        sample_drives[0].prescan_timeout = 600
        sample_drives[0].prescan_retries = 5
        sample_drives[0].disc_enum_timeout = 120
        db.session.commit()

        response = client.get('/api/v1/drives')
        data = response.json()
        drive = next(d for d in data["drives"] if d["name"] == "Living Room")
        assert drive["prescan_cache_mb"] == 128
        assert drive["prescan_timeout"] == 600
        assert drive["prescan_retries"] == 5
        assert drive["disc_enum_timeout"] == 120

    def test_drives_list_null_prescan_fields(self, client, sample_drives):
        response = client.get('/api/v1/drives')
        data = response.json()
        drive = next(d for d in data["drives"] if d["name"] == "Living Room")
        assert drive["prescan_cache_mb"] is None
        assert drive["prescan_timeout"] is None
        assert drive["prescan_retries"] is None
        assert drive["disc_enum_timeout"] is None


class TestApiDriveRipSpeed:
    """Test rip_speed in drive listing endpoints."""

    def test_drives_list_includes_rip_speed(self, client, sample_drives, app_context):
        from arm.database import db
        sample_drives[0].rip_speed = 4
        db.session.commit()

        response = client.get('/api/v1/drives')
        data = response.json()
        drive = next(d for d in data["drives"] if d["name"] == "Living Room")
        assert drive["rip_speed"] == 4

    def test_drives_list_null_rip_speed(self, client, sample_drives):
        response = client.get('/api/v1/drives')
        data = response.json()
        drive = next(d for d in data["drives"] if d["name"] == "Living Room")
        assert drive["rip_speed"] is None


class TestApiApplyDriveRipSpeed:
    """Test _apply_drive_rip_speed writes to settings.conf."""

    def test_applies_speed(self, tmp_path, sample_job, app_context):
        from arm.ripper.makemkv import _apply_drive_rip_speed
        from arm.database import db
        from arm.models.system_drives import SystemDrives

        # Create a drive with rip_speed and assign to job
        drive = SystemDrives()
        drive.name = "Test"
        drive.mount = "/dev/sr0"
        drive.stale = False
        drive.rip_speed = 4
        db.session.add(drive)
        db.session.flush()
        sample_job.drive = drive
        db.session.commit()

        # Create fake settings.conf
        settings = tmp_path / ".MakeMKV" / "settings.conf"
        settings.parent.mkdir()
        settings.write_text('app_Key = "test"\nspeed_DRIVE_ID = "0=99"\n')

        with unittest.mock.patch("os.path.expanduser", return_value=str(settings)):
            _apply_drive_rip_speed(sample_job)

        content = settings.read_text()
        assert '"0=4"' in content
        assert '"0=99"' not in content

    def test_no_speed_set_skips(self, sample_job, app_context):
        from arm.ripper.makemkv import _apply_drive_rip_speed
        from arm.database import db
        from arm.models.system_drives import SystemDrives

        drive = SystemDrives()
        drive.name = "Test"
        drive.mount = "/dev/sr0"
        drive.stale = False
        drive.rip_speed = None
        db.session.add(drive)
        db.session.flush()
        sample_job.drive = drive
        db.session.commit()

        # Should not touch settings.conf at all
        with unittest.mock.patch("builtins.open") as mock_open:
            _apply_drive_rip_speed(sample_job)
            mock_open.assert_not_called()


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
        assert response.status_code == 422  # Pydantic validation

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
        assert response.status_code == 422  # Pydantic validation

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
        assert response.status_code == 422  # Pydantic validation

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
        assert response.status_code == 422  # Pydantic validation

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
        assert response.status_code == 422  # Pydantic validation

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

        mock_usage = {"total": 500107862016, "used": 250053931008, "free": 250053931008, "percent": 50.0}
        with unittest.mock.patch("arm.api.v1.system.psutil.cpu_percent", return_value=25.0), \
             unittest.mock.patch("arm.api.v1.system.psutil.sensors_temperatures",
                                 return_value={}), \
             unittest.mock.patch("arm.api.v1.system.psutil.virtual_memory",
                                 return_value=mock_mem), \
             unittest.mock.patch("arm.services.disk_usage_cache.get_disk_usage",
                                 return_value=mock_usage), \
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
        database_updater({"status": "video_ripping"}, sample_job)
        response = client.post(f'/api/v1/jobs/{sample_job.job_id}/start')
        assert response.status_code == 409

    def test_start_waiting_job_success(self, client, sample_job, app_context):
        from arm.ripper.utils import database_updater
        database_updater({"status": "manual_paused"}, sample_job)
        with unittest.mock.patch("arm.api.v1.jobs.svc_files.database_updater"):
            response = client.post(f'/api/v1/jobs/{sample_job.job_id}/start')
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_start_waiting_folder_job_spawns_folder_thread(self, client, sample_job, app_context, tmp_path):
        from arm.ripper.utils import database_updater
        database_updater(
            {"status": "manual_paused", "source_type": "folder",
             "source_path": str(tmp_path / "x")},
            sample_job,
        )
        with unittest.mock.patch("arm.api.v1.jobs.threading.Thread") as mock_thread:
            response = client.post(f'/api/v1/jobs/{sample_job.job_id}/start')
        assert response.status_code == 200
        assert response.json()["status"] == "video_ripping"
        # Verify it dispatched to the folder helper, not the ISO helper.
        from arm.api.v1 import jobs as jobs_module
        kwargs = mock_thread.call_args.kwargs
        assert kwargs["target"] is jobs_module._rip_folder_by_id

    def test_start_waiting_iso_job_spawns_iso_thread(self, client, sample_job, app_context, tmp_path):
        from arm.ripper.utils import database_updater
        database_updater(
            {"status": "manual_paused", "source_type": "iso",
             "source_path": str(tmp_path / "x.iso")},
            sample_job,
        )
        with unittest.mock.patch("arm.api.v1.jobs.threading.Thread") as mock_thread:
            response = client.post(f'/api/v1/jobs/{sample_job.job_id}/start')
        assert response.status_code == 200
        assert response.json()["status"] == "video_ripping"
        from arm.api.v1 import jobs as jobs_module
        kwargs = mock_thread.call_args.kwargs
        assert kwargs["target"] is jobs_module._rip_iso_by_id


class TestApiJobCancel:
    """Test POST /api/v1/jobs/<id>/cancel endpoint."""

    def test_cancel_nonexistent_job(self, client):
        response = client.post('/api/v1/jobs/99999/cancel')
        assert response.status_code == 404

    def test_cancel_not_waiting(self, client, sample_job, app_context):
        from arm.ripper.utils import database_updater
        database_updater({"status": "video_ripping"}, sample_job)
        response = client.post(f'/api/v1/jobs/{sample_job.job_id}/cancel')
        assert response.status_code == 409

    def test_cancel_waiting_job_success(self, client, sample_job, app_context):
        from arm.ripper.utils import database_updater
        database_updater({"status": "manual_paused"}, sample_job)
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
                                 json={"preset_slug": "cpu_balanced"})
        assert response.status_code == 404

    def test_transcode_config_empty_body(self, client, sample_job, app_context):
        response = client.patch(
            f'/api/v1/jobs/{sample_job.job_id}/transcode-config',
            json=""
        )
        assert response.status_code == 422

    def test_transcode_config_unknown_key(self, client, sample_job, app_context):
        response = client.patch(
            f'/api/v1/jobs/{sample_job.job_id}/transcode-config',
            json={"bad_key": "value"}
        )
        assert response.status_code == 400

    def test_transcode_config_valid(self, client, sample_job, app_context):
        response = client.patch(
            f'/api/v1/jobs/{sample_job.job_id}/transcode-config',
            json={"preset_slug": "nvidia_balanced", "delete_source": "true"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["overrides"]["preset_slug"] == "nvidia_balanced"
        assert data["overrides"]["delete_source"] is True


class TestTranscodeOverridesNewShape:
    """Unit tests for the preset-based transcode override validation."""

    def test_validate_preset_slug(self):
        from arm.api.v1.jobs import _validate_transcode_overrides
        body = {"preset_slug": "nvidia_balanced"}
        overrides, errors = _validate_transcode_overrides(body)
        assert not errors
        assert overrides["preset_slug"] == "nvidia_balanced"

    def test_validate_overrides_dict(self):
        from arm.api.v1.jobs import _validate_transcode_overrides
        body = {
            "preset_slug": "nvidia_balanced",
            "overrides": {"shared": {"audio_encoder": "aac"}, "tiers": {"uhd": {"video_quality": 18}}},
        }
        overrides, errors = _validate_transcode_overrides(body)
        assert not errors
        assert overrides["preset_slug"] == "nvidia_balanced"
        assert overrides["overrides"]["tiers"]["uhd"]["video_quality"] == 18

    def test_reject_old_flat_keys(self):
        """Legacy flat-key shapes (pre-preset-rollout) must be rejected by the
        TranscodeJobConfig contract (extra='forbid' on the envelope).

        NOTE: with contracts typing, preset_slug is required on every PATCH;
        the old ad-hoc validator allowed partial bodies. The UI always sends
        the full envelope so this is a tightening, not a regression.
        """
        from arm.api.v1.jobs import _validate_transcode_overrides
        body = {"preset_slug": "software-balanced", "video_encoder": "nvenc_h265"}
        overrides, errors = _validate_transcode_overrides(body)
        assert errors
        # Pydantic surfaces "Extra inputs are not permitted" for extra=forbid
        assert "video_encoder" in errors[0]

    def test_overrides_must_be_dict(self):
        from arm.api.v1.jobs import _validate_transcode_overrides
        body = {"preset_slug": "software-balanced", "overrides": "not_a_dict"}
        overrides, errors = _validate_transcode_overrides(body)
        assert errors
        # Error references the overrides field
        assert "overrides" in errors[0]

    def test_delete_source_still_works(self):
        """Pydantic coerces string 'true'/'false' to bool by default."""
        from arm.api.v1.jobs import _validate_transcode_overrides
        body = {"preset_slug": "software-balanced", "delete_source": "true"}
        overrides, errors = _validate_transcode_overrides(body)
        assert not errors
        assert overrides["delete_source"] is True

    def test_preset_slug_accepts_builtin_with_underscore(self):
        from arm.api.v1.jobs import _validate_transcode_overrides
        overrides, errors = _validate_transcode_overrides({"preset_slug": "nvidia_balanced"})
        assert not errors
        assert overrides["preset_slug"] == "nvidia_balanced"

    def test_preset_slug_accepts_custom_with_hyphen(self):
        from arm.api.v1.jobs import _validate_transcode_overrides
        overrides, errors = _validate_transcode_overrides({"preset_slug": "my-custom-preset"})
        assert not errors
        assert overrides["preset_slug"] == "my-custom-preset"

    def test_preset_slug_rejects_whitespace_and_uppercase(self):
        from arm.api.v1.jobs import _validate_transcode_overrides
        for bad in ("Nvidia_Balanced", "nvidia balanced"):
            _, errors = _validate_transcode_overrides({"preset_slug": bad})
            assert errors, f"expected rejection for {bad!r}"
            assert "preset_slug" in errors[0]

    def test_preset_slug_rejects_path_traversal(self):
        from arm.api.v1.jobs import _validate_transcode_overrides
        # Slug length cap is now 64 (TranscodeJobConfig pattern); was 100 in the
        # ad-hoc validator. 65 chars still rejected.
        for bad in ("../etc/passwd", "nvidia/balanced", "nvidia;rm -rf /", "a" * 65):
            _, errors = _validate_transcode_overrides({"preset_slug": bad})
            assert errors, f"expected rejection for {bad!r}"
            assert "preset_slug" in errors[0]

    def test_preset_slug_rejects_empty(self):
        from arm.api.v1.jobs import _validate_transcode_overrides
        # Empty string skips validation entirely (treated as "no override")
        overrides, errors = _validate_transcode_overrides({"preset_slug": ""})
        assert not errors
        assert "preset_slug" not in overrides


class TestTranscodeConfigTypedValidation:
    """Phase-2 contracts integration: PATCH /transcode-config now validates via
    arm_contracts.TranscodeJobConfig; malformed payloads return 400 with the
    pydantic error list."""

    def test_patch_accepts_valid_shape(self, client, sample_job, app_context):
        resp = client.patch(
            f"/api/v1/jobs/{sample_job.job_id}/transcode-config",
            json={
                "preset_slug": "software-balanced",
                "overrides": {
                    "shared": {"audio_encoder": "aac"},
                    "tiers": {"dvd": {"video_quality": 20}},
                },
            },
        )
        assert resp.status_code == 200, resp.text

    def test_patch_rejects_bad_slug(self, client, sample_job, app_context):
        resp = client.patch(
            f"/api/v1/jobs/{sample_job.job_id}/transcode-config",
            json={"preset_slug": "BAD SLUG", "overrides": {}},
        )
        assert resp.status_code == 400

    def test_patch_rejects_unknown_top_level_key(self, client, sample_job, app_context):
        resp = client.patch(
            f"/api/v1/jobs/{sample_job.job_id}/transcode-config",
            json={
                "preset_slug": "software-balanced",
                "overrides": {},
                "bogus": 1,
            },
        )
        assert resp.status_code == 400

    def test_patch_rejects_unknown_tier(self, client, sample_job, app_context):
        resp = client.patch(
            f"/api/v1/jobs/{sample_job.job_id}/transcode-config",
            json={
                "preset_slug": "software-balanced",
                "overrides": {"tiers": {"epic_tier": {}}},
            },
        )
        assert resp.status_code == 400


class TestApiTranscodeCallback:
    """Test POST /api/v1/jobs/<id>/transcode-callback endpoint."""

    def test_callback_not_found(self, client):
        response = client.post('/api/v1/jobs/99999/transcode-callback',
                                json={"status": "completed"})
        assert response.status_code == 404

    def test_callback_unknown_status(self, client, sample_job, app_context):
        # Pydantic enum validation now rejects unknown statuses with 422
        # (structured) before the handler runs.
        response = client.post(
            f'/api/v1/jobs/{sample_job.job_id}/transcode-callback',
            json={"status": "invalid_status"}
        )
        assert response.status_code == 422

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
        job.status = "video_ripping"
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
        job.status = "video_ripping"
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


# ---- API Migration Phase 1 ----


class TestApiNotificationsList:
    """Test GET /api/v1/notifications endpoint."""

    def test_list_excludes_cleared(self, client, sample_notifications):
        response = client.get('/api/v1/notifications')
        assert response.status_code == 200
        data = response.json()
        # 3 non-cleared: 2 unseen + 1 seen
        assert len(data["notifications"]) == 3
        for n in data["notifications"]:
            assert n["cleared"] is False

    def test_list_include_cleared(self, client, sample_notifications):
        response = client.get('/api/v1/notifications?include_cleared=true')
        assert response.status_code == 200
        data = response.json()
        assert len(data["notifications"]) == 4

    def test_list_empty(self, client, app_context):
        response = client.get('/api/v1/notifications')
        assert response.status_code == 200
        assert response.json()["notifications"] == []

    def test_list_ordered_newest_first(self, client, sample_notifications):
        response = client.get('/api/v1/notifications')
        data = response.json()
        times = [n["trigger_time"] for n in data["notifications"]]
        assert times == sorted(times, reverse=True)


class TestApiNotificationCount:
    """Test GET /api/v1/notifications/count endpoint."""

    def test_count_with_notifications(self, client, sample_notifications):
        response = client.get('/api/v1/notifications/count')
        assert response.status_code == 200
        data = response.json()
        assert data["unseen"] == 2
        assert data["seen"] == 1
        assert data["cleared"] == 1
        assert data["total"] == 4

    def test_count_empty(self, client, app_context):
        response = client.get('/api/v1/notifications/count')
        assert response.status_code == 200
        data = response.json()
        assert data["unseen"] == 0
        assert data["total"] == 0


class TestApiNotificationDismissAll:
    """Test POST /api/v1/notifications/dismiss-all endpoint."""

    def test_dismiss_all(self, client, sample_notifications):
        response = client.post('/api/v1/notifications/dismiss-all')
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["count"] == 2

        check = client.get('/api/v1/notifications/count')
        assert check.json()["unseen"] == 0

    def test_dismiss_all_none_unseen(self, client, app_context):
        response = client.post('/api/v1/notifications/dismiss-all')
        assert response.status_code == 200
        assert response.json()["count"] == 0


class TestApiNotificationPurge:
    """Test POST /api/v1/notifications/purge endpoint."""

    def test_purge_cleared(self, client, sample_notifications):
        response = client.post('/api/v1/notifications/purge')
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["count"] == 1

        check = client.get('/api/v1/notifications/count')
        assert check.json()["total"] == 3
        assert check.json()["cleared"] == 0

    def test_purge_none_cleared(self, client, app_context):
        response = client.post('/api/v1/notifications/purge')
        assert response.status_code == 200
        assert response.json()["count"] == 0


class TestApiDrivesList:
    """Test GET /api/v1/drives endpoint."""

    def test_list_drives(self, client, sample_drives):
        response = client.get('/api/v1/drives')
        assert response.status_code == 200
        data = response.json()
        assert len(data["drives"]) == 2
        names = [d["name"] for d in data["drives"]]
        assert "Living Room" in names
        assert "Office" in names
        assert "Stale Drive" not in names

    def test_list_drives_include_stale(self, client, sample_drives):
        response = client.get('/api/v1/drives?include_stale=true')
        assert response.status_code == 200
        assert len(response.json()["drives"]) == 3

    def test_list_drives_empty(self, client, app_context):
        response = client.get('/api/v1/drives')
        assert response.status_code == 200
        assert response.json()["drives"] == []

    def test_drive_includes_capabilities(self, client, sample_drives):
        response = client.get('/api/v1/drives')
        data = response.json()
        drive = next(d for d in data["drives"] if d["name"] == "Living Room")
        assert "capabilities" in drive
        assert "BD" in drive["capabilities"]

    def test_drive_includes_job_ids(self, client, sample_drives):
        response = client.get('/api/v1/drives')
        data = response.json()
        drive = data["drives"][0]
        assert "job_id_current" in drive
        assert "job_id_previous" in drive

class TestApiDrivesWithJobs:
    """Test GET /api/v1/drives/with-jobs endpoint."""

    def test_drives_with_current_job(self, client, sample_drives, sample_job, app_context):
        from arm.database import db
        sample_drives[0].job_id_current = sample_job.job_id
        db.session.commit()

        response = client.get('/api/v1/drives/with-jobs')
        assert response.status_code == 200
        data = response.json()
        drive = next(d for d in data["drives"] if d["name"] == "Living Room")
        assert drive["current_job"] is not None
        assert drive["current_job"]["title"] == "SERIAL_MOM"
        assert drive["current_job"]["status"] == "video_ripping"

    def test_drives_without_jobs(self, client, sample_drives):
        response = client.get('/api/v1/drives/with-jobs')
        data = response.json()
        for drive in data["drives"]:
            assert drive["current_job"] is None

    def test_drives_with_jobs_projects_poster_url(self, client, sample_drives, sample_job, app_context):
        """Regression: dashboard 'drive currently working on' badge reads poster_url.

        _job_summary on /api/v1/drives/with-jobs projects MediaMetadata.poster_url
        into the JobSummary wire shape after the Phase 2 column purge.
        """
        from arm.database import db
        from arm_contracts import MediaMetadata

        sample_job.set_metadata_auto(MediaMetadata(
            poster_url="https://example.com/badge-poster.jpg",
        ))
        sample_drives[0].job_id_current = sample_job.job_id
        db.session.commit()

        response = client.get('/api/v1/drives/with-jobs')
        assert response.status_code == 200
        drive = next(d for d in response.json()["drives"] if d["name"] == "Living Room")
        assert drive["current_job"]["poster_url"] == "https://example.com/badge-poster.jpg"


class TestApiJobDetail:
    """Test GET /api/v1/jobs/<id>/detail endpoint."""

    def test_job_detail_basic(self, client, sample_job, app_context):
        response = client.get(f'/api/v1/jobs/{sample_job.job_id}/detail')
        assert response.status_code == 200
        data = response.json()
        assert data["job"]["title"] == "SERIAL_MOM"
        assert data["job"]["year"] == "1994"
        assert "config" in data
        assert "track_counts" in data

    def test_job_detail_track_counts(self, client, sample_job, app_context):
        from arm.models.track import Track
        from arm.database import db

        for i in range(3):
            t = Track(
                job_id=sample_job.job_id, track_number=str(i),
                length=3600, aspect_ratio="16:9", fps="23.976",
                main_feature=i == 0, source="MakeMKV",
                basename=f"title_{i}.mkv", filename=f"title_{i}.mkv",
            )
            t.ripped = i < 2
            db.session.add(t)
        db.session.commit()

        response = client.get(f'/api/v1/jobs/{sample_job.job_id}/detail')
        data = response.json()
        assert data["track_counts"]["total"] == 3
        assert data["track_counts"]["ripped"] == 2

    def test_job_detail_not_found(self, client, app_context):
        response = client.get('/api/v1/jobs/99999/detail')
        assert response.status_code == 404

    def test_job_detail_config_masks_sensitive(self, client, sample_job, app_context):
        response = client.get(f'/api/v1/jobs/{sample_job.job_id}/detail')
        data = response.json()
        config = data["config"]
        for key in ("PB_KEY", "IFTTT_KEY", "PO_USER_KEY", "PO_APP_KEY",
                     "EMBY_PASSWORD", "EMBY_API_KEY"):
            if key in config:
                assert config[key] in (None, "", "***")

    def test_job_detail_includes_tracks(self, client, sample_job, app_context):
        """detail response carries the full track list (UI builds the detail page from it)."""
        from arm.models.track import Track
        from arm.database import db

        for i in range(2):
            t = Track(
                job_id=sample_job.job_id, track_number=str(i),
                length=3600, aspect_ratio="16:9", fps="23.976",
                main_feature=i == 0, source="MakeMKV",
                basename=f"title_{i}.mkv", filename=f"title_{i}.mkv",
            )
            t.ripped = i == 0
            t.status = "success" if i == 0 else "pending"
            db.session.add(t)
        db.session.commit()

        response = client.get(f'/api/v1/jobs/{sample_job.job_id}/detail')
        data = response.json()
        assert "tracks" in data
        assert len(data["tracks"]) == 2
        assert data["tracks"][0]["track_id"] is not None
        assert data["tracks"][0]["job_id"] == sample_job.job_id
        # main_feature -> enabled fallback applied for legacy rows that left enabled NULL
        assert data["tracks"][0]["enabled"] is not None

    def test_job_detail_returns_null_config_when_unset(self, client, sample_job, app_context):
        """A job with no Config row returns config: null (not an empty object)."""
        from arm.database import db
        sample_job.config = None
        db.session.commit()

        response = client.get(f'/api/v1/jobs/{sample_job.job_id}/detail')
        assert response.status_code == 200
        assert response.json()["config"] is None

    def test_job_detail_track_carries_custom_filename(self, client, sample_job, app_context):
        """Audit gap fix: custom_filename was previously dropped by _track_to_dict;
        the contract adoption restores it on the wire so the UI can render it."""
        from arm.models.track import Track
        from arm.database import db

        t = Track(
            job_id=sample_job.job_id, track_number="0",
            length=3600, aspect_ratio="16:9", fps="23.976",
            main_feature=True, source="MakeMKV",
            basename="title_t00.mkv", filename="title_t00.mkv",
        )
        t.custom_filename = "S01E01_pilot.mkv"
        db.session.add(t)
        db.session.commit()

        response = client.get(f'/api/v1/jobs/{sample_job.job_id}/detail')
        data = response.json()
        assert data["tracks"][0]["custom_filename"] == "S01E01_pilot.mkv"

    def test_job_detail_transcode_overrides_dict_round_trips(self, client, sample_job, app_context):
        """A valid JSON-string transcode_overrides column round-trips as a dict
        on the wire (not the raw string), so the UI can read preset_slug etc."""
        import json as _json
        from arm.database import db
        sample_job.transcode_overrides = _json.dumps({"preset_slug": "nvidia_balanced"})
        db.session.commit()

        response = client.get(f'/api/v1/jobs/{sample_job.job_id}/detail')
        data = response.json()
        assert data["job"]["transcode_overrides"] == {"preset_slug": "nvidia_balanced"}

    def test_job_detail_corrupt_transcode_overrides_drops_to_null(self, client, sample_job, app_context):
        """A non-JSON transcode_overrides column drops to null instead of
        propagating garbage to the UI."""
        from arm.database import db
        sample_job.transcode_overrides = "{this is not json"
        db.session.commit()

        response = client.get(f'/api/v1/jobs/{sample_job.job_id}/detail')
        data = response.json()
        assert data["job"]["transcode_overrides"] is None


class TestApiJobProgressState:
    """Test GET /api/v1/jobs/<id>/progress-state endpoint."""

    def test_progress_state_basic(self, client, sample_job, app_context):
        response = client.get(f'/api/v1/jobs/{sample_job.job_id}/progress-state')
        assert response.status_code == 200
        data = response.json()
        assert "track_counts" in data
        assert "total" in data["track_counts"]
        assert "ripped" in data["track_counts"]
        assert "disctype" in data
        assert "logfile" in data
        assert "no_of_titles" in data

    def test_progress_state_not_found(self, client, app_context):
        response = client.get('/api/v1/jobs/99999/progress-state')
        assert response.status_code == 404

    def test_progress_state_carries_job_fields(self, client, sample_job, app_context):
        response = client.get(f'/api/v1/jobs/{sample_job.job_id}/progress-state')
        data = response.json()
        assert data["disctype"] == sample_job.disctype
        assert data["logfile"] == sample_job.logfile


class TestApiActiveJobs:
    """Test GET /api/v1/jobs/active endpoint."""

    def test_active_jobs_returns_active(self, client, sample_job, app_context):
        response = client.get('/api/v1/jobs/active')
        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["title"] == "SERIAL_MOM"
        assert "track_counts" in data["jobs"][0]

    def test_active_jobs_excludes_completed(self, client, sample_job, app_context):
        from arm.database import db
        sample_job.status = "success"
        db.session.commit()

        response = client.get('/api/v1/jobs/active')
        assert response.json()["jobs"] == []

    def test_active_jobs_with_tracks(self, client, sample_job, app_context):
        from arm.models.track import Track
        from arm.database import db

        for i in range(2):
            t = Track(
                job_id=sample_job.job_id, track_number=str(i),
                length=3600, aspect_ratio="16:9", fps="23.976",
                main_feature=i == 0, source="MakeMKV",
                basename=f"title_{i}.mkv", filename=f"title_{i}.mkv",
            )
            t.ripped = i == 0
            db.session.add(t)
        db.session.commit()

        response = client.get('/api/v1/jobs/active')
        job = response.json()["jobs"][0]
        assert job["track_counts"]["total"] == 2
        assert job["track_counts"]["ripped"] == 1


class TestApiJobsPaginated:
    """Test GET /api/v1/jobs/paginated endpoint."""

    def test_basic_pagination(self, client, sample_job, app_context):
        response = client.get('/api/v1/jobs/paginated')
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["page"] == 1
        assert data["per_page"] == 25
        assert data["pages"] == 1
        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["title"] == "SERIAL_MOM"

    def test_paginated_includes_track_counts(self, client, sample_job, app_context):
        """Each job in the list carries track_counts so the UI can render
        ripped/total without a per-row roundtrip."""
        from arm.database import db
        from arm.models.track import Track
        # 3 tracks: 1 ripped, 1 enabled (rippable), 1 disabled
        t1 = Track(job_id=sample_job.job_id, track_number="0", length=3600,
                   aspect_ratio="16:9", fps=23.976, main_feature=True,
                   source="MakeMKV", basename="t1.mkv", filename="t1.mkv",
                   chapters=20, filesize=10000000)
        t1.enabled = True
        t1.ripped = True
        t2 = Track(job_id=sample_job.job_id, track_number="1", length=3600,
                   aspect_ratio="16:9", fps=23.976, main_feature=False,
                   source="MakeMKV", basename="t2.mkv", filename="t2.mkv",
                   chapters=10, filesize=5000000)
        t2.enabled = True
        t2.ripped = False
        t3 = Track(job_id=sample_job.job_id, track_number="2", length=3600,
                   aspect_ratio="16:9", fps=23.976, main_feature=False,
                   source="MakeMKV", basename="t3.mkv", filename="t3.mkv",
                   chapters=5, filesize=1000000)
        t3.enabled = False
        t3.ripped = False
        db.session.add_all([t1, t2, t3])
        db.session.commit()

        response = client.get('/api/v1/jobs/paginated')
        data = response.json()
        job = data["jobs"][0]
        assert "track_counts" in job
        assert job["track_counts"]["total"] == 2  # rippable subset
        assert job["track_counts"]["ripped"] == 1

    def test_filter_by_status(self, client, sample_job, app_context):
        response = client.get('/api/v1/jobs/paginated?status=active')
        assert response.status_code == 200
        assert response.json()["total"] == 1

        response = client.get('/api/v1/jobs/paginated?status=success')
        assert response.json()["total"] == 0

    def test_filter_by_disctype(self, client, sample_job, app_context):
        response = client.get('/api/v1/jobs/paginated?disctype=bluray')
        assert response.json()["total"] == 1

        response = client.get('/api/v1/jobs/paginated?disctype=dvd')
        assert response.json()["total"] == 0

    def test_search(self, client, sample_job, app_context):
        response = client.get('/api/v1/jobs/paginated?search=SERIAL')
        assert response.json()["total"] == 1

        response = client.get('/api/v1/jobs/paginated?search=NONEXISTENT')
        assert response.json()["total"] == 0

    def test_sort_ascending(self, client, sample_job, app_context):
        response = client.get('/api/v1/jobs/paginated?sort_by=title&sort_dir=asc')
        assert response.status_code == 200
        assert len(response.json()["jobs"]) == 1

    def test_page_out_of_range(self, client, sample_job, app_context):
        response = client.get('/api/v1/jobs/paginated?page=999')
        assert response.status_code == 200
        assert response.json()["jobs"] == []
        assert response.json()["total"] == 1

    def test_empty_database(self, client, app_context):
        response = client.get('/api/v1/jobs/paginated')
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["jobs"] == []
        assert data["pages"] == 1

    def test_multiple_jobs_pagination(self, client, sample_job, app_context):
        """Create extra jobs and verify per_page limit works."""
        import unittest.mock
        from arm.models.job import Job
        from arm.database import db

        for i in range(3):
            with unittest.mock.patch.object(Job, 'parse_udev'), \
                 unittest.mock.patch.object(Job, 'get_pid'):
                j = Job('/dev/sr0')
            j.title = f"Movie {i}"
            j.status = "success"
            j.disctype = "bluray"
            j.arm_version = "test"
            j.crc_id = ""
            j.logfile = f"test_{i}.log"
            db.session.add(j)
        db.session.commit()

        response = client.get('/api/v1/jobs/paginated?per_page=2')
        data = response.json()
        assert data["total"] == 4  # sample_job + 3 new
        assert len(data["jobs"]) == 2
        assert data["pages"] == 2

        response = client.get('/api/v1/jobs/paginated?per_page=2&page=2')
        data = response.json()
        assert len(data["jobs"]) == 2


class TestApiJobTrackCounts:
    """Test GET /api/v1/jobs/<id>/track-counts endpoint."""

    def _add_tracks(self, job_id, specs):
        """Helper: add Track rows and commit. specs = list of (length, ripped, enabled) tuples."""
        from arm.models.track import Track
        from arm.database import db
        for i, spec in enumerate(specs):
            length, ripped, enabled = spec
            t = Track(
                job_id=job_id, track_number=str(i),
                length=length, aspect_ratio="16:9", fps="23.976",
                main_feature=i == 0, source="MakeMKV",
                basename=f"title_{i}.mkv", filename=f"title_{i}.mkv",
            )
            t.ripped = ripped
            t.enabled = enabled
            db.session.add(t)
        db.session.commit()

    def test_track_counts_basic(self, client, sample_job, app_context):
        self._add_tracks(sample_job.job_id, [(3600, True, True), (3600, False, True), (3600, True, True)])
        response = client.get(f'/api/v1/jobs/{sample_job.job_id}/track-counts')
        assert response.status_code == 200
        assert response.json() == {"total": 3, "ripped": 2}

    def test_track_counts_not_found(self, client, app_context):
        response = client.get('/api/v1/jobs/99999/track-counts')
        assert response.status_code == 404

    def test_track_counts_excludes_disabled(self, client, sample_job, app_context):
        # 2 enabled (1 ripped), 1 disabled (ripped) - disabled should not count
        self._add_tracks(sample_job.job_id, [(3600, True, True), (3600, False, True), (3600, True, False)])
        response = client.get(f'/api/v1/jobs/{sample_job.job_id}/track-counts')
        assert response.json() == {"total": 2, "ripped": 1}

    def test_track_counts_excludes_below_minlength(self, client, sample_job, app_context):
        # MINLENGTH 600 (10 min); short tracks excluded
        from arm.database import db
        sample_job.config.MINLENGTH = "600"
        db.session.commit()
        self._add_tracks(sample_job.job_id, [(3600, True, True), (300, True, True), (1800, False, True)])
        response = client.get(f'/api/v1/jobs/{sample_job.job_id}/track-counts')
        # Only 3600 and 1800 qualify; 1 ripped (the 3600 one)
        assert response.json() == {"total": 2, "ripped": 1}

    def test_track_counts_music_ignores_minlength(self, client, sample_job, app_context):
        from arm.database import db
        sample_job.disctype = "music"
        sample_job.config.MINLENGTH = "600"
        db.session.commit()
        # Music: short tracks DO count regardless of minlength
        self._add_tracks(sample_job.job_id, [(180, True, True), (200, False, True), (240, True, True)])
        response = client.get(f'/api/v1/jobs/{sample_job.job_id}/track-counts')
        assert response.json() == {"total": 3, "ripped": 2}

    def test_track_counts_no_tracks(self, client, sample_job, app_context):
        response = client.get(f'/api/v1/jobs/{sample_job.job_id}/track-counts')
        assert response.json() == {"total": 0, "ripped": 0}

    def test_track_counts_minlength_zero_keeps_short_tracks(self, client, sample_job, app_context):
        """MINLENGTH=0 (or unset) means no length filter - all enabled tracks count."""
        from arm.database import db
        sample_job.config.MINLENGTH = "0"
        db.session.commit()
        self._add_tracks(sample_job.job_id, [(60, True, True), (120, False, True)])
        response = client.get(f'/api/v1/jobs/{sample_job.job_id}/track-counts')
        assert response.json() == {"total": 2, "ripped": 1}

    def test_track_counts_minlength_unparseable(self, client, sample_job, app_context):
        """Garbage MINLENGTH falls back to 0 (no filter) instead of crashing."""
        from arm.database import db
        sample_job.config.MINLENGTH = "not-a-number"
        db.session.commit()
        self._add_tracks(sample_job.job_id, [(60, True, True), (120, False, True)])
        response = client.get(f'/api/v1/jobs/{sample_job.job_id}/track-counts')
        # ValueError caught, ml=0, all enabled tracks count
        assert response.json() == {"total": 2, "ripped": 1}


class TestApiJobsStats:
    """Test GET /api/v1/jobs/stats endpoint."""

    def _make_jobs(self, statuses):
        """Helper: spin up Job rows in the given statuses."""
        import unittest.mock
        from arm.models.job import Job
        from arm.database import db
        created = []
        for i, status in enumerate(statuses):
            with unittest.mock.patch.object(Job, 'parse_udev'), \
                 unittest.mock.patch.object(Job, 'get_pid'):
                j = Job('/dev/sr0')
            j.title = f"Movie {i}"
            j.status = status
            j.disctype = "bluray"
            j.video_type = "movie"
            j.arm_version = "test"
            j.crc_id = ""
            j.logfile = f"job_{i}.log"
            db.session.add(j)
            created.append(j)
        db.session.commit()
        return created

    def test_stats_empty(self, client, app_context):
        response = client.get('/api/v1/jobs/stats')
        assert response.status_code == 200
        assert response.json() == {"total": 0, "active": 0, "waiting": 0, "success": 0, "fail": 0}

    def test_stats_buckets(self, client, app_context):
        # video_ripping/transcoding map to "active" per
        # _ACTIVE_STATUSES - _WAITING_STATUSES; manual_paused/
        # makemkv_throttled/waiting_transcode all bucket as "waiting".
        self._make_jobs([
            "video_ripping", "transcoding",                    # 2 active
            "manual_paused", "waiting_transcode",              # 2 waiting
            "success", "success",                              # 2 success
            "fail",                                            # 1 fail
        ])
        data = client.get('/api/v1/jobs/stats').json()
        assert data == {"total": 7, "active": 2, "waiting": 2, "success": 2, "fail": 1}

    def test_stats_status_groups_match_paginated(self, client, app_context):
        """Active and waiting buckets must use the same grouping as /jobs/paginated."""
        self._make_jobs(["transcoding", "video_ripping", "manual_paused", "waiting_transcode", "success"])
        stats = client.get('/api/v1/jobs/stats').json()
        active_paged = client.get('/api/v1/jobs/paginated?status=active').json()
        waiting_paged = client.get('/api/v1/jobs/paginated?status=waiting').json()
        assert stats["active"] == active_paged["total"]
        assert stats["waiting"] == waiting_paged["total"]

    def test_stats_filter_by_video_type(self, client, app_context):
        from arm.database import db
        jobs = self._make_jobs(["success", "success", "success"])
        jobs[0].video_type = "movie"
        jobs[1].video_type = "series"
        jobs[2].video_type = "movie"
        db.session.commit()
        data = client.get('/api/v1/jobs/stats?video_type=movie').json()
        assert data["total"] == 2 and data["success"] == 2
        data = client.get('/api/v1/jobs/stats?video_type=series').json()
        assert data["total"] == 1 and data["success"] == 1

    def test_stats_filter_by_disctype(self, client, app_context):
        from arm.database import db
        jobs = self._make_jobs(["success", "success"])
        jobs[0].disctype = "dvd"
        jobs[1].disctype = "bluray"
        db.session.commit()
        data = client.get('/api/v1/jobs/stats?disctype=dvd').json()
        assert data["total"] == 1

    def test_stats_filter_by_search(self, client, app_context):
        from arm.database import db
        jobs = self._make_jobs(["success", "success"])
        jobs[0].title = "SERIAL_MOM"
        jobs[1].title = "OTHER_MOVIE"
        db.session.commit()
        data = client.get('/api/v1/jobs/stats?search=SERIAL').json()
        assert data["total"] == 1 and data["success"] == 1

    def test_stats_filter_by_days(self, client, app_context):
        from arm.database import db
        from datetime import datetime, timedelta
        jobs = self._make_jobs(["success", "success"])
        jobs[0].start_time = datetime.now() - timedelta(days=1)
        jobs[1].start_time = datetime.now() - timedelta(days=30)
        db.session.commit()
        data = client.get('/api/v1/jobs/stats?days=7').json()
        assert data["total"] == 1


class TestApiActiveJobsRippableFilter:
    """Verify /jobs/active and /jobs/{id}/detail use the rippable-track filter."""

    def _add_tracks(self, job_id, specs):
        from arm.models.track import Track
        from arm.database import db
        for i, (length, ripped, enabled) in enumerate(specs):
            t = Track(
                job_id=job_id, track_number=str(i),
                length=length, aspect_ratio="16:9", fps="23.976",
                main_feature=i == 0, source="MakeMKV",
                basename=f"title_{i}.mkv", filename=f"title_{i}.mkv",
            )
            t.ripped = ripped
            t.enabled = enabled
            db.session.add(t)
        db.session.commit()

    def test_active_jobs_excludes_disabled_tracks(self, client, sample_job, app_context):
        self._add_tracks(sample_job.job_id, [(3600, True, True), (3600, False, False)])
        job = client.get('/api/v1/jobs/active').json()["jobs"][0]
        assert job["track_counts"] == {"total": 1, "ripped": 1}

    def test_job_detail_excludes_disabled_tracks(self, client, sample_job, app_context):
        self._add_tracks(sample_job.job_id, [(3600, True, True), (3600, True, False)])
        data = client.get(f'/api/v1/jobs/{sample_job.job_id}/detail').json()
        assert data["track_counts"] == {"total": 1, "ripped": 1}


class TestApiRetranscodeInfo:
    """Test GET /api/v1/jobs/<id>/retranscode-info endpoint."""

    def test_retranscode_info_basic(self, client, sample_job, app_context):
        from arm.database import db
        sample_job.raw_path = "/home/arm/media/raw/SERIAL_MOM"
        db.session.commit()

        response = client.get(f'/api/v1/jobs/{sample_job.job_id}/retranscode-info')
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "SERIAL_MOM"
        assert data["year"] == "1994"
        assert data["job_id"] == sample_job.job_id
        assert data["disctype"] == "bluray"
        assert data["path"] == "/home/arm/media/raw/SERIAL_MOM"

    def test_retranscode_info_not_found(self, client, app_context):
        response = client.get('/api/v1/jobs/99999/retranscode-info')
        assert response.status_code == 404

    def test_retranscode_info_non_video(self, client, sample_job, app_context):
        from arm.database import db
        sample_job.disctype = "music"
        db.session.commit()

        response = client.get(f'/api/v1/jobs/{sample_job.job_id}/retranscode-info')
        assert response.status_code == 400

    def test_retranscode_info_with_overrides(self, client, sample_job, app_context):
        import json
        from arm.database import db
        sample_job.transcode_overrides = json.dumps({"preset_slug": "nvidia_balanced"})
        db.session.commit()

        response = client.get(f'/api/v1/jobs/{sample_job.job_id}/retranscode-info')
        data = response.json()
        assert data["config_overrides"] == {"preset_slug": "nvidia_balanced"}

    def test_retranscode_info_multi_title(self, client, sample_job, app_context):
        from arm.models.track import Track
        from arm.database import db

        sample_job.multi_title = True
        t = Track(
            job_id=sample_job.job_id, track_number="0",
            length=3600, aspect_ratio="16:9", fps="23.976",
            main_feature=True, source="MakeMKV",
            basename="movie.mkv", filename="movie.mkv",
        )
        t.title = "The Movie"
        db.session.add(t)
        db.session.commit()

        response = client.get(f'/api/v1/jobs/{sample_job.job_id}/retranscode-info')
        data = response.json()
        assert data["multi_title"] is True
        assert len(data["tracks"]) == 1
        assert data["tracks"][0]["title"] == "The Movie"


class TestApiJobMetadata:
    """GET /api/v1/jobs/{job_id}/metadata returns the merged MediaMetadata."""

    def test_get_job_metadata_endpoint(self, client, app_context):
        from arm.database import db
        from arm.models.job import Job
        from arm_contracts import MediaMetadata

        job = Job(devpath="/dev/sr0", _skip_hardware=True)
        job.set_metadata_auto(MediaMetadata(
            title="Annihilation",
            year="2018",
            directors=["Alex Garland"],
            genres=["Sci-Fi", "Drama"],
        ))
        db.session.add(job)
        db.session.commit()

        resp = client.get(f"/api/v1/jobs/{job.job_id}/metadata")
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Annihilation"
        assert data["directors"] == ["Alex Garland"]
        assert data["genres"] == ["Sci-Fi", "Drama"]

    def test_get_job_metadata_404_for_unknown_job(self, client):
        resp = client.get("/api/v1/jobs/999999/metadata")
        assert resp.status_code == 404
