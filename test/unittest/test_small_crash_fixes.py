"""
Small bugs that made ARM crash, or report nonsense, instead of handling an
edge case. One test class per fix.
"""
import subprocess
import sys
import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, '/opt/arm')
from arm.models import system_drives  # noqa: E402
from arm.ripper import ARMInfo, arm_ripper, handbrake, makemkv  # noqa: E402
from arm.ui import app  # noqa: E402
from arm.ui.jobs import jobs as jobs_routes  # noqa: E402
from arm.ui.settings import DriveUtils, settings as settings_routes  # noqa: E402


class TestTrayStatusErrors(unittest.TestCase):
    """system_drives._tray_status: f"{err:s}" raised TypeError inside the except blocks"""

    def test_bad_devpath_returns_none(self):
        with patch.object(system_drives.os, "open", side_effect=TypeError("expected str, got NoneType")):
            self.assertIsNone(system_drives._tray_status(None))

    def test_ioctl_error_returns_none(self):
        with patch.object(system_drives.os, "open", return_value=99), \
                patch.object(system_drives.os, "close"), \
                patch.object(system_drives.fcntl, "ioctl", side_effect=OSError(5, "Input/output error")):
            self.assertIsNone(system_drives._tray_status("/dev/sr0"))


class TestHandBrakeScanFailure(unittest.TestCase):
    """handbrake.get_track_info: the failure value was -1 but the caller checked for None"""

    def test_failed_scan_adds_no_track_and_does_not_crash(self):
        failed = subprocess.CalledProcessError(3, "HandBrakeCLI", output=b"")
        with patch.object(handbrake.subprocess, "check_output", side_effect=failed), \
                patch.object(handbrake.utils, "put_track") as put_track:
            handbrake.get_track_info("/dev/sr0", SimpleNamespace(job_id=1))
        put_track.assert_not_called()


class TestMakeMkvDriveNotLinked(unittest.TestCase):
    """makemkv.makemkv: logged a warning, then crashed on job.drive.mdisc with job.drive None"""

    def test_unlinked_drive_raises_a_clear_error(self):
        job = SimpleNamespace(job_id=7, devpath="/dev/sr0", drive=None, config=SimpleNamespace(RIPMETHOD="mkv"))
        drives = MagicMock()
        drives.filter_by.return_value.all.return_value = [SimpleNamespace(mdisc=None)]
        with patch.object(makemkv, "prep_mkv"), \
                patch.object(makemkv, "get_drives", return_value=[SimpleNamespace(mount="/dev/sr0", index=0)]), \
                patch.object(makemkv.SystemDrives, "query", drives), \
                patch.object(makemkv.db.session, "add"), \
                patch.object(makemkv.db.session, "commit"), \
                patch.object(makemkv.db.session, "refresh"):
            with self.assertRaises(ValueError) as raised:
                makemkv.makemkv(job)
        self.assertIn("not linked to job 7", str(raised.exception))


class TestMainFeatureWithoutTitles(unittest.TestCase):
    """makemkv.makemkv_mkv: rip_mainfeature(None) crashed with AttributeError"""

    def test_no_titles_raises_a_clear_error(self):
        job = SimpleNamespace(job_id=7, devpath="/dev/sr0", drive=SimpleNamespace(mdisc=0),
                              config=SimpleNamespace(MAINFEATURE=True))
        tracks = MagicMock()
        tracks.filter_by.return_value.order_by.return_value.first.return_value = None
        with patch.object(makemkv.utils, "get_drive_mode", return_value="auto"), \
                patch.object(makemkv, "get_track_info"), \
                patch.object(makemkv.Track, "query", tracks):
            with self.assertRaises(makemkv.utils.RipperException) as raised:
                makemkv.makemkv_mkv(job, "/home/arm/media/raw/x")
        self.assertIn("no titles", str(raised.exception))


class TestGitCommitWithoutGit(unittest.TestCase):
    """ARMInfo.get_git_commit: re.search(None) raised TypeError when git failed"""

    def test_no_git_output_is_unknown(self):
        info = ARMInfo.ARMInfo.__new__(ARMInfo.ARMInfo)
        info.install_path = "/opt/arm"
        with patch.object(ARMInfo.ProcessHandler, "arm_subprocess", return_value=None):
            info.get_git_commit()
        self.assertEqual((info.git_branch, info.git_commit), ("unknown", "unknown"))


class TestActiveRipsPage(unittest.TestCase):
    """/activerips: filter_by() with a positional expression raised TypeError"""

    def test_page_builds_the_query(self):
        with app.app_context(), app.test_request_context("/activerips"), \
                patch.object(jobs_routes, "render_template", return_value="ok") as render:
            self.assertEqual(jobs_routes.rips.__wrapped__(), "ok")
        self.assertIn("jobs", render.call_args.kwargs)


class TestManualStartDevicePath(unittest.TestCase):
    """drive_manual: lstrip('/dev/') strips characters, so /dev/dvd became ''"""

    def test_dev_prefix_is_removed_once(self):
        drives = MagicMock()
        drives.filter_by.return_value.first.return_value = SimpleNamespace(mount="/dev/dvd", name="DVD")
        process = MagicMock(returncode=0)
        process.communicate.return_value = ("", "")
        with ExitStack() as stack:
            stack.enter_context(app.test_request_context("/drive/manual/1"))
            stack.enter_context(patch.object(settings_routes.SystemDrives, "query", drives))
            popen = stack.enter_context(patch.object(settings_routes.subprocess, "Popen", return_value=process))
            stack.enter_context(patch.object(settings_routes, "flash"))
            stack.enter_context(patch.object(settings_routes, "redirect", return_value="redirected"))
            settings_routes.drive_manual.__wrapped__("1")
        self.assertTrue(popen.call_args.args[0].endswith("docker_arm_wrapper.sh dvd"))


class TestNewDriveCount(unittest.TestCase):
    """drives_update: returned old - new, so one new drive was reported as -1"""

    def test_one_new_drive_is_one(self):
        drives = MagicMock()
        drives.count.side_effect = [1, 2]
        drives.all.return_value = []
        drives.filter_by.return_value.all.return_value = []
        with app.app_context(), \
                patch.object(DriveUtils.SystemDrives, "query", drives), \
                patch.object(DriveUtils, "drives_search", return_value=[]), \
                patch.object(DriveUtils.db.session, "commit"):
            self.assertEqual(DriveUtils.drives_update(), 1)


class TestNotifyExitErrors(unittest.TestCase):
    """notify_exit: ', '.join() on the job.errors string gave "E, r, r, o, r" """

    def test_error_text_is_not_split(self):
        job = SimpleNamespace(title="Dont Breathe", errors="Read error",
                              config=SimpleNamespace(NOTIFY_TRANSCODE=True))
        with patch.object(arm_ripper.utils, "notify") as notify:
            arm_ripper.notify_exit(job)
        self.assertIn("Title(s) Read error failed", notify.call_args.args[2])


if __name__ == '__main__':
    unittest.main()
