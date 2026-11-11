import os
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, '/opt/arm')
from arm.ripper import makemkv    # noqa: E402

MSG_LINE = 'MSG:1005,0,1,"MakeMKV v1.17.8 started","%1 started","MakeMKV v1.17.8"'


def _pid_alive(pid):
    """True if pid is running (zombies count as gone)."""
    try:
        with open(f"/proc/{pid}/stat") as stat_file:
            return stat_file.read().split()[2] != "Z"
    except FileNotFoundError:
        return False


class TestMakeMKVRunStopsProcess(unittest.TestCase):
    """
    makemkv.run() must not leave makemkvcon running (and holding the drive)
    when the caller stops reading early, e.g. after an error or a SIGTERM
    from "Abandon Job".
    """

    def _fake_makemkvcon(self, script_body):
        tmpdir = tempfile.mkdtemp()
        self.pid_file = os.path.join(tmpdir, "pid")
        path = os.path.join(tmpdir, "makemkvcon")
        with open(path, "w") as script:
            script.write("#!/bin/sh\n")
            script.write(f'echo $$ > "{self.pid_file}"\n')
            script.write(script_body)
        os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
        return path

    def _fake_pid(self):
        with open(self.pid_file) as pid_file:
            return int(pid_file.read())

    def _run_and_fail_after_first_message(self, fake_path):
        with patch.object(makemkv.shutil, "which", return_value=fake_path):
            messages = makemkv.run(["info"], makemkv.OutputType.MSG)
            with self.assertRaises(RuntimeError):
                for _ in messages:
                    raise RuntimeError("caller failed")
        return self._fake_pid()

    def test_exception_in_caller_terminates_makemkvcon(self):
        """CHECK an exception while reading stops the hung makemkvcon"""
        fake = self._fake_makemkvcon(f"echo '{MSG_LINE}'\nexec sleep 600\n")
        start = time.monotonic()
        pid = self._run_and_fail_after_first_message(fake)
        self.assertFalse(_pid_alive(pid))
        self.assertLess(time.monotonic() - start, 5)

    def test_makemkvcon_ignoring_sigterm_is_killed(self):
        """CHECK makemkvcon is killed if it ignores SIGTERM"""
        fake = self._fake_makemkvcon(
            f"trap '' TERM\necho '{MSG_LINE}'\nwhile true; do sleep 1; done\n")
        with subprocess.Popen([fake], stdout=subprocess.PIPE, text=True) as proc:
            proc.stdout.readline()  # wait until the trap is set
            makemkv._stop_makemkvcon(proc, timeout=1)
            self.assertEqual(proc.returncode, -signal.SIGKILL)

    def test_closing_generator_terminates_makemkvcon(self):
        """CHECK closing the generator early stops makemkvcon"""
        fake = self._fake_makemkvcon(f"echo '{MSG_LINE}'\nexec sleep 600\n")
        with patch.object(makemkv.shutil, "which", return_value=fake):
            messages = makemkv.run(["info"], makemkv.OutputType.MSG)
            next(messages)
            messages.close()
        self.assertFalse(_pid_alive(self._fake_pid()))

    def test_normal_exit_is_unchanged(self):
        """CHECK a makemkvcon that finishes normally still yields all messages"""
        fake = self._fake_makemkvcon(f"echo '{MSG_LINE}'\necho '{MSG_LINE}'\nexit 0\n")
        with patch.object(makemkv.shutil, "which", return_value=fake):
            messages = list(makemkv.run(["info"], makemkv.OutputType.MSG))
        self.assertEqual(len(messages), 2)


if __name__ == '__main__':
    unittest.main()
