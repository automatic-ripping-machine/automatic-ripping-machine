"""
Tests for multi-worker concurrency feature.

Covers: worker pool startup, concurrent processing, sentinel shutdown,
worker crash isolation, /workers endpoint, and WorkerStatus tracking.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from models import Base, TranscodeJobDB, JobStatus
from transcoder import TranscodeWorker, WorkerStatus


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


# ─── Unit tests for WorkerStatus ────────────────────────────────────────────


class TestWorkerStatus:
    def test_default_idle(self):
        ws = WorkerStatus(worker_id=0)
        assert ws.status == "idle"
        assert ws.current_job is None
        assert ws.current_job_id is None
        assert ws.started_at is None

    def test_processing_state(self):
        now = datetime.now(timezone.utc)
        ws = WorkerStatus(
            worker_id=1, status="processing",
            current_job="Test Movie", current_job_id=42,
            started_at=now,
        )
        assert ws.status == "processing"
        assert ws.current_job == "Test Movie"
        assert ws.current_job_id == 42

    def test_to_dict(self):
        now = datetime.now(timezone.utc)
        ws = WorkerStatus(
            worker_id=0, status="processing",
            current_job="Movie", current_job_id=1,
            started_at=now,
        )
        d = ws.to_dict()
        assert d["worker_id"] == 0
        assert d["status"] == "processing"
        assert d["current_job"] == "Movie"
        assert d["started_at"] == now.isoformat()

    def test_to_dict_idle(self):
        ws = WorkerStatus(worker_id=2)
        d = ws.to_dict()
        assert d["status"] == "idle"
        assert d["started_at"] is None


# ─── Worker properties ──────────────────────────────────────────────────────


class TestWorkerProperties:
    @pytest.fixture
    def worker(self):
        with patch("transcoder.check_gpu_support", return_value={
            "handbrake_nvenc": False, "ffmpeg_nvenc_h265": False,
            "ffmpeg_nvenc_h264": False, "ffmpeg_vaapi_h265": False,
            "ffmpeg_vaapi_h264": False, "ffmpeg_amf_h265": False,
            "ffmpeg_amf_h264": False, "ffmpeg_qsv_h265": False,
            "ffmpeg_qsv_h264": False, "vaapi_device": False,
        }), patch("main.active_scheme", _mock_scheme_software()):
            return TranscodeWorker()

    def test_active_count_empty(self, worker):
        assert worker.active_count == 0

    def test_active_count_with_workers(self, worker):
        worker._active_jobs[0] = WorkerStatus(worker_id=0)
        worker._active_jobs[1] = WorkerStatus(
            worker_id=1, status="processing",
            current_job="Movie", current_job_id=1,
        )
        assert worker.active_count == 1

    def test_current_job_backward_compat(self, worker):
        assert worker.current_job is None
        worker._active_jobs[0] = WorkerStatus(
            worker_id=0, status="processing",
            current_job="Test", current_job_id=1,
        )
        assert worker.current_job == "Test"

    def test_active_jobs_sorted(self, worker):
        worker._active_jobs[2] = WorkerStatus(worker_id=2)
        worker._active_jobs[0] = WorkerStatus(worker_id=0, status="processing", current_job="A", current_job_id=1)
        worker._active_jobs[1] = WorkerStatus(worker_id=1)
        jobs = worker.active_jobs
        assert [j["worker_id"] for j in jobs] == [0, 1, 2]

    def test_is_running_before_start(self, worker):
        assert not worker.is_running

    def test_is_running_after_start(self, worker):
        worker._running = True
        assert worker.is_running

    def test_is_running_after_shutdown(self, worker):
        worker._running = True
        worker.shutdown()
        assert not worker.is_running

    @pytest.mark.asyncio
    async def test_queue_sentinel(self, worker):
        await worker.queue_sentinel()
        assert worker.queue_size == 1


# ─── Multi-worker run loop ──────────────────────────────────────────────────


class TestMultiWorkerRunLoop:
    @pytest_asyncio.fixture
    async def worker_with_db(self, tmp_path):
        db_path = str(tmp_path / "test.db")
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

        with patch("transcoder.get_db", test_get_db), \
             patch("transcoder.check_gpu_support", return_value={
                 "handbrake_nvenc": False, "ffmpeg_nvenc_h265": False,
                 "ffmpeg_nvenc_h264": False, "ffmpeg_vaapi_h265": False,
                 "ffmpeg_vaapi_h264": False, "ffmpeg_amf_h265": False,
                 "ffmpeg_amf_h264": False, "ffmpeg_qsv_h265": False,
                 "ffmpeg_qsv_h264": False, "vaapi_device": False,
             }), patch("main.active_scheme", _mock_scheme_software()):
            worker = TranscodeWorker()
            yield worker, sf

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_sentinel_stops_worker(self, worker_with_db):
        """Putting None in queue should stop one worker."""
        worker, _ = worker_with_db

        with patch.object(worker, "_load_pending_jobs", new_callable=AsyncMock):
            # Start worker, then send sentinel
            async def send_sentinel():
                await asyncio.sleep(0.1)
                await worker.queue_sentinel()

            sentinel_task = asyncio.create_task(send_sentinel())
            await asyncio.wait_for(worker.run(worker_id=0), timeout=10.0)
            await sentinel_task

        assert 0 not in worker._active_jobs

    @pytest.mark.asyncio
    async def test_two_workers_both_stop_with_sentinels(self, worker_with_db):
        """Two workers should both stop when each gets a sentinel."""
        worker, _ = worker_with_db

        with patch.object(worker, "_load_pending_jobs", new_callable=AsyncMock):
            async def send_sentinels():
                await asyncio.sleep(0.1)
                await worker.queue_sentinel()
                await worker.queue_sentinel()

            sentinel_task = asyncio.create_task(send_sentinels())
            t0 = asyncio.create_task(worker.run(worker_id=0))
            t1 = asyncio.create_task(worker.run(worker_id=1))

            await asyncio.wait_for(asyncio.gather(t0, t1), timeout=10.0)
            await sentinel_task

        assert len(worker._active_jobs) == 0

    @pytest.mark.asyncio
    async def test_worker_crash_isolation(self, worker_with_db):
        """One worker crashing should not affect another."""
        worker, sf = worker_with_db

        call_count = {"w0": 0, "w1": 0}

        original_process = worker._process_job

        async def failing_process(job):
            if call_count["w0"] == 0:
                call_count["w0"] += 1
                raise RuntimeError("Simulated GPU crash")
            call_count["w1"] += 1

        with patch.object(worker, "_load_pending_jobs", new_callable=AsyncMock), \
             patch.object(worker, "_process_job", side_effect=failing_process):

            async def feed_and_stop():
                await asyncio.sleep(0.1)
                # Queue two jobs
                from models import TranscodeJob
                job1 = TranscodeJob(id=1, title="Crash Job", source_path="/fake/1")
                job2 = TranscodeJob(id=2, title="Good Job", source_path="/fake/2")
                await worker._queue.put(job1)
                await asyncio.sleep(0.5)
                await worker._queue.put(job2)
                await asyncio.sleep(0.5)
                # Stop both workers
                await worker.queue_sentinel()
                await worker.queue_sentinel()

            feed_task = asyncio.create_task(feed_and_stop())
            t0 = asyncio.create_task(worker.run(worker_id=0))
            t1 = asyncio.create_task(worker.run(worker_id=1))

            await asyncio.wait_for(asyncio.gather(t0, t1), timeout=15.0)
            await feed_task

        # Both workers should have exited cleanly
        assert len(worker._active_jobs) == 0
        # At least one job should have been attempted after the crash
        assert call_count["w0"] + call_count["w1"] >= 2

    @pytest.mark.asyncio
    async def test_worker_tracks_status_during_processing(self, worker_with_db):
        """Worker should set status to processing while running a job."""
        worker, _ = worker_with_db
        status_during_process = None

        async def capture_status(job):
            nonlocal status_during_process
            status_during_process = worker._active_jobs.get(0)

        with patch.object(worker, "_load_pending_jobs", new_callable=AsyncMock), \
             patch.object(worker, "_process_job", side_effect=capture_status):

            async def feed_and_stop():
                await asyncio.sleep(0.1)
                from models import TranscodeJob
                job = TranscodeJob(id=1, title="Status Test", source_path="/fake")
                await worker._queue.put(job)
                await asyncio.sleep(0.5)
                await worker.queue_sentinel()

            feed_task = asyncio.create_task(feed_and_stop())
            await asyncio.wait_for(worker.run(worker_id=0), timeout=10.0)
            await feed_task

        assert status_during_process is not None
        assert status_during_process.status == "processing"
        assert status_during_process.current_job == "Status Test"
        assert status_during_process.current_job_id == 1
        assert status_during_process.started_at is not None


# ─── /workers endpoint ─────────────────────────────────────────────────────


class TestWorkersEndpoint:
    @pytest_asyncio.fixture
    async def client(self, tmp_path):
        db_path = str(tmp_path / "workers_test.db")
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
        sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        @asynccontextmanager
        async def test_get_db():
            async with sf() as session:
                yield session

        mock_worker = MagicMock()
        mock_worker.active_count = 1
        mock_worker.active_jobs = [
            {"worker_id": 0, "status": "processing", "current_job": "Test Movie", "current_job_id": 1, "started_at": "2026-04-03T10:00:00+00:00"},
            {"worker_id": 1, "status": "idle", "current_job": None, "current_job_id": None, "started_at": None},
        ]
        mock_worker.is_running = True
        mock_worker.gpu_support = {}

        import database as db_module
        with patch.object(db_module, "get_db", test_get_db), \
             patch("routers.jobs.get_db", test_get_db), \
             patch("routers.stats.get_db", test_get_db), \
             patch("routers.config.get_db", test_get_db), \
             patch("main.init_db", AsyncMock()):
            import main as m
            m.app.state.worker = mock_worker
            m.app.state.gpu_monitor = None
            transport = ASGITransport(app=m.app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                yield ac
            m.app.state.worker = None

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_workers_endpoint(self, client):
        response = await client.get("/workers")
        assert response.status_code == 200
        data = response.json()
        assert "max_concurrent" in data
        assert data["active_count"] == 1
        assert len(data["workers"]) == 2
        assert data["workers"][0]["status"] == "processing"
        assert data["workers"][0]["current_job"] == "Test Movie"
        assert data["workers"][1]["status"] == "idle"

    @pytest.mark.asyncio
    async def test_health_includes_active_count(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "active_count" in data
        assert "max_concurrent" in data
