import sys
import unittest

sys.path.insert(0, '/opt/arm')
from arm.ripper.makemkv import (MakeMKVMessage, MakeMKVOutputChecker,  # noqa: E402
                                MakeMkvRuntimeError, MessageID)


def _message(code, message, sprintf):
    return MakeMKVMessage(code, 0, len(sprintf), message, sprintf)


class TestMakeMKVOutputChecker(unittest.TestCase):
    def test_title_error_is_not_fatal(self):
        """
        CHECK a single failed title (e.g. a copy-protection decoy with unreadable sectors)
        is logged and does not abort the rip
        """
        msg = _message(MessageID.RIP_TITLE_ERROR,
                       "Failed to save title 0 to file /home/arm/media/raw/Super-8/A17_t00.mkv",
                       ["Failed to save title %1 to file %2", "0", "/home/arm/media/raw/Super-8/A17_t00.mkv"])
        with self.assertLogs(level="WARNING"):
            self.assertIs(MakeMKVOutputChecker(msg).check(), msg)

    def test_rip_completed_with_saved_titles(self):
        """
        CHECK a rip where some titles failed but others saved completes
        """
        msg = _message(MessageID.RIP_COMPLETED, "Copy complete. 3 titles saved, 1 failed.",
                       ["Copy complete. %1 titles saved, %2 failed.", "3", "1"])
        MakeMKVOutputChecker(msg).check()

    def test_rip_completed_with_no_saved_titles(self):
        """
        CHECK a rip that saved nothing still fails the job
        """
        msg = _message(MessageID.RIP_COMPLETED, "Copy complete. 0 titles saved, 4 failed.",
                       ["Copy complete. %1 titles saved, %2 failed.", "0", "4"])
        with self.assertRaises(MakeMkvRuntimeError):
            MakeMKVOutputChecker(msg).check()


if __name__ == '__main__':
    unittest.main()
