"""Tests for arm.ripper.disc_photo (pure helpers, no ARM config or database needed)."""
import datetime
import importlib.util
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]

# arm.ripper.disc_photo is deliberately free of ARM imports. Load it straight from its file so
# these tests do not trigger ``arm/__init__``, which loads the ARM config, the Flask app and
# the database at import time.
_spec = importlib.util.spec_from_file_location("disc_photo", REPO_ROOT / "arm" / "ripper" / "disc_photo.py")
disc_photo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(disc_photo)


def _touch(folder, name, when, content=b"\xff\xd8\xff"):
    path = os.path.join(folder, name)
    with open(path, 'wb') as handle:
        handle.write(content)
    stamp = when.timestamp()
    os.utime(path, (stamp, stamp))
    return path


class TestPhotoFilename(unittest.TestCase):
    def test_devname_and_timestamp_parse(self):
        self.assertEqual(disc_photo.photo_devname("sr1_20261018-143005.jpg"), "sr1")
        self.assertEqual(disc_photo.photo_devname("/x/y/SR12_20261018-143005.JPEG"), "sr12")
        self.assertEqual(disc_photo.photo_timestamp("sr1_20261018-143005.jpg"),
                         datetime.datetime(2026, 10, 18, 14, 30, 5))

    def test_rejects_other_files(self):
        for name in ("sr1.jpg", "poster.png", "sr1_20261018.jpg",
                     "video0_20261018-143005.jpg", "sr1_20261018-143005.jpg.tmp"):
            self.assertIsNone(disc_photo.photo_devname(name), name)
            self.assertIsNone(disc_photo.photo_timestamp(name), name)


class TestFindDiscPhoto(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.start = datetime.datetime(2026, 10, 18, 12, 0, 0)

    def tearDown(self):
        shutil.rmtree(self.folder)

    def test_picks_newest_photo_for_drive_inside_window(self):
        _touch(self.folder, "sr0_20261018-115800.jpg", self.start - datetime.timedelta(seconds=120))
        _touch(self.folder, "sr0_20261018-115930.jpg", self.start - datetime.timedelta(seconds=30))
        _touch(self.folder, "sr1_20261018-115950.jpg", self.start - datetime.timedelta(seconds=10))
        self.assertEqual(disc_photo.find_disc_photo(self.folder, "sr0", self.start, 180),
                         "sr0_20261018-115930.jpg")

    def test_accepts_full_devpath(self):
        _touch(self.folder, "sr2_20261018-115930.jpg", self.start - datetime.timedelta(seconds=30))
        self.assertEqual(disc_photo.find_disc_photo(self.folder, "/dev/sr2", self.start, 180),
                         "sr2_20261018-115930.jpg")

    def test_ignores_too_old_and_future_photos(self):
        _touch(self.folder, "sr0_20261018-114000.jpg", self.start - datetime.timedelta(seconds=1200))
        _touch(self.folder, "sr0_20261018-120500.jpg", self.start + datetime.timedelta(seconds=300))
        self.assertIsNone(disc_photo.find_disc_photo(self.folder, "sr0", self.start, 180))

    def test_allows_small_grace_after_start(self):
        _touch(self.folder, "sr0_20261018-120002.jpg", self.start + datetime.timedelta(seconds=2))
        self.assertEqual(disc_photo.find_disc_photo(self.folder, "sr0", self.start, 180),
                         "sr0_20261018-120002.jpg")

    def test_missing_folder_or_no_match(self):
        self.assertIsNone(disc_photo.find_disc_photo("/nonexistent/folder", "sr0", self.start, 180))
        _touch(self.folder, "sr1_20261018-115930.jpg", self.start - datetime.timedelta(seconds=30))
        self.assertIsNone(disc_photo.find_disc_photo(self.folder, "sr0", self.start, 180))


class TestFindOrphanPhotos(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.now = datetime.datetime(2026, 10, 18, 12, 0, 0)

    def tearDown(self):
        shutil.rmtree(self.folder)

    def test_old_unreferenced_photos_only(self):
        old_orphan = _touch(self.folder, "sr0_20260901-120000.jpg", self.now - datetime.timedelta(days=30))
        _touch(self.folder, "sr0_20260902-120000.jpg", self.now - datetime.timedelta(days=30))  # referenced
        _touch(self.folder, "sr1_20261017-120000.jpg", self.now - datetime.timedelta(days=1))  # too new
        _touch(self.folder, "notes.txt", self.now - datetime.timedelta(days=100))  # not a photo
        orphans = disc_photo.find_orphan_photos(self.folder, {"sr0_20260902-120000.jpg"}, 14, now=self.now)
        self.assertEqual([str(p) for p in orphans], [old_orphan])


class TestCleanOcrText(unittest.TestCase):
    def test_strips_boilerplate_and_ranks_title_first(self):
        text = (
            "WIDESCREEN\n"
            "THE SHAWSHANK REDEMPTION\n"
            "Special Edition  DVD VIDEO\n"
            "Castle Rock Entertainment  © 1994\n"
            "Region 1 NTSC Dolby Digital\n"
            "www.warnerbros.com\n"
            "|||  ~~ ..\n"
        )
        candidates, year = disc_photo.clean_ocr_text(text)
        self.assertEqual(candidates[0], "THE SHAWSHANK REDEMPTION")
        self.assertEqual(year, "1994")
        joined = " ".join(candidates).lower()
        for noise in ("widescreen", "dvd", "region", "ntsc", "dolby", "www"):
            self.assertNotIn(noise, joined)

    def test_empty_and_noise_only(self):
        self.assertEqual(disc_photo.clean_ocr_text(None), ([], None))
        self.assertEqual(disc_photo.clean_ocr_text("DVD\nBLU-RAY DISC\n1080p\n@@@ ###"), ([], None))

    def test_year_hint_is_most_common(self):
        text = "SOME FILM\n2001\n© 2003 Studio\n2003 release"
        _, year = disc_photo.clean_ocr_text(text)
        self.assertEqual(year, "2003")

    def test_dedupes_and_limits_candidates(self):
        text = "ALPHABET\nalphabet\nBRAVO FILM\nCHARLIE PICTURE\nDELTA MOVIE TITLE\n"
        candidates, _ = disc_photo.clean_ocr_text(text, max_candidates=3)
        self.assertEqual(len(candidates), 3)
        self.assertEqual(candidates[0], "DELTA MOVIE TITLE")
        self.assertNotIn("alphabet", candidates)
        self.assertIn("ALPHABET", disc_photo.clean_ocr_text(text, max_candidates=4)[0])

    def test_short_single_words_are_not_searched(self):
        # "FOX", "NEW" or a misread fragment all match some title online and would retitle the rip
        text = "FOX\nNEW\nUP\nABCDE\nINCEPTION\nTHE ROCK\nAN OK\n"
        candidates, _ = disc_photo.clean_ocr_text(text, max_candidates=10)
        self.assertEqual(candidates, ["INCEPTION", "THE ROCK", "AN OK"])


class TestFindDiscBarcode(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.start = datetime.datetime(2026, 10, 18, 12, 0, 0)

    def tearDown(self):
        shutil.rmtree(self.folder)

    def _ago(self, seconds):
        return self.start - datetime.timedelta(seconds=seconds)

    def test_picks_newest_barcode_for_drive_inside_window(self):
        _touch(self.folder, "sr0_20261018-115800.barcode", self._ago(120), b"111111111111\n")
        _touch(self.folder, "sr0_20261018-115930.barcode", self._ago(30), b"085391163926\n")
        _touch(self.folder, "sr1_20261018-115950.barcode", self._ago(10), b"222222222222\n")
        _touch(self.folder, "sr0_20261018-115940.jpg", self._ago(20))
        self.assertEqual(disc_photo.find_disc_barcode(self.folder, "/dev/sr0", self.start, 180),
                         ("sr0_20261018-115930.barcode", "085391163926"))

    def test_outside_window_or_missing(self):
        _touch(self.folder, "sr0_20261018-115000.barcode", self._ago(600), b"085391163926\n")
        self.assertIsNone(disc_photo.find_disc_barcode(self.folder, "sr0", self.start, 180))
        self.assertIsNone(disc_photo.find_disc_barcode(os.path.join(self.folder, "nope"), "sr0", self.start, 180))

    def test_garbage_content_is_rejected(self):
        _touch(self.folder, "sr0_20261018-115930.barcode", self._ago(30), b"hello world\n")
        self.assertIsNone(disc_photo.find_disc_barcode(self.folder, "sr0", self.start, 180))
        _touch(self.folder, "sr0_20261018-115931.barcode", self._ago(29), b"")
        self.assertIsNone(disc_photo.find_disc_barcode(self.folder, "sr0", self.start, 180))

    def test_used_barcode_files_are_never_attached_again(self):
        # the previous case's code, already copied onto a job, newer than the fresh scan
        _touch(self.folder, "sr0_20261018-115950.barcode.used", self._ago(10), b"111111111111\n")
        _touch(self.folder, "sr0_20261018-115930.barcode", self._ago(30), b"085391163926\n")
        self.assertEqual(disc_photo.find_disc_barcode(self.folder, "sr0", self.start, 180),
                         ("sr0_20261018-115930.barcode", "085391163926"))
        used = disc_photo.consume_barcode_file(os.path.join(self.folder, "sr0_20261018-115930.barcode"))
        self.assertEqual(os.path.basename(used), "sr0_20261018-115930.barcode.used")
        self.assertTrue(os.path.isfile(used))
        self.assertIsNone(disc_photo.find_disc_barcode(self.folder, "sr0", self.start, 180),
                          "a disc swapped within the window must not inherit the code")
        self.assertIsNone(disc_photo.consume_barcode_file(os.path.join(self.folder, "missing.barcode")))

    def test_orphan_pruning_includes_barcode_files(self):
        old = datetime.datetime(2026, 9, 1)
        _touch(self.folder, "sr0_20260901-120000.barcode", old, b"085391163926\n")
        _touch(self.folder, "sr0_20260901-120100.barcode.used", old, b"085391163926\n")
        _touch(self.folder, "sr0_20260901-120000.jpg", old)
        _touch(self.folder, "sr1_20261018-115930.barcode", self._ago(30), b"1234567890\n")
        orphans = disc_photo.find_orphan_photos(self.folder, {"sr0_20260901-120000.jpg"}, 14, now=self.start)
        self.assertEqual([p.name for p in orphans], ["sr0_20260901-120000.barcode", "sr0_20260901-120100.barcode.used"])

    def test_barcode_forms(self):
        self.assertEqual(disc_photo.barcode_forms("081227973308"), ["081227973308", "0081227973308"])
        self.assertEqual(disc_photo.barcode_forms("0081227973308"), ["0081227973308", "081227973308"])
        self.assertEqual(disc_photo.barcode_forms("5050582868043"), ["5050582868043"])
        self.assertEqual(disc_photo.barcode_forms("978-0132350884"), ["978-0132350884"])
        self.assertEqual(disc_photo.barcode_forms(None), [])


class TestCleanUpcTitle(unittest.TestCase):
    def test_format_and_year_in_brackets(self):
        self.assertEqual(disc_photo.clean_upc_title("Inception (Blu-ray + DVD, 2010)"), ("Inception", "2010"))
        self.assertEqual(disc_photo.clean_upc_title("Pulp Fiction [DVD]"), ("Pulp Fiction", None))
        self.assertEqual(disc_photo.clean_upc_title("The Dark Knight (Blu-ray/DVD, 2008, 2-Disc Set)"),
                         ("The Dark Knight", "2008"))

    def test_packaging_words_and_trailing_format(self):
        self.assertEqual(disc_photo.clean_upc_title("Firefly: The Complete Series (DVD, 2003, 4-Disc Set)"),
                         ("Firefly", "2003"))
        self.assertEqual(disc_photo.clean_upc_title("Breaking Bad - Season 2 (DVD)"), ("Breaking Bad", None))
        self.assertEqual(disc_photo.clean_upc_title("Coco (Blu-ray + DVD + Digital Copy) Disney 2018 Widescreen"),
                         ("Coco", "2018"))
        self.assertEqual(disc_photo.clean_upc_title("The Lego Movie DVD"), ("The Lego Movie", None))

    def test_numbers_in_titles_survive(self):
        self.assertEqual(disc_photo.clean_upc_title("Blade Runner 2049 4K UHD + Blu-ray"), ("Blade Runner 2049", None))
        self.assertEqual(disc_photo.clean_upc_title("2001: A Space Odyssey (Blu-ray, 2007)"),
                         ("2001: A Space Odyssey", "2007"))

    def test_accents_are_folded(self):
        self.assertEqual(disc_photo.clean_upc_title("Amélie DVD 2002"), ("Amelie", "2002"))
        self.assertEqual(disc_photo.clean_upc_title("Léon (The Professional) - Blu-ray"), ("Leon", None))

    def test_nothing_left(self):
        self.assertEqual(disc_photo.clean_upc_title("DVD"), (None, None))
        self.assertEqual(disc_photo.clean_upc_title(""), (None, None))
        self.assertEqual(disc_photo.clean_upc_title(None), (None, None))


class TestUpcLookup(unittest.TestCase):
    PAYLOAD = {"code": "OK", "total": 2, "items": [
        {"title": "Some Toy Robot", "category": "Toys & Games > Robots"},
        {"title": "Inception (Blu-ray + DVD, 2010)", "category": "Media > Movies & TV > DVDs & Blu-ray Discs"},
        {"title": "Inception - Widescreen", "category": ""},
    ]}

    def test_parse_keeps_video_items_in_order(self):
        results = disc_photo.parse_upc_response(self.PAYLOAD)
        self.assertEqual([r["title"] for r in results], ["Inception", "Inception"])
        self.assertEqual(results[0]["year"], "2010")
        self.assertEqual(results[0]["raw"], "Inception (Blu-ray + DVD, 2010)")
        self.assertEqual(disc_photo.parse_upc_response({"code": "INVALID_UPC", "items": []}), [])
        self.assertEqual(disc_photo.parse_upc_response(None), [])

    def _response(self, status, payload=None):
        response = mock.Mock()
        response.status_code = status
        response.json = mock.Mock(return_value=payload if payload is not None else {})
        if payload is None:
            response.json.side_effect = ValueError("no json")
        return response

    def test_lookup_calls_endpoint_and_parses(self):
        with mock.patch("requests.get", return_value=self._response(200, self.PAYLOAD)) as get:
            results = disc_photo.lookup_upc("085391163926", user_agent="arm/test")
        self.assertEqual(results[0]["title"], "Inception")
        args, kwargs = get.call_args
        self.assertEqual(args[0], disc_photo.UPC_LOOKUP_URL)
        self.assertEqual(kwargs["params"], {"upc": "085391163926"})
        self.assertEqual(kwargs["headers"]["User-Agent"], "arm/test")

    def test_lookup_handles_failures_quietly(self):
        for status in (404, 429, 500):
            with mock.patch("requests.get", return_value=self._response(status, {})):
                self.assertEqual(disc_photo.lookup_upc("085391163926"), [])
        with mock.patch("requests.get", return_value=self._response(200, None)):
            self.assertEqual(disc_photo.lookup_upc("085391163926"), [])
        import requests
        with mock.patch("requests.get", side_effect=requests.ConnectionError("offline")):
            self.assertEqual(disc_photo.lookup_upc("085391163926"), [])

    def test_lookup_refuses_bad_codes_without_a_request(self):
        with mock.patch("requests.get") as get:
            self.assertEqual(disc_photo.lookup_upc(""), [])
            self.assertEqual(disc_photo.lookup_upc("not a code"), [])
        get.assert_not_called()


class TestWriteBarcodeSidecar(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def test_writes_code_and_newline(self):
        target = os.path.join(self.folder, "Film (2001)")
        path = disc_photo.write_barcode_sidecar(target, " 085391163926 ")
        self.assertEqual(path, os.path.join(target, "disc.barcode"))
        with open(path, encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "085391163926\n")

    def test_overwrites_an_earlier_file(self):
        disc_photo.write_barcode_sidecar(self.folder, "111111111111")
        disc_photo.write_barcode_sidecar(self.folder, "222222222222")
        with open(os.path.join(self.folder, "disc.barcode"), encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "222222222222\n")

    def test_refuses_implausible_codes(self):
        for code in ("", None, "ab", "0" * 40, "12 34"):
            self.assertIsNone(disc_photo.write_barcode_sidecar(self.folder, code))
        self.assertFalse(os.path.exists(os.path.join(self.folder, "disc.barcode")))


if __name__ == '__main__':
    unittest.main()
