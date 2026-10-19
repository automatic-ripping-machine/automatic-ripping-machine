"""Tests for arm/camera/daemon.py and capture.py without camera hardware."""
import importlib.util
import json
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


class FailingSource:
    """A camera whose ``open`` blows up, like cv2 missing or a V4L2 error."""

    def __init__(self):
        self.opens = 0

    def open(self):
        self.opens += 1
        raise RuntimeError("no camera here")

    def read(self):  # pragma: no cover - never reached
        return None

    def release(self):
        pass


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

    def test_barcode_filename_matches_ripper_pattern(self):
        name = daemon.barcode_filename("sr2")
        self.assertRegex(name, r"^sr2_\d{8}-\d{6}\.barcode$")

    def test_barcode_defaults(self):
        config = daemon.load_config("/nonexistent/arm.yaml")
        self.assertFalse(daemon.as_bool(config["BARCODE_ENABLED"]))
        self.assertEqual(config["BARCODE_DEVICE"], "")
        self.assertEqual(daemon.as_number(config["BARCODE_PAIR_SECONDS"], 0), 120)

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

    def test_exception_ends_thread_and_start_restarts_it(self):
        source = FailingSource()
        buffer = capture.FrameBuffer(source=source, fps=10, buffer_seconds=1.0)
        buffer.start()
        first = buffer._thread
        first.join(5.0)
        self.assertFalse(buffer.running, "an exception in the source must end the thread, not hang it")
        self.assertFalse(buffer.camera_open)
        self.assertEqual(source.opens, 1)
        buffer.start()
        self.assertIsNot(buffer._thread, first, "start() must replace a dead thread")
        buffer._thread.join(5.0)
        self.assertEqual(source.opens, 2)
        buffer.stop()

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


class TestDaemonTick(unittest.TestCase):
    """Status file, preview, test-capture markers and config reload driven through ``Daemon.tick``."""

    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.photos = os.path.join(self.folder, "photos")
        self.image = os.path.join(self.folder, "disc.jpg")
        with open(self.image, "wb") as handle:
            handle.write(TINY_JPEG)
        self.cfg = os.path.join(self.folder, "arm.yaml")
        self.write_cfg("CAMERA_ENABLED: true\nCAMERA_LEAD_SECONDS: 0\nCAMERA_DRIVE_REGIONS: \"sr0:0,0,1,1\"\n")
        self.states = {"/dev/sr0": tray.TrayState.TRAY_OPEN, "/dev/sr1": tray.TrayState.DISC_OK}
        self.dmn = None

    def tearDown(self):
        if self.dmn is not None:
            self.dmn.close()
        shutil.rmtree(self.folder)

    def write_cfg(self, extra):
        with open(self.cfg, "w") as handle:
            handle.write(f"DISC_PHOTO_PATH: \"{self.photos}\"\nLOGPATH: \"{self.folder}/logs\"\nCAMERA_FPS: 20\n"
                         f"CAMERA_DEVICE: \"/dev/video7\"\n{extra}")

    def make_daemon(self, watch_config=False):
        self.dmn = daemon.Daemon(daemon.load_config(self.cfg), source=capture.FakeFrameSource(self.image),
                                 drives=["/dev/sr0", "/dev/sr1"], poll_interval=0.01,
                                 config_file=self.cfg if watch_config else None,
                                 status_fn=lambda devpath: self.states[devpath])
        self.dmn.status_interval = 0
        self.dmn.preview_interval = 0
        return self.dmn

    def read_status(self):
        with open(os.path.join(self.photos, daemon.STATUS_FILE)) as handle:
            return json.load(handle)

    def test_status_file_contents_when_enabled(self):
        dmn = self.make_daemon()
        dmn.tick()
        self.assertTrue(dmn.buffer.wait_for_frame(5.0))
        dmn.tick()
        status = self.read_status()
        self.assertTrue(status["running"])
        self.assertTrue(status["enabled"])
        self.assertTrue(status["camera_open"])
        self.assertEqual(status["device"], "/dev/video7")
        self.assertEqual(status["drives"], ["sr0", "sr1"])
        self.assertEqual(status["tray_state"], {"sr0": "TRAY_OPEN", "sr1": "DISC_OK"})
        self.assertEqual(status["lead_seconds"], 0)
        self.assertEqual(status["fps"], 20)
        self.assertEqual(status["regions"], {"sr0": [0, 0, 1, 1]})
        self.assertEqual(status["pid"], os.getpid())
        self.assertGreaterEqual(status["frames_read"], 1)
        self.assertIsNotNone(status["last_frame_age_seconds"])
        self.assertIn(status["frame_width"], (None, 1))  # 1 with OpenCV decoding the fake frame, None without
        self.assertAlmostEqual(status["timestamp"], time.time(), delta=5)
        self.assertEqual(status["last_photo"], {})
        self.assertFalse(any(f.endswith(".tmp") for f in os.listdir(self.photos)))

    def test_status_file_in_disabled_mode(self):
        self.write_cfg("CAMERA_ENABLED: false\n")
        dmn = self.make_daemon()
        dmn.tick()
        status = self.read_status()
        self.assertFalse(status["running"])
        self.assertFalse(status["enabled"])
        self.assertFalse(status["camera_open"])
        self.assertFalse(dmn.buffer.running, "camera must stay closed while disabled")

    def test_dying_capture_thread_is_restarted_with_backoff(self):
        source = FailingSource()
        dmn = self.dmn = daemon.Daemon(daemon.load_config(self.cfg), source=source, drives=["/dev/sr0"],
                                       status_fn=lambda devpath: self.states[devpath])

        def tick_and_settle(now):
            dmn.tick(now)
            if dmn.buffer._thread is not None:
                dmn.buffer._thread.join(5.0)

        tick_and_settle(100.0)
        self.assertEqual(source.opens, 1)
        self.assertFalse(dmn.buffer.running)
        tick_and_settle(100.25)
        tick_and_settle(100.5)
        self.assertEqual(source.opens, 1, "no restart before the 1s backoff")
        tick_and_settle(101.1)
        self.assertEqual(source.opens, 2)
        tick_and_settle(102.5)
        self.assertEqual(source.opens, 2, "second backoff is 2s")
        tick_and_settle(103.2)
        self.assertEqual(source.opens, 3)
        self.assertFalse(self.read_status()["camera_open"])
        # disabling resets the backoff so a re-enable starts at once
        dmn.enabled = False
        dmn.tick(103.3)
        dmn.enabled = True
        tick_and_settle(103.4)
        self.assertEqual(source.opens, 4)

    def test_disabled_daemon_writes_status_rarely_and_on_change(self):
        self.write_cfg("CAMERA_ENABLED: false\n")
        dmn = self.make_daemon(watch_config=True)
        writes = []
        original = dmn.write_status
        dmn.write_status = lambda *args, **kwargs: writes.append(args) or original(*args, **kwargs)
        dmn.tick(1000.0)
        self.assertEqual(len(writes), 1, "first tick writes")
        for step in (1.0, 2.0, 30.0, 59.0):
            dmn.tick(1000.0 + step)
        self.assertEqual(len(writes), 1, "idle: no rewrite every second")
        dmn.tick(1000.0 + dmn.idle_status_interval + 0.5)
        self.assertEqual(len(writes), 2)
        time.sleep(0.02)
        self.write_cfg("CAMERA_ENABLED: false\nCAMERA_LEAD_SECONDS: 3\n")
        dmn.tick(1000.0 + dmn.idle_status_interval + 1.0)
        self.assertEqual(len(writes), 3, "a config change is written straight away")
        self.assertEqual(self.read_status()["lead_seconds"], 3)

    def test_ui_test_capture_does_not_claim_pending_scan(self):
        dmn = self.make_daemon()
        dmn.tick(10.0)
        self.assertTrue(dmn.buffer.wait_for_frame(5.0))
        dmn.scans.hold("085391163926", now=10.0)
        Path(os.path.join(self.photos, ".capture_sr1")).touch()
        dmn.tick(11.0)
        names = sorted(f for f in os.listdir(self.photos) if not f.startswith("."))
        self.assertEqual(len(names), 1)
        self.assertTrue(names[0].endswith(".jpg"), "the test capture saves a photo only")
        self.assertEqual(dmn.scans.peek(now=12.0), "085391163926", "a UI test capture must not use up the scan")
        self.assertEqual(self.read_status()["pending_scan"], "085391163926")
        # a real tray close claims it
        self.states["/dev/sr0"] = tray.TrayState.DISC_OK
        dmn.tick(13.0)
        names = sorted(f for f in os.listdir(self.photos) if not f.startswith("."))
        self.assertEqual([n.rsplit(".", 1)[1] for n in names], ["barcode", "jpg", "jpg"])
        self.assertIsNone(dmn.scans.peek(now=14.0))
        status = self.read_status()
        self.assertEqual(status["last_barcode"], {"sr0": "085391163926"})
        self.assertIsNone(status["pending_scan"])

    def test_barcode_only_mode_watches_trays_without_camera(self):
        self.write_cfg("CAMERA_ENABLED: false\nBARCODE_ENABLED: true\nBARCODE_DEVICE: /nonexistent/input/event9\n")
        dmn = self.make_daemon(watch_config=True)
        self.assertTrue(dmn.barcode_enabled)
        self.assertIsNotNone(dmn.reader, "a configured device is used as given")
        self.assertEqual(dmn.reader.device, "/nonexistent/input/event9")
        dmn.tick(10.0)
        self.assertFalse(dmn.buffer.running, "no camera in barcode-only mode")
        dmn.scans.hold("5050582868043", now=10.0)
        self.states["/dev/sr0"] = tray.TrayState.DISC_OK
        dmn.tick(11.0)
        names = [f for f in os.listdir(self.photos) if not f.startswith(".")]
        self.assertEqual(len(names), 1)
        self.assertRegex(names[0], r"^sr0_\d{8}-\d{6}\.barcode$")
        status = self.read_status()
        self.assertFalse(status["running"])
        self.assertTrue(status["barcode_enabled"])
        self.assertEqual(status["barcode_device"], "/nonexistent/input/event9")
        # turning the scanner off at runtime releases it
        time.sleep(0.02)
        self.write_cfg("CAMERA_ENABLED: false\nBARCODE_ENABLED: false\n")
        dmn.tick(12.0)
        self.assertIsNone(dmn.reader)
        self.assertFalse(self.read_status()["barcode_enabled"])

    def test_preview_written_while_requested_and_stops_when_stale(self):
        dmn = self.make_daemon()
        request_file = os.path.join(self.photos, daemon.PREVIEW_REQUEST_FILE)
        preview = os.path.join(self.photos, daemon.PREVIEW_FILE)
        dmn.tick()
        self.assertTrue(dmn.buffer.wait_for_frame(5.0))
        dmn.tick()
        self.assertFalse(os.path.exists(preview), "no preview without a request")
        self.assertFalse(dmn.preview_requested())
        Path(request_file).touch()
        self.assertTrue(dmn.preview_requested())
        dmn.tick()
        self.assertTrue(os.path.isfile(preview))
        with open(preview, "rb") as handle:
            self.assertTrue(handle.read(2) == b"\xff\xd8")
        # request goes stale: no more preview frames
        stale = time.time() - daemon.PREVIEW_REQUEST_MAX_AGE - 5
        os.utime(request_file, (stale, stale))
        os.remove(preview)
        self.assertFalse(dmn.preview_requested())
        dmn.tick()
        self.assertFalse(os.path.exists(preview))

    def test_capture_trigger_file_saves_photo_and_is_removed(self):
        dmn = self.make_daemon()
        dmn.tick()
        self.assertTrue(dmn.buffer.wait_for_frame(5.0))
        trigger = os.path.join(self.photos, ".capture_sr1")
        ignored = os.path.join(self.photos, ".capture_video0")
        Path(trigger).touch()
        Path(ignored).touch()
        dmn.tick()
        self.assertFalse(os.path.exists(trigger))
        self.assertTrue(os.path.exists(ignored), "only .capture_srN markers are consumed")
        photos = [f for f in os.listdir(self.photos) if f.endswith(".jpg") and not f.startswith(".")]
        self.assertEqual(len(photos), 1)
        self.assertRegex(photos[0], r"^sr1_\d{8}-\d{6}\.jpg$")
        self.assertEqual(self.read_status()["last_photo"], {"sr1": photos[0]})

    def test_config_reload_toggles_capture_and_applies_settings(self):
        self.write_cfg("CAMERA_ENABLED: false\n")
        dmn = self.make_daemon(watch_config=True)
        dmn.tick()
        self.assertFalse(dmn.enabled)
        self.assertFalse(dmn.buffer.running)
        self.assertEqual(dmn.check_config(), {}, "unchanged file must not reload")

        time.sleep(0.02)
        self.write_cfg("CAMERA_ENABLED: true\nCAMERA_LEAD_SECONDS: \"0.5\"\n"
                       "CAMERA_DRIVE_REGIONS: \"sr0:10,20,30,40;sr1:1,2,3,4\"\nCAMERA_BUFFER_SECONDS: 6\n")
        changes = dmn.check_config()
        self.assertEqual(set(changes), {"CAMERA_ENABLED", "CAMERA_LEAD_SECONDS", "CAMERA_DRIVE_REGIONS",
                                        "CAMERA_BUFFER_SECONDS"})
        self.assertEqual(changes["CAMERA_ENABLED"], (False, True))
        self.assertTrue(dmn.enabled)
        self.assertEqual(dmn.lead_seconds, 0.5)
        self.assertEqual(dmn.regions, {"sr0": (10, 20, 30, 40), "sr1": (1, 2, 3, 4)})
        self.assertEqual(dmn.buffer.buffer_seconds, 6)
        dmn.tick()
        self.assertTrue(dmn.buffer.running, "enabling at runtime starts capturing")
        self.assertTrue(self.read_status()["running"])

        time.sleep(0.02)
        self.write_cfg("CAMERA_ENABLED: false\n")
        dmn.tick()
        self.assertFalse(dmn.enabled)
        self.assertFalse(dmn.buffer.running, "disabling at runtime releases the camera")
        self.assertFalse(self.read_status()["running"])

    def test_config_reload_skips_half_written_file(self):
        dmn = self.make_daemon(watch_config=True)
        time.sleep(0.02)
        with open(self.cfg, "w") as handle:
            handle.write("CAMERA_ENABLED: [unterminated\n")
        self.assertEqual(dmn.check_config(), {})
        self.assertTrue(dmn.enabled, "a broken file must not change the running settings")
        time.sleep(0.02)
        self.write_cfg("CAMERA_ENABLED: false\n")
        self.assertIn("CAMERA_ENABLED", dmn.check_config())


class TestDaemonBarcode(unittest.TestCase):
    """Barcode handling through ``Daemon.handle`` and the CLI, without camera or scanner hardware."""

    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.photos = os.path.join(self.folder, "photos")
        self.image = os.path.join(self.folder, "disc.jpg")
        with open(self.image, "wb") as handle:
            handle.write(TINY_JPEG)
        self.cfg = os.path.join(self.folder, "arm.yaml")
        with open(self.cfg, "w") as handle:
            handle.write(f"CAMERA_ENABLED: false\nBARCODE_ENABLED: false\nDISC_PHOTO_PATH: \"{self.photos}\"\n"
                         f"LOGPATH: \"{self.folder}/logs\"\nCAMERA_FPS: 20\nCAMERA_LEAD_SECONDS: 0\n"
                         f"BARCODE_PAIR_SECONDS: 60\n")

    def tearDown(self):
        shutil.rmtree(self.folder)

    def _close(self, devname="sr0", now=None):
        return tray.TrayTransition(devname, tray.TrayState.TRAY_OPEN, tray.TrayState.DISC_OK,
                                   time.monotonic() if now is None else now)

    def _daemon(self, **kwargs):
        return daemon.Daemon(daemon.load_config(self.cfg), drives=[], **kwargs)

    def test_save_barcode_writes_plain_text_atomically(self):
        path = daemon.save_barcode("085391163926", self._close("sr3"), self.photos)
        self.assertRegex(os.path.basename(path), r"^sr3_\d{8}-\d{6}\.barcode$")
        with open(path) as handle:
            self.assertEqual(handle.read(), "085391163926\n")
        self.assertEqual(os.listdir(self.photos), [os.path.basename(path)])

    def test_everything_off_saves_nothing_on_close(self):
        dmn = self._daemon()
        self.assertFalse(dmn.enabled)
        self.assertFalse(dmn.barcode_enabled)
        self.assertIsNone(dmn.reader)
        self.assertEqual(dmn.scans.pair_seconds, 60)
        self.assertIsNone(dmn.handle(self._close()))
        self.assertFalse(os.path.exists(self.photos))

    def test_pending_scan_is_written_on_tray_close(self):
        dmn = self._daemon()
        dmn.scans.hold("085391163926", now=100.0)
        saved = dmn.handle(self._close("sr1", now=130.0))
        self.assertIsNotNone(saved)
        self.assertRegex(os.path.basename(saved), r"^sr1_\d{8}-\d{6}\.barcode$")
        self.assertEqual(os.listdir(self.photos), [os.path.basename(saved)], "no photo while the camera is off")
        # claimed: a second close gets nothing
        self.assertIsNone(dmn.handle(self._close("sr1", now=131.0)))

    def test_expired_scan_is_not_written(self):
        dmn = self._daemon()
        dmn.scans.hold("085391163926", now=100.0)
        self.assertIsNone(dmn.handle(self._close("sr1", now=100.0 + 60.1)))
        self.assertFalse(os.path.exists(self.photos))

    def test_tray_open_does_not_claim_scan(self):
        dmn = self._daemon()
        dmn.scans.hold("085391163926", now=100.0)
        opened = tray.TrayTransition("sr0", tray.TrayState.NO_DISC, tray.TrayState.TRAY_OPEN, 101.0)
        self.assertIsNone(dmn.handle(opened))
        self.assertEqual(dmn.scans.peek(now=102.0), "085391163926")

    def test_camera_and_barcode_together_save_both(self):
        dmn = self._daemon(source=capture.FakeFrameSource(self.image), force_enabled=True)
        dmn.scans.hold("5050582868043")
        saved = dmn.simulate_close("sr2")
        self.assertIsNotNone(saved)
        names = sorted(os.listdir(self.photos))
        self.assertEqual(len(names), 2)
        self.assertRegex(names[0], r"^sr2_\d{8}-\d{6}\.barcode$")
        self.assertRegex(names[1], r"^sr2_\d{8}-\d{6}\.jpg$")

    def test_cli_scan_and_simulate_close(self):
        rc = daemon.main(["--config", self.cfg, "--scan", "085391163926", "--simulate-close", "sr0"])
        self.assertEqual(rc, 0)
        files = os.listdir(self.photos)
        self.assertEqual(len(files), 1)
        self.assertRegex(files[0], r"^sr0_\d{8}-\d{6}\.barcode$")
        with open(os.path.join(self.photos, files[0])) as handle:
            self.assertEqual(handle.read().strip(), "085391163926")

    def test_cli_rejects_bad_scan(self):
        rc = daemon.main(["--config", self.cfg, "--scan", "no", "--simulate-close", "sr0"])
        self.assertEqual(rc, 1)
        self.assertFalse(os.path.exists(self.photos))


if __name__ == '__main__':
    unittest.main()
