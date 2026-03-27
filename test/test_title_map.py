"""Tests for deterministic title-to-file mapping from MakeMKV PRGC messages.

When MakeMKV rips in "all" mode, it may skip short titles and renumber
output files sequentially. PRGC messages emitted during the rip contain
the output filename stem which includes the original title number.
By parsing these, we build a deterministic map from original title_id
to sequential output file, eliminating the need for heuristic matching.
"""

import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest


class TestBuildTitleMap:
    """Test build_title_map() which extracts title_id -> output_filename
    from PRGC messages during MakeMKV rip."""

    def test_basic_mapping(self):
        """PRGC messages map sequential output_id to original title via _tNN suffix."""
        from arm.ripper.makemkv import build_title_map, ProgressBarCurrent

        # Simulate PRGC messages for a disc with 16 titles, 5 ripped
        # MakeMKV skips short titles and outputs t00-t04 sequentially
        # but the PRGC name field contains the ORIGINAL title number
        prgc_messages = [
            ProgressBarCurrent(code=0, oid=0, name="Kolchak_The_Night_Stalker_Disc_4_t00"),
            ProgressBarCurrent(code=0, oid=1, name="Kolchak_The_Night_Stalker_Disc_4_t01"),
            ProgressBarCurrent(code=0, oid=2, name="Kolchak_The_Night_Stalker_Disc_4_t02"),
            ProgressBarCurrent(code=0, oid=3, name="Kolchak_The_Night_Stalker_Disc_4_t04"),  # skipped t03
            ProgressBarCurrent(code=0, oid=4, name="Kolchak_The_Night_Stalker_Disc_4_t05"),
        ]

        title_map = build_title_map(prgc_messages, "Kolchak The Night Stalker Disc 4")
        # output_index 0 -> original title 0 -> output file _t00.mkv
        # output_index 3 -> original title 4 -> output file _t03.mkv (renumbered!)
        assert title_map[0] == 0   # oid 0 -> original title 0
        assert title_map[1] == 1   # oid 1 -> original title 1
        assert title_map[2] == 2   # oid 2 -> original title 2
        assert title_map[3] == 4   # oid 3 -> original title 4 (t03 was skipped)
        assert title_map[4] == 5   # oid 4 -> original title 5

    def test_no_skip(self):
        """When no titles are skipped, mapping is identity."""
        from arm.ripper.makemkv import build_title_map, ProgressBarCurrent

        prgc_messages = [
            ProgressBarCurrent(code=0, oid=0, name="Movie_t00"),
            ProgressBarCurrent(code=0, oid=1, name="Movie_t01"),
            ProgressBarCurrent(code=0, oid=2, name="Movie_t02"),
        ]

        title_map = build_title_map(prgc_messages, "Movie")
        assert title_map == {0: 0, 1: 1, 2: 2}

    def test_empty_messages(self):
        """No PRGC messages produces empty map."""
        from arm.ripper.makemkv import build_title_map

        title_map = build_title_map([], "Movie")
        assert title_map == {}

    def test_duplicate_prgc_for_same_output(self):
        """MakeMKV may emit multiple PRGC for the same output_id (progress updates).
        Only the first occurrence should be used."""
        from arm.ripper.makemkv import build_title_map, ProgressBarCurrent

        prgc_messages = [
            ProgressBarCurrent(code=0, oid=0, name="Movie_t00"),
            ProgressBarCurrent(code=0, oid=0, name="Movie_t00"),  # duplicate
            ProgressBarCurrent(code=0, oid=1, name="Movie_t02"),  # skipped t01
            ProgressBarCurrent(code=0, oid=1, name="Movie_t02"),  # duplicate
        ]

        title_map = build_title_map(prgc_messages, "Movie")
        assert title_map == {0: 0, 1: 2}


class TestReconcileWithTitleMap:
    """Test that _reconcile_filenames uses the title map when provided."""

    def test_reconcile_uses_title_map_over_pattern(self):
        """When a title_map is provided, it overrides _tNN pattern matching."""
        from unittest.mock import patch
        from arm.ripper.makemkv import _reconcile_filenames

        job = MagicMock()
        track0 = MagicMock(track_number="0", filename="Show_t00.mkv", track_id=100)
        track1 = MagicMock(track_number="1", filename="Show_t01.mkv", track_id=101)
        track2 = MagicMock(track_number="2", filename="Show_t02.mkv", track_id=102)
        track3 = MagicMock(track_number="3", filename="Show_t03.mkv", track_id=103)
        track4 = MagicMock(track_number="4", filename="Show_t04.mkv", track_id=104)
        track5 = MagicMock(track_number="5", filename="Show_t05.mkv", track_id=105)
        all_tracks = [track0, track1, track2, track3, track4, track5]
        job.tracks.filter_by.return_value.order_by.return_value = all_tracks

        # Actual files on disk: MakeMKV produced t00-t04 (skipped original title 3)
        import tempfile
        with tempfile.TemporaryDirectory() as rawpath:
            for i in range(5):
                Path(rawpath, f"Show_t0{i}.mkv").touch()

            # title_map: output_index -> original_title_id
            # output t03 is actually original title 4, output t04 is original title 5
            title_map = {0: 0, 1: 1, 2: 2, 3: 4, 4: 5}

            with patch("arm.ripper.makemkv.db"):
                _reconcile_filenames(job, rawpath, title_map=title_map)

            # Track 0-2: files match directly (no renumbering for these)
            assert track0.filename == "Show_t00.mkv"
            assert track1.filename == "Show_t01.mkv"
            assert track2.filename == "Show_t02.mkv"
            # Track 3 (22s extra): was skipped by MakeMKV, no file
            # Track 4: should be mapped to output file Show_t03.mkv (output index 3)
            assert track4.filename == "Show_t03.mkv", \
                f"Track 4 should map to Show_t03.mkv via title_map, got {track4.filename}"
            # Track 5: should be mapped to output file Show_t04.mkv (output index 4)
            assert track5.filename == "Show_t04.mkv", \
                f"Track 5 should map to Show_t04.mkv via title_map, got {track5.filename}"

    def test_reconcile_without_title_map_unchanged(self):
        """Without title_map, existing pattern matching still works (backwards compat)."""
        from arm.ripper.makemkv import _reconcile_filenames

        job = MagicMock()
        track0 = MagicMock(track_number="0", filename="Movie_t00.mkv", track_id=200)
        track1 = MagicMock(track_number="1", filename="Movie_t01.mkv", track_id=201)
        all_tracks = [track0, track1]
        job.tracks.filter_by.return_value.order_by.return_value = all_tracks

        import tempfile
        with tempfile.TemporaryDirectory() as rawpath:
            Path(rawpath, "Movie_t00.mkv").touch()
            Path(rawpath, "Movie_t01.mkv").touch()

            # No title_map - falls back to existing matching
            _reconcile_filenames(job, rawpath)

            assert track0.filename == "Movie_t00.mkv"
            assert track1.filename == "Movie_t01.mkv"


class TestFolderRipperTitleMap:
    """Test that folder_ripper.py collects PRGC messages and passes title_map."""

    @pytest.fixture(autouse=True)
    def _mock_logging(self):
        """Mock create_file_handler so tests don't need a real LOGPATH."""
        import logging
        from unittest.mock import patch
        handler = logging.Handler()
        handler.emit = MagicMock()
        with patch("arm.ripper.folder_ripper.create_file_handler", return_value=handler):
            yield
            logging.getLogger().removeHandler(handler)

    def _make_job(self, tmp_path):
        source = tmp_path / "disc"
        source.mkdir()
        (source / "BDMV").mkdir()

        job = MagicMock()
        job.job_id = 1
        job.source_path = str(source)
        job.title = "Test Show"
        job.makemkv_source = f"file:{source}"
        job.config.MAINFEATURE = 0
        job.config.MKV_ARGS = ""
        job.config.MINLENGTH = "600"
        job.build_raw_path.return_value = str(tmp_path / "raw" / "Test Show")
        job.raw_path = None
        job.errors = None
        job.tracks = []
        return job

    def test_prgc_messages_collected_and_passed_to_reconcile(self, tmp_path):
        """folder_ripper should request PRGC messages from run() and pass
        the resulting title_map to _reconcile_filenames."""
        from unittest.mock import patch, call
        from arm.ripper.makemkv import ProgressBarCurrent, OutputType

        rawpath = tmp_path / "raw" / "Test Show"
        rawpath.mkdir(parents=True)

        job = self._make_job(tmp_path)

        # Mock run() to yield PRGC messages
        prgc0 = ProgressBarCurrent(code=0, oid=0, name="Test_Show_t00")
        prgc1 = ProgressBarCurrent(code=0, oid=1, name="Test_Show_t02")  # skipped t01

        def mock_run(cmd, select):
            # Should be called with MSG | PRGC
            assert OutputType.PRGC in select, "folder_ripper must request PRGC messages"
            yield prgc0
            yield prgc1

        with patch("arm.ripper.makemkv.run", side_effect=mock_run), \
             patch("arm.ripper.folder_ripper.setup_rawpath", return_value=str(rawpath)), \
             patch("arm.ripper.folder_ripper.prep_mkv"), \
             patch("arm.ripper.folder_ripper.prescan_track_info"), \
             patch("arm.ripper.folder_ripper._reconcile_filenames") as m_reconcile, \
             patch("arm.ripper.folder_ripper.utils.transcoder_notify"), \
             patch("arm.ripper.folder_ripper.db"), \
             patch("arm.ripper.folder_ripper.cfg") as mock_cfg:
            mock_cfg.arm_config = {"TRANSCODER_URL": ""}
            from arm.ripper.folder_ripper import rip_folder
            rip_folder(job)

        # _reconcile_filenames should be called with title_map keyword
        m_reconcile.assert_called_once()
        call_args = m_reconcile.call_args
        assert "title_map" in call_args.kwargs, \
            "_reconcile_filenames must receive title_map keyword argument"
        tm = call_args.kwargs["title_map"]
        assert tm == {0: 0, 1: 2}, \
            f"title_map should map output 0->title 0, output 1->title 2, got {tm}"
