"""
Coverage tests for router modules.

Targets lines that were previously uncovered in main.py
and remain uncovered after the router refactor.
"""

import os
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from models import Base, TranscodeJobDB, JobStatus


@pytest_asyncio.fixture
async def router_client(tmp_path):
    """Test client that patches get_db in all router modules."""
    db_path = str(tmp_path / "router_test.db")
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

    mock_worker = MagicMock()
    mock_worker.is_running = True
    mock_worker.queue_size = 0
    mock_worker.current_job = None
    mock_worker.queue_job = AsyncMock(return_value=(1, True))
    mock_worker.shutdown = MagicMock()
    mock_worker.gpu_support = {"handbrake_nvenc": False, "ffmpeg_nvenc_h265": False}

    import database as db_module

    with patch.object(db_module, "get_db", test_get_db), \
         patch("routers.jobs.get_db", test_get_db), \
         patch("routers.stats.get_db", test_get_db), \
         patch("routers.config.get_db", test_get_db), \
         patch("main.init_db", AsyncMock()):

        import main as main_module
        main_module.app.state.worker = mock_worker
        main_module.app.state.gpu_monitor = None

        transport = ASGITransport(app=main_module.app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac, main_module.app, sf, mock_worker

        main_module.app.state.worker = None

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ─── jobs.py — list, retry, delete ──────────────────────────────────────────


class TestListJobsCoverage:
    @pytest.mark.asyncio
    async def test_list_jobs_returns_serialized_fields(self, router_client):
        ac, app, sf, _ = router_client
        async with sf() as session:
            session.add(TranscodeJobDB(
                id=1, title="Test Movie (2024)",
                source_path="/data/raw/Test Movie (2024)",
                status=JobStatus.COMPLETED,
                video_type="movie", year="2024", disctype="bluray",
            ))
            await session.commit()

        response = await ac.get("/jobs")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        job = data["jobs"][0]
        assert job["id"] == 1
        assert job["title"] == "Test Movie (2024)"
        assert job["status"] == "completed"
        assert job["video_type"] == "movie"

    @pytest.mark.asyncio
    async def test_list_jobs_pagination(self, router_client):
        ac, app, sf, _ = router_client
        async with sf() as session:
            for i in range(5):
                session.add(TranscodeJobDB(
                    id=100 + i, title=f"Movie {i}",
                    source_path=f"/data/raw/Movie {i}",
                    status=JobStatus.COMPLETED,
                ))
            await session.commit()

        response = await ac.get("/jobs?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 2
        assert data["total"] == 5


class TestRetryJobCoverage:
    @pytest.mark.asyncio
    async def test_retry_requeues_failed_job(self, router_client):
        ac, app, sf, mock_worker = router_client
        async with sf() as session:
            session.add(TranscodeJobDB(
                id=200, title="Failed Movie",
                source_path="/data/raw/Failed Movie",
                status=JobStatus.FAILED, retry_count=0,
            ))
            await session.commit()

        response = await ac.post("/jobs/200/retry")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
        assert data["job_id"] == 200

    @pytest.mark.asyncio
    async def test_retry_rejects_non_failed(self, router_client):
        ac, app, sf, _ = router_client
        async with sf() as session:
            session.add(TranscodeJobDB(
                id=201, title="Pending Movie",
                source_path="/data/raw/Pending",
                status=JobStatus.PENDING,
            ))
            await session.commit()

        response = await ac.post("/jobs/201/retry")
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_retry_rejects_over_limit(self, router_client):
        ac, app, sf, _ = router_client
        from config import settings
        async with sf() as session:
            session.add(TranscodeJobDB(
                id=202, title="Exhausted Movie",
                source_path="/data/raw/Exhausted",
                status=JobStatus.FAILED,
                retry_count=settings.max_retry_count,
            ))
            await session.commit()

        response = await ac.post("/jobs/202/retry")
        assert response.status_code == 400
        assert "retry limit" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_retry_not_found(self, router_client):
        ac, *_ = router_client
        response = await ac.post("/jobs/9999/retry")
        assert response.status_code == 404


class TestDeleteJobCoverage:
    @pytest.mark.asyncio
    async def test_delete_completed_job(self, router_client):
        ac, app, sf, _ = router_client
        async with sf() as session:
            session.add(TranscodeJobDB(
                id=300, title="Done Movie",
                source_path="/data/raw/Done",
                status=JobStatus.COMPLETED,
            ))
            await session.commit()

        response = await ac.delete("/jobs/300")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

    @pytest.mark.asyncio
    async def test_delete_processing_rejected(self, router_client):
        ac, app, sf, _ = router_client
        async with sf() as session:
            session.add(TranscodeJobDB(
                id=301, title="Active Movie",
                source_path="/data/raw/Active",
                status=JobStatus.PROCESSING,
            ))
            await session.commit()

        response = await ac.delete("/jobs/301")
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_not_found(self, router_client):
        ac, *_ = router_client
        response = await ac.delete("/jobs/9999")
        assert response.status_code == 404


# ─── stats.py — stats with data ────────────────────────────────────────────


class TestStatsCoverage:
    @pytest.mark.asyncio
    async def test_stats_with_jobs(self, router_client):
        ac, app, sf, _ = router_client
        async with sf() as session:
            session.add(TranscodeJobDB(id=400, title="A", source_path="/a", status=JobStatus.COMPLETED))
            session.add(TranscodeJobDB(id=401, title="B", source_path="/b", status=JobStatus.FAILED))
            session.add(TranscodeJobDB(id=402, title="C", source_path="/c", status=JobStatus.PENDING))
            await session.commit()

        response = await ac.get("/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["completed"] == 1
        assert data["failed"] == 1
        assert data["pending"] == 1


# ─── config.py — update existing override ──────────────────────────────────


class TestConfigUpdateCoverage:
    @pytest.mark.asyncio
    async def test_update_existing_override(self, router_client):
        ac, app, sf, _ = router_client
        # First update — creates the override
        response = await ac.patch("/config", json={"max_retry_count": 5})
        assert response.status_code == 200
        # Second update — updates existing override (the uncovered branch)
        response = await ac.patch("/config", json={"max_retry_count": 7})
        assert response.status_code == 200
        assert response.json()["applied"]["max_retry_count"] == 7


# ─── health.py — FAKE_GPU_STATS and restart fallback ───────────────────────


class TestFakeGpuStatsCoverage:
    @pytest.mark.asyncio
    async def test_fake_gpu_stats(self, router_client):
        ac, *_ = router_client
        with patch.dict(os.environ, {"FAKE_GPU_STATS": "1"}):
            response = await ac.get("/system/stats")
            assert response.status_code == 200
            data = response.json()
            assert data["gpu"] is not None
            assert data["gpu"]["vendor"] == "nvidia"


class TestRestartFallbackCoverage:
    @pytest.mark.asyncio
    async def test_restart_killpg_fallback(self, router_client):
        ac, *_ = router_client
        with patch("routers.health.os.killpg", side_effect=OSError("not permitted")), \
             patch("routers.health.os.kill") as mock_kill:
            response = await ac.post("/system/restart")
            assert response.status_code == 200

            import asyncio
            await asyncio.sleep(0.1)
