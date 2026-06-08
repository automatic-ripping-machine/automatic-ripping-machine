"""Tests for finalize_output() - moves files from GUID work dir to final library."""
import os
import unittest.mock

from arm.ripper.naming import finalize_output


class TestFinalizeOutput:
    """finalize_output moves ripped files from GUID raw dir to final named path."""

    def test_moves_single_movie(self, app_context, sample_job, tmp_path):
        """Single MKV file moved to completed path with rendered name."""
        from arm.database import db
        from arm.models.track import Track

        raw_dir = tmp_path / "raw" / "test-guid"
        raw_dir.mkdir(parents=True)
        (raw_dir / "B1_t00.mkv").write_bytes(b"fake mkv")

        sample_job.raw_path = str(raw_dir)
        sample_job.config.COMPLETED_PATH = str(tmp_path / "completed")
        sample_job.video_type = "movie"
        sample_job.title = "Serial Mom"
        sample_job.year = "1994"

        t1 = Track(
            job_id=sample_job.job_id, track_number="0", length=7200,
            aspect_ratio="16:9", fps=23.976, main_feature=True,
            source="MakeMKV", basename="B1_t00.mkv", filename="B1_t00.mkv",
        )
        t1.ripped = True
        db.session.add(t1)
        db.session.commit()

        finalize_output(sample_job)

        final_dir = tmp_path / "completed" / "movies"
        assert final_dir.exists()
        mkv_files = list(final_dir.rglob("*.mkv"))
        assert len(mkv_files) == 1

    def test_moves_multiple_tracks(self, app_context, sample_job, tmp_path):
        """Multi-title disc: each track file is moved."""
        from arm.database import db
        from arm.models.track import Track

        raw_dir = tmp_path / "raw" / "test-guid"
        raw_dir.mkdir(parents=True)
        (raw_dir / "B1_t00.mkv").write_bytes(b"fake")
        (raw_dir / "B1_t01.mkv").write_bytes(b"fake")

        sample_job.raw_path = str(raw_dir)
        sample_job.config.COMPLETED_PATH = str(tmp_path / "completed")
        sample_job.video_type = "movie"
        sample_job.title = "Serial Mom"
        sample_job.year = "1994"

        t1 = Track(
            job_id=sample_job.job_id, track_number="0", length=7200,
            aspect_ratio="16:9", fps=23.976, main_feature=True,
            source="MakeMKV", basename="B1_t00.mkv", filename="B1_t00.mkv",
        )
        t1.ripped = True
        t2 = Track(
            job_id=sample_job.job_id, track_number="1", length=3600,
            aspect_ratio="16:9", fps=23.976, main_feature=False,
            source="MakeMKV", basename="B1_t01.mkv", filename="B1_t01.mkv",
        )
        t2.ripped = True
        db.session.add_all([t1, t2])
        db.session.commit()

        finalize_output(sample_job)

        final_dir = tmp_path / "completed" / "movies"
        mkv_files = list(final_dir.rglob("*.mkv"))
        assert len(mkv_files) == 2

    def test_cleans_up_empty_raw_dir(self, app_context, sample_job, tmp_path):
        """After moving all files, empty GUID directory is removed."""
        from arm.database import db
        from arm.models.track import Track

        raw_dir = tmp_path / "raw" / "test-guid"
        raw_dir.mkdir(parents=True)
        (raw_dir / "B1_t00.mkv").write_bytes(b"fake")

        sample_job.raw_path = str(raw_dir)
        sample_job.config.COMPLETED_PATH = str(tmp_path / "completed")

        t1 = Track(
            job_id=sample_job.job_id, track_number="0", length=7200,
            aspect_ratio="16:9", fps=23.976, main_feature=True,
            source="MakeMKV", basename="B1_t00.mkv", filename="B1_t00.mkv",
        )
        t1.ripped = True
        db.session.add(t1)
        db.session.commit()

        finalize_output(sample_job)

        assert not raw_dir.exists()

    def test_updates_job_path(self, app_context, sample_job, tmp_path):
        """job.path is updated to the final directory after move."""
        from arm.database import db
        from arm.models.track import Track

        raw_dir = tmp_path / "raw" / "test-guid"
        raw_dir.mkdir(parents=True)
        (raw_dir / "B1_t00.mkv").write_bytes(b"fake")

        sample_job.raw_path = str(raw_dir)
        sample_job.config.COMPLETED_PATH = str(tmp_path / "completed")

        t1 = Track(
            job_id=sample_job.job_id, track_number="0", length=7200,
            aspect_ratio="16:9", fps=23.976, main_feature=True,
            source="MakeMKV", basename="B1_t00.mkv", filename="B1_t00.mkv",
        )
        t1.ripped = True
        db.session.add(t1)
        db.session.commit()

        finalize_output(sample_job)

        assert sample_job.path is not None
        assert "completed" in sample_job.path

    def test_noop_if_no_raw_path(self, app_context, sample_job):
        """No error if raw_path is not set."""
        sample_job.raw_path = None
        finalize_output(sample_job)  # should not raise

    def test_fallback_moves_mkv_without_tracks(self, app_context, sample_job, tmp_path):
        """If no track records exist, move all MKV files with fallback naming."""
        raw_dir = tmp_path / "raw" / "test-guid"
        raw_dir.mkdir(parents=True)
        (raw_dir / "B1_t00.mkv").write_bytes(b"fake")

        sample_job.raw_path = str(raw_dir)
        sample_job.config.COMPLETED_PATH = str(tmp_path / "completed")
        sample_job.video_type = "movie"
        sample_job.title = "Serial Mom"
        sample_job.year = "1994"

        finalize_output(sample_job)

        final_dir = tmp_path / "completed" / "movies"
        mkv_files = list(final_dir.rglob("*.mkv"))
        assert len(mkv_files) == 1

    def test_noop_if_raw_path_missing(self, app_context, sample_job, tmp_path):
        """No error if raw_path points to a non-existent directory."""
        sample_job.raw_path = str(tmp_path / "nonexistent")
        finalize_output(sample_job)  # should not raise

    def test_skips_tracks_without_filename(self, app_context, sample_job, tmp_path):
        """Tracks with no filename are silently skipped."""
        from arm.database import db
        from arm.models.track import Track

        raw_dir = tmp_path / "raw" / "test-guid"
        raw_dir.mkdir(parents=True)
        (raw_dir / "B1_t00.mkv").write_bytes(b"fake")

        sample_job.raw_path = str(raw_dir)
        sample_job.config.COMPLETED_PATH = str(tmp_path / "completed")
        sample_job.video_type = "movie"
        sample_job.title = "Serial Mom"
        sample_job.year = "1994"

        t1 = Track(
            job_id=sample_job.job_id, track_number="0", length=7200,
            aspect_ratio="16:9", fps=23.976, main_feature=True,
            source="MakeMKV", basename="B1_t00.mkv", filename="B1_t00.mkv",
        )
        t1.ripped = True
        # Second track has no file on disk
        t2 = Track(
            job_id=sample_job.job_id, track_number="1", length=600,
            aspect_ratio="16:9", fps=23.976, main_feature=False,
            source="MakeMKV", basename="B1_t01.mkv", filename=None,
        )
        t2.ripped = True
        db.session.add_all([t1, t2])
        db.session.commit()

        finalize_output(sample_job)

        final_dir = tmp_path / "completed" / "movies"
        mkv_files = list(final_dir.rglob("*.mkv"))
        assert len(mkv_files) == 1
