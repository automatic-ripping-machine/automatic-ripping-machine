"""Tests for arm.ripper.disc_photo (pure helpers, no ARM config or database needed)."""
import datetime
import importlib.util
import os
import shutil
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# arm.ripper.disc_photo is deliberately free of ARM imports. Load it straight from its file so
# these tests do not trigger ``arm/__init__``, which loads the ARM config, the Flask app and
# the database at import time.
_spec = importlib.util.spec_from_file_location("disc_photo", REPO_ROOT / "arm" / "ripper" / "disc_photo.py")
disc_photo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(disc_photo)


def _touch(folder, name, when):
    path = os.path.join(folder, name)
    with open(path, 'wb') as handle:
        handle.write(b"\xff\xd8\xff")
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
        text = "ALPHA\nalpha\nBRAVO FILM\nCHARLIE PICTURE\nDELTA MOVIE TITLE\n"
        candidates, _ = disc_photo.clean_ocr_text(text, max_candidates=3)
        self.assertEqual(len(candidates), 3)
        self.assertEqual(candidates[0], "DELTA MOVIE TITLE")
        self.assertNotIn("alpha", candidates)


if __name__ == '__main__':
    unittest.main()
