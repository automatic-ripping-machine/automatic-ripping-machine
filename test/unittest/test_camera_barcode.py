"""Tests for arm/camera/barcode.py: key decoding, scan pairing and device discovery, no scanner needed."""
import importlib.util
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[2]

_spec = importlib.util.spec_from_file_location("arm_camera_barcode", REPO_ROOT / "arm" / "camera" / "barcode.py")
barcode = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(barcode)


class _Log:
    """Collects log lines so tests can assert on them."""

    def __init__(self):
        self.lines = []

    def _add(self, level):
        def _log(message, *args, **kwargs):
            self.lines.append((level, message))
        return _log

    def __getattr__(self, name):
        if name in ("debug", "info", "warning", "error"):
            return self._add(name)
        raise AttributeError(name)


class TestDecodeKeycode(unittest.TestCase):
    def test_digits_letters_and_punctuation(self):
        self.assertEqual(barcode.decode_keycode("KEY_0"), "0")
        self.assertEqual(barcode.decode_keycode("KEY_7"), "7")
        self.assertEqual(barcode.decode_keycode("KEY_KP7"), "7")
        self.assertEqual(barcode.decode_keycode("KEY_A"), "a")
        self.assertEqual(barcode.decode_keycode("KEY_A", shift=True), "A")
        self.assertEqual(barcode.decode_keycode("KEY_MINUS"), "-")
        self.assertEqual(barcode.decode_keycode("KEY_MINUS", shift=True), "_")

    def test_ignored_keys_and_aliases(self):
        self.assertIsNone(barcode.decode_keycode("KEY_ENTER"))
        self.assertIsNone(barcode.decode_keycode("KEY_LEFTSHIFT"))
        self.assertIsNone(barcode.decode_keycode("KEY_F1"))
        # evdev reports some keys as a list of names
        self.assertEqual(barcode.decode_keycode(["KEY_1", "KEY_ONE"]), "1")
        self.assertIsNone(barcode.decode_keycode([]))


def _type(decoder, text, now=0.0):
    """Feed a string the way a scanner types it: press and release each key, then Enter."""
    result = None
    for i, ch in enumerate(text):
        if ch.isdigit():
            key = f"KEY_{ch}"
        elif ch == "-":
            key = "KEY_MINUS"
        else:
            key = f"KEY_{ch.upper()}"
        shifted = ch.isalpha() and ch.isupper()
        if shifted:
            decoder.feed("KEY_LEFTSHIFT", True, now + i)
        result = decoder.feed(key, True, now + i) or result
        decoder.feed(key, False, now + i)
        if shifted:
            decoder.feed("KEY_LEFTSHIFT", False, now + i)
    return decoder.feed("KEY_ENTER", True, now + len(text)) or result


class TestScanDecoder(unittest.TestCase):
    def test_digits_then_enter_complete_a_scan(self):
        decoder = barcode.ScanDecoder()
        self.assertEqual(_type(decoder, "085391163926"), "085391163926")
        # buffer is cleared for the next scan
        self.assertEqual(_type(decoder, "5050582868043", now=100.0), "5050582868043")

    def test_shift_and_letters(self):
        decoder = barcode.ScanDecoder()
        self.assertEqual(_type(decoder, "ab-C12"), "ab-C12")

    def test_key_up_and_unknown_keys_are_ignored(self):
        decoder = barcode.ScanDecoder()
        self.assertIsNone(decoder.feed("KEY_1", True, 0.0))
        self.assertIsNone(decoder.feed("KEY_1", False, 0.0))
        self.assertIsNone(decoder.feed("KEY_F5", True, 0.0))
        self.assertIsNone(decoder.feed("KEY_2", True, 0.1))
        self.assertEqual(decoder.feed("KEY_KPENTER", True, 0.2), "12")

    def test_enter_without_characters_yields_nothing(self):
        decoder = barcode.ScanDecoder()
        self.assertIsNone(decoder.feed("KEY_ENTER", True, 0.0))

    def test_long_pause_resets_partial_code(self):
        decoder = barcode.ScanDecoder(idle_reset_seconds=2.0)
        decoder.feed("KEY_9", True, 0.0)
        decoder.feed("KEY_9", True, 0.5)
        # scanner unplugged mid code; next scan starts five seconds later
        decoder.feed("KEY_1", True, 5.5)
        decoder.feed("KEY_2", True, 5.6)
        self.assertEqual(decoder.feed("KEY_ENTER", True, 5.7), "12")


class TestScanHolder(unittest.TestCase):
    def test_hold_and_claim(self):
        holder = barcode.ScanHolder(pair_seconds=120, logger=_Log())
        self.assertIsNone(holder.claim(now=10.0))
        self.assertTrue(holder.hold("085391163926", now=10.0))
        self.assertEqual(holder.peek(now=20.0), "085391163926")
        self.assertEqual(holder.claim(now=20.0), "085391163926")
        # claimed once only
        self.assertIsNone(holder.claim(now=21.0))

    def test_scan_expires(self):
        log = _Log()
        holder = barcode.ScanHolder(pair_seconds=120, logger=log)
        holder.hold("085391163926", now=0.0)
        self.assertEqual(holder.peek(now=120.0), "085391163926")
        self.assertIsNone(holder.claim(now=120.1))
        self.assertTrue(any("expired" in msg for _, msg in log.lines))

    def test_new_scan_replaces_pending_one(self):
        holder = barcode.ScanHolder(pair_seconds=120, logger=_Log())
        holder.hold("111111111111", now=0.0)
        holder.hold("222222222222", now=1.0)
        self.assertEqual(holder.claim(now=2.0), "222222222222")

    def test_implausible_scans_are_ignored(self):
        log = _Log()
        holder = barcode.ScanHolder(pair_seconds=120, logger=log)
        self.assertFalse(holder.hold("", now=0.0))
        self.assertFalse(holder.hold("ab", now=0.0))
        self.assertFalse(holder.hold("x" * 40, now=0.0))
        self.assertFalse(holder.hold("12 34", now=0.0))
        self.assertIsNone(holder.claim(now=0.0))
        self.assertEqual(len([m for lvl, m in log.lines if lvl == "warning"]), 4)

    def test_is_valid_scan(self):
        self.assertTrue(barcode.is_valid_scan("5050582868043"))
        self.assertTrue(barcode.is_valid_scan("978-0132350884"))
        self.assertFalse(barcode.is_valid_scan(None))
        self.assertFalse(barcode.is_valid_scan("123"))


class TestFindScannerDevice(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.folder)

    def _touch(self, name):
        path = os.path.join(self.folder, name)
        with open(path, "w") as handle:
            handle.write("")
        return path

    def test_configured_device_wins(self):
        self.assertEqual(barcode.find_scanner_device("/dev/input/event7", by_id_dir=self.folder), "/dev/input/event7")

    def test_autodetect_by_id_name(self):
        self._touch("usb-Logitech_USB_Keyboard-event-kbd")
        wanted = self._touch("usb-Eyoyo_EY-H2_Barcode_Scanner_12345-event-kbd")
        self._touch("usb-Eyoyo_EY-H2_Barcode_Scanner_12345-if01-event-mouse")
        self.assertEqual(barcode.find_scanner_device("", by_id_dir=self.folder, logger=_Log()), wanted)

    def test_no_match_warns_and_returns_none(self):
        log = _Log()
        self._touch("usb-Logitech_USB_Keyboard-event-kbd")
        self.assertIsNone(barcode.find_scanner_device("", by_id_dir=self.folder, logger=log))
        self.assertTrue(any(lvl == "warning" and "BARCODE_DEVICE" in msg for lvl, msg in log.lines))

    def test_missing_by_id_folder(self):
        self.assertIsNone(barcode.find_scanner_device("", by_id_dir=os.path.join(self.folder, "nope"), logger=_Log()))


class TestBarcodeReaderDeviceLifecycle(unittest.TestCase):
    def test_grab_failure_still_closes_device(self):
        """EBUSY on grab() happens on every retry; the fd must be closed each time or they leak."""
        opened = []

        class FakeDevice:
            name = "Fake Scanner"
            fd = 3

            def __init__(self, path):
                self.closed = False
                opened.append(self)

            def grab(self):
                raise OSError(16, "Device or resource busy")

            def ungrab(self):
                raise OSError(22, "Invalid argument")

            def close(self):
                self.closed = True

        fake_evdev = SimpleNamespace(InputDevice=FakeDevice)
        reader = barcode.BarcodeReader("/dev/input/event9", lambda c: None, logger=_Log())
        with self.assertRaises(OSError):
            reader._read_until_error(fake_evdev)
        self.assertEqual(len(opened), 1)
        self.assertTrue(opened[0].closed)

    def test_open_failure_does_not_touch_a_device(self):
        def boom(path):
            raise FileNotFoundError(path)
        reader = barcode.BarcodeReader("/dev/input/event9", lambda c: None, logger=_Log())
        with self.assertRaises(FileNotFoundError):
            reader._read_until_error(SimpleNamespace(InputDevice=boom))


class TestBarcodeReaderWithoutEvdev(unittest.TestCase):
    def test_start_and_stop_without_device(self):
        """The reader thread must come and go cleanly even when evdev or the device is missing."""
        log = _Log()
        reader = barcode.BarcodeReader(os.path.join(tempfile.gettempdir(), "no-such-event"), lambda c: None,
                                       retry_seconds=0.05, logger=log)
        reader.start()
        reader.stop(timeout=2.0)
        self.assertIsNone(reader._thread)


if __name__ == '__main__':
    unittest.main()
