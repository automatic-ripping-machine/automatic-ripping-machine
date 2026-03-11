"""Tests covering remaining patch coverage gaps across multiple modules.

Targets:
- arm/api/v1/settings.py: abcde path validation error paths
- arm/ripper/music_brainz.py: disc_number/disc_total in _build_music_args
- arm/ripper/utils.py: AUDIO_FORMAT flag, OSError in log read, drive unavailable
- arm/ripper/makemkv.py: multi_title auto-flag (enable-all branch)
- arm/ripper/identify.py: music disc early return
- arm/migrations/versions: upgrade/downgrade operations
"""
import os
import subprocess
import unittest.mock

import pytest


# ── settings.py: abcde path validation error paths ──────────────────────


class TestAbcdePathValidation:
    """Test _abcde_path() and error paths in abcde config endpoints."""

    @pytest.fixture
    def client(self, tmp_path):
        import arm.config.config as cfg
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from arm.api.v1.settings import router

        app = FastAPI()
        app.include_router(router)

        original_config = dict(cfg.arm_config)
        original_path = cfg.arm_config_path
        cfg.arm_config_path = str(tmp_path / "arm_test.yaml")

        with TestClient(app) as c:
            yield c

        cfg.arm_config.clear()
        cfg.arm_config.update(original_config)
        cfg.arm_config_path = original_path

    def test_get_abcde_invalid_path_returns_empty(self, client):
        """ValueError from _abcde_path() returns exists=False, not 500."""
        import arm.config.config as cfg

        with unittest.mock.patch(
            'arm.api.v1.settings._abcde_path',
            side_effect=ValueError("bad path"),
        ):
            resp = client.get("/api/v1/settings/abcde")
        assert resp.status_code == 200
        data = resp.json()
        assert data["exists"] is False
        assert data["content"] == ""
        assert data["path"] == ""

    def test_get_abcde_os_error_returns_exists_false(self, client):
        """OSError during file read returns exists=False."""
        import arm.config.config as cfg

        with unittest.mock.patch(
            'arm.api.v1.settings._abcde_path',
            return_value="/valid/absolute/path",
        ), unittest.mock.patch(
            'arm.api.v1.settings.asyncio.to_thread',
            side_effect=OSError("permission denied"),
        ):
            resp = client.get("/api/v1/settings/abcde")
        assert resp.status_code == 200
        data = resp.json()
        assert data["exists"] is False

    def test_put_abcde_invalid_path_returns_400(self, client):
        """ValueError from _abcde_path() on PUT returns 400."""
        with unittest.mock.patch(
            'arm.api.v1.settings._abcde_path',
            side_effect=ValueError("bad path"),
        ):
            resp = client.put(
                "/api/v1/settings/abcde",
                json={"content": "# test"},
            )
        assert resp.status_code == 400
        assert resp.json()["success"] is False

    def test_put_abcde_os_error_returns_500(self, client):
        """OSError during write returns 500."""
        with unittest.mock.patch(
            'arm.api.v1.settings._abcde_path',
            return_value="/valid/absolute/path",
        ), unittest.mock.patch(
            'arm.api.v1.settings.asyncio.to_thread',
            side_effect=OSError("read-only filesystem"),
        ):
            resp = client.put(
                "/api/v1/settings/abcde",
                json={"content": "# test"},
            )
        assert resp.status_code == 500
        assert resp.json()["success"] is False

    def test_abcde_path_relative_raises(self):
        """_abcde_path() raises ValueError if resolved path is relative."""
        import arm.config.config as cfg
        from arm.api.v1.settings import _abcde_path

        original = cfg.arm_config.get("ABCDE_CONFIG_FILE")
        # os.path.realpath always returns absolute on real systems, but we
        # can test the validation by mocking realpath
        with unittest.mock.patch('os.path.realpath', return_value='relative/path'), \
             unittest.mock.patch('os.path.isabs', return_value=False):
            with pytest.raises(ValueError, match="relative path"):
                _abcde_path()


# ── music_brainz.py: disc_number / disc_total ────────────────────────────


class TestBuildMusicArgs:
    """Test _build_music_args disc_number and disc_total parameters."""

    def test_without_disc_info(self):
        from arm.ripper.music_brainz import _build_music_args

        args, artist_title = _build_music_args(
            1, 'crc123', 'Artist', 'Album', '2020', 10
        )
        assert 'disc_number' not in args
        assert 'disc_total' not in args
        assert artist_title == 'Artist Album'

    def test_with_disc_number(self):
        from arm.ripper.music_brainz import _build_music_args

        args, _ = _build_music_args(
            1, 'crc123', 'Artist', 'Album', '2020', 10,
            disc_number=2
        )
        assert args['disc_number'] == 2
        assert 'disc_total' not in args

    def test_with_disc_number_and_total(self):
        from arm.ripper.music_brainz import _build_music_args

        args, _ = _build_music_args(
            1, 'crc123', 'Artist', 'Album', '2020', 10,
            disc_number=1, disc_total=3
        )
        assert args['disc_number'] == 1
        assert args['disc_total'] == 3

    def test_with_disc_total_only(self):
        from arm.ripper.music_brainz import _build_music_args

        args, _ = _build_music_args(
            1, 'crc123', 'Artist', 'Album', '2020', 10,
            disc_total=2
        )
        assert 'disc_number' not in args
        assert args['disc_total'] == 2

    def test_standard_fields(self):
        from arm.ripper.music_brainz import _build_music_args

        args, artist_title = _build_music_args(
            42, 'xyz', 'Pink Floyd', 'The Wall', '1979', 26
        )
        assert args['job_id'] == '42'
        assert args['artist'] == 'Pink Floyd'
        assert args['album'] == 'The Wall'
        assert args['year'] == '1979'
        assert args['no_of_titles'] == 26
        assert args['video_type'] == 'music'
        assert artist_title == 'Pink Floyd The Wall'


# ── utils.py: AUDIO_FORMAT flag and remaining rip_music paths ────────────


class TestRipMusicAudioFormat:
    """Test AUDIO_FORMAT handling in rip_music()."""

    @staticmethod
    def _mock_popen(returncode=0):
        proc = unittest.mock.MagicMock()
        proc.poll.return_value = returncode
        proc.wait.return_value = returncode
        proc.returncode = returncode
        return proc

    def test_audio_format_flag_in_command(self, app_context, sample_job, tmp_path):
        """When AUDIO_FORMAT is set, -o flag appears in abcde command."""
        from arm.ripper.utils import rip_music

        sample_job.disctype = "music"
        sample_job.config.LOGPATH = str(tmp_path)
        sample_job.config.AUDIO_FORMAT = "mp3"

        logfile = "test.log"
        (tmp_path / logfile).write_text("Finished.\n")

        with unittest.mock.patch('subprocess.Popen', return_value=self._mock_popen(0)) as mock_popen, \
             unittest.mock.patch('arm.ripper.utils.cfg') as mock_cfg:
            mock_cfg.arm_config = {"ABCDE_CONFIG_FILE": "/nonexistent", "AUDIO_FORMAT": ""}
            rip_music(sample_job, logfile)

        cmd = mock_popen.call_args[0][0]
        assert "-o mp3" in cmd

    def test_audio_format_from_global_config(self, app_context, sample_job, tmp_path):
        """When job config has no AUDIO_FORMAT, falls back to arm_config."""
        from arm.ripper.utils import rip_music

        sample_job.disctype = "music"
        sample_job.config.LOGPATH = str(tmp_path)
        # No AUDIO_FORMAT on job config

        logfile = "test.log"
        (tmp_path / logfile).write_text("Finished.\n")

        with unittest.mock.patch('subprocess.Popen', return_value=self._mock_popen(0)) as mock_popen, \
             unittest.mock.patch('arm.ripper.utils.cfg') as mock_cfg:
            mock_cfg.arm_config = {"ABCDE_CONFIG_FILE": "/nonexistent", "AUDIO_FORMAT": "vorbis"}
            rip_music(sample_job, logfile)

        cmd = mock_popen.call_args[0][0]
        assert "-o vorbis" in cmd

    def test_no_audio_format_no_flag(self, app_context, sample_job, tmp_path):
        """When AUDIO_FORMAT is empty, no -o flag in command."""
        from arm.ripper.utils import rip_music

        sample_job.disctype = "music"
        sample_job.config.LOGPATH = str(tmp_path)

        logfile = "test.log"
        (tmp_path / logfile).write_text("Finished.\n")

        with unittest.mock.patch('subprocess.Popen', return_value=self._mock_popen(0)) as mock_popen, \
             unittest.mock.patch('arm.ripper.utils.cfg') as mock_cfg:
            mock_cfg.arm_config = {"ABCDE_CONFIG_FILE": "/nonexistent", "AUDIO_FORMAT": ""}
            rip_music(sample_job, logfile)

        cmd = mock_popen.call_args[0][0]
        assert "-o " not in cmd

    def test_log_read_oserror_treated_as_success(self, app_context, sample_job, tmp_path):
        """If log file can't be read after abcde exits 0, treat as success."""
        from arm.ripper.utils import rip_music

        sample_job.disctype = "music"
        sample_job.config.LOGPATH = str(tmp_path)

        logfile = "test.log"
        # Don't create the log file — open() will raise OSError

        with unittest.mock.patch('subprocess.Popen', return_value=self._mock_popen(0)), \
             unittest.mock.patch('arm.ripper.utils.cfg') as mock_cfg, \
             unittest.mock.patch('builtins.open', side_effect=OSError("permission denied")):
            mock_cfg.arm_config = {"ABCDE_CONFIG_FILE": "/nonexistent", "AUDIO_FORMAT": ""}
            result = rip_music(sample_job, logfile)

        # OSError on log read → log_content="" → no errors → success
        assert result is True

    def test_cdrom_drive_unavailable_detected(self, app_context, sample_job, tmp_path):
        """'CDROM drive unavailable' without [ERROR] lines is still a failure."""
        from arm.ripper.utils import rip_music

        sample_job.disctype = "music"
        sample_job.config.LOGPATH = str(tmp_path)

        logfile = "test.log"
        (tmp_path / logfile).write_text(
            "Grabbing track 01...\n"
            "CDROM drive unavailable\n"
        )

        with unittest.mock.patch('subprocess.Popen', return_value=self._mock_popen(0)), \
             unittest.mock.patch('arm.ripper.utils.cfg') as mock_cfg:
            mock_cfg.arm_config = {"ABCDE_CONFIG_FILE": "/nonexistent", "AUDIO_FORMAT": ""}
            result = rip_music(sample_job, logfile)

        assert result is False
        assert sample_job.status == "fail"


# ── makemkv.py: multi_title auto-flag (enable-all branch) ───────────────


class TestMakemkvMultiTitleAutoFlag:
    """Test makemkv_mkv() enables all tracks when multi_title=True."""

    def test_multi_title_enables_all_tracks(self, app_context, sample_job, tmp_path):
        from arm.models.track import Track
        from arm.models.system_drives import SystemDrives
        from arm.database import db

        _, _ = app_context

        drive = SystemDrives()
        drive.mount = sample_job.devpath
        drive.job_id_current = sample_job.job_id
        drive.mdisc = 0
        db.session.add(drive)

        sample_job.config.MAINFEATURE = True
        sample_job.config.MKV_ARGS = ""
        sample_job.config.MAXLENGTH = 99998
        sample_job.video_type = 'movie'
        sample_job.multi_title = True  # Multi-title overrides MAINFEATURE
        sample_job.no_of_titles = 3
        db.session.commit()
        db.session.refresh(sample_job)

        t1 = Track(sample_job.job_id, '1', 7200, '16:9', 24.0, False, 'makemkv',
                    'test', 't01.mkv', chapters=20, filesize=5000000)
        t2 = Track(sample_job.job_id, '2', 1800, '16:9', 24.0, False, 'makemkv',
                    'test', 't02.mkv', chapters=5, filesize=1000000)
        db.session.add_all([t1, t2])
        db.session.commit()

        from arm.ripper import makemkv as mkv_mod

        with unittest.mock.patch.object(mkv_mod.utils, 'get_drive_mode', return_value='auto'), \
             unittest.mock.patch.object(mkv_mod, 'get_track_info'), \
             unittest.mock.patch.object(mkv_mod, 'process_single_tracks'):
            mkv_mod.makemkv_mkv(sample_job, str(tmp_path))

        db.session.refresh(t1)
        db.session.refresh(t2)
        assert t1.enabled is True
        assert t2.enabled is True

    def test_series_type_enables_all_tracks(self, app_context, sample_job, tmp_path):
        from arm.models.track import Track
        from arm.models.system_drives import SystemDrives
        from arm.database import db

        _, _ = app_context

        drive = SystemDrives()
        drive.mount = sample_job.devpath
        drive.job_id_current = sample_job.job_id
        drive.mdisc = 0
        db.session.add(drive)

        sample_job.config.MAINFEATURE = True
        sample_job.config.MKV_ARGS = ""
        sample_job.config.MAXLENGTH = 99998
        sample_job.video_type = 'series'  # Not a single-track type
        sample_job.no_of_titles = 2
        db.session.commit()
        db.session.refresh(sample_job)

        t1 = Track(sample_job.job_id, '1', 3600, '16:9', 24.0, False, 'makemkv',
                    'test', 't01.mkv', chapters=10, filesize=3000000)
        t2 = Track(sample_job.job_id, '2', 3600, '16:9', 24.0, False, 'makemkv',
                    'test', 't02.mkv', chapters=10, filesize=3000000)
        db.session.add_all([t1, t2])
        db.session.commit()

        from arm.ripper import makemkv as mkv_mod

        with unittest.mock.patch.object(mkv_mod.utils, 'get_drive_mode', return_value='auto'), \
             unittest.mock.patch.object(mkv_mod, 'get_track_info'), \
             unittest.mock.patch.object(mkv_mod, 'process_single_tracks'):
            mkv_mod.makemkv_mkv(sample_job, str(tmp_path))

        db.session.refresh(t1)
        db.session.refresh(t2)
        assert t1.enabled is True
        assert t2.enabled is True


# ── identify.py: music disc early return ─────────────────────────────────


class TestIdentifyMusicSkip:
    """Test identify() skips mount/identification for music discs."""

    def test_music_disc_returns_early(self):
        """Music discs skip mount/identify — umount not called."""
        from arm.ripper.identify import identify

        job = unittest.mock.MagicMock()
        job.disctype = 'music'

        with unittest.mock.patch('arm.ripper.identify.check_mount') as mock_mount, \
             unittest.mock.patch('arm.ripper.identify.subprocess.run') as mock_run:
            identify(job)
            mock_mount.assert_not_called()
            mock_run.assert_not_called()


# ── Migrations: upgrade/downgrade smoke tests ────────────────────────────


class TestMigrations:
    """Smoke-test migration upgrade/downgrade with in-memory SQLite."""

    def _run_migration(self, module_path):
        """Import and run upgrade then downgrade for a migration module."""
        import importlib.util
        import sqlalchemy as sa
        from alembic.operations import Operations
        from alembic.runtime.migration import MigrationContext

        engine = sa.create_engine("sqlite:///:memory:")

        with engine.connect() as conn:
            # Create minimal tables so batch_alter_table succeeds
            meta = sa.MetaData()
            sa.Table('job', meta,
                     sa.Column('job_id', sa.Integer, primary_key=True),
                     sa.Column('status', sa.String(32)))
            sa.Table('track', meta,
                     sa.Column('track_id', sa.Integer, primary_key=True),
                     sa.Column('job_id', sa.Integer))
            sa.Table('config', meta,
                     sa.Column('config_id', sa.Integer, primary_key=True),
                     sa.Column('job_id', sa.Integer))
            meta.create_all(conn)
            conn.commit()

            # Set up proper Alembic context
            ctx = MigrationContext.configure(conn)

            spec = importlib.util.spec_from_file_location("migration", module_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            with Operations.context(ctx):
                mod.upgrade()
                mod.downgrade()

            conn.commit()
        engine.dispose()

    def test_multi_title_support_migration(self):
        self._run_migration(
            os.path.join(os.path.dirname(__file__), '..',
                         'arm/migrations/versions/b1c2d3e4f5a6_multi_title_support.py')
        )

    def test_track_add_enabled_migration(self):
        self._run_migration(
            os.path.join(os.path.dirname(__file__), '..',
                         'arm/migrations/versions/c2d3e4f5a6b7_track_add_enabled.py')
        )

    def test_job_add_disc_number_migration(self):
        self._run_migration(
            os.path.join(os.path.dirname(__file__), '..',
                         'arm/migrations/versions/d3e4f5a6b7c8_job_add_disc_number.py')
        )

    def test_config_add_audio_format_migration(self):
        self._run_migration(
            os.path.join(os.path.dirname(__file__), '..',
                         'arm/migrations/versions/c3d4e5f6a7b8_config_add_audio_format.py')
        )
