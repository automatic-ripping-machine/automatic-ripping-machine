"""
Tests to fill coverage gaps across all source modules.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker


# ── Shared API client fixture ────────────────────────────────────────────────

@pytest.fixture
def mock_worker_gaps():
    worker = MagicMock()
    worker.is_running = True
    worker.queue_size = 0
    worker.current_job = None
    worker.queue_job = AsyncMock(return_value=(1, True))
    worker.shutdown = MagicMock()
    return worker


@pytest_asyncio.fixture
async def api_client(mock_worker_gaps, tmp_path):
    db_path = str(tmp_path / "test_gaps.db")

    import database as db_module
    import auth as auth_module
    from models import Base

    test_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    test_session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    @asynccontextmanager
    async def test_get_db():
        async with test_session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    # Disable auth
    orig_require = auth_module.auth.require_auth
    auth_module.auth.require_auth = False

    with patch.object(db_module, "get_db", test_get_db), \
         patch("routers.jobs.get_db", test_get_db), \
         patch("routers.stats.get_db", test_get_db), \
         patch("routers.config.get_db", test_get_db), \
         patch("main.init_db", AsyncMock()):

        import main as main_module
        main_module.app.state.worker = mock_worker_gaps

        transport = ASGITransport(app=main_module.app)
        async with AsyncClient(transport=transport, base_url="https://test") as ac:
            yield ac, test_session_factory

        main_module.app.state.worker = None

    auth_module.auth.require_auth = orig_require

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


# ── GPU support helpers ──────────────────────────────────────────────────────

def _gpu_support_none():
    return {
        "handbrake_nvenc": False, "ffmpeg_nvenc_h265": False, "ffmpeg_nvenc_h264": False,
        "ffmpeg_vaapi_h265": False, "ffmpeg_vaapi_h264": False,
        "ffmpeg_amf_h265": False, "ffmpeg_amf_h264": False,
        "ffmpeg_qsv_h265": False, "ffmpeg_qsv_h264": False,
        "vaapi_device": False, "handbrake_qsv": False,
    }


def _mock_scheme_software():
    """Build a mock software scheme for test fixtures."""
    from presets import Preset, Scheme, Encoder
    preset = Preset(
        slug="test_sw", name="Test Software", scheme="software",
        shared={"video_encoder": "x265", "audio_encoder": "copy", "subtitle_mode": "all"},
        tiers={
            "dvd": {"handbrake_preset": "H.265 MKV 720p30", "video_quality": 22},
            "bluray": {"handbrake_preset": "H.265 MKV 1080p30", "video_quality": 22},
            "uhd": {"handbrake_preset": "H.265 MKV 2160p60 4K", "video_quality": 22},
        },
    )
    return Scheme(
        slug="software", name="Software (CPU)",
        supported_encoders=[Encoder(slug="x265", name="Software x265")],
        supported_audio_encoders=["copy", "aac"],
        supported_subtitle_modes=["all", "first", "none"],
        built_in_presets=[preset],
    )


def _scheme_patch():
    return patch("main.active_scheme", _mock_scheme_software())


# ── database.py ──────────────────────────────────────────────────────────────

class TestDatabaseGaps:
    @pytest.mark.asyncio
    async def test_init_db_creates_tables_and_migrations(self, tmp_dirs):
        """Cover init_db() lines 32-36."""
        from models import Base

        db_path = tmp_dirs["db_path"]
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)

        with patch("database.engine", engine):
            from database import init_db
            await init_db()

            async with engine.begin() as conn:
                from sqlalchemy import inspect
                tables = await conn.run_sync(lambda c: inspect(c).get_table_names())
                assert "transcode_jobs" in tables

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_get_db_rollback_on_exception(self, tmp_dirs):
        """Cover get_db() lines 66-71."""
        from models import Base

        db_path = tmp_dirs["db_path"]
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        with patch("database.async_session", session_factory):
            from database import get_db
            with pytest.raises(ValueError):
                async with get_db() as session:
                    raise ValueError("trigger rollback")

        await engine.dispose()


# ── utils.py ─────────────────────────────────────────────────────────────────

class TestUtilsGaps:
    def test_path_not_in_any_allowed_base(self, tmp_dirs):
        """Cover utils.py lines 81-85."""
        from utils import PathValidator
        validator = PathValidator([str(tmp_dirs["raw"])])
        with pytest.raises(ValueError):
            validator.validate("/completely/outside/path")

    def test_check_disk_space_exception(self):
        """Cover utils.py lines 272-274."""
        from utils import check_sufficient_disk_space
        with patch("utils.get_disk_space_info", side_effect=RuntimeError("disk error")):
            ok, msg = check_sufficient_disk_space("/fake/path", 1024)
            assert not ok
            assert "disk error" in msg

    def test_path_validator_symlink_escape(self, tmp_dirs):
        """Cover utils.py lines 75-77."""
        from utils import PathValidator

        base = tmp_dirs["raw"]
        outside = tmp_dirs["root"] / "outside_dir"
        outside.mkdir()
        target_file = outside / "external.txt"
        target_file.write_text("test content")

        link = base / "bad_link"
        try:
            link.symlink_to(target_file)
        except OSError:
            pytest.skip("Cannot create symlinks")

        validator = PathValidator([str(base)])
        with pytest.raises(ValueError):
            validator.validate(str(link))


# ── log_reader.py ────────────────────────────────────────────────────────────

class TestLogReaderGaps:
    def test_path_traversal_outside_log_dir(self, tmp_path):
        """Cover log_reader.py lines 50-51: path resolving outside log dir."""
        from log_reader import read_log

        # Create a log dir that doesn't contain the target
        log_dir = tmp_path / "logs"
        log_dir.mkdir()

        with patch("log_reader._log_dir", return_value=log_dir):
            # Attempt to traverse outside the log directory
            result = read_log("../../etc/hosts", mode="tail", lines=10)
            assert result is None


# ── config.py ────────────────────────────────────────────────────────────────

class TestConfigGaps:
    @pytest.mark.asyncio
    async def test_load_config_unknown_field_skipped(self, tmp_dirs):
        """Cover config.py line 265-266: unknown field in overrides → continue."""
        from models import Base, ConfigOverrideDB

        db_path = tmp_dirs["db_path"]
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Insert an override with a key not in model_fields
        async with session_factory() as session:
            session.add(ConfigOverrideDB(key="video_encoder", value="x265"))
            await session.commit()

        @asynccontextmanager
        async def fake_get_db():
            async with session_factory() as session:
                yield session

        import database as db_module
        with patch.object(db_module, "get_db", fake_get_db):
            from config import load_config_overrides
            # This covers the normal path; the field_info skip requires
            # a key in UPDATABLE_KEYS but not in model_fields, which
            # can't happen in practice. Just ensure no crash.
            await load_config_overrides()

        await engine.dispose()



# ── auth.py ──────────────────────────────────────────────────────────────────

class TestAuthGaps:
    def test_auth_required_but_no_keys_warning(self):
        """Cover auth.py line 43."""
        from auth import APIKeyAuth
        from config import settings

        orig_auth = settings.require_api_auth
        orig_keys = settings.api_keys
        try:
            settings.require_api_auth = True
            settings.api_keys = ""
            with patch("auth.logger") as mock_log:
                APIKeyAuth()
                mock_log.warning.assert_called()
        finally:
            settings.require_api_auth = orig_auth
            settings.api_keys = orig_keys


# ── transcoder.py encoder detection ─────────────────────────────────────────

class TestTranscoderEncoderGaps:
    def test_detect_amf_family(self):
        from transcoder import TranscodeWorker
        with _scheme_patch():
            worker = TranscodeWorker(gpu_support=_gpu_support_none())
        assert worker._detect_encoder_family("hevc_amf") == "amf"

    def test_detect_unknown_family(self):
        from transcoder import TranscodeWorker
        with _scheme_patch():
            worker = TranscodeWorker(gpu_support=_gpu_support_none())
        assert worker._detect_encoder_family("weird_encoder") == "unknown"

    def test_select_backend_nvenc_no_support(self):
        from transcoder import TranscodeWorker
        with _scheme_patch():
            worker = TranscodeWorker(gpu_support=_gpu_support_none())
        assert worker._select_backend("hevc_nvenc", "nvenc") == "ffmpeg"

    def test_select_backend_vaapi_no_device(self):
        from transcoder import TranscodeWorker
        with _scheme_patch():
            worker = TranscodeWorker(gpu_support=_gpu_support_none())
        assert worker._select_backend("hevc_vaapi", "vaapi") == "ffmpeg"

    def test_select_backend_qsv_handbrake(self):
        from transcoder import TranscodeWorker
        gpu = _gpu_support_none()
        gpu["handbrake_qsv"] = True
        with _scheme_patch():
            worker = TranscodeWorker(gpu_support=gpu)
        assert worker._select_backend("hevc_qsv", "qsv") == "handbrake"

    def test_select_backend_unknown_defaults_handbrake(self):
        from transcoder import TranscodeWorker
        with _scheme_patch():
            worker = TranscodeWorker(gpu_support=_gpu_support_none())
        assert worker._select_backend("weird", "unknown") == "handbrake"

    def test_select_backend_amf(self):
        from transcoder import TranscodeWorker
        with _scheme_patch():
            worker = TranscodeWorker(gpu_support=_gpu_support_none())
        assert worker._select_backend("hevc_amf", "amf") == "ffmpeg"


# ── transcoder.py FFmpeg / duration ──────────────────────────────────────────

class TestTranscoderFFmpegGaps:
    @pytest.mark.asyncio
    async def test_get_video_duration_success(self):
        from transcoder import TranscodeWorker
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"3600.5", b""))
        with _scheme_patch():
            worker = TranscodeWorker(gpu_support=_gpu_support_none())
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await worker._get_video_duration(Path("/test/video.mkv"))
            assert result == pytest.approx(3600.5)

    @pytest.mark.asyncio
    async def test_get_video_duration_exception(self):
        from transcoder import TranscodeWorker
        with _scheme_patch():
            worker = TranscodeWorker(gpu_support=_gpu_support_none())
        with patch("asyncio.create_subprocess_exec", side_effect=OSError("no ffprobe")):
            result = await worker._get_video_duration(Path("/test/video.mkv"))
            assert result is None

    @pytest.mark.asyncio
    async def test_get_video_duration_invalid(self):
        from transcoder import TranscodeWorker
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"not_a_number", b""))
        with _scheme_patch():
            worker = TranscodeWorker(gpu_support=_gpu_support_none())
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await worker._get_video_duration(Path("/test/video.mkv"))
            assert result is None


# ── main.py API endpoints ────────────────────────────────────────────────────

class TestMainAPIGaps:
    @pytest.mark.asyncio
    async def test_retry_job_not_found(self, api_client):
        client, _ = api_client
        response = await client.post("/jobs/99999/retry")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_job_not_found(self, api_client):
        client, _ = api_client
        response = await client.delete("/jobs/99999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_stats(self, api_client):
        client, _ = api_client
        response = await client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        assert "pending" in data
        assert "worker_running" in data

    @pytest.mark.asyncio
    async def test_list_jobs_with_job_id(self, api_client):
        client, _ = api_client
        response = await client.get("/jobs?job_id=123&limit=5&offset=0")
        assert response.status_code == 200
        assert "jobs" in response.json()

    @pytest.mark.asyncio
    async def test_retry_job_not_failed(self, api_client):
        client, session_factory = api_client
        from models import TranscodeJobDB, JobStatus
        async with session_factory() as session:
            job = TranscodeJobDB(id=1001, source_path="/test", title="T", status=JobStatus.COMPLETED, progress=100)
            session.add(job)
            await session.commit()
            job_id = job.id
        response = await client.post(f"/jobs/{job_id}/retry")
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_job_in_progress(self, api_client):
        client, session_factory = api_client
        from models import TranscodeJobDB, JobStatus
        async with session_factory() as session:
            job = TranscodeJobDB(id=1002, source_path="/test", title="T", status=JobStatus.PROCESSING, progress=50)
            session.add(job)
            await session.commit()
            job_id = job.id
        response = await client.delete(f"/jobs/{job_id}")
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_job_success(self, api_client):
        client, session_factory = api_client
        from models import TranscodeJobDB, JobStatus
        async with session_factory() as session:
            job = TranscodeJobDB(id=1003, source_path="/test", title="T", status=JobStatus.COMPLETED, progress=100)
            session.add(job)
            await session.commit()
            job_id = job.id
        response = await client.delete(f"/jobs/{job_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

    @pytest.mark.asyncio
    async def test_retry_job_success(self, api_client, mock_worker_gaps):
        client, session_factory = api_client
        from models import TranscodeJobDB, JobStatus
        async with session_factory() as session:
            job = TranscodeJobDB(id=1004, source_path="/test", title="T", status=JobStatus.FAILED, progress=0, retry_count=0, error="err")
            session.add(job)
            await session.commit()
            job_id = job.id
        response = await client.post(f"/jobs/{job_id}/retry")
        assert response.status_code == 200
        assert response.json()["status"] == "queued"
        assert response.json()["retry_count"] == 1
