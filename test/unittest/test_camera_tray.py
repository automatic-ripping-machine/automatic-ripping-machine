"""Tests for arm/camera/tray.py (tray state polling), driven with a fake status function."""
import importlib.util
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "arm" / "camera" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tray = _load("tray")


class TestDiscoverDrives(unittest.TestCase):
    def test_configured_names_and_paths(self):
        self.assertEqual(tray.discover_drives("sr1, sr0,/dev/sr2"), ["/dev/sr0", "/dev/sr1", "/dev/sr2"])

    def test_blank_uses_glob(self):
        self.assertEqual(tray.discover_drives("", pattern="/nonexistent/sr*"), [])


class TestTrayWatcher(unittest.TestCase):
    def setUp(self):
        self.states = {"/dev/sr0": tray.TrayState.DISC_OK, "/dev/sr1": tray.TrayState.NO_DISC}
        self.watcher = tray.TrayWatcher(self.states.keys(), status_fn=lambda d: self.states[d])

    def test_first_poll_is_baseline_only(self):
        self.assertEqual(self.watcher.poll(now=1.0), [])

    def test_open_then_close_emits_transitions(self):
        self.watcher.poll(now=1.0)
        self.states["/dev/sr1"] = tray.TrayState.TRAY_OPEN
        opened = self.watcher.poll(now=2.0)
        self.assertEqual(opened, [tray.TrayTransition("sr1", tray.TrayState.NO_DISC, tray.TrayState.TRAY_OPEN, 2.0)])
        self.assertFalse(tray.is_tray_close(opened[0]))

        self.states["/dev/sr1"] = tray.TrayState.DRIVE_NOT_READY
        closed = self.watcher.poll(now=3.0)
        self.assertEqual(len(closed), 1)
        self.assertEqual(closed[0].devname, "sr1")
        self.assertTrue(tray.is_tray_close(closed[0]))

        # No change -> nothing
        self.assertEqual(self.watcher.poll(now=4.0), [])

    def test_unreadable_drive_is_not_a_close(self):
        self.watcher.poll(now=1.0)
        self.states["/dev/sr0"] = tray.TrayState.TRAY_OPEN
        self.watcher.poll(now=2.0)
        self.states["/dev/sr0"] = None  # ioctl failed
        transitions = self.watcher.poll(now=3.0)
        self.assertEqual(len(transitions), 1)
        self.assertFalse(tray.is_tray_close(transitions[0]))

    def test_read_tray_status_missing_device(self):
        self.assertIsNone(tray.read_tray_status("/dev/does-not-exist"))


if __name__ == '__main__':
    unittest.main()
