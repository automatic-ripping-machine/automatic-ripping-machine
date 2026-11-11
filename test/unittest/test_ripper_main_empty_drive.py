"""
Opening or ejecting a tray fires the same udev "change" event as inserting a
disc. ARM should exit quietly when there is no disc, not send a "fatal error"
notification.
"""
import sys
import unittest
from argparse import Namespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, '/opt/arm')
from arm.models.system_drives import CDS  # noqa: E402
from arm.ripper import main as ripper_main  # noqa: E402


def fake_drive(status):
    drive = MagicMock()
    drive.mount = "/dev/sr1"
    drive.tray = status
    drive.ready = status == CDS.DISC_OK
    return drive


class TestSetupWithoutDisc(unittest.TestCase):

    def run_setup(self, status):
        drives = MagicMock()
        drives.filter_by.return_value.one.return_value = fake_drive(status)
        with patch.object(ripper_main, "entry", return_value=Namespace(devpath="sr1", syslog=False)), \
                patch.object(ripper_main.logger, "create_early_logger"), \
                patch.object(ripper_main.utils, "arm_setup"), \
                patch.object(ripper_main.SystemDrives, "query", drives), \
                patch.object(ripper_main.time, "sleep"):
            ripper_main.setup()

    def test_tray_open_is_drive_empty(self):
        """CHECK an open tray (eject) raises DriveEmptyException"""
        with self.assertRaises(ripper_main.utils.DriveEmptyException):
            self.run_setup(CDS.TRAY_OPEN)

    def test_no_disc_is_drive_empty(self):
        """CHECK a closed, empty drive raises DriveEmptyException"""
        with self.assertRaises(ripper_main.utils.DriveEmptyException):
            self.run_setup(CDS.NO_DISC)

    def test_drive_not_ready_is_still_an_error(self):
        """CHECK a disc that never becomes ready is still a setup failure"""
        with self.assertRaises(ripper_main.utils.RipperException) as raised:
            self.run_setup(CDS.DRIVE_NOT_READY)
        self.assertNotIsInstance(raised.exception, ripper_main.utils.DriveEmptyException)


class TestRunNotifications(unittest.TestCase):

    def run_with_setup_error(self, error):
        with patch.object(ripper_main, "setup", side_effect=error), \
                patch.object(ripper_main, "main") as main, \
                patch.object(ripper_main.utils, "notify") as notify:
            ripper_main.run()
        main.assert_not_called()
        return notify

    def test_empty_drive_sends_no_notification(self):
        """CHECK an eject doesn't produce a 'fatal error during job setup' notification"""
        notify = self.run_with_setup_error(ripper_main.utils.DriveEmptyException("No disc"))
        notify.assert_not_called()

    def test_setup_failure_still_notifies(self):
        """CHECK real setup failures still send the notification"""
        notify = self.run_with_setup_error(ripper_main.utils.RipperException("Timed out"))
        notify.assert_called_once()
        self.assertIn("fatal error during job setup", notify.call_args.args[2])


if __name__ == '__main__':
    unittest.main()
