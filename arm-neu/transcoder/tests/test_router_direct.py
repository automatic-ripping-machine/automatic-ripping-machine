"""
Direct-call tests for router endpoint functions.

These bypass the ASGI transport to ensure coverage tracks the router code.
The ASGI transport runs code in a context that pytest-cov sometimes misses.
"""

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from models import Base, TranscodeJobDB, JobStatus, ConfigOverrideDB


@pytest_asyncio.fixture
async def db_fixture(tmp_path):
    """Create test DB and provide session factory + get_db mock."""
    db_path = str(tmp_path / "direct_test.db")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    @asynccontextmanager
    async def test_get_db():
        async with sf() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    yield sf, test_get_db

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def _mock_request(worker=None):
    """Create a mock Request with app.state.worker."""
    req = MagicMock()
    req.app.state.worker = worker or MagicMock(
        is_running=True, queue_size=0, current_job=None,
        active_count=0, active_jobs=[], gpu_support={},
    )
    req.app.version = "test"
    return req


# ─── jobs.py direct calls ──────────────────────────────────────────────────


class TestJobsDirectCoverage:
    @pytest.mark.asyncio
    async def test_list_jobs_serialization(self, db_fixture):
        """Direct call to list_jobs to cover response serialization."""
        sf, test_get_db = db_fixture

        async with sf() as session:
            session.add(TranscodeJobDB(
                id=1, title="Direct Test Movie",
                source_path="/data/raw/Direct Test",
                status=JobStatus.COMPLETED,
                video_type="movie", year="2024", disctype="bluray",
                phase="finalizing",
            ))
            await session.commit()

        with patch("routers.jobs.get_db", test_get_db):
            from routers.jobs import list_jobs
            result = await list_jobs(
                _role="viewer",
                status=None, job_id=None, limit=50, offset=0,
            )

        assert result["total"] == 1
        job = result["jobs"][0]
        assert job["id"] == 1
        assert job["title"] == "Direct Test Movie"
        assert job["status"] == "completed"
        assert job["video_type"] == "movie"
        assert job["phase"] == "finalizing"
        assert "created_at" in job
        assert "config_overrides" in job

    @pytest.mark.asyncio
    async def test_list_jobs_with_filter(self, db_fixture):
        sf, test_get_db = db_fixture

        async with sf() as session:
            session.add(TranscodeJobDB(id=10, title="A", source_path="/a", status=JobStatus.COMPLETED))
            session.add(TranscodeJobDB(id=11, title="B", source_path="/b", status=JobStatus.FAILED))
            await session.commit()

        with patch("routers.jobs.get_db", test_get_db):
            from routers.jobs import list_jobs
            result = await list_jobs(_role="viewer", status=JobStatus.FAILED, job_id=None, limit=50, offset=0)

        assert result["total"] == 1
        assert result["jobs"][0]["title"] == "B"

    @pytest.mark.asyncio
    async def test_retry_job_full_flow(self, db_fixture):
        sf, test_get_db = db_fixture
        mock_worker = MagicMock(is_running=True)
        mock_worker.queue_job = AsyncMock()

        async with sf() as session:
            session.add(TranscodeJobDB(
                id=20, title="Retry Movie",
                source_path="/data/raw/Retry",
                status=JobStatus.FAILED, retry_count=0,
            ))
            await session.commit()

        with patch("routers.jobs.get_db", test_get_db):
            from routers.jobs import retry_job
            req = _mock_request(mock_worker)
            result = await retry_job(job_id=20, request=req, _role="admin")

        assert result["status"] == "queued"
        assert result["job_id"] == 20
        mock_worker.queue_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_job_not_found(self, db_fixture):
        _, test_get_db = db_fixture
        mock_worker = MagicMock(is_running=True)

        from fastapi import HTTPException
        with patch("routers.jobs.get_db", test_get_db):
            from routers.jobs import retry_job
            req = _mock_request(mock_worker)
            with pytest.raises(HTTPException) as exc_info:
                await retry_job(job_id=9999, request=req, _role="admin")
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_retry_job_not_failed(self, db_fixture):
        sf, test_get_db = db_fixture
        mock_worker = MagicMock(is_running=True)

        async with sf() as session:
            session.add(TranscodeJobDB(
                id=21, title="Pending", source_path="/p", status=JobStatus.PENDING,
            ))
            await session.commit()

        from fastapi import HTTPException
        with patch("routers.jobs.get_db", test_get_db):
            from routers.jobs import retry_job
            req = _mock_request(mock_worker)
            with pytest.raises(HTTPException) as exc_info:
                await retry_job(job_id=21, request=req, _role="admin")
            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_retry_job_exceeds_limit(self, db_fixture):
        sf, test_get_db = db_fixture
        mock_worker = MagicMock(is_running=True)

        from config import settings
        async with sf() as session:
            session.add(TranscodeJobDB(
                id=22, title="Exhausted", source_path="/e",
                status=JobStatus.FAILED, retry_count=settings.max_retry_count,
            ))
            await session.commit()

        from fastapi import HTTPException
        with patch("routers.jobs.get_db", test_get_db):
            from routers.jobs import retry_job
            req = _mock_request(mock_worker)
            with pytest.raises(HTTPException) as exc_info:
                await retry_job(job_id=22, request=req, _role="admin")
            assert "retry limit" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_delete_job_completed(self, db_fixture):
        sf, test_get_db = db_fixture

        async with sf() as session:
            session.add(TranscodeJobDB(
                id=30, title="Delete Me", source_path="/d", status=JobStatus.COMPLETED,
            ))
            await session.commit()

        with patch("routers.jobs.get_db", test_get_db):
            from routers.jobs import delete_job
            result = await delete_job(job_id=30, _role="admin")

        assert result["status"] == "deleted"
        assert result["job_id"] == 30

    @pytest.mark.asyncio
    async def test_delete_job_processing_rejected(self, db_fixture):
        sf, test_get_db = db_fixture

        async with sf() as session:
            session.add(TranscodeJobDB(
                id=31, title="Active", source_path="/a", status=JobStatus.PROCESSING,
            ))
            await session.commit()

        from fastapi import HTTPException
        with patch("routers.jobs.get_db", test_get_db):
            from routers.jobs import delete_job
            with pytest.raises(HTTPException) as exc_info:
                await delete_job(job_id=31, _role="admin")
            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_job_not_found(self, db_fixture):
        _, test_get_db = db_fixture

        from fastapi import HTTPException
        with patch("routers.jobs.get_db", test_get_db):
            from routers.jobs import delete_job
            with pytest.raises(HTTPException) as exc_info:
                await delete_job(job_id=9999, _role="admin")
            assert exc_info.value.status_code == 404


# ─── stats.py direct call ──────────────────────────────────────────────────


class TestStatsDirectCoverage:
    @pytest.mark.asyncio
    async def test_stats_counts(self, db_fixture):
        sf, test_get_db = db_fixture
        mock_worker = MagicMock(is_running=True, current_job=None, active_count=0)

        async with sf() as session:
            session.add(TranscodeJobDB(id=40, title="A", source_path="/a", status=JobStatus.COMPLETED))
            session.add(TranscodeJobDB(id=41, title="B", source_path="/b", status=JobStatus.FAILED))
            session.add(TranscodeJobDB(id=42, title="C", source_path="/c", status=JobStatus.PENDING))
            await session.commit()

        with patch("routers.stats.get_db", test_get_db):
            from routers.stats import get_stats
            req = _mock_request(mock_worker)
            result = await get_stats(request=req, _role="viewer")

        assert result["completed"] == 1
        assert result["failed"] == 1
        assert result["pending"] == 1
        assert result["active_count"] == 0


# ─── config.py direct call ─────────────────────────────────────────────────


class TestConfigDirectCoverage:
    @pytest.mark.asyncio
    async def test_update_existing_override(self, db_fixture):
        sf, test_get_db = db_fixture

        with patch("routers.config.get_db", test_get_db):
            from routers.config import update_config

            # First update — creates override
            req1 = MagicMock()
            req1.json = AsyncMock(return_value={"max_retry_count": 5})
            result1 = await update_config(request=req1, _role="admin")
            assert result1["success"] is True

            # Second update — hits the 'if override:' branch
            req2 = MagicMock()
            req2.json = AsyncMock(return_value={"max_retry_count": 7})
            result2 = await update_config(request=req2, _role="admin")
            assert result2["success"] is True
            assert result2["applied"]["max_retry_count"] == 7


# ─── main.py lifespan ──────────────────────────────────────────────────────


class TestLifespanCoverage:
    @staticmethod
    def _mock_scheme():
        from presets import Preset, Scheme, Encoder
        preset = Preset(
            slug="test", name="Test", scheme="test",
            shared={"video_encoder": "x265", "audio_encoder": "copy", "subtitle_mode": "all"},
            tiers={
                "dvd": {"handbrake_preset": "Test 720p", "video_quality": 22},
                "bluray": {"handbrake_preset": "Test 1080p", "video_quality": 22},
                "uhd": {"handbrake_preset": "Test 2160p 4K", "video_quality": 22},
            },
        )
        return Scheme(
            slug="test", name="Test",
            supported_encoders=[Encoder(slug="x265", name="x265")],
            supported_audio_encoders=["copy"], supported_subtitle_modes=["all"],
            built_in_presets=[preset],
        )

    @pytest.mark.asyncio
    async def test_lifespan_startup_shutdown(self, tmp_path):
        """Cover lifespan startup and shutdown paths."""
        from unittest.mock import patch, AsyncMock, MagicMock
        from fastapi import FastAPI

        mock_worker = MagicMock()
        mock_worker.run = AsyncMock()
        mock_worker.shutdown = MagicMock()
        mock_worker.queue_sentinel = AsyncMock()

        mock_gpu_monitor = MagicMock()
        mock_scheme = self._mock_scheme()

        with patch("main.init_db", AsyncMock()), \
             patch("main.load_config_overrides", AsyncMock()), \
             patch("main.load_active_scheme", return_value=mock_scheme), \
             patch("main.TranscodeWorker", return_value=mock_worker), \
             patch("transcoder.check_gpu_support", return_value={}), \
             patch("main.create_gpu_monitor", return_value=mock_gpu_monitor), \
             patch("main.settings") as mock_settings:
            mock_settings.gpu_vendor = "nvidia"
            mock_settings.max_concurrent = 2
            mock_settings.arm_callback_url = ""

            from main import lifespan
            app = FastAPI()

            # Make run() complete immediately when called
            mock_worker.run = AsyncMock(return_value=None)

            async with lifespan(app):
                assert hasattr(app.state, 'worker')
                assert hasattr(app.state, 'gpu_monitor')
                assert app.state.worker is mock_worker

            # Verify shutdown called
            mock_worker.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_shutdown_timeout(self, tmp_path):
        """Cover the TimeoutError branch during shutdown."""
        from unittest.mock import patch, AsyncMock, MagicMock
        from fastapi import FastAPI

        mock_worker = MagicMock()
        mock_worker.shutdown = MagicMock()
        mock_worker.queue_sentinel = AsyncMock()

        async def hang_forever(worker_id=0):
            await asyncio.sleep(9999)

        mock_worker.run = AsyncMock(side_effect=hang_forever)
        mock_scheme = self._mock_scheme()

        with patch("main.init_db", AsyncMock()), \
             patch("main.load_config_overrides", AsyncMock()), \
             patch("main.load_active_scheme", return_value=mock_scheme), \
             patch("main.TranscodeWorker", return_value=mock_worker), \
             patch("transcoder.check_gpu_support", return_value={}), \
             patch("main.create_gpu_monitor", return_value=None), \
             patch("main.settings") as mock_settings, \
             patch("main.SHUTDOWN_TIMEOUT", 0.1):
            mock_settings.gpu_vendor = ""
            mock_settings.max_concurrent = 1
            mock_settings.arm_callback_url = ""

            from main import lifespan
            app = FastAPI()

            async with lifespan(app):
                pass  # worker hangs

            # Shutdown should have timed out and cancelled

    @pytest.mark.asyncio
    async def test_lifespan_no_worker(self, tmp_path):
        """Cover the else branch when worker is None at shutdown."""
        from unittest.mock import patch, AsyncMock, MagicMock
        from fastapi import FastAPI

        mock_worker = MagicMock()
        mock_worker.run = AsyncMock(return_value=None)
        mock_worker.shutdown = MagicMock()
        mock_worker.queue_sentinel = AsyncMock()
        mock_scheme = self._mock_scheme()

        with patch("main.init_db", AsyncMock()), \
             patch("main.load_config_overrides", AsyncMock()), \
             patch("main.load_active_scheme", return_value=mock_scheme), \
             patch("main.TranscodeWorker", return_value=mock_worker), \
             patch("transcoder.check_gpu_support", return_value={}), \
             patch("main.create_gpu_monitor", return_value=None), \
             patch("main.settings") as mock_settings:
            mock_settings.gpu_vendor = ""
            mock_settings.max_concurrent = 1
            mock_settings.arm_callback_url = ""

            from main import lifespan
            app = FastAPI()

            async with lifespan(app):
                # Simulate worker being None at shutdown
                app.state.worker = None

            # Should not raise
