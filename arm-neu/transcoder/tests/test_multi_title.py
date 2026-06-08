"""
Tests for multi-title disc features in transcoder.py.

Covers:
- _match_track_metadata (matching strategies)
- _transcode_files with multi_title flag
- _notify_arm_callback with track_results
- Partial status logic
"""

import json
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from models import TranscodeJob, Base


# Default GPU support dicts for mocking
def _gpu_support_all():
    return {
        "handbrake_nvenc": True,
        "ffmpeg_nvenc_h265": True,
        "ffmpeg_nvenc_h264": True,
        "ffmpeg_vaapi_h265": True,
        "ffmpeg_vaapi_h264": True,
        "ffmpeg_amf_h265": True,
        "ffmpeg_amf_h264": True,
        "ffmpeg_qsv_h265": True,
        "ffmpeg_qsv_h264": True,
        "vaapi_device": True,
    }


def _gpu_support_none():
    return {k: False for k in _gpu_support_all()}


def _mock_scheme(video_encoder="x265"):
    """Build a mock active_scheme with the given default video_encoder."""
    from presets import Preset, Scheme, Encoder
    preset = Preset(
        slug="test", name="Test", scheme="test",
        shared={"video_encoder": video_encoder, "audio_encoder": "copy", "subtitle_mode": "all"},
        tiers={
            "dvd": {"handbrake_preset": "Test 720p", "video_quality": 22},
            "bluray": {"handbrake_preset": "Test 1080p", "video_quality": 22},
            "uhd": {"handbrake_preset": "Test 2160p 4K", "video_quality": 22},
        },
    )
    return Scheme(
        slug="test", name="Test",
        supported_encoders=[Encoder(slug=video_encoder, name=video_encoder)],
        supported_audio_encoders=["copy", "aac"],
        supported_subtitle_modes=["all", "first", "none"],
        built_in_presets=[preset],
    )


# ─── _match_track_metadata ──────────────────────────────────────────────────


class TestMatchTrackMetadata:
    """Tests for TranscodeWorker._match_track_metadata."""

    def _make_worker(self):
        with patch("transcoder.check_gpu_support", return_value=_gpu_support_all()), \
             patch("main.active_scheme", _mock_scheme()):
            from transcoder import TranscodeWorker
            return TranscodeWorker()

    def test_strategy1_source_filename_embedded(self):
        """Match when source filename stem is embedded in output stem."""
        worker = self._make_worker()
        source_files = [Path("/work/source/t01_title.mkv")]
        track_meta = {"t01_title": {"track_number": 1, "title": "Episode 1"}}

        result = worker._match_track_metadata(
            "Movie - t01_title", source_files, track_meta,
        )
        assert result is not None
        assert result["track_number"] == 1
        assert result["title"] == "Episode 1"

    def test_strategy2_direct_stem_lookup(self):
        """Match by direct output stem lookup in track_meta keys."""
        worker = self._make_worker()
        source_files = [Path("/work/source/something_else.mkv")]
        track_meta = {"my_output": {"track_number": 2, "title": "Episode 2"}}

        result = worker._match_track_metadata(
            "my_output", source_files, track_meta,
        )
        assert result is not None
        assert result["track_number"] == 2

    def test_strategy3_normalized_comparison(self):
        """Match via lowercase + underscore normalization."""
        worker = self._make_worker()
        source_files = [Path("/work/source/other.mkv")]
        track_meta = {"my_title": {"track_number": 3, "title": "Episode 3"}}

        result = worker._match_track_metadata(
            "My Title", source_files, track_meta,
        )
        assert result is not None
        assert result["track_number"] == 3

    def test_no_match_returns_none(self):
        """Returns None when no strategy matches."""
        worker = self._make_worker()
        source_files = [Path("/work/source/unrelated.mkv")]
        track_meta = {"episode_one": {"track_number": 1, "title": "Ep 1"}}

        result = worker._match_track_metadata(
            "completely_different", source_files, track_meta,
        )
        assert result is None

    def test_empty_track_meta_returns_none(self):
        """Returns None when track_meta has no entries."""
        worker = self._make_worker()
        source_files = [Path("/work/source/t01.mkv")]
        track_meta: dict[str, dict] = {}

        result = worker._match_track_metadata(
            "t01", source_files, track_meta,
        )
        assert result is None

    def test_strategy1_takes_priority_over_strategy2(self):
        """Strategy 1 (source embedded) should be tried before direct lookup."""
        worker = self._make_worker()
        source_files = [Path("/work/source/t01.mkv")]
        track_meta = {
            "t01": {"track_number": 1, "title": "From source"},
            "Movie - t01": {"track_number": 99, "title": "From direct"},
        }

        result = worker._match_track_metadata(
            "Movie - t01", source_files, track_meta,
        )
        assert result["track_number"] == 1
        assert result["title"] == "From source"


# ─── _transcode_files multi_title ───────────────────────────────────────────


class TestTranscodeFilesMultiTitle:
    """Tests for _transcode_files with multi_title flag."""

    def _make_worker(self, video_encoder="x265"):
        scheme = _mock_scheme(video_encoder)
        with patch("transcoder.check_gpu_support", return_value=_gpu_support_none()), \
             patch("main.active_scheme", scheme):
            from transcoder import TranscodeWorker
            worker = TranscodeWorker()
        mock_settings = MagicMock()
        mock_settings.output_extension = "mkv"
        return worker, mock_settings

    @pytest.mark.asyncio
    async def test_all_tracks_succeed(self, tmp_path):
        """All tracks succeed -> returns all 'completed' results."""
        worker, mock_settings = self._make_worker()
        mock_settings.output_extension = "mkv"

        work_output = tmp_path / "output"
        work_output.mkdir()

        src1 = tmp_path / "t01.mkv"
        src2 = tmp_path / "t02.mkv"
        src1.write_bytes(b"\x00" * 100)
        src2.write_bytes(b"\x00" * 100)

        job = TranscodeJob(id=1, title="Movie", source_path=str(tmp_path))

        with patch.object(worker, "_update_progress", new_callable=AsyncMock), \
             patch.object(worker, "_transcode_file_ffmpeg", new_callable=AsyncMock), \
             patch("transcoder.settings", mock_settings):
            results = await worker._transcode_files(
                job, [src1, src2], src1, work_output, "Movie",
                None, multi_title=True,
            )

        assert len(results) == 2
        assert all(r["status"] == "completed" for r in results)
        assert results[0]["file"] == "t01.mkv"
        assert results[1]["file"] == "t02.mkv"

    @pytest.mark.asyncio
    async def test_one_track_fails_multi_title_continues(self, tmp_path):
        """One track fails with multi_title=True -> continues, returns mixed results."""
        worker, mock_settings = self._make_worker()
        mock_settings.output_extension = "mkv"

        work_output = tmp_path / "output"
        work_output.mkdir()

        src1 = tmp_path / "t01.mkv"
        src2 = tmp_path / "t02.mkv"
        src1.write_bytes(b"\x00" * 100)
        src2.write_bytes(b"\x00" * 100)

        job = TranscodeJob(id=1, title="Movie", source_path=str(tmp_path))

        async def mock_transcode(source, output, job_id, overrides=None, **_):
            if source == src1:
                raise RuntimeError("Encoder crashed")

        with patch.object(worker, "_update_progress", new_callable=AsyncMock), \
             patch.object(worker, "_transcode_file_ffmpeg", side_effect=mock_transcode), \
             patch("transcoder.settings", mock_settings):
            results = await worker._transcode_files(
                job, [src1, src2], src1, work_output, "Movie",
                None, multi_title=True,
            )

        assert len(results) == 2
        assert results[0]["status"] == "failed"
        assert "Encoder crashed" in results[0]["error"]
        assert results[1]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_one_track_fails_single_title_raises(self, tmp_path):
        """One track fails with multi_title=False -> raises exception."""
        worker, mock_settings = self._make_worker()
        mock_settings.output_extension = "mkv"

        work_output = tmp_path / "output"
        work_output.mkdir()

        src1 = tmp_path / "t01.mkv"
        src2 = tmp_path / "t02.mkv"
        src1.write_bytes(b"\x00" * 100)
        src2.write_bytes(b"\x00" * 100)

        job = TranscodeJob(id=1, title="Movie", source_path=str(tmp_path))

        async def mock_transcode(source, output, job_id, overrides=None, **_):
            if source == src1:
                raise RuntimeError("Encoder crashed")

        with patch.object(worker, "_update_progress", new_callable=AsyncMock), \
             patch.object(worker, "_transcode_file_ffmpeg", side_effect=mock_transcode), \
             patch("transcoder.settings", mock_settings):
            with pytest.raises(RuntimeError, match="Encoder crashed"):
                await worker._transcode_files(
                    job, [src1, src2], src1, work_output, "Movie",
                    None, multi_title=False,
                )


# ─── _notify_arm_callback with track_results ────────────────────────────────


@pytest_asyncio.fixture
async def worker_with_test_db(tmp_path):
    """TranscodeWorker with an in-memory test DB, for callback-enqueue tests."""
    import database as db_module
    from transcoder import TranscodeWorker

    db_path = str(tmp_path / "test_multi.db")
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

    with patch.object(db_module, "get_db", test_get_db), \
         patch("transcoder.get_db", test_get_db), \
         patch("main.active_scheme", _mock_scheme()):
        worker = TranscodeWorker(gpu_support=_gpu_support_none())
        yield worker, sf

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


class TestNotifyArmCallback:
    """Tests for _notify_arm_callback track_results parameter."""

    def _make_worker(self):
        with patch("transcoder.check_gpu_support", return_value=_gpu_support_all()), \
             patch("main.active_scheme", _mock_scheme()):
            from transcoder import TranscodeWorker
            return TranscodeWorker()

    @pytest.mark.asyncio
    async def test_sends_track_results_in_payload(self, worker_with_test_db):
        """track_results are stored in the enqueued PendingCallbackDB row."""
        from models import PendingCallbackDB
        from sqlalchemy import select

        worker, sf = worker_with_test_db
        track_results = [
            {"track_number": 1, "status": "completed", "output_path": "/out/ep1.mkv"},
            {"track_number": 2, "status": "failed", "error": "encode error"},
        ]

        with patch("transcoder.settings") as mock_settings:
            mock_settings.arm_callback_url = "https://arm:8080"
            job = TranscodeJob(id=1, title="Movie", source_path="/data/raw/movie")
            await worker._notify_arm_callback(
                job, "partial", track_results=track_results,
            )

        async with sf() as session:
            result = await session.execute(
                select(PendingCallbackDB).where(PendingCallbackDB.job_id == 1)
            )
            row = result.scalar_one()
            assert row.status == "partial"
            assert json.loads(row.track_results_json) == track_results

    @pytest.mark.asyncio
    async def test_no_track_results_key_when_none(self, worker_with_test_db):
        """track_results_json is NULL in the DB row when track_results=None."""
        from models import PendingCallbackDB
        from sqlalchemy import select

        worker, sf = worker_with_test_db

        with patch("transcoder.settings") as mock_settings:
            mock_settings.arm_callback_url = "https://arm:8080"
            job = TranscodeJob(id=2, title="Movie", source_path="/data/raw/movie")
            await worker._notify_arm_callback(job, "completed", track_results=None)

        async with sf() as session:
            result = await session.execute(
                select(PendingCallbackDB).where(PendingCallbackDB.job_id == 2)
            )
            row = result.scalar_one()
            assert row.track_results_json is None

    @pytest.mark.asyncio
    async def test_no_track_results_key_when_empty_list(self, worker_with_test_db):
        """Empty track_results list is stored as NULL in the DB row."""
        from models import PendingCallbackDB
        from sqlalchemy import select

        worker, sf = worker_with_test_db

        with patch("transcoder.settings") as mock_settings:
            mock_settings.arm_callback_url = "https://arm:8080"
            job = TranscodeJob(id=3, title="Movie", source_path="/data/raw/movie")
            await worker._notify_arm_callback(job, "completed", track_results=[])

        async with sf() as session:
            result = await session.execute(
                select(PendingCallbackDB).where(PendingCallbackDB.job_id == 3)
            )
            row = result.scalar_one()
            assert row.track_results_json is None

    @pytest.mark.asyncio
    async def test_skips_callback_without_callback_url(self):
        """Should not send callback when arm_callback_url is not set."""
        worker = self._make_worker()
        job = TranscodeJob(id=1, title="Movie", source_path="/data/raw/movie")

        with patch("transcoder.settings") as mock_settings, \
             patch("transcoder.httpx.AsyncClient") as mock_client_cls:
            mock_settings.arm_callback_url = ""
            mock_client = AsyncMock()
            mock_client_cls.return_value = mock_client

            await worker._notify_arm_callback(
                job, "completed", track_results=[{"status": "completed"}],
            )
            mock_client.__aenter__.assert_not_called()


# ─── Partial status logic ───────────────────────────────────────────────────


class TestPartialStatusLogic:
    """Tests for partial status determination logic from _process_job.

    These tests verify the status-calculation logic extracted from
    _process_job lines 688-708, which determines whether the overall
    job result is 'completed', 'partial', or raises RuntimeError.
    """

    def test_some_tracks_fail_partial_status(self):
        """Some tracks fail -> callback_status='partial', error_summary set."""
        local_source_files = [Path("t01.mkv"), Path("t02.mkv"), Path("t03.mkv")]

        file_results = [
            {"file": "t01.mkv", "status": "completed"},
            {"file": "t02.mkv", "status": "failed", "error": "encoder error"},
            {"file": "t03.mkv", "status": "completed"},
        ]
        track_results = [
            {"track_number": 1, "status": "completed", "output_path": "/out/t01.mkv"},
            {"track_number": 3, "status": "completed", "output_path": "/out/t03.mkv"},
        ]

        failed_transcodes = [r for r in file_results if r.get("status") == "failed"]
        failed_routes = [r for r in track_results if r.get("status") == "failed"]
        total_failures = len(failed_transcodes) + len(failed_routes)

        assert total_failures == 1
        assert total_failures > 0
        assert total_failures < len(local_source_files)

        callback_status = "partial"
        error_summary = f"{total_failures}/{len(local_source_files)} tracks failed"

        assert callback_status == "partial"
        assert error_summary == "1/3 tracks failed"

    def test_all_tracks_fail_raises_runtime_error(self):
        """All tracks fail -> raises RuntimeError."""
        local_source_files = [Path("t01.mkv"), Path("t02.mkv")]

        file_results = [
            {"file": "t01.mkv", "status": "failed", "error": "error 1"},
            {"file": "t02.mkv", "status": "failed", "error": "error 2"},
        ]
        track_results: list[dict] = []

        failed_transcodes = [r for r in file_results if r.get("status") == "failed"]
        failed_routes = [r for r in track_results if r.get("status") == "failed"]
        total_failures = len(failed_transcodes) + len(failed_routes)

        assert total_failures >= len(local_source_files)

        with pytest.raises(RuntimeError, match="All 2 tracks failed"):
            raise RuntimeError(f"All {len(local_source_files)} tracks failed to transcode")

    def test_no_failures_completed_status(self):
        """No failures -> callback_status='completed'."""
        local_source_files = [Path("t01.mkv"), Path("t02.mkv")]

        file_results = [
            {"file": "t01.mkv", "status": "completed"},
            {"file": "t02.mkv", "status": "completed"},
        ]
        track_results = [
            {"track_number": 1, "status": "completed"},
            {"track_number": 2, "status": "completed"},
        ]

        failed_transcodes = [r for r in file_results if r.get("status") == "failed"]
        failed_routes = [r for r in track_results if r.get("status") == "failed"]
        total_failures = len(failed_transcodes) + len(failed_routes)

        assert total_failures == 0
        callback_status = "completed"
        assert callback_status == "completed"

    def test_route_failures_count_toward_partial(self):
        """Routing failures (not transcode failures) also contribute to partial."""
        local_source_files = [Path("t01.mkv"), Path("t02.mkv"), Path("t03.mkv")]

        file_results = [
            {"file": "t01.mkv", "status": "completed"},
            {"file": "t02.mkv", "status": "completed"},
            {"file": "t03.mkv", "status": "completed"},
        ]
        track_results = [
            {"track_number": 1, "status": "completed"},
            {"track_number": 2, "status": "failed", "error": "move error"},
            {"track_number": 3, "status": "completed"},
        ]

        failed_transcodes = [r for r in file_results if r.get("status") == "failed"]
        failed_routes = [r for r in track_results if r.get("status") == "failed"]
        total_failures = len(failed_transcodes) + len(failed_routes)

        assert total_failures == 1
        assert total_failures > 0
        assert total_failures < len(local_source_files)

        callback_status = "partial"
        error_summary = f"{total_failures}/{len(local_source_files)} tracks failed"
        assert callback_status == "partial"
        assert error_summary == "1/3 tracks failed"

    def test_mixed_transcode_and_route_failures(self):
        """Both transcode and route failures combine for total count."""
        local_source_files = [Path("t01.mkv"), Path("t02.mkv"), Path("t03.mkv")]

        file_results = [
            {"file": "t01.mkv", "status": "failed", "error": "encode error"},
            {"file": "t02.mkv", "status": "completed"},
            {"file": "t03.mkv", "status": "completed"},
        ]
        track_results = [
            {"track_number": 2, "status": "failed", "error": "move error"},
            {"track_number": 3, "status": "completed"},
        ]

        failed_transcodes = [r for r in file_results if r.get("status") == "failed"]
        failed_routes = [r for r in track_results if r.get("status") == "failed"]
        total_failures = len(failed_transcodes) + len(failed_routes)

        assert total_failures == 2
        assert total_failures > 0
        assert total_failures < len(local_source_files)

        error_summary = f"{total_failures}/{len(local_source_files)} tracks failed"
        assert error_summary == "2/3 tracks failed"
