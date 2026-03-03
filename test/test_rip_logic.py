"""Tests for ripping business logic (no hardware required)."""
import os
import subprocess
import unittest.mock

import pytest


class TestJobState:
    """Test JobState enum and status sets."""

    def test_success_value(self):
        from arm.models.job import JobState
        assert JobState.SUCCESS.value == "success"

    def test_failure_value(self):
        from arm.models.job import JobState
        assert JobState.FAILURE.value == "fail"

    def test_idle_value(self):
        from arm.models.job import JobState
        assert JobState.IDLE.value == "active"

    def test_ripping_value(self):
        from arm.models.job import JobState
        assert JobState.VIDEO_RIPPING.value == "ripping"

    def test_transcoding_value(self):
        from arm.models.job import JobState
        assert JobState.TRANSCODE_ACTIVE.value == "transcoding"

    def test_finished_set(self):
        from arm.models.job import JobState, JOB_STATUS_FINISHED
        assert JobState.SUCCESS in JOB_STATUS_FINISHED
        assert JobState.FAILURE in JOB_STATUS_FINISHED
        assert JobState.IDLE not in JOB_STATUS_FINISHED

    def test_ripping_set(self):
        from arm.models.job import JobState, JOB_STATUS_RIPPING
        assert JobState.VIDEO_RIPPING in JOB_STATUS_RIPPING
        assert JobState.AUDIO_RIPPING in JOB_STATUS_RIPPING
        assert JobState.IDLE not in JOB_STATUS_RIPPING

    def test_transcoding_set(self):
        from arm.models.job import JobState, JOB_STATUS_TRANSCODING
        assert JobState.TRANSCODE_ACTIVE in JOB_STATUS_TRANSCODING
        assert JobState.TRANSCODE_WAITING in JOB_STATUS_TRANSCODING
        assert JobState.IDLE not in JOB_STATUS_TRANSCODING


class TestRipData:
    """Test rip_data() data disc ripping logic."""

    def test_duplicate_label_gets_unique_filename(self, app_context, sample_job, tmp_path):
        """Second data disc with same label should NOT overwrite the first (#1651)."""
        from arm.ripper.utils import rip_data

        raw = tmp_path / "raw"
        completed = tmp_path / "completed"
        raw.mkdir()
        completed.mkdir()

        sample_job.disctype = "data"
        sample_job.label = "MYDATA"
        sample_job.video_type = "unknown"
        sample_job.config.RAW_PATH = str(raw)
        sample_job.config.COMPLETED_PATH = str(completed)

        # First rip: create the raw directory so the second call thinks it's a collision
        (raw / "MYDATA").mkdir()

        with unittest.mock.patch('arm.ripper.utils.subprocess.check_output') as mock_dd, \
             unittest.mock.patch('arm.ripper.utils.shutil.move') as mock_move:
            mock_dd.return_value = b""
            rip_data(sample_job)

            # shutil.move should have been called with a timestamped .iso filename
            assert mock_move.called, "shutil.move was never called"
            final_file = mock_move.call_args[0][1]  # full_final_file
            # The ISO filename should NOT be just "MYDATA.iso" — it should have a suffix
            assert os.path.basename(final_file) != "MYDATA.iso"

    def test_unique_label_uses_plain_filename(self, app_context, sample_job, tmp_path):
        """Data disc with unique label uses plain label as filename."""
        from arm.ripper.utils import rip_data

        raw = tmp_path / "raw"
        completed = tmp_path / "completed"
        raw.mkdir()
        completed.mkdir()

        sample_job.disctype = "data"
        sample_job.label = "UNIQUE_DISC"
        sample_job.video_type = "unknown"
        sample_job.config.RAW_PATH = str(raw)
        sample_job.config.COMPLETED_PATH = str(completed)

        with unittest.mock.patch('arm.ripper.utils.subprocess.check_output') as mock_dd, \
             unittest.mock.patch('arm.ripper.utils.shutil.move') as mock_move:
            mock_dd.return_value = b""
            rip_data(sample_job)

            assert mock_move.called, "shutil.move was never called"
            final_file = mock_move.call_args[0][1]
            assert final_file.endswith("UNIQUE_DISC.iso")

    def test_completed_iso_collision_gets_unique_suffix(self, app_context, sample_job, tmp_path):
        """When completed .iso already exists, use job_id suffix instead of skipping (#1651)."""
        from arm.ripper.utils import rip_data

        raw = tmp_path / "raw"
        completed = tmp_path / "completed"
        raw.mkdir()
        completed.mkdir()

        sample_job.disctype = "data"
        sample_job.label = "COLLISION"
        sample_job.video_type = "unknown"
        sample_job.config.RAW_PATH = str(raw)
        sample_job.config.COMPLETED_PATH = str(completed)

        # Pre-create the final directory and the .iso so it collides
        final_dir = completed / "unidentified" / "COLLISION"
        final_dir.mkdir(parents=True)
        (final_dir / "COLLISION.iso").write_bytes(b"existing")

        with unittest.mock.patch('arm.ripper.utils.subprocess.check_output') as mock_dd, \
             unittest.mock.patch('arm.ripper.utils.shutil.move') as mock_move:
            mock_dd.return_value = b""
            rip_data(sample_job)

            assert mock_move.called, "shutil.move was never called — file was silently skipped"
            final_file = mock_move.call_args[0][1]
            # Should contain the job_id suffix
            assert f"COLLISION_{sample_job.job_id}.iso" in final_file


class TestSaveDiscPoster:
    """Test save_disc_poster() mount/umount safety (#1664)."""

    def test_happy_path_ntsc_poster(self, app_context, sample_job, tmp_path):
        """DVD with NTSC poster should mount, convert, and umount."""
        from arm.ripper.utils import save_disc_poster

        sample_job.disctype = "dvd"
        sample_job.mountpoint = str(tmp_path / "mnt")
        os.makedirs(os.path.join(sample_job.mountpoint, "JACKET_P"))
        # Create a fake poster file
        ntsc = os.path.join(sample_job.mountpoint, "JACKET_P", "J00___5L.MP2")
        with open(ntsc, "w") as f:
            f.write("fake")

        final_dir = str(tmp_path / "output")
        os.makedirs(final_dir)

        ok_result = subprocess.CompletedProcess([], 0, "", "")

        with unittest.mock.patch('arm.ripper.utils.subprocess.run', return_value=ok_result) as mock_run, \
             unittest.mock.patch('arm.ripper.utils.cfg') as mock_cfg:
            mock_cfg.arm_config = {"RIP_POSTER": True}
            save_disc_poster(final_dir, sample_job)

        # mount, ffmpeg, umount = 3 calls
        assert mock_run.call_count == 3
        # First call is mount
        assert mock_run.call_args_list[0][0][0][0] == "mount"
        # Second call is ffmpeg
        assert mock_run.call_args_list[1][0][0][0] == "ffmpeg"
        # Third call is umount
        assert mock_run.call_args_list[2][0][0][0] == "umount"

    def test_umount_always_called_even_if_ffmpeg_fails(self, app_context, sample_job, tmp_path):
        """Umount must run even when ffmpeg raises an exception (#1664)."""
        from arm.ripper.utils import save_disc_poster

        sample_job.disctype = "dvd"
        sample_job.mountpoint = str(tmp_path / "mnt")
        os.makedirs(os.path.join(sample_job.mountpoint, "JACKET_P"))
        ntsc = os.path.join(sample_job.mountpoint, "JACKET_P", "J00___5L.MP2")
        with open(ntsc, "w") as f:
            f.write("fake")

        final_dir = str(tmp_path / "output")
        os.makedirs(final_dir)

        ok_result = subprocess.CompletedProcess([], 0, "", "")

        def side_effect(cmd, **kwargs):
            if cmd[0] == "ffmpeg":
                raise OSError("ffmpeg crashed")
            return ok_result

        with unittest.mock.patch('arm.ripper.utils.subprocess.run', side_effect=side_effect) as mock_run, \
             unittest.mock.patch('arm.ripper.utils.cfg') as mock_cfg:
            mock_cfg.arm_config = {"RIP_POSTER": True}
            # ffmpeg raises, but umount should still be called
            with pytest.raises(OSError, match="ffmpeg crashed"):
                save_disc_poster(final_dir, sample_job)

        # mount was called, ffmpeg raised, umount was still called = 3 calls
        call_cmds = [c[0][0][0] for c in mock_run.call_args_list]
        assert "mount" in call_cmds
        assert "umount" in call_cmds

    def test_non_dvd_is_noop(self, app_context, sample_job):
        """Non-DVD disc should skip poster extraction entirely."""
        from arm.ripper.utils import save_disc_poster

        sample_job.disctype = "bluray"

        with unittest.mock.patch('arm.ripper.utils.subprocess.run') as mock_run, \
             unittest.mock.patch('arm.ripper.utils.cfg') as mock_cfg:
            mock_cfg.arm_config = {"RIP_POSTER": True}
            save_disc_poster("/tmp/output", sample_job)

        mock_run.assert_not_called()

    def test_rip_poster_disabled_is_noop(self, app_context, sample_job):
        """RIP_POSTER=False should skip poster extraction entirely."""
        from arm.ripper.utils import save_disc_poster

        sample_job.disctype = "dvd"

        with unittest.mock.patch('arm.ripper.utils.subprocess.run') as mock_run, \
             unittest.mock.patch('arm.ripper.utils.cfg') as mock_cfg:
            mock_cfg.arm_config = {"RIP_POSTER": False}
            save_disc_poster("/tmp/output", sample_job)

        mock_run.assert_not_called()


class TestRipMusic:
    """Test rip_music() audio CD ripping logic."""

    def test_abcde_error_in_log_detected(self, app_context, sample_job, tmp_path):
        """abcde exit 0 with [ERROR] in log should be treated as failure (#1526)."""
        from arm.ripper.utils import rip_music

        sample_job.disctype = "music"
        sample_job.config.LOGPATH = str(tmp_path)

        # Write a log file with abcde error markers
        logfile = "test_music.log"
        (tmp_path / logfile).write_text(
            "Grabbing track 01...\n"
            "[ERROR] cdparanoia could not read disc\n"
            "CDROM drive unavailable\n"
        )

        with unittest.mock.patch('arm.ripper.utils.subprocess.check_output', return_value=b""), \
             unittest.mock.patch('arm.ripper.utils.cfg') as mock_cfg:
            mock_cfg.arm_config = {"ABCDE_CONFIG_FILE": "/nonexistent"}
            result = rip_music(sample_job, logfile)

        assert result is False
        assert sample_job.status == "fail"

    def test_abcde_clean_log_succeeds(self, app_context, sample_job, tmp_path):
        """abcde exit 0 with clean log should be treated as success."""
        from arm.ripper.utils import rip_music

        sample_job.disctype = "music"
        sample_job.config.LOGPATH = str(tmp_path)

        logfile = "test_music.log"
        (tmp_path / logfile).write_text(
            "Grabbing track 01...\n"
            "Grabbing track 02...\n"
            "Finished.\n"
        )

        with unittest.mock.patch('arm.ripper.utils.subprocess.check_output', return_value=b""), \
             unittest.mock.patch('arm.ripper.utils.cfg') as mock_cfg:
            mock_cfg.arm_config = {"ABCDE_CONFIG_FILE": "/nonexistent"}
            result = rip_music(sample_job, logfile)

        assert result is True

    def test_abcde_nonzero_exit_detected(self, app_context, sample_job, tmp_path):
        """abcde with non-zero exit code should be caught."""
        import subprocess
        from arm.ripper.utils import rip_music

        sample_job.disctype = "music"
        sample_job.config.LOGPATH = str(tmp_path)

        with unittest.mock.patch('arm.ripper.utils.subprocess.check_output',
                                 side_effect=subprocess.CalledProcessError(1, "abcde", b"error")), \
             unittest.mock.patch('arm.ripper.utils.cfg') as mock_cfg:
            mock_cfg.arm_config = {"ABCDE_CONFIG_FILE": "/nonexistent"}
            result = rip_music(sample_job, "test.log")

        assert result is False


class TestMakemkvDiscDiscovery:
    """Test MakeMKV disc number discovery guard (#1545)."""

    def test_mdisc_none_no_drives_raises(self, app_context, sample_job):
        """When job.drive is None and get_drives yields nothing, raise ValueError."""
        from arm.ripper.makemkv import makemkv

        # Ensure no SystemDrives linked
        assert sample_job.drive is None

        with unittest.mock.patch('arm.ripper.makemkv.prep_mkv'), \
             unittest.mock.patch('arm.ripper.makemkv.get_drives', return_value=iter([])):
            with pytest.raises(ValueError, match="No MakeMKV disc number"):
                makemkv(sample_job)

    def test_mdisc_none_drive_exists_but_mdisc_null_raises(self, app_context, sample_job):
        """When job.drive exists but mdisc is None, and scan finds no match, raise ValueError."""
        from arm.models.system_drives import SystemDrives
        from arm.database import db
        from arm.ripper.makemkv import makemkv

        # Create a SystemDrives row linked to this job, but mdisc=None
        drive = SystemDrives()
        drive.mount = sample_job.devpath
        drive.job_id_current = sample_job.job_id
        drive.mdisc = None
        db.session.add(drive)
        db.session.commit()
        db.session.refresh(sample_job)
        assert sample_job.drive is not None
        assert sample_job.drive.mdisc is None

        with unittest.mock.patch('arm.ripper.makemkv.prep_mkv'), \
             unittest.mock.patch('arm.ripper.makemkv.get_drives', return_value=iter([])):
            with pytest.raises(ValueError, match="No MakeMKV disc number"):
                makemkv(sample_job)

    def test_mdisc_populated_skips_scan(self, app_context, sample_job, tmp_path):
        """When job.drive.mdisc is already set, skip disc:9999 scan entirely."""
        from arm.models.system_drives import SystemDrives
        from arm.database import db
        from arm.ripper.makemkv import makemkv

        # Create a SystemDrives row with mdisc already populated
        drive = SystemDrives()
        drive.mount = sample_job.devpath
        drive.job_id_current = sample_job.job_id
        drive.mdisc = 0
        db.session.add(drive)
        db.session.commit()
        db.session.refresh(sample_job)

        mock_get_drives = unittest.mock.MagicMock()

        with unittest.mock.patch('arm.ripper.makemkv.prep_mkv'), \
             unittest.mock.patch('arm.ripper.makemkv.get_drives', mock_get_drives), \
             unittest.mock.patch('arm.ripper.makemkv.setup_rawpath', return_value=str(tmp_path)), \
             unittest.mock.patch('arm.ripper.makemkv.makemkv_mkv'), \
             unittest.mock.patch.object(sample_job, 'eject'), \
             unittest.mock.patch('arm.ripper.makemkv._reconcile_filenames'), \
             unittest.mock.patch.object(sample_job, 'build_raw_path', return_value='raw'):
            makemkv(sample_job)

        # get_drives should NOT have been called — mdisc was already set
        mock_get_drives.assert_not_called()


class TestDiscLabelParsing:
    """Test parse_disc_label_for_identifiers() (#1605)."""

    def test_s_d_no_separator(self):
        from arm.ripper.utils import parse_disc_label_for_identifiers
        assert parse_disc_label_for_identifiers("BB_S1D1") == "S1D1"
        assert parse_disc_label_for_identifiers("S01D02") == "S1D2"

    def test_s_d_with_underscore(self):
        from arm.ripper.utils import parse_disc_label_for_identifiers
        assert parse_disc_label_for_identifiers("S1_D1") == "S1D1"
        assert parse_disc_label_for_identifiers("S01_D02") == "S1D2"

    def test_s_d_with_hyphen(self):
        from arm.ripper.utils import parse_disc_label_for_identifiers
        assert parse_disc_label_for_identifiers("S1-D1") == "S1D1"

    def test_s_e_d_format(self):
        from arm.ripper.utils import parse_disc_label_for_identifiers
        assert parse_disc_label_for_identifiers("S1E1D1") == "S1E1D1"
        assert parse_disc_label_for_identifiers("S01E01D1") == "S1E1D1"

    def test_season_disc_word_format(self):
        from arm.ripper.utils import parse_disc_label_for_identifiers
        assert parse_disc_label_for_identifiers("Season1Disc1") == "S1D1"
        assert parse_disc_label_for_identifiers("SEASON01DISC02") == "S1D2"
        assert parse_disc_label_for_identifiers("Season 1 Disc 1") == "S1D1"

    def test_separate_s_and_d_tokens(self):
        from arm.ripper.utils import parse_disc_label_for_identifiers
        assert parse_disc_label_for_identifiers("Breaking Bad S01 Disc 1") == "S1D1"
        assert parse_disc_label_for_identifiers("GOT S5 D3") == "S5D3"

    def test_case_insensitivity(self):
        from arm.ripper.utils import parse_disc_label_for_identifiers
        assert parse_disc_label_for_identifiers("s1d1") == "S1D1"
        assert parse_disc_label_for_identifiers("BREAKING_BAD_S01_D02") == "S1D2"

    def test_no_match_returns_none(self):
        from arm.ripper.utils import parse_disc_label_for_identifiers
        assert parse_disc_label_for_identifiers("BREAKING_BAD_2008") is None
        assert parse_disc_label_for_identifiers("Disc1") is None
        assert parse_disc_label_for_identifiers("S1") is None

    def test_empty_or_none(self):
        from arm.ripper.utils import parse_disc_label_for_identifiers
        assert parse_disc_label_for_identifiers("") is None
        assert parse_disc_label_for_identifiers(None) is None

    def test_complex_labels(self):
        from arm.ripper.utils import parse_disc_label_for_identifiers
        assert parse_disc_label_for_identifiers("TheWire_S01_D01_BluRay") == "S1D1"
        assert parse_disc_label_for_identifiers("GOT_Season_05_Disc_03") == "S5D3"
        assert parse_disc_label_for_identifiers("Breaking.Bad.S02.D02") == "S2D2"


class TestNormalizeSeriesName:
    """Test normalize_series_name() (#1605)."""

    def test_basic_normalization(self):
        from arm.ripper.utils import normalize_series_name
        assert normalize_series_name("Breaking Bad") == "Breaking_Bad"
        assert normalize_series_name("Game of Thrones") == "Game_of_Thrones"

    def test_special_characters(self):
        from arm.ripper.utils import normalize_series_name
        assert normalize_series_name("Series!Name") == "Series_Name"
        assert normalize_series_name("Series: The Show") == "Series_The_Show"

    def test_preserve_hyphens_and_parens(self):
        from arm.ripper.utils import normalize_series_name
        assert normalize_series_name("The Walking-Dead") == "The_Walking-Dead"
        assert normalize_series_name("Series (US)") == "Series_(US)"

    def test_unicode_characters(self):
        from arm.ripper.utils import normalize_series_name
        assert normalize_series_name("Café") == "Cafe"

    def test_empty_or_none(self):
        from arm.ripper.utils import normalize_series_name
        assert normalize_series_name("") == ""
        assert normalize_series_name(None) == ""


class TestTVFolderName:
    """Test get_tv_folder_name() and build_final_path() for TV series (#1605)."""

    def test_disc_label_naming_enabled(self, app_context, sample_job):
        from arm.ripper.utils import get_tv_folder_name
        sample_job.video_type = "series"
        sample_job.title = "Breaking Bad"
        sample_job.title_manual = None
        sample_job.label = "BB_S1D1"
        sample_job.config.USE_DISC_LABEL_FOR_TV = True
        result = get_tv_folder_name(sample_job)
        assert result == "Breaking_Bad_S1D1"

    def test_disc_label_naming_disabled(self, app_context, sample_job):
        from arm.ripper.utils import get_tv_folder_name
        sample_job.video_type = "series"
        sample_job.title = "Breaking Bad"
        sample_job.title_manual = None
        sample_job.year = "2008"
        sample_job.label = "BB_S1D1"
        sample_job.config.USE_DISC_LABEL_FOR_TV = False
        result = get_tv_folder_name(sample_job)
        assert result == "Breaking Bad (2008)"

    def test_non_series_uses_standard_naming(self, app_context, sample_job):
        from arm.ripper.utils import get_tv_folder_name
        sample_job.video_type = "movie"
        sample_job.title = "Breaking Bad"
        sample_job.year = "2008"
        sample_job.config.USE_DISC_LABEL_FOR_TV = True
        result = get_tv_folder_name(sample_job)
        assert result == "Breaking Bad (2008)"

    def test_unparseable_label_fallback(self, app_context, sample_job):
        from arm.ripper.utils import get_tv_folder_name
        sample_job.video_type = "series"
        sample_job.title = "The Office"
        sample_job.title_manual = None
        sample_job.year = "2005"
        sample_job.label = "NO_IDENTIFIER"
        sample_job.config.USE_DISC_LABEL_FOR_TV = True
        result = get_tv_folder_name(sample_job)
        assert result == "The Office (2005)"

    def test_build_final_path_with_disc_label(self, app_context, sample_job):
        sample_job.video_type = "series"
        sample_job.title = "Breaking Bad"
        sample_job.title_manual = None
        sample_job.label = "BB_S1D1"
        sample_job.config.USE_DISC_LABEL_FOR_TV = True
        sample_job.config.GROUP_TV_DISCS_UNDER_SERIES = False
        sample_job.config.COMPLETED_PATH = "/media/completed"
        path = sample_job.build_final_path()
        assert path == "/media/completed/tv/Breaking_Bad_S1D1"

    def test_build_final_path_with_grouping(self, app_context, sample_job):
        sample_job.video_type = "series"
        sample_job.title = "Breaking Bad"
        sample_job.title_manual = None
        sample_job.year = "2008"
        sample_job.label = "BB_S1D1"
        sample_job.config.USE_DISC_LABEL_FOR_TV = True
        sample_job.config.GROUP_TV_DISCS_UNDER_SERIES = True
        sample_job.config.COMPLETED_PATH = "/media/completed"
        path = sample_job.build_final_path()
        assert path == "/media/completed/tv/Breaking Bad (2008)/Breaking_Bad_S1D1"

    def test_build_final_path_disabled_uses_standard(self, app_context, sample_job):
        sample_job.video_type = "series"
        sample_job.title = "Breaking Bad"
        sample_job.title_manual = None
        sample_job.year = "2008"
        sample_job.label = "BB_S1D1"
        sample_job.config.USE_DISC_LABEL_FOR_TV = False
        sample_job.config.COMPLETED_PATH = "/media/completed"
        path = sample_job.build_final_path()
        assert "Breaking Bad" in path
        assert "S1D1" not in path


class TestMainfeatureSorting:
    """Test MAINFEATURE track selection with chapters/filesize (#1698)."""

    def _create_track(self, db, job, track_number, length, chapters=0, filesize=0):
        from arm.models.track import Track
        t = Track(
            job_id=job.job_id,
            track_number=str(track_number),
            length=length,
            aspect_ratio="16:9",
            fps="23.976",
            main_feature=False,
            source="makemkv",
            basename=job.title,
            filename=f"title{track_number:02d}.mkv",
            chapters=chapters,
            filesize=filesize,
        )
        db.session.add(t)
        return t

    def test_chapters_beats_longer_duration(self, app_context, sample_job):
        """Track with more chapters should win even if another is longer (#1698)."""
        from arm.models.track import Track
        _, db = app_context

        # Track 1: longer but fewer chapters (Disney obfuscation victim)
        self._create_track(db, sample_job, 1, length=7200, chapters=5, filesize=5_000_000_000)
        # Track 2: shorter but more chapters (real main feature)
        self._create_track(db, sample_job, 2, length=7100, chapters=28, filesize=4_500_000_000)
        db.session.commit()

        best = Track.query.filter_by(job_id=sample_job.job_id).order_by(
            Track.chapters.desc(),
            Track.length.desc(),
            Track.filesize.desc(),
            Track.track_number.asc()
        ).first()

        assert best.track_number == "2"
        assert best.chapters == 28

    def test_equal_chapters_falls_back_to_length(self, app_context, sample_job):
        """When chapters are equal, longer track wins (standard non-Disney disc)."""
        from arm.models.track import Track
        _, db = app_context

        self._create_track(db, sample_job, 1, length=7200, chapters=20, filesize=5_000_000_000)
        self._create_track(db, sample_job, 2, length=6000, chapters=20, filesize=4_000_000_000)
        db.session.commit()

        best = Track.query.filter_by(job_id=sample_job.job_id).order_by(
            Track.chapters.desc(),
            Track.length.desc(),
            Track.filesize.desc(),
            Track.track_number.asc()
        ).first()

        assert best.track_number == "1"
        assert best.length == 7200

    def test_equal_chapters_and_length_falls_back_to_filesize(self, app_context, sample_job):
        """When chapters and length are equal, bigger file wins."""
        from arm.models.track import Track
        _, db = app_context

        self._create_track(db, sample_job, 1, length=7200, chapters=20, filesize=4_000_000_000)
        self._create_track(db, sample_job, 2, length=7200, chapters=20, filesize=5_000_000_000)
        db.session.commit()

        best = Track.query.filter_by(job_id=sample_job.job_id).order_by(
            Track.chapters.desc(),
            Track.length.desc(),
            Track.filesize.desc(),
            Track.track_number.asc()
        ).first()

        assert best.track_number == "2"
        assert best.filesize == 5_000_000_000

    def test_all_equal_falls_back_to_track_number(self, app_context, sample_job):
        """When everything is equal, lowest track number wins."""
        from arm.models.track import Track
        _, db = app_context

        self._create_track(db, sample_job, 3, length=7200, chapters=20, filesize=5_000_000_000)
        self._create_track(db, sample_job, 1, length=7200, chapters=20, filesize=5_000_000_000)
        db.session.commit()

        best = Track.query.filter_by(job_id=sample_job.job_id).order_by(
            Track.chapters.desc(),
            Track.length.desc(),
            Track.filesize.desc(),
            Track.track_number.asc()
        ).first()

        assert best.track_number == "1"

    def test_zero_chapters_legacy_fallback(self, app_context, sample_job):
        """Tracks with 0 chapters (legacy data) fall back to length sorting."""
        from arm.models.track import Track
        _, db = app_context

        self._create_track(db, sample_job, 1, length=7200, chapters=0, filesize=0)
        self._create_track(db, sample_job, 2, length=6000, chapters=0, filesize=0)
        db.session.commit()

        best = Track.query.filter_by(job_id=sample_job.job_id).order_by(
            Track.chapters.desc(),
            Track.length.desc(),
            Track.filesize.desc(),
            Track.track_number.asc()
        ).first()

        assert best.track_number == "1"
        assert best.length == 7200


class TestTrackInfoParsing:
    """Test MakeMKV TINFO chapters/filesize parsing (#1698)."""

    def test_chapters_parsed_from_tinfo(self, app_context, sample_job):
        """TrackInfoProcessor should parse TINFO field 8 as chapters."""
        from arm.ripper.makemkv import TrackInfoProcessor, TrackID

        proc = TrackInfoProcessor(sample_job, 0)
        assert proc.chapters == 0

        # Simulate receiving a chapters TINFO message
        class FakeTInfo:
            tid = 0
            id = TrackID.CHAPTERS
            value = "28"

        proc.track_id = 0
        proc._handle_tinfo(FakeTInfo())
        assert proc.chapters == 28

    def test_filesize_parsed_from_tinfo(self, app_context, sample_job):
        """TrackInfoProcessor should parse TINFO field 11 as filesize."""
        from arm.ripper.makemkv import TrackInfoProcessor, TrackID

        proc = TrackInfoProcessor(sample_job, 0)
        assert proc.filesize == 0

        class FakeTInfo:
            tid = 0
            id = TrackID.FILESIZE
            value = "4500000000"

        proc.track_id = 0
        proc._handle_tinfo(FakeTInfo())
        assert proc.filesize == 4_500_000_000

    def test_invalid_chapters_value_logged_not_crash(self, app_context, sample_job):
        """Non-integer chapters value should log warning, not crash."""
        from arm.ripper.makemkv import TrackInfoProcessor, TrackID

        proc = TrackInfoProcessor(sample_job, 0)
        proc.track_id = 0

        class FakeTInfo:
            tid = 0
            id = TrackID.CHAPTERS
            value = "N/A"

        proc._handle_tinfo(FakeTInfo())
        assert proc.chapters == 0  # unchanged from default

    def test_invalid_filesize_value_logged_not_crash(self, app_context, sample_job):
        """Non-integer filesize value should log warning, not crash."""
        from arm.ripper.makemkv import TrackInfoProcessor, TrackID

        proc = TrackInfoProcessor(sample_job, 0)
        proc.track_id = 0

        class FakeTInfo:
            tid = 0
            id = TrackID.FILESIZE
            value = ""

        proc._handle_tinfo(FakeTInfo())
        assert proc.filesize == 0  # unchanged from default

    def test_put_track_stores_chapters_filesize(self, app_context, sample_job):
        """put_track() should store chapters and filesize in the DB."""
        from arm.ripper.utils import put_track
        from arm.models.track import Track
        _, db = app_context

        put_track(sample_job, 1, 3600, "16:9", "23.976", False, "makemkv",
                  "title01.mkv", chapters=15, filesize=2_000_000_000)

        track = Track.query.filter_by(job_id=sample_job.job_id).first()
        assert track is not None
        assert track.chapters == 15
        assert track.filesize == 2_000_000_000

    def test_put_track_defaults_chapters_filesize_zero(self, app_context, sample_job):
        """put_track() without chapters/filesize should default to 0."""
        from arm.ripper.utils import put_track
        from arm.models.track import Track
        _, db = app_context

        put_track(sample_job, 1, 3600, "16:9", "23.976", False, "makemkv", "title01.mkv")

        track = Track.query.filter_by(job_id=sample_job.job_id).first()
        assert track is not None
        assert track.chapters == 0
        assert track.filesize == 0


class TestSettingsReload:
    """Test that config reload mutates the dict in-place (#1639)."""

    def test_reload_updates_existing_reference(self, tmp_path):
        """After PUT, a separate reference to cfg.arm_config sees new values."""
        import yaml
        import arm.config.config as cfg

        # Save original state
        original_config = dict(cfg.arm_config)
        original_path = cfg.arm_config_path

        # Grab a reference to the SAME dict object before the reload
        ref_before = cfg.arm_config

        try:
            # Write a modified config to a temp file
            new_config = dict(original_config)
            new_config["SOME_TEST_KEY"] = "test_value_1639"
            config_file = tmp_path / "arm_test.yaml"
            with open(config_file, "w") as f:
                yaml.dump(new_config, f)

            # Simulate what the settings endpoint does: write, then reload in-place
            cfg.arm_config_path = str(config_file)
            with open(cfg.arm_config_path, "r") as f:
                new_values = yaml.safe_load(f)
            cfg.arm_config.clear()
            cfg.arm_config.update(new_values)

            # The reference grabbed BEFORE the reload should see the new value
            assert ref_before is cfg.arm_config, "Dict object identity was lost"
            assert ref_before.get("SOME_TEST_KEY") == "test_value_1639"
        finally:
            # Restore original state
            cfg.arm_config.clear()
            cfg.arm_config.update(original_config)
            cfg.arm_config_path = original_path
