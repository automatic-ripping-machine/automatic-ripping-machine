#!/usr/bin/env python3
"""
ARM disc camera daemon.

Keeps a rolling buffer of webcam frames and, when an optical drive tray closes, saves the frame
from ``CAMERA_LEAD_SECONDS`` earlier (the disc sitting in the open tray) as
``DISC_PHOTO_PATH/<srN>_<YYYYmmdd-HHMMSS>.jpg``. The ripper picks that file up when udev starts
a job for the same drive.

Run as a service::

    python3 /opt/arm/arm/camera/daemon.py

Run without hardware (handy for checking the install)::

    python3 /opt/arm/arm/camera/daemon.py --frames-from /path/to/disc.jpg --simulate-close sr0

Config comes from the ARM config file (``ARM_CONFIG_FILE``, default ``/etc/arm/config/arm.yaml``)
merged over the template in ``setup/arm.yaml``. It is read directly rather than through
``arm.config.config`` so that this process never imports the Flask app or touches the database.
"""
import argparse
import datetime
import json
import logging
import logging.handlers
import os
import re
import signal
import sys
import time
from pathlib import Path
from typing import Dict, Optional

import yaml

# Sibling modules are imported by path so that ``arm/__init__.py`` (which pulls in the whole
# ripper and the web UI) is never executed by this process.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import capture  # noqa: E402
import tray  # noqa: E402

INSTALL_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_FILE = os.environ.get("ARM_CONFIG_FILE", "/etc/arm/config/arm.yaml")

DEFAULTS = {
    "CAMERA_ENABLED": False,
    "CAMERA_DEVICE": "/dev/video0",
    "CAMERA_DRIVES": "",
    "CAMERA_DRIVE_REGIONS": "",
    "CAMERA_FPS": 5,
    "CAMERA_BUFFER_SECONDS": 4,
    "CAMERA_LEAD_SECONDS": 1.5,
    "CAMERA_JPEG_QUALITY": 85,
    "DISC_PHOTO_PATH": "/home/arm/media/disc_photos/",
    "LOGPATH": "/home/arm/logs/",
    "LOGLEVEL": "INFO",
}

# Files the daemon shares with the web UI inside DISC_PHOTO_PATH. The UI never talks to the
# daemon directly; it reads the status file and drops marker files that the daemon picks up.
STATUS_FILE = ".camera_status.json"
"""Rewritten about once a second with the daemon's state (see ``Daemon.status``)."""
PREVIEW_REQUEST_FILE = ".preview_requested"
"""Touched by the UI while the setup page is open; the daemon keeps ``PREVIEW_FILE`` fresh meanwhile."""
PREVIEW_FILE = ".preview.jpg"
"""Latest full camera frame with the crop regions drawn on it."""
PREVIEW_REQUEST_MAX_AGE = 10.0
"""Seconds after the last touch of ``PREVIEW_REQUEST_FILE`` before preview frames stop."""
CAPTURE_TRIGGER_RE = re.compile(r"^\.capture_(sr\d+)$")
"""``.capture_sr0`` in the photo folder asks for a photo as if that drive's tray had just closed."""
RELOAD_PREFIXES = ("CAMERA_", "DISC_PHOTO_")
"""Config keys that are re-read from arm.yaml while the daemon runs."""


def load_config(config_file: str = DEFAULT_CONFIG_FILE, template: Optional[Path] = None) -> Dict:
    """
    Load the ARM config: built-in defaults, then ``setup/arm.yaml``, then the user's file.

    Any of the files may be missing; the daemon still starts with defaults.
    """
    merged = dict(DEFAULTS)
    template = template or INSTALL_ROOT / "setup" / "arm.yaml"
    for path in (template, Path(config_file)):
        try:
            with open(path, "r") as handle:
                data = yaml.safe_load(handle) or {}
            merged.update({k: v for k, v in data.items() if v is not None})
        except (OSError, yaml.YAMLError) as error:
            logging.debug(f"Config {path} not loaded: {error}")
    return merged


def read_yaml(path) -> Dict:
    """Parse one YAML mapping file. Raises ``OSError``/``yaml.YAMLError`` so callers can decide what to do."""
    with open(path, "r") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise yaml.YAMLError(f"{path} is not a mapping")
    return data


def write_bytes_atomic(path: str, data: bytes) -> None:
    """Write ``data`` to ``path`` via a temp file and ``os.replace`` so readers never see a partial file."""
    temp_path = f"{path}.tmp"
    with open(temp_path, "wb") as handle:
        handle.write(data)
    os.replace(temp_path, path)


def write_json_atomic(path: str, data: Dict) -> None:
    write_bytes_atomic(path, json.dumps(data, indent=1, sort_keys=True).encode("utf-8"))


def file_age(path: str) -> Optional[float]:
    """Seconds since ``path`` was last modified, or ``None`` when it does not exist."""
    try:
        return max(0.0, time.time() - os.stat(path).st_mtime)
    except OSError:
        return None


def as_bool(value) -> bool:
    """ARM writes booleans back as true/false but the UI may hand us strings."""
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def as_number(value, default, cast=float):
    """Config numbers come back quoted after the settings page saves them."""
    try:
        return cast(value)
    except (TypeError, ValueError):
        return default


def parse_regions(value: str) -> Dict[str, capture.Region]:
    """
    ``CAMERA_DRIVE_REGIONS``: ``sr0:x,y,w,h;sr1:x,y,w,h`` -> ``{"sr0": (x, y, w, h), ...}``.

    Malformed entries are logged and skipped.
    """
    regions: Dict[str, capture.Region] = {}
    if not value or not str(value).strip():
        return regions
    for entry in str(value).split(";"):
        entry = entry.strip()
        if not entry:
            continue
        try:
            name, coords = entry.split(":", 1)
            x, y, w, h = (int(part) for part in coords.split(","))
            regions[os.path.basename(name.strip())] = (x, y, w, h)
        except ValueError:
            logging.warning(f"Ignoring malformed CAMERA_DRIVE_REGIONS entry: {entry!r}")
    return regions


def setup_logging(log_dir: str, level: str) -> None:
    handlers = [logging.StreamHandler(sys.stdout)]
    try:
        os.makedirs(log_dir, exist_ok=True)
        handlers.append(logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, "camera.log"), maxBytes=2_000_000, backupCount=3))
    except OSError as error:
        print(f"Cannot write camera.log in {log_dir}: {error}", file=sys.stderr)
    logging.basicConfig(level=getattr(logging, str(level).upper(), logging.INFO),
                        format="[%(asctime)s] %(levelname)s ARM camera: %(message)s",
                        handlers=handlers, force=True)


def photo_filename(devname: str, when: Optional[datetime.datetime] = None) -> str:
    when = when or datetime.datetime.now()
    return f"{devname}_{when:%Y%m%d-%H%M%S}.jpg"


def save_photo(buffer: capture.FrameBuffer, transition: tray.TrayTransition, photo_dir: str,
               lead_seconds: float, regions: Dict[str, capture.Region], quality: int) -> Optional[str]:
    """
    Write the frame from ``lead_seconds`` before the tray closed for this drive.

    :return: the saved file path, or ``None`` when no frame was available
    """
    frame = buffer.frame_at(transition.timestamp - lead_seconds)
    if frame is None:
        logging.warning(f"{transition.devname}: tray closed but the frame buffer is empty, no photo saved")
        return None
    frame = capture.crop(frame, regions.get(transition.devname))
    data = capture.encode_jpeg(frame, quality)
    os.makedirs(photo_dir, exist_ok=True)
    final_path = os.path.join(photo_dir, photo_filename(transition.devname))
    temp_path = final_path + ".tmp"
    with open(temp_path, "wb") as handle:
        handle.write(data)
    os.replace(temp_path, final_path)
    logging.info(f"{transition.devname}: tray closed, saved disc photo {final_path} ({len(data)} bytes)")
    return final_path


class Daemon:
    """
    Wires the tray watcher and the frame buffer together.

    ``tick()`` does one round of work and is what ``run()`` loops over; tests call it directly.
    Besides saving photos on tray closes it keeps the status file fresh, serves preview frames
    while the setup page asks for them, honours test-capture marker files and re-reads arm.yaml
    when it changes.
    """

    def __init__(self, config: Dict, source=None, drives=None, poll_interval: float = 0.25,
                 config_file: Optional[str] = None, template: Optional[Path] = None,
                 force_enabled: bool = False, overrides: Optional[Dict] = None,
                 status_fn=tray.read_tray_status):
        self.poll_interval = poll_interval
        self.config_file = config_file
        self.template = template or INSTALL_ROOT / "setup" / "arm.yaml"
        self.force_enabled = force_enabled
        self.overrides = dict(overrides or {})
        self.status_interval = 1.0
        self.preview_interval = 1.0
        self.last_photo: Dict[str, str] = {}
        self._injected_source = source
        self._fixed_drives = list(drives) if drives is not None else None
        self._status_fn = status_fn
        self._last_status = -1.0
        self._last_preview = -1.0
        self._status_error_logged = False
        self._idle_logged = False
        self._running = False
        self.config: Dict = {}
        self.drives: list = []
        self.source = None
        self.buffer: Optional[capture.FrameBuffer] = None
        self.watcher: Optional[tray.TrayWatcher] = None
        self._config_stamps = self._config_mtimes()
        self.apply_config(config)

    # -- configuration -------------------------------------------------------------------

    def apply_config(self, config: Dict) -> Dict:
        """
        Take a (re)loaded config into use.

        :return: ``{key: (old, new)}`` for every CAMERA_/DISC_PHOTO_ key whose value changed
        """
        config = dict(config)
        config.update(self.overrides)
        previous = self.config
        changes = {key: (previous.get(key), config.get(key))
                   for key in sorted(set(previous) | set(config))
                   if key.startswith(RELOAD_PREFIXES) and previous.get(key) != config.get(key)}
        self.config = config
        self.enabled = self.force_enabled or as_bool(config.get("CAMERA_ENABLED", False))
        self.photo_dir = str(config.get("DISC_PHOTO_PATH") or DEFAULTS["DISC_PHOTO_PATH"])
        self.lead_seconds = as_number(config.get("CAMERA_LEAD_SECONDS"), 1.5)
        self.quality = as_number(config.get("CAMERA_JPEG_QUALITY"), 85, int)
        self.regions = parse_regions(config.get("CAMERA_DRIVE_REGIONS", ""))
        self.fps = as_number(config.get("CAMERA_FPS"), 5)
        self.buffer_seconds = as_number(config.get("CAMERA_BUFFER_SECONDS"), 4)
        self.device = str(config.get("CAMERA_DEVICE") or "/dev/video0")
        self._apply_source(previous_device=previous.get("CAMERA_DEVICE"))
        drives = (list(self._fixed_drives) if self._fixed_drives is not None
                  else tray.discover_drives(str(config.get("CAMERA_DRIVES") or "")))
        if self.watcher is None or drives != self.drives:
            self.drives = drives
            self.watcher = tray.TrayWatcher(drives, status_fn=self._status_fn)
        return changes

    def _apply_source(self, previous_device) -> None:
        """Create the frame buffer, or swap the camera when CAMERA_DEVICE changed at runtime."""
        if self.buffer is None:
            self.source = self._injected_source or capture.CameraSource(self.device)
            self.buffer = capture.FrameBuffer(self.source, fps=self.fps, buffer_seconds=self.buffer_seconds)
            return
        if self._injected_source is None and previous_device is not None \
                and str(previous_device) != self.device:
            was_running = self.buffer.running
            self.buffer.stop()
            self.source = capture.CameraSource(self.device)
            self.buffer = capture.FrameBuffer(self.source, fps=self.fps, buffer_seconds=self.buffer_seconds)
            if was_running:
                self.buffer.start()
            return
        self.buffer.interval = 1.0 / max(float(self.fps), 0.5)
        self.buffer.buffer_seconds = max(float(self.buffer_seconds), self.buffer.interval)

    def _config_mtimes(self):
        stamps = []
        for path in (self.template, self.config_file):
            try:
                info = os.stat(path) if path else None
                stamps.append((info.st_mtime_ns, info.st_size) if info else None)
            except OSError:
                stamps.append(None)
        return tuple(stamps)

    def check_config(self) -> Dict:
        """Reload arm.yaml when it (or the template) changed on disk. Returns the changes applied."""
        if self.config_file is None:
            return {}
        stamps = self._config_mtimes()
        if stamps == self._config_stamps:
            return {}
        try:
            read_yaml(self.config_file)
        except (OSError, yaml.YAMLError) as error:
            # Probably caught mid-write by the settings page; try again on the next tick
            logging.debug(f"Config {self.config_file} not readable yet: {error}")
            return {}
        self._config_stamps = stamps
        changes = self.apply_config(load_config(self.config_file, self.template))
        if changes:
            for key, (old, new) in changes.items():
                logging.info(f"Config reloaded: {key} changed from {old!r} to {new!r}")
        else:
            logging.debug("Config file changed but no camera settings differ")
        return changes

    # -- photos --------------------------------------------------------------------------

    def handle(self, transition: tray.TrayTransition) -> Optional[str]:
        if tray.is_tray_close(transition):
            saved = save_photo(self.buffer, transition, self.photo_dir, self.lead_seconds,
                               self.regions, self.quality)
            if saved:
                self.last_photo[transition.devname] = os.path.basename(saved)
            return saved
        return None

    def _safe_handle(self, transition: tray.TrayTransition) -> None:
        try:
            self.handle(transition)
        except Exception as error:  # keep the service alive whatever happens
            logging.error(f"Failed to save disc photo: {error}", exc_info=True)

    def pop_capture_triggers(self) -> list:
        """Delete any ``.capture_srN`` marker files in the photo folder and return their drive names."""
        try:
            names = os.listdir(self.photo_dir)
        except OSError:
            return []
        found = []
        for name in sorted(names):
            match = CAPTURE_TRIGGER_RE.match(name)
            if not match:
                continue
            try:
                os.remove(os.path.join(self.photo_dir, name))
            except OSError as error:
                logging.warning(f"Cannot remove capture trigger {name}: {error}")
                continue
            logging.info(f"{match.group(1)}: test capture requested from the web UI")
            found.append(match.group(1))
        return found

    # -- preview -------------------------------------------------------------------------

    def preview_requested(self) -> bool:
        age = file_age(os.path.join(self.photo_dir, PREVIEW_REQUEST_FILE))
        return age is not None and age <= PREVIEW_REQUEST_MAX_AGE

    def write_preview(self) -> bool:
        """Write the newest buffered frame (regions drawn on) to the preview file. False when no frame yet."""
        latest = self.buffer.latest()
        if latest is None:
            return False
        frame = capture.draw_regions(latest[1], self.regions)
        try:
            data = capture.encode_jpeg(frame, self.quality)
            write_bytes_atomic(os.path.join(self.photo_dir, PREVIEW_FILE), data)
        except (OSError, RuntimeError, ImportError) as error:
            logging.warning(f"Cannot write preview frame: {error}")
            return False
        return True

    def _maybe_write_preview(self, now: float) -> None:
        if now - self._last_preview < self.preview_interval or not self.preview_requested():
            return
        if self.write_preview():
            self._last_preview = now

    # -- status --------------------------------------------------------------------------

    def status(self, now: Optional[float] = None, running: Optional[bool] = None) -> Dict:
        """The dictionary written to the status file."""
        now = time.monotonic() if now is None else now
        latest = self.buffer.latest()
        size = capture.frame_size(latest[1]) if latest else None
        return {
            "running": self.enabled if running is None else running,
            "enabled": self.enabled,
            "camera_open": bool(self.buffer.camera_open),
            "device": self.device,
            "frame_width": size[0] if size else None,
            "frame_height": size[1] if size else None,
            "fps": self.fps,
            "buffer_seconds": self.buffer_seconds,
            "frames_read": self.buffer.frames_read,
            "last_frame_age_seconds": round(now - latest[0], 3) if latest else None,
            "drives": [tray.TrayWatcher.devname(d) for d in self.drives],
            "tray_state": self.watcher.states(),
            "last_photo": dict(self.last_photo),
            "lead_seconds": self.lead_seconds,
            "regions": {name: list(region) for name, region in self.regions.items()},
            "photo_dir": self.photo_dir,
            "pid": os.getpid(),
            "timestamp": time.time(),
        }

    def write_status(self, now: Optional[float] = None, running: Optional[bool] = None) -> bool:
        try:
            os.makedirs(self.photo_dir, exist_ok=True)
            write_json_atomic(os.path.join(self.photo_dir, STATUS_FILE), self.status(now, running))
        except OSError as error:
            if not self._status_error_logged:
                logging.warning(f"Cannot write {STATUS_FILE} in {self.photo_dir}: {error}")
                self._status_error_logged = True
            return False
        self._status_error_logged = False
        return True

    # -- main loop -----------------------------------------------------------------------

    def tick(self, now: Optional[float] = None) -> None:
        """One round: reload config if needed, poll trays, honour marker files, refresh status."""
        now = time.monotonic() if now is None else now
        self.check_config()
        if self.enabled:
            if not self.buffer.running:
                logging.info(f"Watching {', '.join(self.drives) or 'nothing'}; photos go to {self.photo_dir}; "
                             f"lead {self.lead_seconds}s; regions {self.regions or 'full frame'}")
                self.buffer.start()
                self._idle_logged = False
            for transition in self.watcher.poll(now):
                self._safe_handle(transition)
            for devname in self.pop_capture_triggers():
                self._safe_handle(tray.TrayTransition(devname, tray.TrayState.TRAY_OPEN, tray.TrayState.DISC_OK, now))
            self._maybe_write_preview(now)
        else:
            if self.buffer.running:
                self.buffer.stop()
                logging.info("CAMERA_ENABLED is now false; camera released")
            if not self._idle_logged:
                logging.info("CAMERA_ENABLED is false; the disc camera daemon is idle until it is enabled in arm.yaml")
                self._idle_logged = True
        if self._last_status < 0 or now - self._last_status >= self.status_interval:
            self.write_status(now)
            self._last_status = now

    def stop(self, *_args) -> None:
        self._running = False

    def run(self) -> int:
        if not self.drives:
            logging.warning("No optical drives found to watch (CAMERA_DRIVES is blank and no /dev/sr* present)")
        self._running = True
        try:
            while self._running:
                self.tick()
                time.sleep(self.poll_interval)
        finally:
            self.buffer.stop()
            self.write_status(running=False)
            logging.info("Camera daemon stopped")
        return 0

    def simulate_close(self, devname: str, wait: float = 5.0) -> Optional[str]:
        """Capture one frame and save it as if ``devname`` had just closed its tray."""
        self.buffer.start()
        try:
            if not self.buffer.wait_for_frame(wait):
                logging.error("No frame captured, cannot simulate a tray close")
                return None
            now = time.monotonic()
            return self.handle(tray.TrayTransition(devname, tray.TrayState.TRAY_OPEN, tray.TrayState.DISC_OK, now))
        finally:
            self.buffer.stop()


def parse_args(argv):
    parser = argparse.ArgumentParser(description="ARM disc camera daemon")
    parser.add_argument("--config", default=DEFAULT_CONFIG_FILE, help="ARM config file (arm.yaml)")
    parser.add_argument("--frames-from", metavar="PATH",
                        help="use an image file or folder of images instead of the camera")
    parser.add_argument("--simulate-close", metavar="SRN",
                        help="save one photo as if this drive's tray just closed, then exit")
    parser.add_argument("--drives", help="override CAMERA_DRIVES (comma separated, e.g. sr0,sr1)")
    parser.add_argument("--photo-dir", help="override DISC_PHOTO_PATH")
    parser.add_argument("--poll-interval", type=float, default=0.25, help="tray poll interval in seconds")
    parser.add_argument("--force", action="store_true", help="run even when CAMERA_ENABLED is false")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    config = load_config(args.config)
    overrides = {"DISC_PHOTO_PATH": args.photo_dir} if args.photo_dir else {}
    config.update(overrides)
    setup_logging(str(config.get("LOGPATH") or DEFAULTS["LOGPATH"]), str(config.get("LOGLEVEL") or "INFO"))

    source = capture.FakeFrameSource(args.frames_from) if args.frames_from else None
    drives = tray.discover_drives(args.drives) if args.drives else None
    # A fake camera means someone is testing: run even when CAMERA_ENABLED is false, like --force
    daemon = Daemon(config, source=source, drives=drives, poll_interval=args.poll_interval,
                    config_file=args.config, force_enabled=bool(args.force or args.frames_from),
                    overrides=overrides)

    if args.simulate_close:
        saved = daemon.simulate_close(os.path.basename(args.simulate_close))
        return 0 if saved else 1

    # When CAMERA_ENABLED is false the loop idles (status file only) until the setting changes,
    # so runit/systemd never restart the service in a loop.
    signal.signal(signal.SIGTERM, daemon.stop)
    signal.signal(signal.SIGINT, daemon.stop)
    return daemon.run()


if __name__ == "__main__":
    sys.exit(main())
