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

    def test_skipped_track_not_matched_to_claimed_file(self):
        """A skipped track whose original filename collides with a file
        claimed by another track via title_map should NOT be matched."""
        from unittest.mock import patch
        from arm.ripper.makemkv import _reconcile_filenames

        job = MagicMock()
        # Prescan: track 3 (skipped, 22s) and tracks 4,5 (episodes)
        # MakeMKV output: _t00.mkv (=title 4), _t01.mkv (=title 5)
        track3 = MagicMock(track_number="3", filename="Show_t03.mkv", track_id=103)
        track4 = MagicMock(track_number="4", filename="Show_t04.mkv", track_id=104)
        track5 = MagicMock(track_number="5", filename="Show_t05.mkv", track_id=105)
        all_tracks = [track3, track4, track5]
        job.tracks.filter_by.return_value.order_by.return_value = all_tracks

        import tempfile
        with tempfile.TemporaryDirectory() as rawpath:
            Path(rawpath, "Show_t00.mkv").touch()
            Path(rawpath, "Show_t01.mkv").touch()

            # title_map: output 0 (_t00) -> title 4, output 1 (_t01) -> title 5
            title_map = {0: 4, 1: 5}

            with patch("arm.ripper.makemkv.db"):
                _reconcile_filenames(job, rawpath, title_map=title_map)

            # Track 4 mapped to _t00.mkv, track 5 mapped to _t01.mkv
            assert track4.filename == "Show_t00.mkv"
            assert track5.filename == "Show_t01.mkv"
            # Track 3 was skipped - its original filename Show_t03.mkv
            # doesn't exist on disk, so it won't match in Pass 1 either
            assert track3.filename == "Show_t03.mkv"  # unchanged

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


class TestBuildTitleMapFromTracks:
    """Test _build_title_map_from_tracks which uses prescan track data
    and output file count to build the deterministic mapping."""

    def test_skipped_short_track_default_threshold(self, tmp_path):
        """Tracks below MakeMKV's default 120s threshold are skipped.
        The Kolchak disc 4 scenario: tracks 3 (22s) and 6 (49s) are
        below 120s, so 5 episode tracks map to 5 output files."""
        from arm.ripper.folder_ripper import _build_title_map_from_tracks

        rawpath = tmp_path / "raw"
        rawpath.mkdir()
        for i in range(5):
            (rawpath / f"Show_t0{i}.mkv").write_bytes(b"x")

        job = MagicMock()
        tracks = []
        for tn, length in [(0, 3012), (1, 3012), (2, 3015), (3, 22), (4, 3017), (5, 3011), (6, 49)]:
            t = MagicMock()
            t.track_number = str(tn)
            t.length = length
            tracks.append(t)
        job.tracks = tracks

        title_map = _build_title_map_from_tracks(job, str(rawpath))
        # Default 120s threshold: tracks 0,1,2,4,5 qualify (>=120s)
        assert title_map == {0: 0, 1: 1, 2: 2, 3: 4, 4: 5}

    def test_fallback_threshold_search(self, tmp_path):
        """When default threshold doesn't match, searches for the right one."""
        from arm.ripper.folder_ripper import _build_title_map_from_tracks

        rawpath = tmp_path / "raw"
        rawpath.mkdir()
        for i in range(3):
            (rawpath / f"Show_t0{i}.mkv").write_bytes(b"x")

        job = MagicMock()
        # 5 tracks: 3 long + 2 medium (above 120s but MakeMKV still skipped them)
        tracks = []
        for tn, length in [(0, 3012), (1, 200), (2, 3015), (3, 150), (4, 3017)]:
            t = MagicMock()
            t.track_number = str(tn)
            t.length = length
            tracks.append(t)
        job.tracks = tracks

        title_map = _build_title_map_from_tracks(job, str(rawpath))
        # Default 120s gives 5 qualifying (all >= 120) != 3 output
        # Fallback search finds threshold >=200: tracks 0,2,4 = 3 files
        assert title_map == {0: 0, 1: 2, 2: 4}

    def test_no_skip_identity_map(self, tmp_path):
        """When all tracks qualify, mapping is identity."""
        from arm.ripper.folder_ripper import _build_title_map_from_tracks

        rawpath = tmp_path / "raw"
        rawpath.mkdir()
        for i in range(3):
            (rawpath / f"Movie_t0{i}.mkv").write_bytes(b"x")

        job = MagicMock()
        tracks = []
        for tn in range(3):
            t = MagicMock()
            t.track_number = str(tn)
            t.length = 3000
            tracks.append(t)
        job.tracks = tracks

        title_map = _build_title_map_from_tracks(job, str(rawpath))
        assert title_map == {0: 0, 1: 1, 2: 2}

    def test_empty_rawpath(self):
        """Empty or missing rawpath returns empty map."""
        from arm.ripper.folder_ripper import _build_title_map_from_tracks
        job = MagicMock()
        job.tracks = []
        assert _build_title_map_from_tracks(job, "") == {}
        assert _build_title_map_from_tracks(job, "/nonexistent") == {}

    def test_count_mismatch_returns_empty(self, tmp_path):
        """When output count doesn't match qualifying tracks, returns empty."""
        from arm.ripper.folder_ripper import _build_title_map_from_tracks

        rawpath = tmp_path / "raw"
        rawpath.mkdir()
        # 3 output files but 4 qualifying tracks
        for i in range(3):
            (rawpath / f"Show_t0{i}.mkv").write_bytes(b"x")

        job = MagicMock()
        tracks = []
        for tn in range(4):
            t = MagicMock()
            t.track_number = str(tn)
            t.length = 3000
            tracks.append(t)
        job.tracks = tracks

        title_map = _build_title_map_from_tracks(job, str(rawpath))
        assert title_map == {}


class TestFolderRipperTitleMap:
    """Test that folder_ripper builds title_map and passes to reconcile."""

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
        job.config.LOGPATH = str(tmp_path / "logs")
        job.build_raw_path.return_value = str(tmp_path / "raw" / "Test Show")
        job.raw_path = None
        job.errors = None
        job.tracks = []
        return job

    def test_title_map_passed_to_reconcile(self, tmp_path):
        """folder_ripper builds title_map from prescan tracks and passes
        it to _reconcile_filenames."""
        from unittest.mock import patch

        rawpath = tmp_path / "raw" / "Test Show"
        rawpath.mkdir(parents=True)
        # 2 output files
        (rawpath / "Show_t00.mkv").write_bytes(b"x")
        (rawpath / "Show_t01.mkv").write_bytes(b"x")

        job = self._make_job(tmp_path)
        # 3 prescan tracks: 2 episodes + 1 very short
        t0 = MagicMock(track_number="0", length=3000, filename="Show_t00.mkv", ripped=False)
        t1 = MagicMock(track_number="1", length=5, filename="Show_t01.mkv", ripped=False)  # below threshold
        t2 = MagicMock(track_number="2", length=3000, filename="Show_t02.mkv", ripped=False)
        job.tracks = [t0, t1, t2]

        with patch("arm.ripper.makemkv.run", return_value=iter([])), \
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

        m_reconcile.assert_called_once()
        call_args = m_reconcile.call_args
        assert "title_map" in call_args.kwargs
        tm = call_args.kwargs["title_map"]
        # 2 output files, 2 qualifying tracks (0, 2) -> map {0: 0, 1: 2}
        assert tm == {0: 0, 1: 2}, f"Expected {{0: 0, 1: 2}}, got {tm}"
