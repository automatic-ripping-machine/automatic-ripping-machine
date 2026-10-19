#!/usr/bin/env python3
"""
USB barcode scanner input for the disc camera daemon.

Handheld scanners such as the Eyoyo EY-H2 enumerate as a USB keyboard and "type" the code
followed by Enter. On a headless ARM box nothing has keyboard focus, so the daemon reads the
scanner straight from its ``/dev/input/event*`` node with ``evdev`` and grabs it exclusively,
which also stops the digits landing on a console.

Three pieces live here, kept apart so they can be tested without a scanner:

* ``ScanDecoder`` turns key events into complete scans.
* ``ScanHolder`` keeps the most recent scan until a tray closes (or it expires).
* ``BarcodeReader`` is the thread that owns the device and feeds the decoder.

``evdev`` is imported lazily so the rest of the daemon (and the tests) work without it.
"""
import glob
import logging
import os
import re
import select
import threading
import time
from typing import Callable, List, Optional, Tuple

SCAN_RE = re.compile(r"^[0-9A-Za-z\-]{4,32}$")
"""What a plausible barcode looks like: UPC/EAN are 8 to 14 digits, ISBN/Code128 may carry letters."""

DEVICE_NAME_HINT = re.compile(r"(eyoyo|barcode|bar_code|scanner)", re.IGNORECASE)
"""Substrings that identify a scanner in ``/dev/input/by-id`` names or evdev device names."""

# Key names (as evdev reports them) to the character they produce, unshifted and shifted
_KEY_CHARS = {
    **{f"KEY_{d}": (d, ")!@#$%^&*("[int(d)]) for d in "0123456789"},
    **{f"KEY_{c}": (c.lower(), c) for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"},
    "KEY_MINUS": ("-", "_"),
    "KEY_SPACE": (" ", " "),
    "KEY_DOT": (".", ">"),
    "KEY_SLASH": ("/", "?"),
    "KEY_EQUAL": ("=", "+"),
    "KEY_SEMICOLON": (";", ":"),
    "KEY_APOSTROPHE": ("'", '"'),
    "KEY_COMMA": (",", "<"),
    **{f"KEY_KP{d}": (d, d) for d in "0123456789"},
    "KEY_KPMINUS": ("-", "-"),
    "KEY_KPDOT": (".", "."),
}
_ENTER_KEYS = {"KEY_ENTER", "KEY_KPENTER", "KEY_TAB"}
_SHIFT_KEYS = {"KEY_LEFTSHIFT", "KEY_RIGHTSHIFT"}


def decode_keycode(keycode: str, shift: bool = False) -> Optional[str]:
    """
    Map an evdev key name to the character the scanner meant, or ``None`` for keys we ignore.

    evdev reports a few keys with a list of aliases (``["KEY_ENTER", ...]``); the first is used.
    """
    if isinstance(keycode, (list, tuple)):
        keycode = keycode[0] if keycode else ""
    chars = _KEY_CHARS.get(str(keycode))
    if chars is None:
        return None
    return chars[1] if shift else chars[0]


class ScanDecoder:
    """
    Accumulates key presses into scans.

    Feed it ``(keycode, is_press)`` pairs; ``feed`` returns the completed code when the scanner
    sends its Enter (or Tab) suffix, otherwise ``None``. A long pause between keys resets the
    buffer so a half typed code from an unplug does not glue onto the next scan.
    """

    def __init__(self, idle_reset_seconds: float = 2.0):
        self.idle_reset_seconds = idle_reset_seconds
        self._chars: List[str] = []
        self._shift = False
        self._last_key: Optional[float] = None

    def reset(self) -> None:
        self._chars = []
        self._shift = False

    def feed(self, keycode, is_press: bool, now: Optional[float] = None) -> Optional[str]:
        now = time.monotonic() if now is None else now
        if isinstance(keycode, (list, tuple)):
            keycode = keycode[0] if keycode else ""
        keycode = str(keycode)
        if keycode in _SHIFT_KEYS:
            self._shift = is_press
            return None
        if not is_press:
            return None
        if self._last_key is not None and now - self._last_key > self.idle_reset_seconds:
            self.reset()
        self._last_key = now
        if keycode in _ENTER_KEYS:
            code = "".join(self._chars).strip()
            self.reset()
            return code or None
        char = decode_keycode(keycode, self._shift)
        if char is not None:
            self._chars.append(char)
        return None


def is_valid_scan(code: Optional[str]) -> bool:
    return bool(code) and SCAN_RE.match(str(code)) is not None


class ScanHolder:
    """
    Remembers the latest scan until a tray closes.

    The workflow is "scan the case, put the disc in, close the tray", so whichever drive closes
    next claims the code. A scan older than ``pair_seconds`` is dropped so a case that was scanned
    but never inserted cannot attach itself to a later disc.
    """

    def __init__(self, pair_seconds: float = 120.0, logger=logging):
        self.pair_seconds = pair_seconds
        self._lock = threading.Lock()
        self._scan: Optional[Tuple[str, float]] = None
        self._logger = logger

    def hold(self, code: str, now: Optional[float] = None) -> bool:
        """Keep ``code`` as the pending scan; returns False (and ignores it) when it is not plausible."""
        if not is_valid_scan(code):
            self._logger.warning(f"Ignoring implausible barcode scan {code!r}")
            return False
        now = time.monotonic() if now is None else now
        with self._lock:
            if self._scan is not None and self._scan[0] != code:
                self._logger.info(f"Replacing unused barcode {self._scan[0]} with {code}")
            self._scan = (code, now)
        self._logger.info(f"Barcode scanned: {code} (waiting for a tray to close)")
        return True

    def _current(self, now: float) -> Optional[str]:
        """The pending scan, dropping it when expired. Caller holds the lock."""
        if self._scan is None:
            return None
        code, when = self._scan
        if now - when > self.pair_seconds:
            self._logger.info(f"Barcode {code} expired after {self.pair_seconds:.0f}s without a tray close")
            self._scan = None
            return None
        return code

    def peek(self, now: Optional[float] = None) -> Optional[str]:
        """The pending scan, or ``None`` when there is none or it has expired."""
        now = time.monotonic() if now is None else now
        with self._lock:
            return self._current(now)

    def claim(self, now: Optional[float] = None) -> Optional[str]:
        """Take the pending scan (clearing it), or ``None``."""
        now = time.monotonic() if now is None else now
        # One lock acquisition: a scan held between a separate peek and clear would be lost
        with self._lock:
            code = self._current(now)
            self._scan = None
        return code


def find_scanner_device(configured: str = "", by_id_dir: str = "/dev/input/by-id", logger=logging) -> Optional[str]:
    """
    Work out which input node to read.

    :param configured: ``BARCODE_DEVICE`` from arm.yaml: a path, or blank to autodetect
    :return: a device path, or ``None`` when nothing matched
    """
    configured = str(configured or "").strip()
    if configured:
        return configured
    # Prefer the stable by-id names, which carry the USB product string
    candidates = sorted(glob.glob(os.path.join(by_id_dir, "*-event-kbd")))
    for path in candidates:
        if DEVICE_NAME_HINT.search(os.path.basename(path)):
            return path
    # Fall back to asking evdev for device names
    try:
        import evdev  # pylint: disable=import-outside-toplevel
        for path in sorted(evdev.list_devices()):
            try:
                name = evdev.InputDevice(path).name
            except OSError:
                continue
            if DEVICE_NAME_HINT.search(name or ""):
                return path
    except ImportError:
        logger.debug("evdev is not installed; cannot autodetect the barcode scanner by name")
    if candidates:
        logger.warning(f"No input device looked like a barcode scanner; set BARCODE_DEVICE to one of: "
                       f"{', '.join(candidates)}")
    return None


class BarcodeReader:
    """
    Reads a keyboard-style scanner from ``/dev/input`` on a background thread.

    ``on_scan(code)`` is called for every completed scan. The device is grabbed exclusively; if it
    disappears (unplugged) the thread keeps retrying every ``retry_seconds`` until stopped.
    """

    def __init__(self, device: str, on_scan: Callable[[str], None], retry_seconds: float = 5.0,
                 grab: bool = True, logger=logging):
        self.device = device
        self.on_scan = on_scan
        self.retry_seconds = retry_seconds
        self.grab = grab
        self._logger = logger
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="arm-barcode", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout)
            self._thread = None

    def _run(self) -> None:
        try:
            import evdev  # pylint: disable=import-outside-toplevel
        except ImportError:
            self._logger.error("The evdev package is not installed; barcode scanning is unavailable "
                               "(pip install evdev)")
            return
        while not self._stop.is_set():
            try:
                self._read_until_error(evdev)
            except OSError as error:
                self._logger.warning(f"Barcode scanner {self.device}: {error}; retrying in {self.retry_seconds:.0f}s")
            except Exception as error:  # never let the reader thread die silently
                self._logger.error(f"Barcode reader failed: {error}", exc_info=True)
            self._stop.wait(self.retry_seconds)

    def _read_until_error(self, evdev) -> None:
        decoder = ScanDecoder()
        device = None
        try:
            # Opening and grabbing sit inside the try so a failed grab (EBUSY) still closes the fd
            device = evdev.InputDevice(self.device)
            self._logger.info(f"Reading barcode scanner {self.device} ({device.name})")
            if self.grab:
                device.grab()
            # A short select timeout keeps stop() responsive without busy waiting
            while not self._stop.is_set():
                ready, _, _ = select.select([device.fd], [], [], 0.5)
                if not ready:
                    continue
                for event in device.read():
                    if event.type != evdev.ecodes.EV_KEY:
                        continue
                    key = evdev.categorize(event)
                    if key.keystate not in (key.key_down, key.key_up):
                        continue  # ignore auto-repeat
                    code = decoder.feed(key.keycode, key.keystate == key.key_down)
                    if code:
                        try:
                            self.on_scan(code)
                        except Exception as error:
                            self._logger.error(f"Barcode handler failed for {code}: {error}", exc_info=True)
        finally:
            if device is not None:
                try:
                    if self.grab:
                        device.ungrab()
                except OSError:
                    pass
                device.close()
