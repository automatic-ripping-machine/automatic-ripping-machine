"""Tests for arm/camera/daemon.py and capture.py without camera hardware."""
import importlib.util
import os
import re
import shutil
import tempfile
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# daemon.py puts its own folder on sys.path and imports ``capture`` and ``tray`` from there.
_spec = importlib.util.spec_from_file_location("arm_camera_daemon", REPO_ROOT / "arm" / "camera" / "daemon.py")
daemon = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(daemon)
capture = daemon.capture
tray = daemon.tray

# Smallest valid JPEG (1x1 pixel) so the fake source has something to serve without OpenCV
TINY_JPEG = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707070909080a0c140d0c0b0b0c1912130f14"
    "1d1a1f1e1d1a1c1c20242e2720222c231c1c2837292c30313434341f27393d38323c2e333432ffc0000b080001000101011100"
    "ffc40014000100000000000000000000000000000009ffc40014100100000000000000000000000000000000ffda0008010100"
    "003f00d2cf20ffd9"
)


class TestConfigHelpers(unittest.TestCase):
    def test_parse_regions(self):
        regions = daemon.parse_regions("sr0:10,20,300,200; /dev/sr1:0,0,640,480;bad;sr2:1,2")
        self.assertEqual(regions, {"sr0": (10, 20, 300, 200), "sr1": (0, 0, 640, 480)})
        self.assertEqual(daemon.parse_regions(""), {})

    def test_as_bool_and_number(self):
        self.assertTrue(daemon.as_bool("True"))
        self.assertFalse(daemon.as_bool("false"))
        self.assertFalse(daemon.as_bool(None))
        self.assertEqual(daemon.as_number("1.5", 2.0), 1.5)
        self.assertEqual(daemon.as_number("nope", 2.0), 2.0)
        self.assertEqual(daemon.as_number("85", 50, int), 85)

    def test_load_config_merges_template_and_user_file(self):
        folder = tempfile.mkdtemp()
        try:
            user_cfg = os.path.join(folder, "arm.yaml")
            with open(user_cfg, "w") as handle:
                handle.write("CAMERA_ENABLED: true\nCAMERA_LEAD_SECONDS: \"2.5\"\n")
            config = daemon.load_config(user_cfg)
            self.assertTrue(config["CAMERA_ENABLED"])
            self.assertEqual(config["CAMERA_LEAD_SECONDS"], "2.5")
            # from the repo template
            self.assertEqual(config["DISC_PHOTO_PATH"], "/home/arm/media/disc_photos/")
            # missing user file still yields defaults
            self.assertIn("CAMERA_DEVICE", daemon.load_config(os.path.join(folder, "missing.yaml")))
        finally:
            shutil.rmtree(folder)

    def test_photo_filename_matches_ripper_pattern(self):
        name = daemon.photo_filename("sr2")
        self.assertRegex(name, r"^sr2_\d{8}-\d{6}\.jpg$")


class TestFrameBuffer(unittest.TestCase):
    def test_frame_at_picks_nearest_and_prunes(self):
        buffer = capture.FrameBuffer(source=None, fps=10, buffer_seconds=1.0)
        buffer._append(10.0, "a")
        buffer._append(10.5, "b")
        buffer._append(11.2, "c")  # prunes "a" (older than 11.2 - 1.0)
        self.assertEqual(len(buffer), 2)
        self.assertEqual(buffer.frame_at(10.6), "b")
        self.assertEqual(buffer.frame_at(50.0), "c")
        self.assertIsNone(capture.FrameBuffer(source=None).frame_at(1.0))

    def test_crop_and_encode_pass_bytes_through(self):
        self.assertEqual(capture.crop(TINY_JPEG, (0, 0, 1, 1)), TINY_JPEG)
        self.assertEqual(capture.encode_jpeg(TINY_JPEG), TINY_JPEG)


class TestDaemonEndToEnd(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.photos = os.path.join(self.folder, "photos")
        self.image = os.path.join(self.folder, "disc.jpg")
        with open(self.image, "wb") as handle:
            handle.write(TINY_JPEG)
        self.cfg = os.path.join(self.folder, "arm.yaml")
        with open(self.cfg, "w") as handle:
            handle.write(f"CAMERA_ENABLED: false\nDISC_PHOTO_PATH: \"{self.photos}\"\n"
                         f"LOGPATH: \"{self.folder}/logs\"\nCAMERA_FPS: 20\nCAMERA_LEAD_SECONDS: 0\n")

    def tearDown(self):
        shutil.rmtree(self.folder)

    def test_simulate_close_writes_named_jpeg(self):
        rc = daemon.main(["--config", self.cfg, "--frames-from", self.image, "--simulate-close", "sr0"])
        self.assertEqual(rc, 0)
        files = os.listdir(self.photos)
        self.assertEqual(len(files), 1)
        self.assertRegex(files[0], r"^sr0_\d{8}-\d{6}\.jpg$")
        with open(os.path.join(self.photos, files[0]), "rb") as handle:
            data = handle.read()
        self.assertTrue(data.startswith(b"\xff\xd8"), "not a JPEG")
        self.assertFalse(any(f.endswith(".tmp") for f in files))
        self.assertTrue(os.path.isfile(os.path.join(self.folder, "logs", "camera.log")))

    def test_tray_close_transition_saves_photo_via_watcher(self):
        states = {"/dev/sr1": tray.TrayState.TRAY_OPEN}
        config = daemon.load_config(self.cfg)
        source = capture.FakeFrameSource(self.image)
        dmn = daemon.Daemon(config, source=source, drives=["/dev/sr1"], poll_interval=0.01)
        dmn.watcher = tray.TrayWatcher(["/dev/sr1"], status_fn=lambda d: states[d])
        dmn.buffer.start()
        try:
            self.assertTrue(dmn.buffer.wait_for_frame(5.0))
            dmn.watcher.poll()                       # baseline: open
            states["/dev/sr1"] = tray.TrayState.DISC_OK
            time.sleep(0.1)
            saved = [dmn.handle(t) for t in dmn.watcher.poll()]
        finally:
            dmn.buffer.stop()
        self.assertEqual(len(saved), 1)
        self.assertIsNotNone(saved[0])
        self.assertTrue(re.match(r"^sr1_\d{8}-\d{6}\.jpg$", os.path.basename(saved[0])))

    def test_open_transition_does_not_save(self):
        config = daemon.load_config(self.cfg)
        dmn = daemon.Daemon(config, source=capture.FakeFrameSource(self.image), drives=[])
        transition = tray.TrayTransition("sr0", tray.TrayState.NO_DISC, tray.TrayState.TRAY_OPEN, time.monotonic())
        self.assertIsNone(dmn.handle(transition))
        self.assertFalse(os.path.exists(self.photos))


if __name__ == '__main__':
    unittest.main()
