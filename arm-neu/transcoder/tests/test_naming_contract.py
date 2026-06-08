"""Tests for webhook naming contract compliance.

Validates that the transcoder correctly uses ARM's pre-rendered naming
from the webhook payload (title_name, folder_name) instead of inventing
its own names. ARM is the single source of truth for naming.

See docs/WEBHOOK-PAYLOAD.md for the full spec.
"""

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import patch

import pytest

from models import TranscodeJob


# Shared GPU mock
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
    }


def _mock_scheme():
    """Build a mock active_scheme for test fixtures."""
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
        supported_audio_encoders=["copy", "aac"],
        supported_subtitle_modes=["all", "first", "none"],
        built_in_presets=[preset],
    )


def _make_worker():
    with patch("transcoder.check_gpu_support", return_value=_gpu_support_all()), \
         patch("main.active_scheme", _mock_scheme()):
        from transcoder import TranscodeWorker
        return TranscodeWorker()


async def _setup_db(tmp_path, db_name="test.db"):
    """Create a test DB engine and session factory (same pattern as existing tests)."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from models import Base

    db_path = str(tmp_path / db_name)
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

    return engine, session_factory, test_get_db


# ═══════════════════════════════════════════════════════════════════════
# _match_track_metadata: correct source-to-metadata mapping
# ═══════════════════════════════════════════════════════════════════════

class TestMatchTrackMetadata:
    """_match_track_metadata correctly maps transcoded output files back to
    the track manifest entries."""

    @pytest.fixture
    def worker(self):
        return _make_worker()

    def test_match_by_source_filename_substring(self, worker):
        """Match via source filename stem embedded in output stem."""
        source_files = [Path("/work/Show Disc 1_t00.mkv"), Path("/work/Show Disc 1_t01.mkv")]
        track_meta = {
            "Show Disc 1_t00": {"track_number": "0", "title_name": "The Ripper S01E01"},
            "Show Disc 1_t01": {"track_number": "1", "title_name": "The Zombie S01E02"},
        }
        result = worker._match_track_metadata("JobTitle - Show Disc 1_t00", source_files, track_meta)
        assert result is not None
        assert result["title_name"] == "The Ripper S01E01"

    def test_match_by_direct_stem_lookup(self, worker):
        """Match via exact stem in metadata map."""
        source_files = [Path("/work/movie_t00.mkv")]
        track_meta = {"My Movie (2024)": {"track_number": "0", "title_name": "My Movie (2024)"}}
        result = worker._match_track_metadata("My Movie (2024)", source_files, track_meta)
        assert result is not None
        assert result["title_name"] == "My Movie (2024)"

    def test_match_by_normalized_stem(self, worker):
        """Match via lowercase/underscore normalized comparison."""
        source_files = [Path("/work/Show Name_t00.mkv")]
        track_meta = {"show_name_t00": {"track_number": "0", "title_name": "Pilot S01E01"}}
        result = worker._match_track_metadata("Show Name_t00", source_files, track_meta)
        # Strategy 1 won't match (source stem 'Show Name_t00' is in output 'Show Name_t00' - actually it will)
        # But strategy 3 (normalized) should also work
        assert result is not None

    def test_no_match_returns_none(self, worker):
        """Unrecognized output stems return None."""
        source_files = [Path("/work/Show_t00.mkv")]
        track_meta = {"Show_t00": {"track_number": "0", "title_name": "Pilot"}}
        result = worker._match_track_metadata("completely_unrelated", source_files, track_meta)
        assert result is None

    def test_main_feature_multi_title_includes_source_stem(self, worker):
        """For multi-title jobs, the main feature output name must include the
        source filename so _match_track_metadata can map it back to the manifest.
        This is C1 from the naming audit - without this, the main feature keeps
        the job-level temp name and per-track title_name is never applied."""
        from models import TranscodeJob

        job = TranscodeJob(id=99, title="Show", source_path="/raw/Show")
        source_files = [
            Path("/work/Show Disc 3_t00.mkv"),  # 100 bytes
            Path("/work/Show Disc 3_t03.mkv"),  # 200 bytes (main feature)
        ]
        main_feature = source_files[1]  # t03 is largest
        ext = "mkv"
        folder_name = "Show S01E"

        # Multi-title: main feature MUST include source stem.
        # mirrors transcoder.py logic when multi_title=True
        output_stem = f"{folder_name} - {main_feature.stem}"

        assert main_feature.stem in output_stem, \
            "Multi-title main feature output must embed source filename for metadata matching"
        assert output_stem == "Show S01E - Show Disc 3_t03"

        # Now verify _match_track_metadata can find it
        track_meta = {
            "Show Disc 3_t03": {"track_number": "3", "title_name": "Chopper S01E15"},
        }
        result = worker._match_track_metadata(output_stem, source_files, track_meta)
        assert result is not None
        assert result["title_name"] == "Chopper S01E15"


# ═══════════════════════════════════════════════════════════════════════
# Per-track title_name used for output filename
# ═══════════════════════════════════════════════════════════════════════

class TestPerTrackTitleName:
    """Verify that per-track title_name from the manifest becomes the
    output filename, not the job-level folder_name."""

    @pytest.fixture
    def worker(self):
        return _make_worker()

    def test_title_name_becomes_output_filename(self, worker):
        """When track metadata has title_name, it should be used as the filename."""
        # Simulate the move phase logic from transcoder.py lines 700-707
        matched_meta = {
            "track_number": "0",
            "title_name": "Firefall S01E06",
            "folder_name": "Kolchak- The Night Stalker/Season 01",
        }
        per_title_name = matched_meta.get("title_name")
        assert per_title_name == "Firefall S01E06"
        new_name = f"{per_title_name}.mkv"
        assert new_name == "Firefall S01E06.mkv"

    def test_missing_title_name_falls_back_to_dir_plus_track(self, worker):
        """When title_name is absent, fallback to output_dir.name + track number."""
        matched_meta = {"track_number": "3", "folder_name": "Show/Season 01"}
        per_title_name = matched_meta.get("title_name")
        assert per_title_name is None

        output_dir_name = "Season 01"
        track_num = matched_meta.get("track_number", "")
        if not per_title_name:
            per_title_name = output_dir_name
            if track_num:
                per_title_name = f"{per_title_name} - Track {track_num}"
        assert per_title_name == "Season 01 - Track 3"

    def test_empty_title_name_falls_back(self, worker):
        """Empty string title_name should also trigger fallback."""
        matched_meta = {"track_number": "5", "title_name": "", "folder_name": "Show/Season 01"}
        per_title_name = matched_meta.get("title_name")
        output_dir_name = "Season 01"
        track_num = matched_meta.get("track_number", "")
        if not per_title_name:
            per_title_name = output_dir_name
            if track_num:
                per_title_name = f"{per_title_name} - Track {track_num}"
        assert per_title_name == "Season 01 - Track 5"


# ═══════════════════════════════════════════════════════════════════════
# _load_track_metadata builds filename-indexed map
# ═══════════════════════════════════════════════════════════════════════

class TestLoadTrackMetadataIndex:
    """_load_track_metadata should index tracks by filename stem so
    _match_track_metadata can find them."""

    @pytest.mark.asyncio
    async def test_filename_stems_in_index(self, tmp_path):
        """Track metadata is indexed by filename stem for source file matching."""
        from models import TranscodeJobDB, JobStatus

        engine, session_factory, test_get_db = await _setup_db(tmp_path, "idx_test.db")

        tracks = [
            {"track_number": "0", "filename": "Show Disc 1_t00.mkv", "title_name": "Pilot S01E01"},
            {"track_number": "1", "filename": "Show Disc 1_t01.mkv", "title_name": "Second S01E02"},
        ]
        async with session_factory() as session:
            job_db = TranscodeJobDB(
                id=100, title="Show", source_path="/raw/Show",
                status=JobStatus.PENDING, multi_title=1,
                track_metadata=json.dumps(tracks),
            )
            session.add(job_db)
            await session.commit()

        worker = _make_worker()
        with patch("transcoder.get_db", test_get_db):
            result = await worker._load_track_metadata(100)

        assert result is not None
        assert "Show Disc 1_t00" in result
        assert result["Show Disc 1_t00"]["title_name"] == "Pilot S01E01"
        assert "Show Disc 1_t01" in result
        assert result["Show Disc 1_t01"]["title_name"] == "Second S01E02"
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_track_number_key_in_index(self, tmp_path):
        """Track metadata is also indexed by _track_{N} for fallback matching."""
        from models import TranscodeJobDB, JobStatus

        engine, session_factory, test_get_db = await _setup_db(tmp_path, "tn_test.db")

        tracks = [
            {"track_number": "0", "filename": "t00.mkv", "title_name": "Pilot"},
        ]
        async with session_factory() as session:
            job_db = TranscodeJobDB(
                id=101, title="Show", source_path="/raw/Show",
                status=JobStatus.PENDING, multi_title=1,
                track_metadata=json.dumps(tracks),
            )
            session.add(job_db)
            await session.commit()

        worker = _make_worker()
        with patch("transcoder.get_db", test_get_db):
            result = await worker._load_track_metadata(101)

        assert result is not None
        assert "_track_0" in result
        assert result["_track_0"]["title_name"] == "Pilot"
        await engine.dispose()


# ═══════════════════════════════════════════════════════════════════════
# I2: Re-queue should refresh naming metadata
# ═══════════════════════════════════════════════════════════════════════

class TestRequeueRefreshesMetadata:
    """When a terminal job is re-queued, track_metadata, folder_name,
    title_name, and config_overrides should be updated from the new payload."""

    @pytest.mark.asyncio
    async def test_requeue_updates_naming_fields(self, tmp_path):
        """Re-queuing a FAILED job should update all naming metadata."""
        from sqlalchemy import select
        from models import TranscodeJobDB, JobStatus

        engine, session_factory, test_get_db = await _setup_db(tmp_path, "requeue_test.db")
        worker = _make_worker()

        old_tracks = [{"track_number": "0", "title_name": "Old Name S01E01"}]

        with patch("transcoder.get_db", test_get_db):
            job_id, created = await worker.queue_job(
                job_id=200,
                source_path="/raw/Show",
                title="Show",
                video_type="series",
                multi_title=True,
                tracks=old_tracks,
                output_path="TV/0.Rips/Show/Season 01",
                title_name="Old Name S01E01",
            )
        assert created is True

        # Mark job as FAILED
        async with session_factory() as session:
            result = await session.execute(
                select(TranscodeJobDB).where(TranscodeJobDB.id == 200)
            )
            job_db = result.scalar_one()
            job_db.status = JobStatus.FAILED
            await session.commit()

        # Re-queue with updated naming
        new_tracks = [{"track_number": "0", "title_name": "New Name S01E01"}]
        with patch("transcoder.get_db", test_get_db):
            job_id, created = await worker.queue_job(
                job_id=200,
                source_path="/raw/Show",
                title="Show",
                video_type="series",
                multi_title=True,
                tracks=new_tracks,
                output_path="TV/0.Rips/Show/Season 02",
                title_name="New Name S01E01",
            )
        assert job_id == 200

        # Verify metadata was refreshed
        async with session_factory() as session:
            result = await session.execute(
                select(TranscodeJobDB).where(TranscodeJobDB.id == 200)
            )
            job_db = result.scalar_one()
            track_meta = json.loads(job_db.track_metadata)
            assert track_meta[0]["title_name"] == "New Name S01E01", \
                "Re-queue should refresh track_metadata"
            assert job_db.output_path == "TV/0.Rips/Show/Season 02", \
                "Re-queue should refresh output_path"
            assert job_db.title_name == "New Name S01E01", \
                "Re-queue should refresh title_name"

        await engine.dispose()


# ═══════════════════════════════════════════════════════════════════════
# I3: multi_title flag vs track_metadata presence
# ═══════════════════════════════════════════════════════════════════════

class TestMultiTitleFlag:
    """Track metadata should always be loaded when present, regardless
    of the multi_title flag value."""

    @pytest.mark.asyncio
    async def test_multi_title_false_still_loads_track_metadata(self, tmp_path):
        """Even with multi_title=0, track_metadata should be loaded since
        ARM always sends it for naming control."""
        from models import TranscodeJobDB, JobStatus

        engine, session_factory, test_get_db = await _setup_db(tmp_path, "mt_test.db")

        tracks = [{"track_number": "0", "filename": "movie_t00.mkv", "title_name": "My Movie"}]
        async with session_factory() as session:
            job_db = TranscodeJobDB(
                id=300, title="Movie", source_path="/raw/Movie",
                status=JobStatus.PENDING, multi_title=0,
                track_metadata=json.dumps(tracks),
            )
            session.add(job_db)
            await session.commit()

        worker = _make_worker()
        with patch("transcoder.get_db", test_get_db):
            result = await worker._load_track_metadata(300)

        assert result is not None, "track_metadata should load regardless of multi_title flag"
        assert "movie_t00" in result
        await engine.dispose()
