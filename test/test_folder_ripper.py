"""Tests for folder ripper pipeline."""
import os
import pytest
from unittest.mock import MagicMock, patch


class TestRipFolder:
    """Test rip_folder happy path and error paths."""

    def _make_job(self, tmp_path):
        """Create a mock job with required attributes."""
        source = tmp_path / "disc"
        source.mkdir()
        (source / "BDMV").mkdir()

        job = MagicMock()
        job.job_id = 1
        job.source_path = str(source)
        job.title = "Test Movie"
        job.config.MAINFEATURE = 0
        job.build_raw_path.return_value = str(tmp_path / "raw" / "Test Movie")
        job.raw_path = None
        job.errors = None
        return job

    @patch("arm.ripper.folder_ripper.db")
    @patch("arm.ripper.folder_ripper.utils.transcoder_notify")
    @patch("arm.ripper.folder_ripper._reconcile_filenames")
    @patch("arm.ripper.folder_ripper.process_single_tracks")
    @patch("arm.ripper.folder_ripper.prescan_track_info")
    @patch("arm.ripper.folder_ripper.setup_rawpath", return_value="/tmp/raw/Test Movie")
    @patch("arm.ripper.folder_ripper.prep_mkv")
    def test_happy_path_single_tracks(
        self, mock_prep, mock_setup, mock_prescan, mock_process,
        mock_reconcile, mock_notify, mock_db, tmp_path
    ):
        from arm.ripper.folder_ripper import rip_folder

        job = self._make_job(tmp_path)

        with patch("arm.ripper.folder_ripper.cfg") as mock_cfg:
            mock_cfg.arm_config = {"TRANSCODER_URL": ""}
            rip_folder(job)

        mock_prep.assert_called_once()
        mock_setup.assert_called_once_with(job, job.build_raw_path())
        mock_prescan.assert_called_once_with(job)
        mock_process.assert_called_once_with(job, "/tmp/raw/Test Movie", "auto")
        mock_reconcile.assert_called_once_with(job, "/tmp/raw/Test Movie")
        mock_notify.assert_not_called()
        assert job.status == "waiting_transcode"

    @patch("arm.ripper.folder_ripper.db")
    @patch("arm.ripper.folder_ripper.utils.transcoder_notify")
    @patch("arm.ripper.folder_ripper._reconcile_filenames")
    @patch("arm.ripper.folder_ripper.process_single_tracks")
    @patch("arm.ripper.folder_ripper.prescan_track_info")
    @patch("arm.ripper.folder_ripper.setup_rawpath", return_value="/tmp/raw/Test Movie")
    @patch("arm.ripper.folder_ripper.prep_mkv")
    def test_happy_path_with_transcoder_notify(
        self, mock_prep, mock_setup, mock_prescan, mock_process,
        mock_reconcile, mock_notify, mock_db, tmp_path
    ):
        from arm.ripper.folder_ripper import rip_folder

        job = self._make_job(tmp_path)

        with patch("arm.ripper.folder_ripper.cfg") as mock_cfg:
            mock_cfg.arm_config = {"TRANSCODER_URL": "http://transcoder:8080"}
            rip_folder(job)

        mock_notify.assert_called_once()
        assert job.status == "waiting_transcode"

    @patch("arm.ripper.folder_ripper.db")
    @patch("arm.ripper.folder_ripper.utils.transcoder_notify")
    @patch("arm.ripper.folder_ripper._reconcile_filenames")
    @patch("arm.ripper.folder_ripper.rip_mainfeature")
    @patch("arm.ripper.folder_ripper.prescan_track_info")
    @patch("arm.ripper.folder_ripper.setup_rawpath", return_value="/tmp/raw/Test Movie")
    @patch("arm.ripper.folder_ripper.prep_mkv")
    def test_mainfeature_rip(
        self, mock_prep, mock_setup, mock_prescan, mock_mainfeature,
        mock_reconcile, mock_notify, mock_db, tmp_path
    ):
        from arm.ripper.folder_ripper import rip_folder

        job = self._make_job(tmp_path)
        job.config.MAINFEATURE = 1

        mock_best_track = MagicMock()
        mock_best_track.track_number = 0

        mock_track_cls = MagicMock()
        mock_track_cls.query.filter_by.return_value.order_by.return_value.first.return_value = mock_best_track

        with patch("arm.ripper.folder_ripper.cfg") as mock_cfg, \
             patch("arm.ripper.folder_ripper.Track", mock_track_cls):
            mock_cfg.arm_config = {"TRANSCODER_URL": ""}
            rip_folder(job)

        mock_mainfeature.assert_called_once_with(job, mock_best_track, "/tmp/raw/Test Movie")
        assert job.status == "waiting_transcode"

    @patch("arm.ripper.folder_ripper.db")
    def test_missing_source_folder(self, mock_db):
        from arm.ripper.folder_ripper import rip_folder

        job = MagicMock()
        job.job_id = 1
        job.source_path = "/nonexistent/path"
        job.errors = None

        with pytest.raises(FileNotFoundError):
            rip_folder(job)

        assert job.status == "fail"

    @patch("arm.ripper.folder_ripper.db")
    def test_invalid_disc_structure(self, mock_db, tmp_path):
        from arm.ripper.folder_ripper import rip_folder

        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        job = MagicMock()
        job.job_id = 2
        job.source_path = str(empty_dir)
        job.errors = None

        with pytest.raises(ValueError, match="No disc structure"):
            rip_folder(job)

        assert job.status == "fail"

    @patch("arm.ripper.folder_ripper.db")
    @patch("arm.ripper.folder_ripper.prescan_track_info", side_effect=RuntimeError("MakeMKV failed"))
    @patch("arm.ripper.folder_ripper.setup_rawpath", return_value="/tmp/raw/Test Movie")
    @patch("arm.ripper.folder_ripper.prep_mkv")
    def test_rip_error_sets_failure(
        self, mock_prep, mock_setup, mock_prescan, mock_db, tmp_path
    ):
        from arm.ripper.folder_ripper import rip_folder

        job = self._make_job(tmp_path)

        with patch("arm.ripper.folder_ripper.cfg") as mock_cfg:
            mock_cfg.arm_config = {"TRANSCODER_URL": ""}
            with pytest.raises(RuntimeError, match="MakeMKV failed"):
                rip_folder(job)

        assert job.status == "fail"
        assert "MakeMKV failed" in str(job.errors)
