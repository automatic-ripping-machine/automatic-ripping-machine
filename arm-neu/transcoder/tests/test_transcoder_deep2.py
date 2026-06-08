"""
Deep coverage tests part 2 — _resolve_source_path, _wait_for_stable,
_notify_arm_callback, _match_track_metadata, _load_track_metadata,
_cleanup_source, _get_codec_name, _classify_media_type, _format_resolution,
_transcode_files, and _process_job error/cleanup paths.
"""

import asyncio
import json
import shutil
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

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
    """Build a minimal software scheme for test fixtures."""
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
async def worker_db(tmp_path):
    """TranscodeWorker with real test DB."""
    from transcoder import TranscodeWorker
    import database as db_module

    db_path = str(tmp_path / "test_deep2.db")
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
         patch("main.active_scheme", _mock_scheme_software()):
        worker = TranscodeWorker(gpu_support=_gpu_support_none())
        yield worker, sf, tmp_path

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# _resolve_source_path / _find_media_candidates were removed in v18.0.0.
# ARM now sends an explicit input_path which the webhook handler joins
# directly to settings.raw_path - no resolution / candidate search.


# ── _wait_for_stable ─────────────────────────────────────────────────────────

class TestWaitForStable:
    @pytest.mark.asyncio
    async def test_stable_immediately(self, worker_db, tmp_path):
        """Cover lines 868-885: files already stable."""
        worker, _, _ = worker_db
        source = tmp_path / "stable_dir"
        source.mkdir()
        (source / "file.mkv").write_bytes(b"\x00" * 100)

        with patch("transcoder.settings") as ms:
            ms.stabilize_seconds = 1
            with patch("transcoder.asyncio.sleep", new_callable=AsyncMock):
                await worker._wait_for_stable(str(source))

    @pytest.mark.asyncio
    async def test_path_missing_then_appears(self, worker_db, tmp_path):
        """Cover lines 854-860: NFS propagation wait."""
        worker, _, _ = worker_db
        source = tmp_path / "nfs_dir"

        call_count = 0
        async def fake_sleep(t):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                source.mkdir(exist_ok=True)
                (source / "file.mkv").write_bytes(b"\x00" * 100)

        with patch("transcoder.settings") as ms:
            ms.stabilize_seconds = 1
            with patch("transcoder.asyncio.sleep", side_effect=fake_sleep):
                await worker._wait_for_stable(str(source))

    @pytest.mark.asyncio
    async def test_path_never_appears(self, worker_db, tmp_path):
        """Cover line 860: path never appears → ValueError."""
        worker, _, _ = worker_db
        source = tmp_path / "never_appears"

        with patch("transcoder.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(ValueError, match="does not exist"):
                await worker._wait_for_stable(str(source))


# ── _notify_arm_callback ────────────────────────────────────────────────────

class TestNotifyArmCallbackEnqueues:
    """After the callback-drainer refactor, terminal callbacks enqueue
    a PendingCallbackDB row and return immediately (no inline retry)."""

    @pytest.mark.asyncio
    async def test_terminal_status_enqueues_row(self, worker_db):
        """completed status inserts a PendingCallbackDB row."""
        from models import PendingCallbackDB
        from sqlalchemy import select

        worker, sf, _ = worker_db
        worker._drainer = None  # Set by main.py at runtime; not exercised here

        with patch("transcoder.settings") as mock_settings:
            mock_settings.arm_callback_url = "https://arm.example/callback"

            job = TranscodeJob(id=900, title="T", source_path="/x")
            await worker._notify_arm_callback(job, "completed")

        async with sf() as session:
            result = await session.execute(
                select(PendingCallbackDB).where(PendingCallbackDB.job_id == 900)
            )
            row = result.scalar_one()
            assert row.status == "completed"
            assert row.delivered_at is None
            assert row.attempt_count == 0

    @pytest.mark.asyncio
    async def test_informational_status_does_not_enqueue(self, worker_db):
        """transcoding status stays fire-and-forget: no DB row."""
        from models import PendingCallbackDB
        from sqlalchemy import select

        worker, sf, _ = worker_db
        with patch("transcoder.settings") as mock_settings, \
             patch("transcoder.httpx.AsyncClient") as mock_client_cls:
            mock_settings.arm_callback_url = "https://arm.example/callback"
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.post.return_value.status_code = 200

            job = TranscodeJob(id=901, title="T", source_path="/x")
            await worker._notify_arm_callback(job, "transcoding")

        async with sf() as session:
            result = await session.execute(
                select(PendingCallbackDB).where(PendingCallbackDB.job_id == 901)
            )
            rows = list(result.scalars())
            assert rows == []

    @pytest.mark.asyncio
    async def test_no_callback_url_returns_without_enqueue(self, worker_db):
        """With no callback URL configured, terminal status is a no-op."""
        from models import PendingCallbackDB
        from sqlalchemy import select

        worker, sf, _ = worker_db
        with patch("transcoder.settings") as mock_settings:
            mock_settings.arm_callback_url = ""

            job = TranscodeJob(id=902, title="T", source_path="/x")
            await worker._notify_arm_callback(job, "completed")

        async with sf() as session:
            result = await session.execute(
                select(PendingCallbackDB).where(PendingCallbackDB.job_id == 902)
            )
            rows = list(result.scalars())
            assert rows == []

    @pytest.mark.asyncio
    async def test_enqueue_includes_error_and_track_results(self, worker_db):
        """partial status with extra fields stores them in the DB row."""
        import json
        from models import PendingCallbackDB
        from sqlalchemy import select

        worker, sf, _ = worker_db
        with patch("transcoder.settings") as mock_settings:
            mock_settings.arm_callback_url = "https://arm.example/callback"

            job = TranscodeJob(id=903, title="T", source_path="/x")
            await worker._notify_arm_callback(
                job, "partial",
                error="one track failed",
                track_results=[{"track_number": 1, "status": "failed"}],
            )

        async with sf() as session:
            result = await session.execute(
                select(PendingCallbackDB).where(PendingCallbackDB.job_id == 903)
            )
            row = result.scalar_one()
            assert row.status == "partial"
            assert row.error == "one track failed"
            assert json.loads(row.track_results_json) == [
                {"track_number": 1, "status": "failed"}
            ]


# ── _match_track_metadata ────────────────────────────────────────────────────

class TestMatchTrackMetadata:
    def test_match_by_source_stem(self, worker_db):
        """Cover _match_track_metadata: strategy 1 — source stem in output."""
        worker, _, _ = worker_db
        source_files = [Path("/test/title_01.mkv"), Path("/test/title_02.mkv")]
        track_meta = {"title_01": {"track_number": "1", "title": "Ep 1"}}
        result = worker._match_track_metadata("Movie - title_01", source_files, track_meta)
        assert result["track_number"] == "1"

    def test_match_by_direct_lookup(self, worker_db):
        """Cover _match_track_metadata: strategy 2 — direct stem."""
        worker, _, _ = worker_db
        track_meta = {"output_name": {"track_number": "2"}}
        result = worker._match_track_metadata("output_name", [], track_meta)
        assert result["track_number"] == "2"

    def test_match_by_normalized(self, worker_db):
        """Cover _match_track_metadata: strategy 3 — normalized."""
        worker, _, _ = worker_db
        track_meta = {"my_track": {"track_number": "3"}}
        result = worker._match_track_metadata("My Track", [], track_meta)
        assert result["track_number"] == "3"

    def test_no_match(self, worker_db):
        """Cover _match_track_metadata line 474: no match → None."""
        worker, _, _ = worker_db
        result = worker._match_track_metadata("unknown", [], {"other": {}})
        assert result is None


# ── _load_track_metadata ─────────────────────────────────────────────────────

class TestLoadTrackMetadata:
    @pytest.mark.asyncio
    async def test_load_track_meta_with_data(self, worker_db):
        """Cover _load_track_metadata line 441: normalized key added."""
        worker, sf, _ = worker_db
        tracks = [
            {"track_number": "1", "filename": "Title 01.mkv", "title": "Ep 1"},
        ]
        async with sf() as session:
            job = TranscodeJobDB(
                id=101, title="Series", source_path="/test",
                status=JobStatus.PENDING, multi_title=1,
                track_metadata=json.dumps(tracks),
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)
            job_id = job.id

        result = await worker._load_track_metadata(job_id)
        assert result is not None
        # Should have both original and normalized keys
        assert "Title 01" in result
        assert "title_01" in result  # normalized

    @pytest.mark.asyncio
    async def test_load_track_meta_no_data(self, worker_db):
        """Cover _load_track_metadata: no track_metadata → None."""
        worker, sf, _ = worker_db
        async with sf() as session:
            job = TranscodeJobDB(
                id=102, title="Movie", source_path="/test",
                status=JobStatus.PENDING,
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)
            job_id = job.id

        result = await worker._load_track_metadata(job_id)
        assert result is None


# ── _get_codec_name ──────────────────────────────────────────────────────────

class TestGetCodecName:
    def test_h265_codec(self, worker_db):
        worker, _, _ = worker_db
        assert worker._get_codec_name({"video_encoder": "hevc_nvenc"}) == "HEVC"

    def test_h264_codec(self, worker_db):
        worker, _, _ = worker_db
        assert worker._get_codec_name({"video_encoder": "h264_nvenc"}) == "H264"

    def test_unknown_codec(self, worker_db):
        """Cover line 1025: unknown encoder → uppercase."""
        worker, _, _ = worker_db
        assert worker._get_codec_name({"video_encoder": "av1_svt"}) == "AV1_SVT"


# ── _cleanup_source ──────────────────────────────────────────────────────────

class TestCleanupSource:
    @pytest.mark.asyncio
    async def test_cleanup_directory(self, worker_db, tmp_path):
        """Cover _cleanup_source: removes directory."""
        worker, _, _ = worker_db
        source = tmp_path / "to_clean"
        source.mkdir()
        (source / "file.mkv").write_bytes(b"\x00" * 100)

        await worker._cleanup_source(str(source))
        assert not source.exists()

    @pytest.mark.asyncio
    async def test_cleanup_single_file(self, worker_db, tmp_path):
        """Cover _cleanup_source: removes single file."""
        worker, _, _ = worker_db
        source = tmp_path / "single.mkv"
        source.write_bytes(b"\x00" * 100)

        await worker._cleanup_source(str(source))
        assert not source.exists()


# ── _classify_media_type and _format_resolution ──────────────────────────────

class TestMediaClassification:
    def test_classify_dvd(self, worker_db):
        from transcoder import TranscodeWorker
        assert TranscodeWorker._classify_media_type(480) == "DVD"

    def test_classify_bluray(self, worker_db):
        from transcoder import TranscodeWorker
        assert TranscodeWorker._classify_media_type(1080) == "Blu-ray"

    def test_classify_uhd(self, worker_db):
        from transcoder import TranscodeWorker
        assert TranscodeWorker._classify_media_type(2160) == "UHD Blu-ray"

    def test_format_480p(self, worker_db):
        from transcoder import TranscodeWorker
        assert TranscodeWorker._format_resolution(480) == "480p"

    def test_format_720p(self, worker_db):
        from transcoder import TranscodeWorker
        assert TranscodeWorker._format_resolution(720) == "720p"

    def test_format_1080p(self, worker_db):
        from transcoder import TranscodeWorker
        assert TranscodeWorker._format_resolution(1080) == "1080p"

    def test_format_2160p(self, worker_db):
        from transcoder import TranscodeWorker
        assert TranscodeWorker._format_resolution(2160) == "2160p"

    def test_format_unusual(self, worker_db):
        from transcoder import TranscodeWorker
        assert TranscodeWorker._format_resolution(1440) == "1440p"


# ── _detect_video_type ───────────────────────────────────────────────────────

class TestDetectVideoType:
    def test_detect_tv(self, worker_db):
        worker, _, _ = worker_db
        assert worker._detect_video_type("Show S01E01", "/raw/Show S01E01") == "tv"

    def test_detect_movie(self, worker_db):
        worker, _, _ = worker_db
        assert worker._detect_video_type("My Movie 2024", "/raw/My Movie 2024") == "movie"

    def test_detect_tv_from_path(self, worker_db):
        worker, _, _ = worker_db
        assert worker._detect_video_type("Unknown", "/raw/Show_S02") == "tv"
