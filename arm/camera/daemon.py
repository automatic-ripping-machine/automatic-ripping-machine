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
import logging
import logging.handlers
import os
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
    """Wires the tray watcher and the frame buffer together."""

    def __init__(self, config: Dict, source=None, drives=None, poll_interval: float = 0.25):
        self.config = config
        self.poll_interval = poll_interval
        self.photo_dir = str(config.get("DISC_PHOTO_PATH") or DEFAULTS["DISC_PHOTO_PATH"])
        self.lead_seconds = as_number(config.get("CAMERA_LEAD_SECONDS"), 1.5)
        self.quality = as_number(config.get("CAMERA_JPEG_QUALITY"), 85, int)
        self.regions = parse_regions(config.get("CAMERA_DRIVE_REGIONS", ""))
        fps = as_number(config.get("CAMERA_FPS"), 5)
        buffer_seconds = as_number(config.get("CAMERA_BUFFER_SECONDS"), 4)
        self.source = source or capture.CameraSource(str(config.get("CAMERA_DEVICE") or "/dev/video0"))
        self.buffer = capture.FrameBuffer(self.source, fps=fps, buffer_seconds=buffer_seconds)
        self.drives = drives if drives is not None else tray.discover_drives(str(config.get("CAMERA_DRIVES") or ""))
        self.watcher = tray.TrayWatcher(self.drives)
        self._running = False

    def handle(self, transition: tray.TrayTransition) -> Optional[str]:
        if tray.is_tray_close(transition):
            return save_photo(self.buffer, transition, self.photo_dir, self.lead_seconds,
                              self.regions, self.quality)
        return None

    def stop(self, *_args) -> None:
        self._running = False

    def run(self) -> int:
        if not self.drives:
            logging.warning("No optical drives found to watch (CAMERA_DRIVES is blank and no /dev/sr* present)")
        logging.info(f"Watching {', '.join(self.drives) or 'nothing'}; photos go to {self.photo_dir}; "
                     f"lead {self.lead_seconds}s; regions {self.regions or 'full frame'}")
        self.buffer.start()
        self._running = True
        try:
            while self._running:
                for transition in self.watcher.poll():
                    try:
                        self.handle(transition)
                    except Exception as error:  # keep the service alive whatever happens
                        logging.error(f"Failed to save disc photo: {error}", exc_info=True)
                time.sleep(self.poll_interval)
        finally:
            self.buffer.stop()
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


def sleep_disabled() -> int:
    """CAMERA_ENABLED is off: idle quietly so runit/systemd do not restart us in a loop."""
    logging.info("CAMERA_ENABLED is false; the disc camera daemon is idle. Enable it in arm.yaml and restart.")
    stop = {"flag": False}

    def _stop(*_args):
        stop["flag"] = True

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    while not stop["flag"]:
        time.sleep(5)
    return 0


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
    if args.photo_dir:
        config["DISC_PHOTO_PATH"] = args.photo_dir
    setup_logging(str(config.get("LOGPATH") or DEFAULTS["LOGPATH"]), str(config.get("LOGLEVEL") or "INFO"))

    testing = bool(args.frames_from or args.simulate_close or args.force)
    if not as_bool(config.get("CAMERA_ENABLED", False)) and not testing:
        return sleep_disabled()

    source = capture.FakeFrameSource(args.frames_from) if args.frames_from else None
    drives = tray.discover_drives(args.drives) if args.drives else None
    daemon = Daemon(config, source=source, drives=drives, poll_interval=args.poll_interval)

    if args.simulate_close:
        saved = daemon.simulate_close(os.path.basename(args.simulate_close))
        return 0 if saved else 1

    signal.signal(signal.SIGTERM, daemon.stop)
    signal.signal(signal.SIGINT, daemon.stop)
    return daemon.run()


if __name__ == "__main__":
    sys.exit(main())
