"""Tests for Job model folder import features (from_folder, makemkv_source, is_folder_import)."""
import unittest.mock

import pytest

from arm.models.job import Job


class TestJobFromFolder:
    """Test Job.from_folder() classmethod."""

    def test_from_folder_creates_folder_job(self, app_context):
        """from_folder() creates a job with source_type='folder'."""
        with unittest.mock.patch("arm.config.config.arm_config", {"VIDEOTYPE": "auto"}):
            job = Job.from_folder("/ingress/My Movie 2024", "bluray")

        assert job.source_type == "folder"
        assert job.source_path == "/ingress/My Movie 2024"
        assert job.disctype == "bluray"
        assert job.devpath is None
        assert job.is_iso is False
        assert job.video_type == "unknown"
        assert job.ejected is False
        assert job.updated is False
        assert job.manual_start is False
        assert job.manual_pause is False
        assert job.manual_mode is False
        assert job.start_time is not None

    def test_from_folder_respects_videotype_config(self, app_context):
        """from_folder() uses VIDEOTYPE when not 'auto'."""
        with unittest.mock.patch("arm.config.config.arm_config", {"VIDEOTYPE": "movie"}):
            job = Job.from_folder("/ingress/test", "dvd")

        assert job.video_type == "movie"

    def test_from_folder_videotype_auto(self, app_context):
        """from_folder() defaults video_type to 'unknown' when VIDEOTYPE is 'auto'."""
        with unittest.mock.patch("arm.config.config.arm_config", {"VIDEOTYPE": "auto"}):
            job = Job.from_folder("/ingress/test", "dvd")

        assert job.video_type == "unknown"

    def test_from_folder_persists_to_database(self, app_context):
        """from_folder() job can be persisted and queried from the database."""
        from arm.database import db

        with unittest.mock.patch("arm.config.config.arm_config", {"VIDEOTYPE": "auto"}):
            job = Job.from_folder("/ingress/Movie", "bluray")

        job.title = "Movie"
        job.status = "ripping"
        job.label = "MOVIE"
        db.session.add(job)
        db.session.commit()

        queried = Job.query.filter_by(source_type="folder").first()
        assert queried is not None
        assert queried.source_path == "/ingress/Movie"
        assert queried.disctype == "bluray"
        assert queried.job_id is not None


class TestMakemkvSource:
    """Test job.makemkv_source property."""

    def test_makemkv_source_folder_job(self, app_context):
        """Folder jobs return 'file:<source_path>'."""
        with unittest.mock.patch("arm.config.config.arm_config", {"VIDEOTYPE": "auto"}):
            job = Job.from_folder("/ingress/Movie", "bluray")

        assert job.makemkv_source == "file:/ingress/Movie"

    def test_makemkv_source_disc_job(self, sample_job):
        """Disc jobs return 'dev:<devpath>'."""
        job = sample_job
        assert job.makemkv_source == "dev:/dev/sr0"


class TestIsFolderImport:
    """Test job.is_folder_import property."""

    def test_is_folder_import_true(self, app_context):
        """Folder import jobs return True."""
        with unittest.mock.patch("arm.config.config.arm_config", {"VIDEOTYPE": "auto"}):
            job = Job.from_folder("/ingress/Movie", "bluray")

        assert job.is_folder_import is True

    def test_is_folder_import_false_for_disc(self, sample_job):
        """Disc jobs return False."""
        assert sample_job.is_folder_import is False
