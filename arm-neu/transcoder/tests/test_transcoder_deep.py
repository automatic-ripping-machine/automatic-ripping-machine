"""
Deep coverage tests for transcoder.py — queue_job paths, process_job flow,
worker run loop, audio passthrough, multi-title routing.
"""

import asyncio
import json
import shutil
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock, PropertyMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from models import TranscodeJob, TranscodeJobDB, JobStatus, Base


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


@pytest_asyncio.fixture
async def worker_with_db(tmp_path):
    """Create a TranscodeWorker with a real test DB."""
    from transcoder import TranscodeWorker

    db_path = str(tmp_path / "test_worker.db")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    @asynccontextmanager
    async def test_get_db():
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    import database as db_module
    with patch.object(db_module, "get_db", test_get_db), \
         patch("transcoder.get_db", test_get_db), \
         patch("main.active_scheme", _mock_scheme_software()):
        worker = TranscodeWorker(gpu_support=_gpu_support_none())
        yield worker, session_factory

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ── queue_job paths ──────────────────────────────────────────────────────────

class TestQueueJobPaths:
    @pytest.mark.asyncio
    async def test_queue_job_creates_new_job(self, worker_with_db):
        """Cover queue_job new job creation path."""
        worker, session_factory = worker_with_db
        job_id, created = await worker.queue_job(
            job_id=1, source_path="/test/movie", title="Test Movie"
        )
        assert created is True
        assert job_id == 1

    @pytest.mark.asyncio
    async def test_queue_job_dedup_returns_existing(self, worker_with_db):
        """Cover queue_job: duplicate detection by ID."""
        worker, session_factory = worker_with_db

        # Queue first job
        job_id1, created1 = await worker.queue_job(
            job_id=1, source_path="/test/movie", title="Movie"
        )
        assert created1 is True

        # Queue same ID — should dedup (active job)
        job_id2, created2 = await worker.queue_job(
            job_id=1, source_path="/test/movie", title="Movie Again"
        )
        assert created2 is False
        assert job_id2 == job_id1

    @pytest.mark.asyncio
    async def test_queue_job_requeue_failed(self, worker_with_db):
        """Cover queue_job: re-queue a failed job by same ID."""
        worker, session_factory = worker_with_db

        # Create a failed job in DB
        async with session_factory() as session:
            job_db = TranscodeJobDB(
                id=50, title="Failed Job", source_path="/test/fail",
                status=JobStatus.FAILED
            )
            session.add(job_db)
            await session.commit()

        job_id, created = await worker.queue_job(
            job_id=50, source_path="/test/fail", title="Failed Job"
        )
        assert created is True
        assert job_id == 50

    @pytest.mark.asyncio
    async def test_queue_job_with_overrides_and_tracks(self, worker_with_db):
        """Cover queue_job with config_overrides and tracks metadata."""
        worker, session_factory = worker_with_db

        overrides = {"video_encoder": "hevc_nvenc", "video_quality": 18}
        tracks = [{"track_number": "1", "title": "Episode 1"}]

        job_id, created = await worker.queue_job(
            job_id=3, source_path="/test/series", title="Series",
            config_overrides=overrides,
            multi_title=True, tracks=tracks,
            output_path="TV/0.Rips/Series/Season 1", title_name="S01E01",
        )
        assert created is True

        # Verify data persisted
        async with session_factory() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(TranscodeJobDB).where(TranscodeJobDB.id == job_id)
            )
            job_db = result.scalar_one()
            assert job_db.config_overrides is not None
            assert job_db.multi_title == 1
            assert job_db.track_metadata is not None
            assert job_db.output_path == "TV/0.Rips/Series/Season 1"


# ── Worker run loop ──────────────────────────────────────────────────────────

class TestWorkerRunLoop:
    @pytest.mark.asyncio
    async def test_run_loop_timeout_continues(self, worker_with_db):
        """Cover run() lines 322-323: TimeoutError continues loop."""
        worker, _ = worker_with_db

        async def shutdown_after_loop():
            # Give the loop time to hit one timeout cycle
            await asyncio.sleep(6.0)
            worker.shutdown()

        with patch.object(worker, "_load_pending_jobs", new_callable=AsyncMock):
            shutdown_task = asyncio.create_task(shutdown_after_loop())
            await asyncio.wait_for(worker.run(), timeout=15.0)
            shutdown_task.cancel()

        assert not worker.is_running

    @pytest.mark.asyncio
    async def test_run_loop_handles_process_error(self, worker_with_db):
        """Cover run() lines 330-332: exception in process_job."""
        worker, _ = worker_with_db

        job = TranscodeJob(id=999, title="Crash Job", source_path="/fake")

        async def shutdown_after_error():
            await asyncio.sleep(0.5)
            worker.shutdown()

        with patch.object(worker, "_load_pending_jobs", new_callable=AsyncMock), \
             patch.object(worker, "_process_job", side_effect=RuntimeError("boom")), \
             patch("transcoder.asyncio.sleep", new_callable=AsyncMock):
            await worker._queue.put(job)
            shutdown_task = asyncio.create_task(shutdown_after_error())
            await asyncio.wait_for(worker.run(), timeout=10.0)
            shutdown_task.cancel()


# ── _load_job_metadata ───────────────────────────────────────────────────────

class TestLoadJobMetadata:
    @pytest.mark.asyncio
    async def test_load_metadata_with_overrides(self, worker_with_db):
        """Cover _load_job_metadata: config_overrides and output_path
        round-trip via the DB."""
        worker, session_factory = worker_with_db

        overrides = {"video_encoder": "hevc_nvenc"}
        async with session_factory() as session:
            job_db = TranscodeJobDB(
                id=60, title="Test", source_path="/test",
                status=JobStatus.PENDING,
                config_overrides=json.dumps(overrides),
                output_path="Movies/0.Rips/Test (2024)",
                title_name="Test (2024)",
                video_type="movie", year="2024",
            )
            session.add(job_db)
            await session.commit()
            await session.refresh(job_db)
            job_id = job_db.id

        result = await worker._load_job_metadata(job_id)
        loaded_overrides, video_type, year, output_path, title_name = result
        assert loaded_overrides == overrides
        assert video_type == "movie"
        assert year == "2024"
        assert output_path == "Movies/0.Rips/Test (2024)"
        assert title_name == "Test (2024)"

    @pytest.mark.asyncio
    async def test_load_metadata_invalid_json(self, worker_with_db):
        """Cover _load_job_metadata line 408: invalid JSON in overrides."""
        worker, session_factory = worker_with_db

        async with session_factory() as session:
            job_db = TranscodeJobDB(
                id=61, title="Test", source_path="/test",
                status=JobStatus.PENDING,
                config_overrides="not valid json{{{",
            )
            session.add(job_db)
            await session.commit()
            await session.refresh(job_db)
            job_id = job_db.id

        result = await worker._load_job_metadata(job_id)
        overrides, _, _, _, _ = result
        assert overrides is None  # Invalid JSON falls back to None


# ── _setup_job_logging ───────────────────────────────────────────────────────

class TestSetupJobLogging:
    def test_setup_job_logging_exception(self, worker_with_db):
        """Cover _setup_job_logging lines 380-382: exception returns None."""
        worker, _ = worker_with_db

        with patch("transcoder.settings") as mock_settings:
            mock_settings.log_path = "/nonexistent/impossible/path"
            result = worker._setup_job_logging(999, "test.log")
            assert result is None


# ── _resolve_and_stabilize ───────────────────────────────────────────────────

class TestResolveAndStabilize:
    @pytest.mark.asyncio
    async def test_resolve_just_waits_for_stable(self, worker_with_db):
        """_resolve_and_stabilize is now a thin wrapper around
        _wait_for_stable (ARM sends an explicit input_path). The path
        on the job is never mutated."""
        worker, _ = worker_with_db

        job = TranscodeJob(id=1, title="Test", source_path="/some/path")

        with patch.object(worker, "_wait_for_stable", new_callable=AsyncMock) as mock_wait:
            await worker._resolve_and_stabilize(job)
            mock_wait.assert_called_once_with("/some/path")
            assert job.source_path == "/some/path"


# ── _discover_or_passthrough ─────────────────────────────────────────────────

class TestDiscoverOrPassthrough:
    @pytest.mark.asyncio
    async def test_discover_audio_passthrough(self, worker_with_db):
        """Cover _discover_or_passthrough: audio files trigger passthrough."""
        worker, _ = worker_with_db

        job = TranscodeJob(id=1, title="Audio CD", source_path="/test/audio")

        with patch.object(worker, "_discover_source_files", return_value=[]), \
             patch.object(worker, "_discover_audio_files", return_value=[Path("/test/audio/track01.flac")]), \
             patch.object(worker, "_passthrough_audio", new_callable=AsyncMock) as mock_passthrough:
            result = await worker._discover_or_passthrough(job)
            assert result == []
            mock_passthrough.assert_called_once()

    @pytest.mark.asyncio
    async def test_discover_no_files_raises(self, worker_with_db):
        """Cover _discover_or_passthrough: no video or audio raises."""
        worker, _ = worker_with_db

        job = TranscodeJob(id=1, title="Empty", source_path="/test/empty")

        with patch.object(worker, "_discover_source_files", return_value=[]), \
             patch.object(worker, "_discover_audio_files", return_value=[]):
            with pytest.raises(ValueError, match="No video or audio"):
                await worker._discover_or_passthrough(job)


# ── _transcode_file_ffmpeg ───────────────────────────────────────────────────

class _AsyncLineIterator:
    """Helper to mock async stdout line iteration.

    Supports both the legacy `async for line in stdout` interface and the
    new chunk-based `await stdout.read(n)` interface used by
    `_stream_progress_lines`.
    """
    def __init__(self, lines):
        self._lines = iter(lines)
        self._buffer = b"".join(lines) if lines else b""

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._lines)
        except StopIteration:
            raise StopAsyncIteration

    async def read(self, n: int = -1) -> bytes:
        if not self._buffer:
            return b""
        if n < 0 or n >= len(self._buffer):
            chunk, self._buffer = self._buffer, b""
        else:
            chunk, self._buffer = self._buffer[:n], self._buffer[n:]
        return chunk


def _hb_json_progress(fraction: float, *, rate: float = 0.0,
                      rate_avg: float = 0.0) -> bytes:
    """Build a HandBrake ``--json`` ``Progress:`` block as stdout bytes.

    Mirrors the labelled multi-line JSON HandBrakeCLI emits with --json.
    ``fraction`` is the 0..1 per-file progress; ``rate``/``rate_avg`` are
    the instantaneous/average fps. Used to drive the JSON progress parser
    through ``_transcode_file_handbrake`` in tests."""
    block = {
        "Progress": {
            "Progress": fraction,
            "Rate": rate,
            "RateAvg": rate_avg,
            "ETASeconds": 30,
            "Pass": 1,
        },
        "State": "WORKING",
    }
    return ("Progress:\n" + json.dumps(block, indent=4) + "\n").encode()


class TestTranscodeFileFFmpeg:
    @pytest.mark.asyncio
    async def test_ffmpeg_transcode_success(self, worker_with_db, tmp_path):
        """Cover _transcode_file_ffmpeg lines 1258-1292: successful transcode."""
        worker, _ = worker_with_db

        source = tmp_path / "input.mkv"
        source.write_bytes(b"\x00" * 100)
        output = tmp_path / "output.mkv"

        mock_proc = AsyncMock()
        mock_proc.stdout = _AsyncLineIterator([
            b"frame=100 fps=30 time=00:01:00.00 bitrate=5000kbits/s\n",
            b"frame=200 fps=30 time=00:02:00.00 bitrate=5000kbits/s\n",
        ])
        mock_proc.wait = AsyncMock(return_value=0)
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc), \
             patch.object(worker, "_get_video_resolution", new_callable=AsyncMock, return_value=(1920, 1080)), \
             patch.object(worker, "_get_video_duration", new_callable=AsyncMock, return_value=3600.0), \
             patch.object(worker, "_build_ffmpeg_command", return_value=["ffmpeg", "-i", str(source), str(output)]), \
             patch.object(worker, "_update_progress", new_callable=AsyncMock):
            output.write_bytes(b"\x00" * 50)
            await worker._transcode_file_ffmpeg(source, output, job_id=1)

    @pytest.mark.asyncio
    async def test_ffmpeg_transcode_failure(self, worker_with_db, tmp_path):
        """Cover _transcode_file_ffmpeg: non-zero exit code."""
        worker, _ = worker_with_db

        source = tmp_path / "input.mkv"
        source.write_bytes(b"\x00" * 100)
        output = tmp_path / "output.mkv"

        mock_proc = AsyncMock()
        mock_proc.stdout = _AsyncLineIterator([])
        mock_proc.wait = AsyncMock(return_value=1)
        mock_proc.returncode = 1

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc), \
             patch.object(worker, "_get_video_resolution", new_callable=AsyncMock, return_value=(1920, 1080)), \
             patch.object(worker, "_get_video_duration", new_callable=AsyncMock, return_value=3600.0), \
             patch.object(worker, "_build_ffmpeg_command", return_value=["ffmpeg"]):
            with pytest.raises(RuntimeError, match="FFmpeg failed"):
                await worker._transcode_file_ffmpeg(source, output, job_id=1)

    @pytest.mark.asyncio
    async def test_ffmpeg_no_output_file(self, worker_with_db, tmp_path):
        """Cover _transcode_file_ffmpeg: output not created."""
        worker, _ = worker_with_db

        source = tmp_path / "input.mkv"
        source.write_bytes(b"\x00" * 100)
        output = tmp_path / "output.mkv"

        mock_proc = AsyncMock()
        mock_proc.stdout = _AsyncLineIterator([])
        mock_proc.wait = AsyncMock(return_value=0)
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc), \
             patch.object(worker, "_get_video_resolution", new_callable=AsyncMock, return_value=(1920, 1080)), \
             patch.object(worker, "_get_video_duration", new_callable=AsyncMock, return_value=3600.0), \
             patch.object(worker, "_build_ffmpeg_command", return_value=["ffmpeg"]):
            with pytest.raises(RuntimeError, match="Output file was not created"):
                await worker._transcode_file_ffmpeg(source, output, job_id=1)

    @pytest.mark.asyncio
    async def test_ffmpeg_progress_passes_fps(self, worker_with_db, tmp_path):
        """FFmpeg stats lines propagate fps into _update_progress."""
        worker, _ = worker_with_db

        source = tmp_path / "input.mkv"
        source.write_bytes(b"\x00" * 100)
        output = tmp_path / "output.mkv"

        mock_proc = AsyncMock()
        mock_proc.stdout = _AsyncLineIterator([
            b"frame=100 fps=42.5 time=00:01:00.00 bitrate=5000kbits/s\n",
        ])
        mock_proc.wait = AsyncMock(return_value=0)
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc), \
             patch.object(worker, "_get_video_resolution", new_callable=AsyncMock, return_value=(1920, 1080)), \
             patch.object(worker, "_get_video_duration", new_callable=AsyncMock, return_value=3600.0), \
             patch.object(worker, "_build_ffmpeg_command", return_value=["ffmpeg"]), \
             patch.object(worker, "_update_progress", new_callable=AsyncMock) as mock_progress:
            output.write_bytes(b"\x00" * 50)
            await worker._transcode_file_ffmpeg(source, output, job_id=1)
            mock_progress.assert_called_once()
            kwargs = mock_progress.call_args.kwargs
            assert kwargs.get("fps") == 42.5

    @pytest.mark.asyncio
    async def test_ffmpeg_no_duration(self, worker_with_db, tmp_path):
        """Cover _transcode_file_ffmpeg: no duration skips progress parsing."""
        worker, _ = worker_with_db

        source = tmp_path / "input.mkv"
        source.write_bytes(b"\x00" * 100)
        output = tmp_path / "output.mkv"

        mock_proc = AsyncMock()
        mock_proc.stdout = _AsyncLineIterator([
            b"frame=100 fps=30 time=00:01:00.00\n",
        ])
        mock_proc.wait = AsyncMock(return_value=0)
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc), \
             patch.object(worker, "_get_video_resolution", new_callable=AsyncMock, return_value=(1920, 1080)), \
             patch.object(worker, "_get_video_duration", new_callable=AsyncMock, return_value=None), \
             patch.object(worker, "_build_ffmpeg_command", return_value=["ffmpeg"]), \
             patch.object(worker, "_update_progress", new_callable=AsyncMock) as mock_progress:
            output.write_bytes(b"\x00" * 50)
            await worker._transcode_file_ffmpeg(source, output, job_id=1)
            # Progress should NOT be updated since duration is None
            mock_progress.assert_not_called()

    @pytest.mark.asyncio
    async def test_ffmpeg_progress_without_fps_in_line(self, worker_with_db, tmp_path):
        """A progress line without fps= still updates progress; fps kwarg is None."""
        worker, _ = worker_with_db

        source = tmp_path / "input.mkv"
        source.write_bytes(b"\x00" * 100)
        output = tmp_path / "output.mkv"

        mock_proc = AsyncMock()
        # No "fps=" token in the line - simulates the rare ffmpeg config
        # where the stats line is suppressed but a time= token still appears.
        mock_proc.stdout = _AsyncLineIterator([
            b"time=00:01:00.00 bitrate=5000kbits/s\n",
        ])
        mock_proc.wait = AsyncMock(return_value=0)
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc), \
             patch.object(worker, "_get_video_resolution", new_callable=AsyncMock, return_value=(1920, 1080)), \
             patch.object(worker, "_get_video_duration", new_callable=AsyncMock, return_value=3600.0), \
             patch.object(worker, "_build_ffmpeg_command", return_value=["ffmpeg"]), \
             patch.object(worker, "_update_progress", new_callable=AsyncMock) as mock_progress:
            output.write_bytes(b"\x00" * 50)
            await worker._transcode_file_ffmpeg(source, output, job_id=1)
            mock_progress.assert_called_once()
            assert mock_progress.call_args.kwargs.get("fps") is None


class TestTranscodeFileHandBrake:
    @pytest.mark.asyncio
    async def test_handbrake_progress_passes_fps(self, worker_with_db, tmp_path):
        """HandBrake progress lines propagate the instantaneous fps reading."""
        worker, _ = worker_with_db

        source = tmp_path / "input.mkv"
        source.write_bytes(b"\x00" * 100)
        output = tmp_path / "output.mkv"

        mock_proc = AsyncMock()
        mock_proc.stdout = _AsyncLineIterator([
            _hb_json_progress(0.1234, rate=45.67),
        ])
        mock_proc.wait = AsyncMock(return_value=0)
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc), \
             patch.object(worker, "_update_progress", new_callable=AsyncMock) as mock_progress:
            output.write_bytes(b"\x00" * 50)
            await worker._transcode_file_handbrake(source, output, job_id=1)
            mock_progress.assert_called_once()
            args = mock_progress.call_args
            assert args.args[1] == pytest.approx(12.34)
            assert args.kwargs.get("fps") == pytest.approx(45.67)

    @pytest.mark.asyncio
    async def test_handbrake_progress_without_fps(self, worker_with_db, tmp_path):
        """HandBrake line with a percentage but no fps token still updates progress."""
        worker, _ = worker_with_db

        source = tmp_path / "input.mkv"
        source.write_bytes(b"\x00" * 100)
        output = tmp_path / "output.mkv"

        mock_proc = AsyncMock()
        mock_proc.stdout = _AsyncLineIterator([
            _hb_json_progress(0.075, rate=0.0, rate_avg=0.0),  # No fps reading
        ])
        mock_proc.wait = AsyncMock(return_value=0)
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc), \
             patch.object(worker, "_update_progress", new_callable=AsyncMock) as mock_progress:
            output.write_bytes(b"\x00" * 50)
            await worker._transcode_file_handbrake(source, output, job_id=1)
            mock_progress.assert_called_once()
            assert mock_progress.call_args.kwargs.get("fps") is None

    @pytest.mark.asyncio
    async def test_handbrake_failure(self, worker_with_db, tmp_path):
        """Non-zero HandBrake exit raises RuntimeError."""
        worker, _ = worker_with_db

        source = tmp_path / "input.mkv"
        source.write_bytes(b"\x00" * 100)
        output = tmp_path / "output.mkv"

        mock_proc = AsyncMock()
        mock_proc.stdout = _AsyncLineIterator([])
        mock_proc.wait = AsyncMock(return_value=1)
        mock_proc.returncode = 1

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            with pytest.raises(RuntimeError, match="HandBrake failed"):
                await worker._transcode_file_handbrake(source, output, job_id=1)

    @pytest.mark.asyncio
    async def test_handbrake_no_output_file(self, worker_with_db, tmp_path):
        """HandBrake exit 0 but no output file raises RuntimeError."""
        worker, _ = worker_with_db

        source = tmp_path / "input.mkv"
        source.write_bytes(b"\x00" * 100)
        output = tmp_path / "output.mkv"

        mock_proc = AsyncMock()
        mock_proc.stdout = _AsyncLineIterator([])
        mock_proc.wait = AsyncMock(return_value=0)
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            with pytest.raises(RuntimeError, match="Output file was not created"):
                await worker._transcode_file_handbrake(source, output, job_id=1)


class TestUpdateProgressFps:
    @pytest.mark.asyncio
    async def test_update_progress_passes_fps_to_db(self, worker_with_db):
        """When fps is supplied, it lands in the DB write alongside progress."""
        worker, _ = worker_with_db
        with patch.object(worker, "_update_job", new_callable=AsyncMock) as mock_update:
            await worker._update_progress(job_id=42, progress=50.0, fps=24.5)
            mock_update.assert_called_once()
            assert mock_update.call_args.kwargs["progress"] == pytest.approx(50.0)
            assert mock_update.call_args.kwargs["current_fps"] == pytest.approx(24.5)

    @pytest.mark.asyncio
    async def test_update_progress_omits_fps_when_none(self, worker_with_db):
        """fps=None means the kwarg is omitted from the DB write entirely."""
        worker, _ = worker_with_db
        with patch.object(worker, "_update_job", new_callable=AsyncMock) as mock_update:
            await worker._update_progress(job_id=42, progress=50.0, fps=None)
            mock_update.assert_called_once()
            assert "current_fps" not in mock_update.call_args.kwargs
            assert mock_update.call_args.kwargs["progress"] == pytest.approx(50.0)

    @pytest.mark.asyncio
    async def test_update_progress_rate_limited_skips_write(self, worker_with_db):
        """Two updates within the rate-limit window result in only one DB write."""
        worker, _ = worker_with_db
        with patch.object(worker, "_update_job", new_callable=AsyncMock) as mock_update:
            await worker._update_progress(job_id=42, progress=50.0, fps=24.0)
            await worker._update_progress(job_id=42, progress=50.1, fps=24.5)
            # Second call below the delta threshold should not write again
            assert mock_update.call_count == 1


# ── _effective helper ────────────────────────────────────────────────────────

class TestEffectiveHelper:
    def test_effective_returns_override(self, worker_with_db):
        """Cover _effective line 133: override takes precedence."""
        worker, _ = worker_with_db
        result = worker._effective("delete_source", {"delete_source": False})
        assert result is False

    def test_effective_returns_global(self, worker_with_db):
        """Cover _effective line 134: falls back to settings."""
        worker, _ = worker_with_db
        result = worker._effective("delete_source", None)
        from config import settings
        assert result == settings.delete_source

    def test_effective_key_not_in_overrides(self, worker_with_db):
        """Cover _effective: key not in overrides dict."""
        worker, _ = worker_with_db
        result = worker._effective("delete_source", {"output_extension": "mp4"})
        from config import settings
        assert result == settings.delete_source


# ── Preset snapshot: resolve once per job, not per file ─────────────────────
#
# These tests lock in the invariant that _snapshot_preset is called exactly
# once per _process_job invocation, regardless of how many source files the
# job contains. Per-file _resolve_effective_settings still runs (it chooses
# the tier from the file's resolution), but it must receive the cached
# snapshot and skip any DB / global_overrides re-resolution.

class TestPresetSnapshotOncePerJob:
    """_snapshot_preset runs once per job; _resolve_effective_settings is
    called per-file but must use the snapshot (no mid-job DB/settings hits)."""

    @pytest.mark.asyncio
    async def test_snapshot_called_exactly_once_per_job(self, worker_with_db, tmp_path):
        """_snapshot_preset fires once even when the job has many source files."""
        worker, session_factory = worker_with_db

        # 3 source MKVs simulating a multi-title disc
        source_dir = tmp_path / "raw" / "Multi Movie"
        source_dir.mkdir(parents=True)
        for i in range(3):
            (source_dir / f"title_{i:02d}.mkv").write_bytes(b"\x00" * (1000 + i))
        completed_dir = tmp_path / "completed"
        completed_dir.mkdir()

        from transcoder import TranscodeJob
        await worker.queue_job(
            job_id=9001, source_path=str(source_dir), title="Multi Movie",
        )
        job = await worker._queue.get()

        real_snapshot = worker._snapshot_preset
        snapshot_calls = 0

        async def counting_snapshot(overrides):
            nonlocal snapshot_calls
            snapshot_calls += 1
            return await real_snapshot(overrides)

        transcode_mock = AsyncMock()

        async def _passthrough_copy(s, d, **kw):
            """Copy into the work-dir source folder for discovery."""
            from pathlib import Path as _P
            import shutil as _sh
            _sh.copytree(s, d)

        async def _passthrough_move(s, d):
            import os as _os, shutil as _sh
            _os.makedirs(_os.path.dirname(d) or ".", exist_ok=True)
            _sh.move(s, d)

        async def _passthrough_rmtree(p):
            import shutil as _sh
            _sh.rmtree(p, ignore_errors=True)

        with patch.object(worker, "_snapshot_preset", side_effect=counting_snapshot), \
             patch.object(worker, "_wait_for_stable", new_callable=AsyncMock), \
             patch.object(worker, "_transcode_file_handbrake", transcode_mock), \
             patch.object(worker, "_transcode_file_ffmpeg", transcode_mock), \
             patch.object(worker, "_notify_arm_callback", new_callable=AsyncMock), \
             patch("transcoder.async_copy", side_effect=_passthrough_copy), \
             patch("transcoder.async_move_file", side_effect=_passthrough_move), \
             patch("transcoder.async_rmtree", side_effect=_passthrough_rmtree), \
             patch("transcoder.settings") as mock_settings:
            mock_settings.work_path = str(tmp_path / "work")
            mock_settings.raw_path = str(tmp_path / "raw")
            mock_settings.completed_path = str(completed_dir)
            mock_settings.output_extension = "mkv"
            mock_settings.delete_source = False
            mock_settings.stabilize_seconds = 0
            mock_settings.minimum_free_space_gb = 0.0
            mock_settings.log_path = str(tmp_path / "logs")
            mock_settings.arm_callback_url = ""
            mock_settings.selected_preset_slug = ""
            mock_settings.global_overrides = "{}"

            await worker._process_job(job)

        # Core invariant: snapshot resolved exactly once regardless of N files
        assert snapshot_calls == 1, (
            f"_snapshot_preset should run once per job, not per file; "
            f"got {snapshot_calls} calls for 3 source files"
        )
        # And the per-file transcode mock should have been invoked per file
        assert transcode_mock.await_count == 3, (
            f"expected 3 per-file transcode calls, got {transcode_mock.await_count}"
        )

    @pytest.mark.asyncio
    async def test_snapshot_passed_through_to_resolve(self, worker_with_db, tmp_path):
        """Snapshot flows from _transcode_files into _resolve_effective_settings."""
        worker, _ = worker_with_db

        work_output = tmp_path / "output"
        work_output.mkdir()

        src1 = tmp_path / "t01.mkv"
        src2 = tmp_path / "t02.mkv"
        src1.write_bytes(b"\x00" * 100)
        src2.write_bytes(b"\x00" * 100)

        from transcoder import TranscodeJob
        job = TranscodeJob(id=1, title="Movie", source_path=str(tmp_path))

        snapshot = await worker._snapshot_preset(None)

        received_snapshots = []

        async def fake_transcode(source, output, job_id, overrides=None, *, preset_snapshot=None, file_index=0, total_files=1):
            received_snapshots.append(preset_snapshot)

        mock_settings = MagicMock()
        mock_settings.output_extension = "mkv"

        with patch.object(worker, "_update_progress", new_callable=AsyncMock), \
             patch.object(worker, "_transcode_file_ffmpeg", side_effect=fake_transcode), \
             patch.object(worker, "_transcode_file_handbrake", side_effect=fake_transcode), \
             patch("transcoder.settings", mock_settings):
            await worker._transcode_files(
                job, [src1, src2], src1, work_output, "Movie",
                None, multi_title=True, preset_snapshot=snapshot,
            )

        assert len(received_snapshots) == 2
        # Every per-file call must see the SAME snapshot object
        assert all(s is snapshot for s in received_snapshots), (
            "each per-file transcode must receive the exact snapshot from the job"
        )

    @pytest.mark.asyncio
    async def test_mid_job_patch_does_not_leak_into_job(self, worker_with_db, tmp_path):
        """Mid-job PATCH to settings.selected_preset_slug must NOT affect later files.

        This is the race the snapshot eliminates: a user changing /config
        between track 1 and track 2 of the same disc would previously have
        produced tracks with different encoders. The snapshot pins the
        effective preset at job start.
        """
        worker, _ = worker_with_db

        # Build a second preset so we can swap it in mid-job
        from presets import Preset, Scheme, Encoder
        alt_preset = Preset(
            slug="alt_preset", name="Alt", scheme="software",
            shared={"video_encoder": "x264", "audio_encoder": "copy", "subtitle_mode": "all"},
            tiers={
                "dvd": {"handbrake_preset": "Alt 720p", "video_quality": 30},
                "bluray": {"handbrake_preset": "Alt 1080p", "video_quality": 30},
                "uhd": {"handbrake_preset": "Alt 2160p", "video_quality": 30},
            },
        )
        # Build a scheme that has BOTH the original test_sw preset and alt_preset
        scheme_with_both = Scheme(
            slug="software", name="Software (CPU)",
            supported_encoders=[
                Encoder(slug="x265", name="Software x265"),
                Encoder(slug="x264", name="Software x264"),
            ],
            supported_audio_encoders=["copy", "aac"],
            supported_subtitle_modes=["all", "first", "none"],
            built_in_presets=[_mock_scheme_software().default_preset, alt_preset],
        )

        src1 = tmp_path / "t01.mkv"
        src2 = tmp_path / "t02.mkv"
        src1.write_bytes(b"\x00" * 100)
        src2.write_bytes(b"\x00" * 100)
        work_output = tmp_path / "work_output"
        work_output.mkdir()

        from transcoder import TranscodeJob
        job = TranscodeJob(id=1, title="Movie", source_path=str(tmp_path))

        mock_settings = MagicMock()
        mock_settings.output_extension = "mkv"
        # Start with test_sw (x265) selected
        mock_settings.selected_preset_slug = "test_sw"
        mock_settings.global_overrides = "{}"

        # Resolve snapshot with test_sw active
        with patch("main.active_scheme", scheme_with_both), \
             patch("transcoder.settings", mock_settings):
            snapshot = await worker._snapshot_preset(None)
        assert snapshot.preset.slug == "test_sw"

        # Now simulate a mid-job PATCH flipping selected_preset_slug to alt_preset
        mock_settings.selected_preset_slug = "alt_preset"

        # Each per-file transcode runs _resolve_effective_settings with the
        # job-scoped snapshot. Despite settings now pointing at alt_preset,
        # the effective preset MUST remain test_sw.
        seen_encoders = []

        async def capture_transcode(source, output, job_id, overrides=None, *, preset_snapshot=None, file_index=0, total_files=1):
            with patch("main.active_scheme", scheme_with_both), \
                 patch("transcoder.settings", mock_settings):
                effective = await worker._resolve_effective_settings(
                    (1920, 1080), None, snapshot=preset_snapshot,
                )
            seen_encoders.append(effective.get("video_encoder"))

        with patch.object(worker, "_update_progress", new_callable=AsyncMock), \
             patch.object(worker, "_transcode_file_ffmpeg", side_effect=capture_transcode), \
             patch.object(worker, "_transcode_file_handbrake", side_effect=capture_transcode), \
             patch("transcoder.settings", mock_settings):
            await worker._transcode_files(
                job, [src1, src2], src1, work_output, "Movie",
                None, multi_title=True, preset_snapshot=snapshot,
            )

        # Both tracks must have resolved to x265 (the snapshotted preset),
        # not x264 (the mid-job-patched preset)
        assert seen_encoders == ["x265", "x265"], (
            f"mid-job PATCH leaked into later tracks; got {seen_encoders}, "
            f"expected both tracks to use the snapshot (x265)"
        )


# ── TranscodePhase: sub-status surfaced via /jobs ────────────────────────────

class TestTranscodePhase:
    """Phase column on TranscodeJobDB - the UI uses it to render
    'Copying source files' / 'Finalizing' indeterminate sliders during
    periods where no encoder progress is being reported.
    """

    @pytest.mark.asyncio
    async def test_new_job_defaults_to_queued_phase(self, worker_with_db):
        """A freshly queued job has phase='queued'."""
        worker, session_factory = worker_with_db
        await worker.queue_job(job_id=1, source_path="/test/movie", title="M")
        async with session_factory() as session:
            from sqlalchemy import select as _sel
            result = await session.execute(_sel(TranscodeJobDB).where(TranscodeJobDB.id == 1))
            job = result.scalar_one()
        assert job.phase == "queued"

    @pytest.mark.asyncio
    async def test_update_job_persists_phase(self, worker_with_db):
        """_update_job(phase=...) writes the phase column."""
        worker, session_factory = worker_with_db
        await worker.queue_job(job_id=2, source_path="/test/movie", title="M")
        await worker._update_job(2, phase="copying_source")
        async with session_factory() as session:
            from sqlalchemy import select as _sel
            result = await session.execute(_sel(TranscodeJobDB).where(TranscodeJobDB.id == 2))
            job = result.scalar_one()
        assert job.phase == "copying_source"

    @pytest.mark.asyncio
    async def test_requeue_resets_phase_to_queued(self, worker_with_db):
        """Re-queuing a terminal job resets phase to 'queued'."""
        from models import JobStatus as _JobStatus
        worker, session_factory = worker_with_db
        # Seed a completed job with phase=finalizing
        async with session_factory() as session:
            session.add(TranscodeJobDB(
                id=3, title="M", source_path="/test/movie",
                status=_JobStatus.COMPLETED, phase="finalizing",
            ))
            await session.commit()
        # Re-queue
        await worker.queue_job(job_id=3, source_path="/test/movie", title="M")
        async with session_factory() as session:
            from sqlalchemy import select as _sel
            result = await session.execute(_sel(TranscodeJobDB).where(TranscodeJobDB.id == 3))
            job = result.scalar_one()
        assert job.phase == "queued"


class TestMultiFileProgressScaling:
    """File-index-aware progress writes for multi-file jobs.

    HandBrake / FFmpeg emit per-FILE progress (0..100% per file). When a
    job has N source files, the per-file value must be scaled to overall
    job progress before being persisted, otherwise the rate limiter sees
    backward jumps at every file boundary and suppresses all writes after
    file 0 completes. The job appears stuck at 0% (or the file-0 high-water
    mark) for the rest of the encode.
    """

    @pytest.mark.asyncio
    async def test_handbrake_scales_progress_by_file_index(self, worker_with_db, tmp_path):
        """File 0 of 3 at 60% file-progress should write 20.0% overall."""
        worker, _ = worker_with_db

        source = tmp_path / "in.mkv"
        source.write_bytes(b"\x00" * 100)
        output = tmp_path / "out.mkv"

        mock_proc = AsyncMock()
        mock_proc.stdout = _AsyncLineIterator([
            _hb_json_progress(0.60, rate=45.67),
        ])
        mock_proc.wait = AsyncMock(return_value=0)
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc), \
             patch.object(worker, "_update_progress", new_callable=AsyncMock) as mock_progress:
            output.write_bytes(b"\x00" * 50)
            await worker._transcode_file_handbrake(
                source, output, job_id=1, file_index=0, total_files=3,
            )

        mock_progress.assert_called_once()
        # (0 + 60/100) / 3 * 100 == 20.0
        assert mock_progress.call_args.args[1] == pytest.approx(20.0)

    @pytest.mark.asyncio
    async def test_handbrake_scales_progress_mid_job(self, worker_with_db, tmp_path):
        """File 3 of 6 at 50% file-progress should write 58.33% overall."""
        worker, _ = worker_with_db

        source = tmp_path / "in.mkv"
        source.write_bytes(b"\x00" * 100)
        output = tmp_path / "out.mkv"

        mock_proc = AsyncMock()
        mock_proc.stdout = _AsyncLineIterator([
            _hb_json_progress(0.50, rate=0.0, rate_avg=0.0),
        ])
        mock_proc.wait = AsyncMock(return_value=0)
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc), \
             patch.object(worker, "_update_progress", new_callable=AsyncMock) as mock_progress:
            output.write_bytes(b"\x00" * 50)
            await worker._transcode_file_handbrake(
                source, output, job_id=1, file_index=3, total_files=6,
            )

        mock_progress.assert_called_once()
        # (3 + 50/100) / 6 * 100 == 58.3333...
        assert mock_progress.call_args.args[1] == pytest.approx(58.333, abs=0.01)

    @pytest.mark.asyncio
    async def test_handbrake_single_file_unchanged(self, worker_with_db, tmp_path):
        """file_index=0, total_files=1 (default) is a no-op scaling."""
        worker, _ = worker_with_db

        source = tmp_path / "in.mkv"
        source.write_bytes(b"\x00" * 100)
        output = tmp_path / "out.mkv"

        mock_proc = AsyncMock()
        mock_proc.stdout = _AsyncLineIterator([
            _hb_json_progress(0.333, rate=0.0, rate_avg=0.0),
        ])
        mock_proc.wait = AsyncMock(return_value=0)
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc), \
             patch.object(worker, "_update_progress", new_callable=AsyncMock) as mock_progress:
            output.write_bytes(b"\x00" * 50)
            await worker._transcode_file_handbrake(source, output, job_id=1)

        mock_progress.assert_called_once()
        # (0 + 33.3/100) / 1 * 100 == 33.3
        assert mock_progress.call_args.args[1] == pytest.approx(33.30)

    @pytest.mark.asyncio
    async def test_ffmpeg_scales_progress_by_file_index(self, worker_with_db, tmp_path):
        """Same scaling applies to the FFmpeg path."""
        worker, _ = worker_with_db

        source = tmp_path / "in.mkv"
        source.write_bytes(b"\x00" * 100)
        output = tmp_path / "out.mkv"

        mock_proc = AsyncMock()
        # FFmpeg-style stats: time=00:30:00 of a 60-min file = 50% file-progress.
        mock_proc.stdout = _AsyncLineIterator([
            b"frame=  100 fps= 24.0 time=00:30:00.00 bitrate=...\n",
        ])
        mock_proc.wait = AsyncMock(return_value=0)
        mock_proc.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc), \
             patch.object(worker, "_get_video_resolution", new_callable=AsyncMock, return_value=(1920, 1080)), \
             patch.object(worker, "_get_video_duration", new_callable=AsyncMock, return_value=3600.0), \
             patch.object(worker, "_build_ffmpeg_command", return_value=["ffmpeg"]), \
             patch.object(worker, "_update_progress", new_callable=AsyncMock) as mock_progress:
            output.write_bytes(b"\x00" * 50)
            await worker._transcode_file_ffmpeg(
                source, output, job_id=1, file_index=1, total_files=4,
            )

        mock_progress.assert_called_once()
        # (1 + 50/100) / 4 * 100 == 37.5
        assert mock_progress.call_args.args[1] == pytest.approx(37.5)
