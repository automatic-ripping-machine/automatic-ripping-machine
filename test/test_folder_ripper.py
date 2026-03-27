"""Tests for folder ripper pipeline."""
import os
import pytest
from unittest.mock import MagicMock, patch


class TestRipFolder:
    """Test rip_folder happy path and error paths."""

    @pytest.fixture(autouse=True)
    def _mock_logging(self):
        """Mock create_file_handler so tests don't need a real LOGPATH."""
        import logging
        handler = logging.Handler()
        handler.emit = MagicMock()
        with patch("arm.ripper.folder_ripper.create_file_handler", return_value=handler):
            yield
            # Clean up handler from root logger
            logging.getLogger().removeHandler(handler)

    def _make_job(self, tmp_path):
        """Create a mock job with required attributes."""
        source = tmp_path / "disc"
        source.mkdir()
        (source / "BDMV").mkdir()

        job = MagicMock()
        job.job_id = 1
        job.source_path = str(source)
        job.title = "Test Movie"
        job.makemkv_source = f"file:{source}"
        job.config.MAINFEATURE = 0
        job.config.MKV_ARGS = ""
        job.config.MINLENGTH = "600"
        job.build_raw_path.return_value = str(tmp_path / "raw" / "Test Movie")
        job.raw_path = None
        job.errors = None
        job.tracks = []
        return job

    @patch("arm.ripper.folder_ripper.db")
    @patch("arm.ripper.folder_ripper.utils.transcoder_notify")
    @patch("arm.ripper.folder_ripper._reconcile_filenames")
    @patch("arm.ripper.makemkv.run")
    @patch("arm.ripper.folder_ripper.prescan_track_info")
    @patch("arm.ripper.folder_ripper.prep_mkv")
    def test_happy_path_all_mode(
        self, mock_prep, mock_prescan, mock_run,
        mock_reconcile, mock_notify, mock_db, tmp_path
    ):
        from arm.ripper.folder_ripper import rip_folder

        rawpath = tmp_path / "raw" / "Test Movie"
        rawpath.mkdir(parents=True)

        job = self._make_job(tmp_path)
        mock_run.return_value = iter([])  # MakeMKV yields nothing on success

        with patch("arm.ripper.folder_ripper.setup_rawpath", return_value=str(rawpath)), \
             patch("arm.ripper.folder_ripper.cfg") as mock_cfg:
            mock_cfg.arm_config = {"TRANSCODER_URL": ""}
            rip_folder(job)

        mock_prep.assert_called_once()
        mock_prescan.assert_called_once_with(job)
        mock_reconcile.assert_called_once_with(job, str(rawpath))
        mock_notify.assert_not_called()
        assert job.status == "waiting_transcode"

    @patch("arm.ripper.folder_ripper.db")
    @patch("arm.ripper.folder_ripper.utils.transcoder_notify")
    @patch("arm.ripper.folder_ripper._reconcile_filenames")
    @patch("arm.ripper.makemkv.run")
    @patch("arm.ripper.folder_ripper.prescan_track_info")
    @patch("arm.ripper.folder_ripper.prep_mkv")
    def test_happy_path_with_transcoder_notify(
        self, mock_prep, mock_prescan, mock_run,
        mock_reconcile, mock_notify, mock_db, tmp_path
    ):
        from arm.ripper.folder_ripper import rip_folder

        rawpath = tmp_path / "raw" / "Test Movie"
        rawpath.mkdir(parents=True)

        job = self._make_job(tmp_path)
        mock_run.return_value = iter([])

        with patch("arm.ripper.folder_ripper.setup_rawpath", return_value=str(rawpath)), \
             patch("arm.ripper.folder_ripper.cfg") as mock_cfg:
            mock_cfg.arm_config = {"TRANSCODER_URL": "http://transcoder:8080"}
            rip_folder(job)

        mock_notify.assert_called_once()
        assert job.status == "waiting_transcode"

    @patch("arm.ripper.folder_ripper.db")
    @patch("arm.ripper.folder_ripper.utils.transcoder_notify")
    @patch("arm.ripper.folder_ripper._reconcile_filenames")
    @patch("arm.ripper.makemkv.run")
    @patch("arm.ripper.folder_ripper.prescan_track_info")
    @patch("arm.ripper.folder_ripper.prep_mkv")
    def test_tracks_marked_ripped_only_if_file_exists(
        self, mock_prep, mock_prescan, mock_run,
        mock_reconcile, mock_notify, mock_db, tmp_path
    ):
        """Only tracks whose filename exists on disk should be marked ripped."""
        from arm.ripper.folder_ripper import rip_folder

        # Create raw output dir with 2 of 3 track files
        rawpath = tmp_path / "raw" / "Test Movie"
        rawpath.mkdir(parents=True)
        (rawpath / "movie_t00.mkv").write_bytes(b"data")
        (rawpath / "movie_t01.mkv").write_bytes(b"data")
        # movie_t02.mkv intentionally missing (MakeMKV skipped it)

        mock_setup = patch(
            "arm.ripper.folder_ripper.setup_rawpath",
            return_value=str(rawpath),
        )

        job = self._make_job(tmp_path)
        track0 = MagicMock(filename="movie_t00.mkv", ripped=False)
        track1 = MagicMock(filename="movie_t01.mkv", ripped=False)
        track2 = MagicMock(filename="movie_t02.mkv", ripped=False)
        job.tracks = [track0, track1, track2]
        mock_run.return_value = iter([])

        with patch("arm.ripper.folder_ripper.cfg") as mock_cfg, mock_setup:
            mock_cfg.arm_config = {"TRANSCODER_URL": ""}
            rip_folder(job)

        assert track0.ripped is True
        assert track1.ripped is True
        assert track2.ripped is False, "Track without file on disk should not be marked ripped"

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

    @patch("arm.ripper.folder_ripper.db")
    def test_failure_status_update_exception(self, mock_db):
        """When both the rip AND the failure status update raise, the original
        exception is still re-raised."""
        from arm.ripper.folder_ripper import rip_folder

        job = MagicMock()
        job.job_id = 99
        job.source_path = "/nonexistent/path"
        job.errors = None

        # First commit (logfile save) succeeds, subsequent commits fail
        mock_db.session.commit.side_effect = [None, RuntimeError("DB is down")]

        with pytest.raises(FileNotFoundError):
            rip_folder(job)

    @patch("arm.ripper.folder_ripper.db")
    @patch("arm.ripper.folder_ripper.structlog")
    @patch("arm.ripper.folder_ripper.prescan_track_info", side_effect=RuntimeError("boom"))
    @patch("arm.ripper.folder_ripper.setup_rawpath", return_value="/tmp/raw/Test")
    @patch("arm.ripper.folder_ripper.prep_mkv")
    def test_clear_contextvars_called_on_failure(
        self, mock_prep, mock_setup, mock_prescan, mock_structlog, mock_db, tmp_path
    ):
        """structlog.contextvars.clear_contextvars() is called in the finally block even when rip fails."""
        from arm.ripper.folder_ripper import rip_folder

        job = self._make_job(tmp_path)

        with patch("arm.ripper.folder_ripper.cfg") as mock_cfg:
            mock_cfg.arm_config = {"TRANSCODER_URL": ""}
            with pytest.raises(RuntimeError, match="boom"):
                rip_folder(job)

        mock_structlog.contextvars.clear_contextvars.assert_called()

    @patch("arm.ripper.folder_ripper.db")
    @patch("arm.ripper.folder_ripper.prescan_track_info", side_effect=RuntimeError("boom"))
    @patch("arm.ripper.folder_ripper.setup_rawpath", return_value="/tmp/raw/Test")
    @patch("arm.ripper.folder_ripper.prep_mkv")
    def test_file_handler_removed_on_failure(
        self, mock_prep, mock_setup, mock_prescan, mock_db, tmp_path
    ):
        """File handler is removed from root logger on cleanup even when rip fails."""
        import logging
        from arm.ripper.folder_ripper import rip_folder

        job = self._make_job(tmp_path)
        root_logger = logging.getLogger()
        handlers_before = len(root_logger.handlers)

        with patch("arm.ripper.folder_ripper.cfg") as mock_cfg:
            mock_cfg.arm_config = {"TRANSCODER_URL": ""}
            with pytest.raises(RuntimeError, match="boom"):
                rip_folder(job)

        # The handler added during rip should be removed in the finally block
        assert len(root_logger.handlers) <= handlers_before
