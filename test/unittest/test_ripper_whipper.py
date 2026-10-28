import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Ensure repository root is on sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, repo_root)
os.environ["ARM_CONFIG_FILE"] = os.path.join(repo_root, "setup/arm.yaml")

import types

class MockModule(types.ModuleType):
    def __init__(self, name):
        super().__init__(name)
        self.__path__ = []

    def __getattr__(self, name):
        if name in ("__file__", "__path__", "__spec__"):
            return None
        mock = MagicMock()
        setattr(self, name, mock)
        return mock

# Mock heavy/external dependencies if not installed in current environment
for dep in [
    "apprise", "flask", "flask.logging", "flask.views", "flask_login", "flask_sqlalchemy", "sqlalchemy",
    "sqlalchemy.orm", "sqlalchemy.ext", "sqlalchemy.ext.hybrid", "flask_migrate", "flask_cors", "flask_wtf",
    "wtforms", "wtforms.validators", "netifaces", "bcrypt", "requests", "psutil", "pyudev", "pydvdid", "xmltodict", "alembic", "alembic.script", "alembic.config",
    "sqlalchemy.sql", "sqlalchemy.sql.schema", "sqlalchemy.exc",
    "discid", "musicbrainzngs", "werkzeug", "werkzeug.utils", "werkzeug.routing", "prettytable"
]:
    if dep not in sys.modules:
        sys.modules[dep] = MockModule(dep)

# Fix metaclass inheritance issues in mock environment
class DummyModel: pass
class DummyUserMixin: pass
sys.modules["flask_login"].UserMixin = DummyUserMixin
sys.modules["sqlalchemy.exc"].SQLAlchemyError = Exception
sys.modules["werkzeug.routing"].ValidationError = Exception
db_mock = MockModule("arm.ui.db")
db_mock.Model = DummyModel
sys.modules["arm.ui"] = MockModule("arm.ui")
sys.modules["arm.ui"].__path__ = [os.path.join(repo_root, "arm/ui")]
sys.modules["arm.ui"].db = db_mock

from arm.ripper.utils import check_whipper_errors, rip_music
from arm.ui.json_api import process_audio_logfile


class TestWhipperRipper(unittest.TestCase):
    def test_check_whipper_errors_success(self):
        """Test success when returncode is 0."""
        success, msg = check_whipper_errors("Rip completed successfully", 0, accuraterip_strict=True)
        self.assertTrue(success)
        self.assertEqual(msg, "")

    def test_check_whipper_errors_read_failure(self):
        """Test failure when unrecoverable read or scratch error is logged."""
        log = "Ripping track 1... Read error at sector 12345. Unrecoverable error."
        success, msg = check_whipper_errors(log, 1, accuraterip_strict=False)
        self.assertFalse(success)
        self.assertIn("read/disc error", msg)

    def test_check_whipper_errors_accuraterip_strict(self):
        """Test AccurateRip mismatch fails when strict mode is enabled."""
        log = "Track 1: AccurateRip: no matches found in database."
        success, msg = check_whipper_errors(log, 1, accuraterip_strict=True)
        self.assertFalse(success)
        self.assertIn("failed AccurateRip verification", msg)

    def test_check_whipper_errors_accuraterip_permissive(self):
        """Test AccurateRip mismatch succeeds with notice when permissive mode is enabled."""
        log = "Track 1: AccurateRip: no matches found in database."
        success, msg = check_whipper_errors(log, 1, accuraterip_strict=False)
        self.assertTrue(success)
        self.assertIn("tolerated per WHIPPER_ACCURATERIP=False", msg)

    def test_check_whipper_errors_mixed_mode_cd_extra(self):
        """Test mixed-mode CD (Enhanced CD with data track) succeeds with warning when audio tracks were ripped."""
        log = (
            "INFO:whipper.command.cd:Ripping track 1 of 2\n"
            "Track 1: Rip quality 100.0%\n"
            "INFO:whipper.command.cd:Ripping track 2 of 2\n"
            "Track 2: cannot rip data track (skipping data track)\n"
            "CRITICAL:whipper:error reading data track\n"
        )
        success, msg = check_whipper_errors(log, 1, accuraterip_strict=True)
        self.assertTrue(success)
        self.assertIn("data track skipped or unreadable on mixed-mode CD", msg)

    @patch("arm.ripper.utils.subprocess.run")
    @patch("arm.ripper.utils.database_updater")
    @patch("arm.ripper.utils.set_permissions")
    def test_rip_music_cli_arguments(self, mock_perms, mock_db_update, mock_run):
        """Test that rip_music builds the correct whipper CLI arguments and passes headless input."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_run.return_value = mock_proc

        job = MagicMock()
        job.disctype = "music"
        job.devpath = "/dev/sr0"
        job.crc_id = "12345678-1234-5678-1234-567812345678"
        job.config.LOGPATH = "/tmp"
        job.config.COMPLETED_PATH = "/tmp/completed"

        with patch("arm.config.config.arm_config", {
            "WHIPPER_DRIVE_OFFSET": 667,
            "WHIPPER_ACCURATERIP": True,
            "WHIPPER_OUTPUT_FORMAT": "%A/%d/%t - %n",
            "WHIPPER_DISC_TEMPLATE": "%A/%d/%A - %d",
            "LOGPATH": "/tmp"
        }):
            res = rip_music(job, "test_job.log")
            self.assertTrue(res)

        # Inspect CLI arguments passed to subprocess.run
        mock_run.assert_called_once()
        cmd_called = mock_run.call_args[0][0]
        kwargs_called = mock_run.call_args[1]
        self.assertEqual(cmd_called[0], "whipper")
        self.assertIn("cd", cmd_called)
        self.assertIn("-d", cmd_called)
        self.assertIn("/dev/sr0", cmd_called)
        self.assertIn("rip", cmd_called)
        self.assertIn("--offset", cmd_called)
        self.assertIn("667", cmd_called)
        self.assertIn("--unknown", cmd_called)
        self.assertIn("--release-id", cmd_called)
        self.assertIn("12345678-1234-5678-1234-567812345678", cmd_called)
        self.assertIn("--output-directory", cmd_called)
        self.assertIn("/tmp/completed/music", cmd_called)
        # Verify headless input passed to avoid hanging on multimatch
        self.assertEqual(kwargs_called.get("input"), b"1\n")

    @patch("arm.ui.json_api.read_all_log_lines")
    def test_process_audio_logfile_whipper(self, mock_read_lines):
        """Test process_audio_logfile correctly parses whipper progress lines."""
        mock_read_lines.return_value = [
            "INFO:whipper.command.cd:Ripping disc...",
            "INFO:whipper.command.cd:Ripping track 3 of 10",
        ]
        job = MagicMock()
        job.no_of_titles = 10
        job.start_time = MagicMock()
        job_results = {}

        with patch("arm.config.config.arm_config", {"LOGPATH": "/tmp"}):
            res = process_audio_logfile("test.log", job, job_results)

    def test_check_whipper_errors_toc_failure(self):
        """Test failure when cdrdao/whipper fails to read TOC or file is missing."""
        log = "CRITICAL:whipper:FileNotFoundError: [Errno 2] No such file or directory: '/tmp/test.cdrdao.read-toc.whipper.task'"
        success, msg = check_whipper_errors(log, 1, accuraterip_strict=False)
        self.assertFalse(success)
        self.assertIn("No disc present / Read error", msg)

    @patch("arm.ripper.utils.check_cd_present")
    @patch("arm.ripper.utils.database_updater")
    def test_rip_music_no_cd_present_prevalidation(self, mock_db_update, mock_check_cd):
        """Test that rip_music fails gracefully and ejects when no CD is present."""
        mock_check_cd.return_value = (False, "Cannot read CD TOC on /dev/sr0")

        job = MagicMock()
        job.disctype = "music"
        job.devpath = "/dev/sr0"
        job.eject = MagicMock()

        with patch("arm.config.config.arm_config", {"AUTO_EJECT": True, "LOGPATH": "/tmp"}):
            res = rip_music(job, "test_job.log")
            self.assertFalse(res)
            self.assertEqual(job.errors, "No disc present / Read error")
            job.eject.assert_called_once()
            mock_db_update.assert_called()

    @patch("arm.ripper.utils.check_cd_present")
    @patch("arm.ripper.utils.subprocess.run")
    @patch("arm.ripper.utils.database_updater")
    def test_rip_music_toc_error_during_whipper_execution(self, mock_db_update, mock_run, mock_check_cd):
        """Test that whipper TOC read failure during execution marks job as failed and ejects."""
        mock_check_cd.return_value = (True, "")

        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_run.return_value = mock_proc

        job = MagicMock()
        job.disctype = "music"
        job.devpath = "/dev/sr0"
        job.crc_id = None
        job.config.LOGPATH = "/tmp"
        job.config.COMPLETED_PATH = "/tmp/completed"
        job.eject = MagicMock()

        # Simulate log containing cdrdao read-toc FileNotFoundError
        log_content = "FileNotFoundError: [Errno 2] No such file or directory: '/tmp/whipper.task.cdrdao.read-toc.task'\n"
        with patch("builtins.open", unittest.mock.mock_open(read_data=log_content)), \
             patch("os.path.isfile", return_value=True), \
             patch("arm.config.config.arm_config", {"AUTO_EJECT": True, "LOGPATH": "/tmp", "WHIPPER_ACCURATERIP": True}):
            res = rip_music(job, "test_job.log")
            self.assertFalse(res)
            self.assertEqual(job.errors, "No disc present / Read error")
            job.eject.assert_called_once()


if __name__ == "__main__":
    unittest.main()
