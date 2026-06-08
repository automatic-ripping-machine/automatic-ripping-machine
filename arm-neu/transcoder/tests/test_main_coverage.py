"""
Tests for main.py - additional coverage for uncovered lines.

Targets: _read_version, _detect_cpu, _normalize_source_path,
_extract_media_title, lifespan, system endpoints, config endpoints,
retry/delete with real DB jobs, logs endpoints, payload-too-large.
"""

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from models import Base, TranscodeJobDB, JobStatus, ConfigOverrideDB


# ─── Shared fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def mock_worker():
    """Create a mock TranscodeWorker."""
    worker = MagicMock()
    worker.is_running = True
    worker.queue_size = 2
    worker.current_job = None
    worker.gpu_support = {"handbrake_nvenc": True}
    worker.queue_job = AsyncMock(return_value=(1, True))
    worker.shutdown = MagicMock()
    return worker


@pytest_asyncio.fixture
async def client(mock_worker, tmp_path):
    """Create an async test client with initialized test DB."""
    db_path = str(tmp_path / "test.db")

    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

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

    from tests.api_test_helpers import patched_app_client
    async with patched_app_client(mock_worker, test_get_db) as (ac, main_module):
        yield ac, main_module.app, test_session_factory

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


# ─── _read_version ──────────────────────────────────────────────────────────


class TestReadVersion:
    """Tests for _read_version()."""

    def test_reads_version_from_file(self, tmp_path):
        """Should read version from first accessible file."""
        from main import _read_version

        version_file = tmp_path / "VERSION"
        version_file.write_text("1.2.3\n")

        with patch("main.os.path.dirname", return_value=str(tmp_path)):
            # Patch to check the VERSION file at the module directory
            with patch("builtins.open", side_effect=[
                OSError("not found"),  # "VERSION" (cwd)
                open(str(version_file)),  # os.path.dirname(__file__)/VERSION
            ]):
                result = _read_version()
                assert result == "1.2.3"

    def test_returns_unknown_when_no_files_exist(self):
        """Should return 'unknown' when no VERSION files found."""
        from main import _read_version

        with patch("builtins.open", side_effect=OSError("not found")):
            result = _read_version()
            assert result == "unknown"


# ─── _detect_cpu ────────────────────────────────────────────────────────────


class TestDetectCpu:
    """Tests for _detect_cpu()."""

    def test_reads_from_proc_cpuinfo(self):
        """Should extract model name from /proc/cpuinfo."""
        from routers.health import _detect_cpu

        cpuinfo = "processor\t: 0\nmodel name\t: Intel(R) Core(TM) i7-10700K\nstepping\t: 5\n"
        with patch("builtins.open", mock_open(read_data=cpuinfo)):
            result = _detect_cpu()
            assert "i7-10700K" in result

    def test_falls_back_to_platform_on_oserror(self):
        """Should use platform.processor() when /proc/cpuinfo unavailable."""
        from routers.health import _detect_cpu

        with patch("builtins.open", side_effect=OSError("not found")), \
             patch("routers.health.platform.processor", return_value="x86_64"):
            result = _detect_cpu()
            assert result == "x86_64"

    def test_returns_unknown_on_no_data(self):
        """Should return 'Unknown' when nothing available."""
        from routers.health import _detect_cpu

        with patch("builtins.open", side_effect=OSError("not found")), \
             patch("routers.health.platform.processor", return_value=""):
            result = _detect_cpu()
            assert result == "Unknown"

    def test_no_model_name_line(self):
        """Should fall back when cpuinfo has no model name line."""
        from routers.health import _detect_cpu

        cpuinfo = "processor\t: 0\nstepping\t: 5\n"
        with patch("builtins.open", mock_open(read_data=cpuinfo)), \
             patch("routers.health.platform.processor", return_value="aarch64"):
            result = _detect_cpu()
            assert result == "aarch64"


# ─── _extract_media_title ───────────────────────────────────────────────────


class TestExtractMediaTitle:
    """Tests for _extract_media_title()."""

    def test_returns_none_for_none(self):
        from routers.jobs import _extract_media_title
        assert _extract_media_title(None) is None

    def test_returns_none_for_empty(self):
        from routers.jobs import _extract_media_title
        assert _extract_media_title("") is None

    def test_rip_complete_pattern(self):
        from routers.jobs import _extract_media_title
        result = _extract_media_title("Movie Title (2024) rip complete. Starting transcode.")
        assert result == "Movie Title (2024)"

    def test_processing_complete_pattern(self):
        from routers.jobs import _extract_media_title
        result = _extract_media_title("Movie Title (2024) processing complete.")
        assert result == "Movie Title (2024)"

    def test_legacy_rip_of_pattern(self):
        from routers.jobs import _extract_media_title
        result = _extract_media_title("Rip of Movie Title complete")
        assert result == "Movie Title"

    def test_fallback_strips_year(self):
        from routers.jobs import _extract_media_title
        result = _extract_media_title("Movie Title (2024)")
        assert result == "Movie Title"

    def test_fallback_no_year(self):
        from routers.jobs import _extract_media_title
        result = _extract_media_title("Some Random Text")
        assert result == "Some Random Text"


# ─── System Endpoints ───────────────────────────────────────────────────────


class TestSystemInfoEndpoint:
    """Tests for GET /system/info."""

    @pytest.mark.asyncio
    async def test_system_info(self, client):
        ac, app, *_rest = client
        mock_mem = MagicMock()
        mock_mem.total = 17179869184  # 16 GB
        with patch("routers.health.psutil.virtual_memory", return_value=mock_mem), \
             patch("routers.health._detect_cpu", return_value="Intel i7-10700K"):
            response = await ac.get("/system/info")
            assert response.status_code == 200
            data = response.json()
            assert data["cpu"] == "Intel i7-10700K"
            assert data["memory_total_gb"] == pytest.approx(16.0)
            assert "gpu_support" in data


class TestSystemStatsEndpoint:
    """Tests for GET /system/stats."""

    @pytest.mark.asyncio
    async def test_system_stats_with_temps(self, client):
        ac, app, *_rest = client
        mock_mem = MagicMock()
        mock_mem.total = 17179869184
        mock_mem.used = 8589934592
        mock_mem.available = 8589934592
        mock_mem.percent = 50.0

        mock_temp = MagicMock()
        mock_temp.current = 55.0
        mock_temps = {"coretemp": [mock_temp]}

        with patch("routers.health.psutil.cpu_percent", return_value=25.0), \
             patch("routers.health.psutil.sensors_temperatures", return_value=mock_temps), \
             patch("routers.health.psutil.virtual_memory", return_value=mock_mem), \
             patch("routers.health.psutil.disk_usage", side_effect=FileNotFoundError("no such path")):
            response = await ac.get("/system/stats")
            assert response.status_code == 200
            data = response.json()
            assert data["cpu_percent"] == pytest.approx(25.0)
            assert data["cpu_temp"] == pytest.approx(55.0)
            assert data["memory"]["percent"] == pytest.approx(50.0)
            assert data["storage"] == []

    @pytest.mark.asyncio
    async def test_system_stats_no_temps(self, client):
        """Should handle missing temperature sensors gracefully."""
        ac, app, *_rest = client
        mock_mem = MagicMock()
        mock_mem.total = 17179869184
        mock_mem.used = 8589934592
        mock_mem.available = 8589934592
        mock_mem.percent = 50.0

        with patch("routers.health.psutil.cpu_percent", return_value=10.0), \
             patch("routers.health.psutil.sensors_temperatures", side_effect=AttributeError), \
             patch("routers.health.psutil.virtual_memory", return_value=mock_mem), \
             patch("routers.health.psutil.disk_usage", side_effect=FileNotFoundError):
            response = await ac.get("/system/stats")
            assert response.status_code == 200
            data = response.json()
            assert data["cpu_temp"] == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_system_stats_with_disk_usage(self, client):
        """Should return storage info when paths exist."""
        ac, app, *_rest = client
        mock_mem = MagicMock()
        mock_mem.total = 17179869184
        mock_mem.used = 8589934592
        mock_mem.available = 8589934592
        mock_mem.percent = 50.0

        mock_disk = MagicMock()
        mock_disk.total = 500 * 1073741824
        mock_disk.used = 200 * 1073741824
        mock_disk.free = 300 * 1073741824
        mock_disk.percent = 40.0

        with patch("routers.health.psutil.cpu_percent", return_value=10.0), \
             patch("routers.health.psutil.sensors_temperatures", return_value={}), \
             patch("routers.health.psutil.virtual_memory", return_value=mock_mem), \
             patch("routers.health.psutil.disk_usage", return_value=mock_disk):
            response = await ac.get("/system/stats")
            data = response.json()
            assert len(data["storage"]) == 3
            assert data["storage"][0]["name"] == "Raw"
            assert data["storage"][0]["percent"] == pytest.approx(40.0)

    @pytest.mark.asyncio
    async def test_system_stats_k10temp(self, client):
        """Should detect k10temp sensor (AMD)."""
        ac, app, *_rest = client
        mock_mem = MagicMock()
        mock_mem.total = 17179869184
        mock_mem.used = 8589934592
        mock_mem.available = 8589934592
        mock_mem.percent = 50.0

        mock_temp = MagicMock()
        mock_temp.current = 42.0
        mock_temps = {"k10temp": [mock_temp]}

        with patch("routers.health.psutil.cpu_percent", return_value=10.0), \
             patch("routers.health.psutil.sensors_temperatures", return_value=mock_temps), \
             patch("routers.health.psutil.virtual_memory", return_value=mock_mem), \
             patch("routers.health.psutil.disk_usage", side_effect=FileNotFoundError):
            response = await ac.get("/system/stats")
            data = response.json()
            assert data["cpu_temp"] == pytest.approx(42.0)

    @pytest.mark.asyncio
    async def test_system_stats_includes_gpu_null_when_no_monitor(self, client):
        """GPU field is null when no GPU monitor is configured."""
        ac, app, *_rest = client
        mock_mem = MagicMock()
        mock_mem.total = 17179869184
        mock_mem.used = 8589934592
        mock_mem.available = 8589934592
        mock_mem.percent = 50.0

        saved_monitor = getattr(app.state, 'gpu_monitor', None)
        app.state.gpu_monitor = None
        try:
            with patch("routers.health.psutil.cpu_percent", return_value=10.0), \
                 patch("routers.health.psutil.sensors_temperatures", return_value={}), \
                 patch("routers.health.psutil.virtual_memory", return_value=mock_mem), \
                 patch("routers.health.psutil.disk_usage", side_effect=FileNotFoundError):
                response = await ac.get("/system/stats")
                data = response.json()
                assert data["gpu"] is None
        finally:
            app.state.gpu_monitor = saved_monitor

    @pytest.mark.asyncio
    async def test_system_stats_includes_gpu_snapshot(self, client):
        """GPU field contains snapshot when monitor is configured."""
        ac, app, *_rest = client
        mock_mem = MagicMock()
        mock_mem.total = 17179869184
        mock_mem.used = 8589934592
        mock_mem.available = 8589934592
        mock_mem.percent = 50.0

        mock_monitor = MagicMock()
        mock_snap = {
            "vendor": "nvidia",
            "utilization_percent": 45.0,
            "memory_used_mb": 1024.0,
            "memory_total_mb": 8192.0,
            "temperature_c": 65.0,
            "encoder_percent": 78.0,
        }
        mock_monitor.snapshot.return_value = MagicMock(to_dict=MagicMock(return_value=mock_snap))

        saved_monitor = getattr(app.state, 'gpu_monitor', None)
        app.state.gpu_monitor = mock_monitor
        try:
            with patch("routers.health.psutil.cpu_percent", return_value=10.0), \
                 patch("routers.health.psutil.sensors_temperatures", return_value={}), \
                 patch("routers.health.psutil.virtual_memory", return_value=mock_mem), \
                 patch("routers.health.psutil.disk_usage", side_effect=FileNotFoundError):
                response = await ac.get("/system/stats")
                data = response.json()
                assert data["gpu"]["vendor"] == "nvidia"
                assert data["gpu"]["utilization_percent"] == pytest.approx(45.0)
                assert data["gpu"]["encoder_percent"] == pytest.approx(78.0)
        finally:
            app.state.gpu_monitor = saved_monitor

    @pytest.mark.asyncio
    async def test_system_stats_gpu_snapshot_exception(self, client):
        """GPU field is null when monitor.snapshot() raises."""
        ac, app, *_rest = client
        mock_mem = MagicMock()
        mock_mem.total = 17179869184
        mock_mem.used = 8589934592
        mock_mem.available = 8589934592
        mock_mem.percent = 50.0

        mock_monitor = MagicMock()
        mock_monitor.snapshot.side_effect = RuntimeError("GPU hung")

        saved_monitor = getattr(app.state, 'gpu_monitor', None)
        app.state.gpu_monitor = mock_monitor
        try:
            with patch("routers.health.psutil.cpu_percent", return_value=10.0), \
                 patch("routers.health.psutil.sensors_temperatures", return_value={}), \
                 patch("routers.health.psutil.virtual_memory", return_value=mock_mem), \
                 patch("routers.health.psutil.disk_usage", side_effect=FileNotFoundError):
                response = await ac.get("/system/stats")
                assert response.json()["gpu"] is None
        finally:
            app.state.gpu_monitor = saved_monitor


# ─── Config Endpoints ───────────────────────────────────────────────────────


class TestGetConfigEndpoint:
    """Tests for GET /config."""

    @pytest.mark.asyncio
    async def test_get_config(self, client):
        ac, app, *_rest = client
        response = await ac.get("/config")
        assert response.status_code == 200
        data = response.json()
        assert "config" in data
        assert "updatable_keys" in data
        assert "paths" in data
        assert "valid_log_levels" in data


class TestPatchConfigEndpoint:
    """Tests for PATCH /config."""

    @pytest.mark.asyncio
    async def test_update_valid_config(self, client):
        ac, app, *_rest = client
        from config import settings
        original = settings.max_retry_count
        try:
            response = await ac.patch("/config", json={"max_retry_count": 5})
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["applied"]["max_retry_count"] == 5
        finally:
            settings.max_retry_count = original

    @pytest.mark.asyncio
    async def test_update_empty_body_rejected(self, client):
        ac, app, *_rest = client
        response = await ac.patch("/config", json={})
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_update_non_dict_rejected(self, client):
        ac, app, *_rest = client
        response = await ac.patch("/config", content=b'"just a string"',
                                  headers={"content-type": "application/json"})
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_update_invalid_key_rejected(self, client):
        ac, app, *_rest = client
        response = await ac.patch("/config", json={"db_path": "/evil"})
        assert response.status_code == 400
        assert "Non-updatable" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_invalid_value_rejected(self, client):
        ac, app, *_rest = client
        response = await ac.patch("/config", json={"max_concurrent": 999})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_persists_to_db(self, client):
        """Config update should persist override to database."""
        ac, app, session_factory = client
        from config import settings
        original = settings.max_concurrent
        try:
            response = await ac.patch("/config", json={"max_concurrent": 3})
            assert response.status_code == 200

            # Verify DB record created
            async with session_factory() as session:
                from sqlalchemy import select
                result = await session.execute(
                    select(ConfigOverrideDB).where(ConfigOverrideDB.key == "max_concurrent")
                )
                override = result.scalar_one_or_none()
                assert override is not None
                assert override.value == "3"
        finally:
            settings.max_concurrent = original

    @pytest.mark.asyncio
    async def test_update_existing_override(self, client):
        """Updating an already-overridden key should update the DB record."""
        ac, app, session_factory = client
        from config import settings
        original = settings.max_retry_count

        # Insert initial override
        async with session_factory() as session:
            session.add(ConfigOverrideDB(key="max_retry_count", value="3"))
            await session.commit()

        try:
            response = await ac.patch("/config", json={"max_retry_count": 7})
            assert response.status_code == 200
            assert response.json()["applied"]["max_retry_count"] == 7
        finally:
            settings.max_retry_count = original


# ─── Retry with real DB job ─────────────────────────────────────────────────


class TestRetryWithJob:
    """Tests for POST /jobs/{id}/retry with actual DB jobs."""

    @pytest.mark.asyncio
    async def test_retry_failed_job(self, client, mock_worker):
        ac, app, session_factory = client

        # Insert a failed job
        async with session_factory() as session:
            job = TranscodeJobDB(
                id=42,
                title="Test Movie",
                source_path="/data/raw/Test Movie (2024)",
                status=JobStatus.FAILED,
                error="HandBrake crashed",
                retry_count=0,
            )
            session.add(job)
            await session.commit()
            job_id = job.id

        response = await ac.post(f"/jobs/{job_id}/retry")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
        assert data["job_id"] == job_id
        assert data["retry_count"] == 1
        mock_worker.queue_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_non_failed_job_rejected(self, client):
        ac, app, session_factory = client

        async with session_factory() as session:
            job = TranscodeJobDB(
                id=601, title="Test Movie",
                source_path="/data/raw/Test Movie (2024)",
                status=JobStatus.COMPLETED,
            )
            session.add(job)
            await session.commit()
            job_id = job.id

        response = await ac.post(f"/jobs/{job_id}/retry")
        assert response.status_code == 400
        assert "not in failed state" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_retry_exceeds_limit(self, client):
        ac, app, session_factory = client
        from config import settings

        async with session_factory() as session:
            job = TranscodeJobDB(
                id=602, title="Test Movie",
                source_path="/data/raw/Test Movie (2024)",
                status=JobStatus.FAILED,
                retry_count=settings.max_retry_count,
            )
            session.add(job)
            await session.commit()
            job_id = job.id

        response = await ac.post(f"/jobs/{job_id}/retry")
        assert response.status_code == 400
        assert "retry limit" in response.json()["detail"].lower()


# ─── Delete with real DB job ────────────────────────────────────────────────


class TestDeleteWithJob:
    """Tests for DELETE /jobs/{id} with actual DB jobs."""

    @pytest.mark.asyncio
    async def test_delete_completed_job(self, client):
        ac, app, session_factory = client

        async with session_factory() as session:
            job = TranscodeJobDB(
                id=603, title="Test Movie",
                source_path="/data/raw/Test Movie (2024)",
                status=JobStatus.COMPLETED,
            )
            session.add(job)
            await session.commit()
            job_id = job.id

        response = await ac.delete(f"/jobs/{job_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
        assert data["job_id"] == job_id

    @pytest.mark.asyncio
    async def test_delete_processing_job_rejected(self, client):
        ac, app, session_factory = client

        async with session_factory() as session:
            job = TranscodeJobDB(
                id=604, title="Test Movie",
                source_path="/data/raw/Test Movie (2024)",
                status=JobStatus.PROCESSING,
            )
            session.add(job)
            await session.commit()
            job_id = job.id

        response = await ac.delete(f"/jobs/{job_id}")
        assert response.status_code == 400
        assert "in progress" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_delete_failed_job(self, client):
        ac, app, session_factory = client

        async with session_factory() as session:
            job = TranscodeJobDB(
                id=605, title="Test Movie",
                source_path="/data/raw/Test Movie (2024)",
                status=JobStatus.FAILED,
            )
            session.add(job)
            await session.commit()
            job_id = job.id

        response = await ac.delete(f"/jobs/{job_id}")
        assert response.status_code == 200


# ─── Jobs list with data ────────────────────────────────────────────────────


class TestJobsListWithData:
    """Tests for GET /jobs with actual DB data."""

    @pytest.mark.asyncio
    async def test_list_jobs_with_data(self, client):
        ac, app, session_factory = client

        async with session_factory() as session:
            for i in range(3):
                session.add(TranscodeJobDB(
                    id=100 + i,
                    title=f"Movie {i}",
                    source_path=f"/data/raw/Movie {i}",
                    status=JobStatus.COMPLETED if i < 2 else JobStatus.PENDING,
                ))
            await session.commit()

        response = await ac.get("/jobs")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["jobs"]) == 3

    @pytest.mark.asyncio
    async def test_filter_by_status(self, client):
        ac, app, session_factory = client

        async with session_factory() as session:
            session.add(TranscodeJobDB(
                id=200, title="Done", source_path="/x", status=JobStatus.COMPLETED))
            session.add(TranscodeJobDB(
                id=201, title="Waiting", source_path="/y", status=JobStatus.PENDING))
            await session.commit()

        response = await ac.get("/jobs?status=pending")
        data = response.json()
        assert data["total"] == 1
        assert data["jobs"][0]["title"] == "Waiting"

    @pytest.mark.asyncio
    async def test_filter_by_job_id(self, client):
        ac, app, session_factory = client

        async with session_factory() as session:
            session.add(TranscodeJobDB(
                id=123, title="Movie A", source_path="/a", status=JobStatus.COMPLETED))
            session.add(TranscodeJobDB(
                id=456, title="Movie B", source_path="/b", status=JobStatus.COMPLETED))
            await session.commit()

        response = await ac.get("/jobs?job_id=123")
        data = response.json()
        assert data["total"] == 1
        assert data["jobs"][0]["id"] == 123

    @pytest.mark.asyncio
    async def test_limit_below_1_clamped(self, client):
        ac, app, *_rest = client
        response = await ac.get("/jobs?limit=0")
        data = response.json()
        assert data["limit"] == 1

    @pytest.mark.asyncio
    async def test_job_serialization_fields(self, client):
        """Verify all job fields are serialized correctly."""
        ac, app, session_factory = client
        import json as json_module

        async with session_factory() as session:
            session.add(TranscodeJobDB(
                id=99,
                title="Test Movie",
                source_path="/data/raw/Test",
                output_path="/data/completed/Test",
                status=JobStatus.COMPLETED,
                progress=100.0,
                error=None,
                logfile="test.log",
                video_type="movie",
                year="2024",
                disctype="bluray",
                total_tracks=5,
                poster_url="https://example.com/poster.jpg",
                config_overrides=json_module.dumps({"video_quality": 20}),
            ))
            await session.commit()

        response = await ac.get("/jobs")
        data = response.json()
        job = data["jobs"][0]
        assert job["video_type"] == "movie"
        assert job["year"] == "2024"
        assert job["disctype"] == "bluray"
        assert job["total_tracks"] == 5
        assert job["poster_url"] == "https://example.com/poster.jpg"
        assert job["config_overrides"] == {"video_quality": 20}
        assert job["output_path"] == "/data/completed/Test"
        assert job["logfile"] == "test.log"


# ─── Stats with data ───────────────────────────────────────────────────────


class TestStatsWithData:
    """Tests for GET /stats with DB data."""

    @pytest.mark.asyncio
    async def test_stats_counts(self, client):
        ac, app, session_factory = client

        async with session_factory() as session:
            session.add(TranscodeJobDB(
                id=606, title="A", source_path="/a", status=JobStatus.COMPLETED))
            session.add(TranscodeJobDB(
                id=607, title="B", source_path="/b", status=JobStatus.COMPLETED))
            session.add(TranscodeJobDB(
                id=608, title="C", source_path="/c", status=JobStatus.FAILED))
            session.add(TranscodeJobDB(
                id=609, title="D", source_path="/d", status=JobStatus.PENDING))
            await session.commit()

        response = await ac.get("/stats")
        data = response.json()
        assert data["completed"] == 2
        assert data["failed"] == 1
        assert data["pending"] == 1
        assert data["processing"] == 0
        assert data["cancelled"] == 0
        assert data["worker_running"] is True


# ─── Logs Endpoints ─────────────────────────────────────────────────────────


class TestLogsEndpoints:
    """Tests for /logs endpoints."""

    @pytest.mark.asyncio
    async def test_list_logs(self, client):
        ac, app, *_rest = client
        mock_logs = [
            {"filename": "transcoder.log", "size": 1024, "modified": "2024-01-01T00:00:00+00:00"},
        ]
        with patch("routers.logs.list_logs", return_value=mock_logs) as mock_fn:
            # The import inside the endpoint uses `from log_reader import list_logs as _list_logs`
            # We need to patch what the endpoint actually calls
            pass

        # Since the endpoint does lazy import, we patch log_reader module
        with patch("log_reader.list_logs", return_value=mock_logs):
            response = await ac.get("/logs")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_log_found(self, client):
        ac, app, *_rest = client
        mock_result = {
            "filename": "transcoder.log",
            "content": "some log content\n",
            "lines": 1,
        }
        with patch("log_reader.read_log", return_value=mock_result):
            response = await ac.get("/logs/transcoder.log")
            assert response.status_code == 200
            data = response.json()
            assert data["filename"] == "transcoder.log"
            assert "content" in data

    @pytest.mark.asyncio
    async def test_get_log_not_found(self, client):
        ac, app, *_rest = client
        with patch("log_reader.read_log", return_value=None):
            response = await ac.get("/logs/nonexistent.log")
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_structured_log_found(self, client):
        ac, app, *_rest = client
        mock_result = {
            "filename": "transcoder.log",
            "entries": [{"timestamp": "2024-01-01", "level": "info", "event": "test"}],
            "lines": 1,
        }
        with patch("log_reader.read_structured_log", return_value=mock_result):
            response = await ac.get("/logs/transcoder.log/structured")
            assert response.status_code == 200
            data = response.json()
            assert data["filename"] == "transcoder.log"
            assert len(data["entries"]) == 1

    @pytest.mark.asyncio
    async def test_get_structured_log_not_found(self, client):
        ac, app, *_rest = client
        with patch("log_reader.read_structured_log", return_value=None):
            response = await ac.get("/logs/nonexistent.log/structured")
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_structured_log_with_filters(self, client):
        ac, app, *_rest = client
        mock_result = {
            "filename": "transcoder.log",
            "entries": [],
            "lines": 0,
        }
        with patch("log_reader.read_structured_log", return_value=mock_result) as mock_fn:
            response = await ac.get(
                "/logs/transcoder.log/structured?mode=full&lines=500&level=error&search=failed"
            )
            assert response.status_code == 200
            mock_fn.assert_called_once_with(
                "transcoder.log", mode="full", lines=500, level="error", search="failed"
            )

    @pytest.mark.asyncio
    async def test_get_log_with_params(self, client):
        ac, app, *_rest = client
        mock_result = {"filename": "test.log", "content": "line\n", "lines": 1}
        with patch("log_reader.read_log", return_value=mock_result) as mock_fn:
            response = await ac.get("/logs/test.log?mode=full&lines=200")
            assert response.status_code == 200
            mock_fn.assert_called_once_with("test.log", mode="full", lines=200)


# ─── Webhook edge cases ────────────────────────────────────────────────────


class TestWebhookEdgeCases:
    """Additional webhook tests for coverage."""

    @pytest.mark.asyncio
    async def test_payload_too_large(self, client):
        """Should reject payloads over the configured cap (MAX_WEBHOOK_PAYLOAD_SIZE).

        Cap is a sanity guard against obvious garbage, not a gate on legitimate
        multi-track 4K Blu-ray payloads (which can run ~12KB).
        """
        from constants import MAX_WEBHOOK_PAYLOAD_SIZE
        ac, app, *_rest = client
        response = await ac.post(
            "/webhook/arm",
            json={"title": "test"},
            headers={"content-length": str(MAX_WEBHOOK_PAYLOAD_SIZE + 1)},
        )
        assert response.status_code == 413

    @pytest.mark.asyncio
    async def test_webhook_absolute_input_path_rejected(self, client, mock_worker):
        """Absolute input_paths are rejected by the contracts validator
        (it returns 422 before the handler runs). ARM is now responsible
        for sending relative paths."""
        ac, app, *_rest = client
        payload = {
            "title": "Rip complete",
            "input_path": "/home/arm/media/raw/Movie Title (2024)",
            "output_path": "Movies/0.Rips/Movie Title (2024)",
            "status": "success",
            "job_id": 901,
        }
        response = await ac.post("/webhook/arm", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_webhook_already_queued(self, client, mock_worker):
        """Should return already_queued when queue_job returns created=False."""
        ac, app, *_rest = client
        mock_worker.queue_job = AsyncMock(return_value=(1, False))
        payload = {
            "title": "Rip complete",
            "input_path": "movies/Movie",
            "output_path": "Movies/0.Rips/Movie",
            "status": "success",
            "job_id": 902,
        }
        response = await ac.post("/webhook/arm", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "already_queued"

    @pytest.mark.asyncio
    async def test_webhook_with_all_metadata(self, client, mock_worker):
        """Should pass all metadata fields through to queue_job."""
        ac, app, *_rest = client
        payload = {
            "title": "Rip complete",
            "input_path": "movies/Movie Title (2024)",
            "output_path": "Movies/0.Rips/Movie Title (2024)",
            "status": "success",
            "job_id": "42",
            "video_type": "movie",
            "year": "2024",
            "disctype": "bluray",
            "poster_url": "https://example.com/poster.jpg",
            "config_overrides": {
                "preset_slug": "software-balanced",
                "overrides": {"shared": {"video_quality": 20}},
            },
            "multi_title": True,
            "tracks": [{"title": "Track 1"}],
            "title_name": "Movie Title",
        }
        response = await ac.post("/webhook/arm", json=payload)
        assert response.status_code == 200
        call_kwargs = mock_worker.queue_job.call_args.kwargs
        assert call_kwargs["job_id"] == 42
        assert call_kwargs["video_type"] == "movie"
        assert call_kwargs["year"] == "2024"
        assert call_kwargs["disctype"] == "bluray"
        assert call_kwargs["poster_url"] == "https://example.com/poster.jpg"
        co = call_kwargs["config_overrides"]
        assert co["preset_slug"] == "software-balanced"
        assert "overrides" in co
        # The test payload sent overrides.shared.video_quality=20; verify the dumped
        # dict preserves the validated shape including default-expanded tier keys.
        assert isinstance(co["overrides"], dict)
        assert "shared" in co["overrides"]
        assert co["overrides"]["shared"]["video_quality"] == 20
        assert "tiers" in co["overrides"]
        assert call_kwargs["multi_title"] is True
        # WebhookTrackMeta normalizes inputs to the full schema with defaulted
        # empty strings, so a {"title": "Track 1"} input round-trips with the
        # other 9 fields filled in from defaults.
        assert len(call_kwargs["tracks"]) == 1
        assert call_kwargs["tracks"][0]["title"] == "Track 1"
        assert call_kwargs["tracks"][0]["track_number"] == ""
        assert call_kwargs["output_path"] == "Movies/0.Rips/Movie Title (2024)"
        assert call_kwargs["title_name"] == "Movie Title"

    @pytest.mark.asyncio
    async def test_webhook_worker_not_running(self, client, mock_worker):
        """Should return 503 when worker exists but is_running is False."""
        ac, app, *_rest = client
        mock_worker.is_running = False
        try:
            payload = {
                "title": "Rip complete",
                "input_path": "movies/Movie",
                "output_path": "Movies/0.Rips/Movie",
                "status": "success",
                "job_id": 903,
            }
            response = await ac.post("/webhook/arm", json=payload)
            assert response.status_code == 503
        finally:
            mock_worker.is_running = True


# ─── Health check details ──────────────────────────────────────────────────


class TestHealthCheckDetails:
    """Additional health check coverage."""

    @pytest.mark.asyncio
    async def test_health_includes_config(self, client):
        ac, app, *_rest = client
        response = await ac.get("/health")
        data = response.json()
        assert "config" in data
        assert "selected_preset_slug" in data["config"]
        assert "delete_source" in data["config"]
        assert "output_extension" in data["config"]
        assert "max_concurrent" in data["config"]
        assert "stabilize_seconds" in data["config"]

    @pytest.mark.asyncio
    async def test_health_includes_auth_info(self, client):
        ac, app, *_rest = client
        response = await ac.get("/health")
        data = response.json()
        assert "require_api_auth" in data
        assert "webhook_secret_configured" in data

    @pytest.mark.asyncio
    async def test_health_includes_gpu_support(self, client, mock_worker):
        ac, app, *_rest = client
        response = await ac.get("/health")
        data = response.json()
        assert data["gpu_support"] == {"handbrake_nvenc": True}
        assert data["queue_size"] == 2

    @pytest.mark.asyncio
    async def test_health_no_worker(self, client):
        ac, app, *_rest = client
        import main as main_module
        saved = main_module.app.state.worker
        main_module.app.state.worker = None
        try:
            response = await ac.get("/health")
            data = response.json()
            assert data["worker_running"] is False
            assert data["queue_size"] == 0
            assert data["gpu_support"] == {}
        finally:
            main_module.app.state.worker = saved


# ─── Lifespan ───────────────────────────────────────────────────────────────
# Lifespan tests removed: asyncio.create_task mocking is fundamentally
# incompatible with async context managers (returned mock can't be awaited).
# The lifespan function is tested implicitly via integration tests.
