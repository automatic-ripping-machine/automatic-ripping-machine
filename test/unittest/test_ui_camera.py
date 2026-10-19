"""
Flask test-client smoke tests for the disc camera setup page (arm/ui/camera).

Importing ``arm.ui`` loads the ARM config, the Flask app and the SQLite database, so this
module builds a throwaway config under a temp folder first (unless ARM_CONFIG_FILE is already
set) and skips itself when the ARM package cannot be imported, e.g. on a machine without the
Linux libraries ARM needs. Run it in the ARM Docker image or on an ARM install.
"""
import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
TINY_JPEG = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707070909080a0c140d0c0b0b0c1912130f14"
    "1d1a1f1e1d1a1c1c20242e2720222c231c1c2837292c30313434341f27393d38323c2e333432ffc0000b080001000101011100"
    "ffc40014000100000000000000000000000000000009ffc40014100100000000000000000000000000000000ffda0008010100"
    "003f00d2cf20ffd9"
)

_TEMP_ROOT = None
if "ARM_CONFIG_FILE" not in os.environ:
    _TEMP_ROOT = tempfile.mkdtemp(prefix="arm-ui-test-")
    for sub in ("logs", "db", "photos"):
        os.makedirs(os.path.join(_TEMP_ROOT, sub))
    with open(REPO_ROOT / "setup" / "arm.yaml") as _handle:
        _template = yaml.safe_load(_handle)
    _template.update({
        "INSTALLPATH": str(REPO_ROOT),
        "DBFILE": os.path.join(_TEMP_ROOT, "db", "arm.db"),
        "LOGPATH": os.path.join(_TEMP_ROOT, "logs") + "/",
        "ABCDE_CONFIG_FILE": str(REPO_ROOT / "setup" / ".abcde.conf"),
        "DISC_PHOTO_PATH": os.path.join(_TEMP_ROOT, "photos") + "/",
        "DISABLE_LOGIN": True,
        "CAMERA_DRIVES": "sr0,sr1",
    })
    with open(os.path.join(_TEMP_ROOT, "arm.yaml"), "w") as _handle:
        yaml.safe_dump(_template, _handle)
    os.environ["ARM_CONFIG_FILE"] = os.path.join(_TEMP_ROOT, "arm.yaml")

try:
    import arm.config.config as cfg
    from arm.ui import app
    import arm.ui.routes  # noqa: F401  (creates the database and the UI settings row like runui.py does)
    from arm.ui.camera import camera as camera_bp
    IMPORT_ERROR = None
except Exception as error:  # pragma: no cover - depends on the host
    IMPORT_ERROR = error


def tearDownModule():
    if _TEMP_ROOT:
        shutil.rmtree(_TEMP_ROOT, ignore_errors=True)


@unittest.skipIf(IMPORT_ERROR is not None, f"ARM web UI cannot be imported here: {IMPORT_ERROR}")
class TestCameraPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        app.config["LOGIN_DISABLED"] = True
        cls.client = app.test_client()

    def setUp(self):
        self.photos = Path(cfg.arm_config["DISC_PHOTO_PATH"])
        self.photos.mkdir(parents=True, exist_ok=True)
        for entry in self.photos.iterdir():
            entry.unlink()

    def write_status(self, **extra):
        status = {"running": True, "enabled": True, "camera_open": True, "device": "/dev/video0",
                  "frame_width": 1280, "frame_height": 720, "fps": 5, "buffer_seconds": 4, "frames_read": 42,
                  "last_frame_age_seconds": 0.2, "drives": ["sr0", "sr1"],
                  "tray_state": {"sr0": "TRAY_OPEN", "sr1": "DISC_OK"},
                  "last_photo": {"sr0": "sr0_20261018-120000.jpg"}, "lead_seconds": 1.5,
                  "regions": {"sr0": [10, 20, 300, 200]}, "photo_dir": str(self.photos), "pid": 4242,
                  "timestamp": time.time()}
        status.update(extra)
        with open(self.photos / camera_bp.STATUS_FILE, "w") as handle:
            json.dump(status, handle)
        return status

    def test_page_renders_without_daemon(self):
        response = self.client.get("/camera")
        self.assertEqual(response.status_code, 200)
        html = response.data.decode()
        self.assertIn("Disc Camera", html)
        self.assertIn("Daemon not running", html)
        self.assertIn('name="CAMERA_LEAD_SECONDS"', html)
        self.assertIn('name="CAMERA_DRIVE_REGIONS"', html)
        self.assertIn("Enable the disc camera daemon.", html, "comments.json help text is shown")
        self.assertIn('data-capture="sr0"', html)
        self.assertIn("No disc photos yet", html)
        # nav link
        self.assertIn('href="camera"', html)

    def test_page_renders_with_status_and_gallery(self):
        self.write_status()
        with open(self.photos / "sr0_20261018-120000.jpg", "wb") as handle:
            handle.write(TINY_JPEG)
        with open(self.photos / "not-a-photo.jpg", "wb") as handle:
            handle.write(TINY_JPEG)
        response = self.client.get("/camera")
        self.assertEqual(response.status_code, 200)
        html = response.data.decode()
        self.assertIn(">Running<", html)
        self.assertIn("1280&times;720", html)
        self.assertIn("TRAY_OPEN", html)
        self.assertIn("camera/photo?name=sr0_20261018-120000.jpg", html)
        self.assertNotIn("not-a-photo.jpg", html)

    def test_status_endpoint(self):
        response = self.client.get("/camera/status")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertFalse(data["running"])
        self.assertFalse(data["found"])
        self.assertIn("no-store", response.headers["Cache-Control"])

        self.write_status()
        data = self.client.get("/camera/status").get_json()
        self.assertTrue(data["running"])
        self.assertTrue(data["found"])
        self.assertFalse(data["stale"])
        self.assertEqual(data["drives"], ["sr0", "sr1"])
        self.assertEqual(data["regions"], {"sr0": [10, 20, 300, 200]})

        # an old status file means the daemon died
        stale = time.time() - 60
        os.utime(self.photos / camera_bp.STATUS_FILE, (stale, stale))
        data = self.client.get("/camera/status").get_json()
        self.assertTrue(data["stale"])
        self.assertFalse(data["running"])

    def test_capture_creates_trigger_file(self):
        response = self.client.post("/camera/capture?drive=sr1")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertIsNotNone(data["warning"], "no daemon status: warn the user")
        self.assertTrue((self.photos / ".capture_sr1").is_file())

        self.write_status()
        self.assertIsNone(self.client.post("/camera/capture?drive=sr0").get_json()["warning"])
        for bad in ("video0", "../sr0", "", "sr"):
            self.assertEqual(self.client.post(f"/camera/capture?drive={bad}").status_code, 400, bad)
        self.assertEqual(self.client.get("/camera/capture?drive=sr0").status_code, 405)

    def test_keepalive_touches_request_file(self):
        marker = self.photos / camera_bp.PREVIEW_REQUEST_FILE
        self.assertFalse(marker.exists())
        self.assertTrue(self.client.get("/camera/preview/keepalive").get_json()["success"])
        self.assertTrue(marker.is_file())
        first = marker.stat().st_mtime_ns
        time.sleep(0.01)
        self.assertTrue(self.client.post("/camera/preview/keepalive").get_json()["success"])
        self.assertGreater(marker.stat().st_mtime_ns, first)

    def test_preview_serves_placeholder_then_frame(self):
        response = self.client.get("/camera/preview.jpg")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "image/png")
        self.assertEqual(response.headers["X-ARM-Preview"], "placeholder")
        self.assertIn("no-store", response.headers["Cache-Control"])
        self.assertTrue(response.data.startswith(b"\x89PNG"))

        preview = self.photos / camera_bp.PREVIEW_FILE
        with open(preview, "wb") as handle:
            handle.write(TINY_JPEG)
        response = self.client.get("/camera/preview.jpg")
        self.assertEqual(response.mimetype, "image/jpeg")
        self.assertEqual(response.headers["X-ARM-Preview"], "live")
        self.assertEqual(response.data, TINY_JPEG)

        old = time.time() - camera_bp.STALE_PREVIEW_SECONDS - 10
        os.utime(preview, (old, old))
        self.assertEqual(self.client.get("/camera/preview.jpg").headers["X-ARM-Preview"], "placeholder")

    def test_photo_route_only_serves_disc_photos_inside_folder(self):
        with open(self.photos / "sr0_20261018-120000.jpg", "wb") as handle:
            handle.write(TINY_JPEG)
        response = self.client.get("/camera/photo?name=sr0_20261018-120000.jpg")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "image/jpeg")
        self.assertEqual(response.data, TINY_JPEG)
        for bad in ("../arm.yaml", ".camera_status.json", "sr0.jpg", "sr0_20261018-120000.jpg.tmp", "",
                    "sr0_20261018-999999.jpg"):
            self.assertEqual(self.client.get(f"/camera/photo?name={bad}").status_code, 404, bad)

    def read_yaml(self):
        with open(cfg.arm_config_path) as handle:
            return yaml.safe_load(handle)

    def test_save_rewrites_only_camera_keys(self):
        before = self.read_yaml()
        with open(cfg.arm_config_path) as handle:
            before_text = handle.read()
        self.assertFalse(before["CAMERA_ENABLED"])
        form = {
            "CAMERA_ENABLED": "y",
            "CAMERA_DEVICE": "/dev/video2",
            "CAMERA_DRIVES": "/dev/sr0, sr2",
            "CAMERA_DRIVE_REGIONS": " sr2:5,6,70,80; sr0:1,2,3,4 ",
            "CAMERA_FPS": "10",
            "CAMERA_BUFFER_SECONDS": "6",
            "CAMERA_LEAD_SECONDS": "2.5",
            "CAMERA_JPEG_QUALITY": "90",
            "DISC_PHOTO_PATH": cfg.arm_config["DISC_PHOTO_PATH"],
            "DISC_PHOTO_MAX_AGE": "240",
            "DISC_PHOTO_RETENTION_DAYS": "7",
            # DISC_PHOTO_OCR unchecked -> false
            "DISC_PHOTO_COPY": "y",
        }
        response = self.client.post("/camera/save", data=form)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/camera"))

        after = self.read_yaml()
        self.assertIs(after["CAMERA_ENABLED"], True)
        self.assertIs(after["DISC_PHOTO_OCR"], False)
        self.assertIs(after["DISC_PHOTO_COPY"], True)
        self.assertEqual(after["CAMERA_FPS"], 10)
        self.assertEqual(after["CAMERA_JPEG_QUALITY"], 90)
        self.assertEqual(after["DISC_PHOTO_MAX_AGE"], 240)
        self.assertEqual(after["CAMERA_DEVICE"], "/dev/video2")
        self.assertEqual(after["CAMERA_DRIVES"], "sr0,sr2")
        self.assertEqual(after["CAMERA_DRIVE_REGIONS"], "sr0:1,2,3,4;sr2:5,6,70,80")
        # ARM writes non-integer numbers quoted; the daemon casts them back
        self.assertEqual(after["CAMERA_LEAD_SECONDS"], "2.5")
        self.assertEqual(float(after["CAMERA_LEAD_SECONDS"]), 2.5)
        # everything else is untouched, comments included
        camera_keys = set(camera_bp.CAMERA_KEYS)
        self.assertEqual({k: v for k, v in before.items() if k not in camera_keys},
                         {k: v for k, v in after.items() if k not in camera_keys})
        with open(cfg.arm_config_path) as handle:
            after_text = handle.read()
        self.assertIn("##               DISC CAMERA                   ##", after_text)
        self.assertIn("# Enable the disc camera daemon.", after_text)
        self.assertEqual(before_text.count("\n#"), after_text.count("\n#"), "comment lines preserved")
        # the running config was reloaded
        self.assertIs(cfg.arm_config["CAMERA_ENABLED"], True)
        self.assertEqual(self.client.get("/camera/status").get_json()["enabled"], True)

        # and the page shows the new values
        html = self.client.get("/camera").data.decode()
        self.assertIn('value="sr0:1,2,3,4;sr2:5,6,70,80"', html)
        self.assertIn('value="2.5"', html)

    def test_save_rejects_bad_values_and_leaves_file_alone(self):
        before = self.read_yaml()
        base = {"CAMERA_DEVICE": "/dev/video0", "CAMERA_DRIVES": "", "CAMERA_DRIVE_REGIONS": "",
                "CAMERA_FPS": "5", "CAMERA_BUFFER_SECONDS": "4", "CAMERA_LEAD_SECONDS": "1.5",
                "CAMERA_JPEG_QUALITY": "85", "DISC_PHOTO_PATH": "/tmp/x/", "DISC_PHOTO_MAX_AGE": "180",
                "DISC_PHOTO_RETENTION_DAYS": "14"}
        for broken in ({"CAMERA_LEAD_SECONDS": "9"},                 # longer than the buffer
                       {"CAMERA_FPS": "fast"},
                       {"CAMERA_JPEG_QUALITY": "101"},
                       {"CAMERA_DRIVE_REGIONS": "sr0:1,2,3"},
                       {"CAMERA_DRIVES": "video0"},
                       {"CAMERA_DEVICE": ""}):
            response = self.client.post("/camera/save", data={**base, **broken}, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn("Camera settings not saved", response.data.decode(), str(broken))
            self.assertEqual(self.read_yaml(), before, str(broken))

    def test_routes_require_login_when_enabled(self):
        app.config["LOGIN_DISABLED"] = False
        try:
            for path in ("/camera", "/camera/status", "/camera/preview.jpg", "/camera/photo?name=x",
                         "/camera/preview/keepalive", "/camera/photos"):
                response = self.client.get(path)
                self.assertIn(response.status_code, (302, 401), path)
            self.assertIn(self.client.post("/camera/capture?drive=sr0").status_code, (302, 401))
            self.assertIn(self.client.post("/camera/save", data={}).status_code, (302, 401))
        finally:
            app.config["LOGIN_DISABLED"] = True


if __name__ == '__main__':
    unittest.main()
