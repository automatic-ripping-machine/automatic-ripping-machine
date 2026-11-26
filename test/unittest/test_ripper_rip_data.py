"""
rip_data() builds paths and the dd command from the disc label, which is read
from the disc. It must not go through a shell or out of ARM's folders.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, '/opt/arm')
from arm.ripper import utils  # noqa: E402


class RipDataTest(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp()
        for sub in ("raw", "completed", "logs"):
            os.makedirs(os.path.join(self.root, sub))
        self.marker = os.path.join(self.root, "injected")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def make_job(self, label):
        config = SimpleNamespace(RAW_PATH=os.path.join(self.root, "raw"), LOGPATH=os.path.join(self.root, "logs"),
                                 COMPLETED_PATH=os.path.join(self.root, "completed"))
        # setup_job_log() names the log after the label with "/" replaced
        logfile = label.replace("/", "_") + ".log"
        return SimpleNamespace(label=label, devpath="/dev/sr0", video_type="unknown", logfile=logfile,
                               config=config, status="active")

    def fake_dd(self, cmd, **kwargs):
        """Write the output file like dd would; record how it was called"""
        self.calls.append((cmd, kwargs))
        out = next(arg[3:] for arg in cmd if arg.startswith("of="))
        with open(out, "w") as part:
            part.write("iso")
        return subprocess.CompletedProcess(cmd, 0)

    def rip(self, label, side_effect=None):
        self.calls = []
        job = self.make_job(label)
        with patch.dict(utils.cfg.arm_config, {"DATA_RIP_PARAMETERS": "bs=2048 conv=noerror"}), \
                patch.object(utils.subprocess, "run", side_effect=side_effect or self.fake_dd), \
                patch.object(utils, "database_updater"):
            return utils.rip_data(job), job


class TestRipDataCommand(RipDataTest):

    def test_label_with_shell_characters_is_not_run_by_a_shell(self):
        """CHECK a label like 'A & touch X' is a file name, not a command"""
        label = f'MY DISC & touch {self.marker} ; ("x")'
        ok, _job = self.rip(label)
        self.assertTrue(ok)
        cmd, kwargs = self.calls[0]
        self.assertEqual(cmd[:2], ["dd", "if=/dev/sr0"])
        self.assertEqual(cmd[3:], ["bs=2048", "conv=noerror"])
        self.assertNotIn("shell", kwargs)
        self.assertFalse(os.path.exists(self.marker))
        name = label.replace("/", "_")  # the marker path in the label contains "/"
        iso = os.path.join(self.root, "completed", "unidentified", name, f"{name}.iso")
        self.assertTrue(os.path.isfile(iso))

    def test_label_with_slash_stays_inside_raw_path(self):
        """CHECK a label containing '/' doesn't create folders outside RAW_PATH"""
        ok, _job = self.rip("../../escape")
        self.assertTrue(ok)
        out = next(arg[3:] for arg in self.calls[0][0] if arg.startswith("of="))
        raw = os.path.join(self.root, "raw")
        self.assertEqual(os.path.dirname(os.path.dirname(os.path.abspath(out))), raw)

    def test_dd_failure_without_output_file_is_reported(self):
        """CHECK a dd failure before the .part file exists fails the rip cleanly"""
        failed = subprocess.CalledProcessError(1, "dd", output=b"")
        ok, _job = self.rip("DATA_DISC", side_effect=failed)
        self.assertFalse(ok)


if __name__ == '__main__':
    unittest.main()
