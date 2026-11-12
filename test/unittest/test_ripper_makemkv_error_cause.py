"""
When MakeMKV fails, the job log, job.errors and the notification should say
why, not only "Error while running MakeMKV".
"""
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, '/opt/arm')
from arm.ripper import arm_ripper, makemkv  # noqa: E402


class TestMakeMkvRuntimeErrorMessage(unittest.TestCase):

    def test_first_output_line_is_in_the_message(self):
        """CHECK the first output line is added to the message"""
        error = makemkv.MakeMkvRuntimeError(1, ["RIP_COMPLETED"], output="\n0 titles were saved. See log\nmore")
        self.assertEqual(str(error), "Call to MakeMKV failed with code: 1: 0 titles were saved. See log")

    def test_no_output_keeps_the_old_message(self):
        """CHECK the message is unchanged without output"""
        self.assertEqual(str(makemkv.MakeMkvRuntimeError(2, ["mkv"])), "Call to MakeMKV failed with code: 2")


def make_job():
    config = SimpleNamespace(TRANSCODE_PATH="/tmp/transcode", COMPLETED_PATH="/tmp/completed", NOTIFY_RIP=False)
    return SimpleNamespace(video_type="movie", title="Dont-Breathe", year="2016", title_manual=None,
                           devpath="/dev/sr0", status="active", config=config)


class TestRipVisualMediaKeepsCause(unittest.TestCase):

    def rip_with_makemkv_error(self, error):
        with patch.object(arm_ripper.utils, "check_for_dupe_folder", side_effect=lambda _dupes, path, _job: path), \
                patch.object(arm_ripper.utils, "database_updater"), \
                patch.object(arm_ripper.utils, "save_disc_poster"), \
                patch.object(arm_ripper, "rip_with_mkv", return_value=True), \
                patch.object(arm_ripper.db.session, "commit"), \
                patch.object(arm_ripper.makemkv, "makemkv", side_effect=error):
            with self.assertRaises(arm_ripper.utils.RipperException) as raised:
                arm_ripper.rip_visual_media(False, make_job(), "job.log", 0)
        self.assertIs(raised.exception.__cause__, error)
        return str(raised.exception)

    def test_makemkv_error_reason_is_kept(self):
        """CHECK a MakeMKV failure keeps its reason"""
        error = makemkv.MakeMkvRuntimeError(1, ["RIP_TITLE_ERROR"], output="Failed to save title 0 to file")
        self.assertEqual(self.rip_with_makemkv_error(error),
                         "Error while running MakeMKV: Call to MakeMKV failed with code: 1: "
                         "Failed to save title 0 to file")

    def test_sigterm_reason_is_kept(self):
        """CHECK an abandoned job says it received SIGTERM"""
        message = self.rip_with_makemkv_error(arm_ripper.utils.RipperException("Received SIGTERM"))
        self.assertEqual(message, "Error while running MakeMKV: Received SIGTERM")

    def test_unexpected_error_names_type_and_logs_traceback(self):
        """CHECK an unexpected exception is named and its traceback logged"""
        with self.assertLogs(level="ERROR") as logs:
            message = self.rip_with_makemkv_error(TypeError("'NoneType' object is not subscriptable"))
        self.assertEqual(message, "Error while running MakeMKV: TypeError: 'NoneType' object is not subscriptable")
        self.assertTrue(any("Unexpected error while running MakeMKV" in line for line in logs.output))


if __name__ == '__main__':
    unittest.main()
