"""Tests for folder ripper pipeline."""
import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch

# Secure temp dir used only as a mock return value for setup_rawpath; nothing
# is written here (db and filesystem ops are mocked in these tests).
_RAW_DIR = tempfile.mkdtemp(prefix="arm_test_raw_")


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
    @patch("arm.ripper.folder_ripper._reconcile_filenames")
    @patch("arm.ripper.makemkv.run")
    @patch("arm.ripper.folder_ripper.prescan_track_info")
    @patch("arm.ripper.folder_ripper.prep_mkv")
    def test_happy_path_all_mode(
        self, mock_prep, mock_prescan, mock_run,
        mock_reconcile, mock_db, tmp_path
    ):
        """Post-rip handoff is called after rip completes."""
        from arm.ripper.folder_ripper import rip_folder

        rawpath = tmp_path / "raw" / "Test Movie"
        rawpath.mkdir(parents=True)

        job = self._make_job(tmp_path)
        mock_run.return_value = iter([])  # MakeMKV yields nothing on success

        with patch("arm.ripper.folder_ripper.setup_rawpath", return_value=str(rawpath)), \
             patch("arm.ripper.folder_ripper.cfg") as mock_cfg, \
             patch("arm.ripper.arm_ripper._post_rip_handoff") as mock_handoff:
            mock_cfg.arm_config = {"TRANSCODER_URL": ""}
            rip_folder(job)

        mock_prep.assert_called_once()
        mock_prescan.assert_called_once_with(job)
        mock_reconcile.assert_called_once()
        args, kwargs = mock_reconcile.call_args
        assert args[0] is job
        assert args[1] == str(rawpath)
        assert "title_map" in kwargs
        mock_handoff.assert_called_once_with(job)

    @patch("arm.ripper.folder_ripper.db")
    @patch("arm.ripper.folder_ripper._reconcile_filenames")
    @patch("arm.ripper.makemkv.run")
    @patch("arm.ripper.folder_ripper.prescan_track_info")
    @patch("arm.ripper.folder_ripper.prep_mkv")
    def test_happy_path_with_transcoder_notify(
        self, mock_prep, mock_prescan, mock_run,
        mock_reconcile, mock_db, tmp_path
    ):
        from arm.ripper.folder_ripper import rip_folder

        rawpath = tmp_path / "raw" / "Test Movie"
        rawpath.mkdir(parents=True)

        job = self._make_job(tmp_path)
        mock_run.return_value = iter([])

        with patch("arm.ripper.folder_ripper.setup_rawpath", return_value=str(rawpath)), \
             patch("arm.ripper.folder_ripper.cfg") as mock_cfg, \
             patch("arm.ripper.arm_ripper._post_rip_handoff") as mock_handoff:
            mock_cfg.arm_config = {"TRANSCODER_URL": "http://transcoder:8080"}
            rip_folder(job)

        mock_handoff.assert_called_once_with(job)

    @patch("arm.ripper.folder_ripper.db")
    @patch("arm.ripper.folder_ripper._reconcile_filenames")
    @patch("arm.ripper.makemkv.run")
    @patch("arm.ripper.folder_ripper.prescan_track_info")
    @patch("arm.ripper.folder_ripper.prep_mkv")
    def test_tracks_marked_ripped_only_if_file_exists(
        self, mock_prep, mock_prescan, mock_run,
        mock_reconcile, mock_db, tmp_path
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
        track0 = MagicMock(track_number="0", filename="movie_t00.mkv", ripped=False, length=3000)
        track1 = MagicMock(track_number="1", filename="movie_t01.mkv", ripped=False, length=3000)
        track2 = MagicMock(track_number="2", filename="movie_t02.mkv", ripped=False, length=3000)
        job.tracks = [track0, track1, track2]
        mock_run.return_value = iter([])

        with patch("arm.ripper.folder_ripper.cfg") as mock_cfg, mock_setup, \
             patch("arm.ripper.arm_ripper._post_rip_handoff"):
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
    @patch("arm.ripper.folder_ripper.setup_rawpath",
           return_value=os.path.join(_RAW_DIR, "Test Movie"))
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
    @patch("arm.ripper.folder_ripper.setup_rawpath",
           return_value=os.path.join(_RAW_DIR, "Test"))
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
    @patch("arm.ripper.folder_ripper.setup_rawpath",
           return_value=os.path.join(_RAW_DIR, "Test"))
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

    @patch("arm.ripper.folder_ripper.db")
    @patch("arm.ripper.folder_ripper._reconcile_filenames")
    @patch("arm.ripper.makemkv.run")
    @patch("arm.ripper.folder_ripper.prescan_track_info")
    @patch("arm.ripper.folder_ripper.prep_mkv")
    def test_orchestration_call_sequence(
        self, mock_prep, mock_prescan, mock_run,
        mock_reconcile, mock_db, tmp_path
    ):
        """Characterization test: lock the rip_folder orchestration call order.

        Records the ordering of the post-Job-creation orchestration helpers so a
        future refactor that extracts kick_off_import_rip(job) cannot accidentally
        reorder calls. Order under test: prep_mkv -> setup_rawpath -> prescan_track_info
        -> makemkv run -> _reconcile_filenames -> _post_rip_handoff.
        """
        from arm.ripper.folder_ripper import rip_folder

        rawpath = tmp_path / "raw" / "Test Movie"
        rawpath.mkdir(parents=True)

        job = self._make_job(tmp_path)
        mock_run.return_value = iter([])

        calls = []
        mock_prep.side_effect = lambda *a, **kw: calls.append("prep_mkv")
        mock_prescan.side_effect = lambda *a, **kw: calls.append("prescan")
        mock_run.side_effect = lambda *a, **kw: (calls.append("makemkv_run"), iter([]))[1]
        mock_reconcile.side_effect = lambda *a, **kw: calls.append("reconcile")

        def fake_setup(path):
            calls.append("setup_rawpath")
            return str(rawpath)

        def fake_handoff(j):
            calls.append("post_rip_handoff")

        with patch("arm.ripper.folder_ripper.setup_rawpath", side_effect=fake_setup), \
             patch("arm.ripper.folder_ripper.cfg") as mock_cfg, \
             patch("arm.ripper.arm_ripper._post_rip_handoff", side_effect=fake_handoff):
            mock_cfg.arm_config = {"TRANSCODER_URL": ""}
            rip_folder(job)

        assert calls == [
            "prep_mkv",
            "setup_rawpath",
            "prescan",
            "makemkv_run",
            "reconcile",
            "post_rip_handoff",
        ]

    @patch("arm.ripper.folder_ripper.db")
    @patch("arm.ripper.folder_ripper._reconcile_filenames")
    @patch("arm.ripper.makemkv.run")
    @patch("arm.ripper.folder_ripper.prescan_track_info")
    @patch("arm.ripper.folder_ripper.prep_mkv")
    def test_deselected_track_files_are_removed(
        self, mock_prep, mock_prescan, mock_run,
        mock_reconcile, mock_db, tmp_path
    ):
        """Output files for tracks with process=False are deleted post-rip.

        MakeMKV's `all` mode rips every title above its minlength filter.
        The user (or auto-disable) may set process=False on tracks they
        don't want; without this filter those files would still rsync to
        media + reach the transcoder. Repro on hifi 17.6.0-rc job 200:
        user selected only track 0 in review; rip produced 28 mkv files.
        """
        from arm.ripper.folder_ripper import rip_folder

        rawpath = tmp_path / "raw" / "Test Movie"
        rawpath.mkdir(parents=True)
        kept = rawpath / "kept.mkv"
        dropped = rawpath / "dropped.mkv"
        kept.write_bytes(b"keep me")
        dropped.write_bytes(b"discard me")

        job = self._make_job(tmp_path)
        kept_track = MagicMock(track_number="0", filename="kept.mkv", process=True)
        dropped_track = MagicMock(track_number="1", filename="dropped.mkv", process=False)
        job.tracks = [kept_track, dropped_track]
        mock_run.return_value = iter([])

        with patch("arm.ripper.folder_ripper.setup_rawpath", return_value=str(rawpath)), \
             patch("arm.ripper.folder_ripper.cfg") as mock_cfg, \
             patch("arm.ripper.arm_ripper._post_rip_handoff"):
            mock_cfg.arm_config = {"TRANSCODER_URL": ""}
            rip_folder(job)

        assert kept.exists(), "kept track file should not be deleted"
        assert not dropped.exists(), "deselected track file should be removed"

    @patch("arm.ripper.folder_ripper.db")
    @patch("arm.ripper.folder_ripper._reconcile_filenames")
    @patch("arm.ripper.makemkv.run")
    @patch("arm.ripper.folder_ripper.prescan_track_info")
    @patch("arm.ripper.folder_ripper.prep_mkv")
    def test_deselected_filename_collision_with_kept_track(
        self, mock_prep, mock_prescan, mock_run,
        mock_reconcile, mock_db, tmp_path
    ):
        """Deselect-delete must skip filenames that a kept track now claims.

        Repro on hifi 18.1.0-rc job 220 ("Annihilation" 4K BD import):
        prescan seeded 70 tracks with sequential filenames _t00..._t69.
        Auto-disable flipped 68 short tracks to process=False (including
        track #0 with stale filename 'Annihilation_t00.mkv'). MakeMKV's
        'all' rip produced 2 output files which got renamed by
        reconciliation (kept track #3 -> '_t00.mkv'). The deselect-delete
        loop then deleted '_t00.mkv' off disk because deselected track #0
        still pointed at that filename - destroying the kept rip output
        and 413-ing the transcoder handoff.
        """
        from arm.ripper.folder_ripper import rip_folder

        rawpath = tmp_path / "raw" / "Test Movie"
        rawpath.mkdir(parents=True)
        # Only the renamed kept-track file exists on disk after MakeMKV +
        # reconciliation. The deselected track row's stale filename
        # collides with this exact path.
        kept_after_rename = rawpath / "Annihilation_t00.mkv"
        kept_after_rename.write_bytes(b"the actual rip output")

        job = self._make_job(tmp_path)
        # Kept track was renamed by reconciliation: '_t03.mkv' -> '_t00.mkv'.
        kept_track = MagicMock(
            track_number="3", filename="Annihilation_t00.mkv",
            process=True, length=8000,
        )
        # Deselected track still has its prescan filename, which now
        # collides with the kept track's renamed filename.
        deselected_with_collision = MagicMock(
            track_number="0", filename="Annihilation_t00.mkv",
            process=False, length=7,
        )
        job.tracks = [kept_track, deselected_with_collision]
        mock_run.return_value = iter([])

        with patch("arm.ripper.folder_ripper.setup_rawpath", return_value=str(rawpath)), \
             patch("arm.ripper.folder_ripper.cfg") as mock_cfg, \
             patch("arm.ripper.arm_ripper._post_rip_handoff"):
            mock_cfg.arm_config = {"TRANSCODER_URL": ""}
            rip_folder(job)

        assert kept_after_rename.exists(), (
            "kept track's renamed output must NOT be deleted by the "
            "deselect-delete loop just because a deselected track row "
            "still points at the same filename"
        )
