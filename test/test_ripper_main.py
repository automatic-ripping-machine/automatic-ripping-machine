"""Tests for arm/ripper/main.py — the main ripper entry point.

Covers: entry(), log_arm_params(), check_fstab(), main() branching,
and the __main__ exception/finally logic.
"""
import argparse
import datetime
import unittest.mock

import pytest


class TestEntry:
    """Test entry() argument parsing."""

    def test_parses_devpath(self):
        with unittest.mock.patch('sys.argv', ['main.py', '-d', 'sr0']):
            from arm.ripper.main import entry
            args = entry()
        assert args.devpath == 'sr0'

    def test_requires_devpath(self):
        with unittest.mock.patch('sys.argv', ['main.py']):
            from arm.ripper.main import entry
            with pytest.raises(SystemExit):
                entry()

    def test_syslog_default_true(self):
        with unittest.mock.patch('sys.argv', ['main.py', '-d', 'sr0']):
            from arm.ripper.main import entry
            args = entry()
        assert args.syslog is True

    def test_syslog_no_syslog(self):
        with unittest.mock.patch('sys.argv', ['main.py', '-d', 'sr0', '--no-syslog']):
            from arm.ripper.main import entry
            args = entry()
        assert args.syslog is False


class TestLogArmParams:
    """Test log_arm_params() logging of job and config parameters."""

    def test_logs_job_attributes(self):
        from arm.ripper.main import log_arm_params

        job = unittest.mock.MagicMock()
        job.devpath = '/dev/sr0'
        job.mountpoint = '/mnt/sr0'
        job.title = 'Test'
        job.year = '2024'
        job.video_type = 'movie'
        job.hasnicetitle = True
        job.label = 'TEST'
        job.disctype = 'dvd'
        job.manual_start = False

        with unittest.mock.patch('arm.ripper.main.logging') as mock_log:
            log_arm_params(job)
        # Should have logged multiple info calls for job params + config params
        assert mock_log.info.call_count >= 10


class TestCheckFstab:
    """Test check_fstab() fstab scanning logic."""

    def test_found_entry(self, tmp_path):
        import arm.ripper.main as main_mod

        fstab = tmp_path / "fstab"
        fstab.write_text("/dev/sr0 /mnt/sr0 udf defaults 0 0\n")

        # Set module-level job
        job = unittest.mock.MagicMock()
        job.devpath = '/dev/sr0'
        old_job = main_mod.job
        main_mod.job = job
        try:
            with unittest.mock.patch('builtins.open', unittest.mock.mock_open(
                read_data="/dev/sr0 /mnt/sr0 udf defaults 0 0\n"
            )):
                main_mod.check_fstab()
        finally:
            main_mod.job = old_job

    def test_no_entry_logs_error(self):
        import arm.ripper.main as main_mod

        job = unittest.mock.MagicMock()
        job.devpath = '/dev/sr0'
        old_job = main_mod.job
        main_mod.job = job
        try:
            with unittest.mock.patch('builtins.open', unittest.mock.mock_open(
                read_data="# empty fstab\n"
            )), unittest.mock.patch('arm.ripper.main.logging') as mock_log:
                main_mod.check_fstab()
            mock_log.error.assert_called_once()
        finally:
            main_mod.job = old_job


class TestMainBranching:
    """Test main() disc type routing."""

    def _make_job(self, disctype, video_type='movie'):
        job = unittest.mock.MagicMock()
        job.disctype = disctype
        job.video_type = video_type
        job.title = 'Test'
        job.label = 'TEST'
        job.has_track_99 = False
        job.tracks = []
        job.devpath = '/dev/sr0'
        job.job_id = 1
        return job

    def test_dvd_routes_to_visual_media(self):
        import arm.ripper.main as main_mod

        job = self._make_job('dvd')
        job.tracks = [unittest.mock.MagicMock()]
        old_job = main_mod.job
        main_mod.job = job
        try:
            with unittest.mock.patch('arm.ripper.main.identify.identify'), \
                 unittest.mock.patch('arm.ripper.main.logger.setup_job_log', return_value='test.log'), \
                 unittest.mock.patch('arm.ripper.main.utils.job_dupe_check', return_value=False), \
                 unittest.mock.patch('arm.ripper.main.utils.notify_entry'), \
                 unittest.mock.patch('arm.ripper.main.utils.check_for_wait'), \
                 unittest.mock.patch('arm.ripper.main.log_arm_params'), \
                 unittest.mock.patch('arm.ripper.main.check_fstab'), \
                 unittest.mock.patch('arm.ripper.main.arm_ripper.rip_visual_media') as mock_rip, \
                 unittest.mock.patch('arm.ripper.main.makemkv.prep_mkv'), \
                 unittest.mock.patch('arm.ripper.main.makemkv.prescan_track_info'), \
                 unittest.mock.patch('arm.ripper.identify._wait_for_drive_ready', return_value=True), \
                 unittest.mock.patch('pathlib.Path.exists', return_value=True), \
                 unittest.mock.patch('arm.ripper.main.db'):
                main_mod.main()
            mock_rip.assert_called_once()
        finally:
            main_mod.job = old_job

    def test_music_routes_to_music_brainz(self):
        import arm.ripper.main as main_mod

        job = self._make_job('music')
        job.build_final_path.return_value = '/home/arm/music/Test'
        old_job = main_mod.job
        main_mod.job = job
        try:
            with unittest.mock.patch('arm.ripper.main.identify.identify'), \
                 unittest.mock.patch('arm.ripper.main.logger.setup_job_log', return_value='test.log'), \
                 unittest.mock.patch('arm.ripper.main.utils.job_dupe_check', return_value=False), \
                 unittest.mock.patch('arm.ripper.main.utils.notify_entry'), \
                 unittest.mock.patch('arm.ripper.main.utils.check_for_wait'), \
                 unittest.mock.patch('arm.ripper.main.log_arm_params'), \
                 unittest.mock.patch('arm.ripper.main.check_fstab'), \
                 unittest.mock.patch('arm.ripper.main.music_brainz.main') as mock_mb, \
                 unittest.mock.patch('arm.ripper.main.utils.rip_music', return_value=True), \
                 unittest.mock.patch('arm.ripper.main.utils.notify'), \
                 unittest.mock.patch('arm.ripper.main.utils.scan_emby'), \
                 unittest.mock.patch('arm.ripper.main.db'):
                main_mod.main()
            mock_mb.assert_called_once_with(job)
        finally:
            main_mod.job = old_job

    def test_data_disc_routes_to_rip_data(self):
        import arm.ripper.main as main_mod

        job = self._make_job('data')
        old_job = main_mod.job
        main_mod.job = job
        try:
            with unittest.mock.patch('arm.ripper.main.identify.identify'), \
                 unittest.mock.patch('arm.ripper.main.logger.setup_job_log', return_value='test.log'), \
                 unittest.mock.patch('arm.ripper.main.utils.job_dupe_check', return_value=False), \
                 unittest.mock.patch('arm.ripper.main.utils.notify_entry'), \
                 unittest.mock.patch('arm.ripper.main.utils.check_for_wait'), \
                 unittest.mock.patch('arm.ripper.main.log_arm_params'), \
                 unittest.mock.patch('arm.ripper.main.check_fstab'), \
                 unittest.mock.patch('arm.ripper.main.utils.rip_data', return_value=True) as mock_data, \
                 unittest.mock.patch('arm.ripper.main.utils.notify'), \
                 unittest.mock.patch('arm.ripper.main.db'):
                main_mod.main()
            mock_data.assert_called_once_with(job)
        finally:
            main_mod.job = old_job

    def test_unknown_disc_logs_critical(self):
        import arm.ripper.main as main_mod

        job = self._make_job('unknown_type')
        old_job = main_mod.job
        main_mod.job = job
        try:
            with unittest.mock.patch('arm.ripper.main.identify.identify'), \
                 unittest.mock.patch('arm.ripper.main.logger.setup_job_log', return_value='test.log'), \
                 unittest.mock.patch('arm.ripper.main.utils.job_dupe_check', return_value=False), \
                 unittest.mock.patch('arm.ripper.main.utils.notify_entry'), \
                 unittest.mock.patch('arm.ripper.main.utils.check_for_wait'), \
                 unittest.mock.patch('arm.ripper.main.log_arm_params'), \
                 unittest.mock.patch('arm.ripper.main.check_fstab'), \
                 unittest.mock.patch('arm.ripper.main.logging') as mock_log, \
                 unittest.mock.patch('arm.ripper.main.db'):
                main_mod.main()
            mock_log.critical.assert_called()
        finally:
            main_mod.job = old_job

    def test_music_rip_failure(self):
        import arm.ripper.main as main_mod

        job = self._make_job('music')
        job.build_final_path.return_value = '/home/arm/music/Test'
        old_job = main_mod.job
        main_mod.job = job
        try:
            with unittest.mock.patch('arm.ripper.main.identify.identify'), \
                 unittest.mock.patch('arm.ripper.main.logger.setup_job_log', return_value='test.log'), \
                 unittest.mock.patch('arm.ripper.main.utils.job_dupe_check', return_value=False), \
                 unittest.mock.patch('arm.ripper.main.utils.notify_entry'), \
                 unittest.mock.patch('arm.ripper.main.utils.check_for_wait'), \
                 unittest.mock.patch('arm.ripper.main.log_arm_params'), \
                 unittest.mock.patch('arm.ripper.main.check_fstab'), \
                 unittest.mock.patch('arm.ripper.main.music_brainz.main'), \
                 unittest.mock.patch('arm.ripper.main.utils.rip_music', return_value=False), \
                 unittest.mock.patch('arm.ripper.main.logging') as mock_log, \
                 unittest.mock.patch('arm.ripper.main.db'):
                main_mod.main()
            mock_log.critical.assert_called()
        finally:
            main_mod.job = old_job

    def test_tvdb_matching_attempted_for_series(self):
        """TVDB matching is attempted when video_type=series and API key set."""
        import arm.ripper.main as main_mod
        import arm.config.config as cfg

        job = self._make_job('dvd', video_type='series')
        job.tracks = [unittest.mock.MagicMock()]
        old_job = main_mod.job
        main_mod.job = job
        old_key = cfg.arm_config.get('TVDB_API_KEY')
        cfg.arm_config['TVDB_API_KEY'] = 'test-key'
        try:
            with unittest.mock.patch('arm.ripper.main.identify.identify'), \
                 unittest.mock.patch('arm.ripper.main.logger.setup_job_log', return_value='test.log'), \
                 unittest.mock.patch('arm.ripper.main.utils.job_dupe_check', return_value=False), \
                 unittest.mock.patch('arm.ripper.main.utils.notify_entry'), \
                 unittest.mock.patch('arm.ripper.main.utils.check_for_wait'), \
                 unittest.mock.patch('arm.ripper.main.log_arm_params'), \
                 unittest.mock.patch('arm.ripper.main.check_fstab'), \
                 unittest.mock.patch('arm.ripper.main.arm_ripper.rip_visual_media'), \
                 unittest.mock.patch('arm.ripper.main.makemkv.prep_mkv'), \
                 unittest.mock.patch('arm.ripper.main.makemkv.prescan_track_info'), \
                 unittest.mock.patch('arm.ripper.identify._wait_for_drive_ready', return_value=True), \
                 unittest.mock.patch('pathlib.Path.exists', return_value=True), \
                 unittest.mock.patch('arm.services.tvdb_sync.match_episodes_sync', return_value=True) as mock_tvdb, \
                 unittest.mock.patch('arm.ripper.main.db'):
                main_mod.main()
            mock_tvdb.assert_called_once()
        finally:
            main_mod.job = old_job
            if old_key is not None:
                cfg.arm_config['TVDB_API_KEY'] = old_key
            else:
                cfg.arm_config.pop('TVDB_API_KEY', None)


class TestPreScanRetry:
    """Test pre-scan retry logic in main()."""

    def test_prescan_retries_on_failure(self):
        """Pre-scan retries up to 3 times with increasing wait."""
        import arm.ripper.main as main_mod

        job = unittest.mock.MagicMock()
        job.disctype = 'bluray'
        job.video_type = 'movie'
        job.title = 'Test'
        job.label = 'TEST'
        job.has_track_99 = False
        job.devpath = '/dev/sr0'
        job.job_id = 1
        job.tracks = []  # Empty tracks to trigger pre-scan

        old_job = main_mod.job
        main_mod.job = job
        try:
            # Use a side_effect for db.session.expire that does nothing
            mock_db = unittest.mock.MagicMock()
            with unittest.mock.patch('arm.ripper.main.identify.identify'), \
                 unittest.mock.patch('arm.ripper.main.logger.setup_job_log', return_value='test.log'), \
                 unittest.mock.patch('arm.ripper.main.utils.job_dupe_check', return_value=False), \
                 unittest.mock.patch('arm.ripper.main.utils.notify_entry'), \
                 unittest.mock.patch('arm.ripper.main.utils.check_for_wait'), \
                 unittest.mock.patch('arm.ripper.main.log_arm_params'), \
                 unittest.mock.patch('arm.ripper.main.check_fstab'), \
                 unittest.mock.patch('arm.ripper.main.arm_ripper.rip_visual_media'), \
                 unittest.mock.patch('arm.ripper.main.makemkv.prep_mkv'), \
                 unittest.mock.patch('arm.ripper.main.makemkv.prescan_track_info',
                                     side_effect=RuntimeError("scan failed")) as mock_prescan, \
                 unittest.mock.patch('arm.ripper.identify._wait_for_drive_ready', return_value=True), \
                 unittest.mock.patch('pathlib.Path.exists', return_value=True), \
                 unittest.mock.patch('arm.ripper.main.time.sleep'), \
                 unittest.mock.patch('arm.ripper.main.db'):
                main_mod.main()
            assert mock_prescan.call_count == 3
        finally:
            main_mod.job = old_job
