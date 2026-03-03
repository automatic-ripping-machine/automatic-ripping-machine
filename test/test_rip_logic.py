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
