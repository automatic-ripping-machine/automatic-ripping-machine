"""
Tests for identify.identify_from_barcode with the network and database mocked.

Importing ``arm.ripper.identify`` pulls in the whole of ARM (config, Flask app, database), so a
throwaway arm.yaml is written first and pointed at with ARM_CONFIG_FILE. Needs the Linux
dependencies ARM itself needs (libdiscid, pyudev); skipped when they are missing.
"""
import importlib
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]

_TMP = tempfile.mkdtemp(prefix="arm_identify_test_")
_CONFIG = os.path.join(_TMP, "arm.yaml")
with open(_CONFIG, "w") as _handle:
    _handle.write(f"INSTALLPATH: \"{REPO_ROOT}\"\n"
                  f"DBFILE: \"{_TMP}/arm.db\"\n"
                  f"LOGPATH: \"{_TMP}/logs/\"\n"
                  f"ABCDE_CONFIG_FILE: \"{REPO_ROOT}/setup/.abcde.conf\"\n"
                  f"RAW_PATH: \"{_TMP}/raw/\"\nTRANSCODE_PATH: \"{_TMP}/transcode/\"\n"
                  f"COMPLETED_PATH: \"{_TMP}/completed/\"\n"
                  f"DISC_PHOTO_PATH: \"{_TMP}/photos/\"\n"
                  "DISABLE_LOGIN: true\nMETADATA_PROVIDER: \"tmdb\"\nBARCODE_LOOKUP: true\n")
os.environ["ARM_CONFIG_FILE"] = _CONFIG

try:
    identify = importlib.import_module("arm.ripper.identify")
    cfg = importlib.import_module("arm.config.config")
    IMPORT_ERROR = None
except Exception as error:  # pragma: no cover - depends on the host
    identify = cfg = None
    IMPORT_ERROR = error


def tearDownModule():
    shutil.rmtree(_TMP, ignore_errors=True)


def _job(**overrides):
    base = dict(job_id=7, disctype="dvd", disc_barcode="085391163926", hasnicetitle=False,
                title="not identified", year="", arm_version="test", label="LOGICAL_VOLUME")
    base.update(overrides)
    return SimpleNamespace(**base)


def _fake_updater(args, job):
    if isinstance(args, dict):
        for key, value in args.items():
            setattr(job, key, value)
    return True


@unittest.skipIf(IMPORT_ERROR is not None, f"ARM could not be imported here: {IMPORT_ERROR}")
class TestIdentifyFromBarcode(unittest.TestCase):
    def setUp(self):
        # another test module may have imported ARM with its own throwaway config: switch to ours
        os.environ["ARM_CONFIG_FILE"] = _CONFIG
        if cfg.arm_config_path != _CONFIG:
            importlib.reload(cfg)
        cfg.arm_config["BARCODE_LOOKUP"] = True
        self.updater = mock.patch.object(identify.utils, "database_updater", side_effect=_fake_updater)
        self.updater.start()

    def tearDown(self):
        self.updater.stop()

    def test_skips_when_disabled_or_not_needed(self):
        with mock.patch.object(identify.disc_photo, "lookup_upc") as lookup:
            cfg.arm_config["BARCODE_LOOKUP"] = False
            self.assertFalse(identify.identify_from_barcode(_job()))
            cfg.arm_config["BARCODE_LOOKUP"] = True
            self.assertFalse(identify.identify_from_barcode(_job(disc_barcode=None)))
            self.assertFalse(identify.identify_from_barcode(_job(hasnicetitle=True)))
            self.assertFalse(identify.identify_from_barcode(_job(disctype="data")))
        lookup.assert_not_called()

    def test_video_title_found_from_upc(self):
        candidates = [{"title": "Inception", "year": "2010", "raw": "Inception (Blu-ray + DVD, 2010)"}]

        def fake_search(job, response, title, year=None):
            if response is None and title == "Inception":
                job.title, job.year, job.hasnicetitle = "Inception", "2010", True
                return {"Search": [{"Title": "Inception"}]}
            return response

        job = _job()
        with mock.patch.object(identify.disc_photo, "lookup_upc", return_value=candidates) as lookup, \
                mock.patch.object(identify, "try_with_year", side_effect=fake_search), \
                mock.patch.object(identify, "try_without_year", side_effect=lambda j, r, t: r):
            self.assertTrue(identify.identify_from_barcode(job))
        lookup.assert_called_once_with("085391163926", user_agent="arm/test")
        self.assertEqual(job.title, "Inception")
        self.assertEqual(job.disc_barcode_title, "Inception (Blu-ray + DVD, 2010)")

    def test_video_no_online_match_keeps_product_title(self):
        candidates = [{"title": "Obscure Film", "year": None, "raw": "Obscure Film (DVD)"}]
        job = _job()
        with mock.patch.object(identify.disc_photo, "lookup_upc", return_value=candidates), \
                mock.patch.object(identify, "try_with_year", return_value=None), \
                mock.patch.object(identify, "try_without_year", return_value=None):
            self.assertFalse(identify.identify_from_barcode(job))
        self.assertEqual(job.disc_barcode_title, "Obscure Film (DVD)")
        self.assertEqual(job.title, "not identified")

    def test_video_lookup_empty(self):
        job = _job()
        with mock.patch.object(identify.disc_photo, "lookup_upc", return_value=[]), \
                mock.patch.object(identify, "try_with_year") as search:
            self.assertFalse(identify.identify_from_barcode(job))
        search.assert_not_called()

    def test_music_release_found_on_musicbrainz(self):
        release = {"id": "abc-123", "title": "Rumours", "artist-credit-phrase": "Fleetwood Mac", "date": "1977-02-04"}
        fake_mb = mock.Mock()
        fake_mb.search_releases.return_value = {"release-list": [release]}
        fake_mb.WebServiceError = Exception
        job = _job(disctype="music", disc_barcode="081227973308")
        with mock.patch.dict("sys.modules", {"musicbrainzngs": fake_mb}):
            self.assertTrue(identify.identify_from_barcode(job))
        fake_mb.search_releases.assert_called_once_with(barcode="081227973308", limit=5)
        self.assertEqual(job.title, "Fleetwood Mac Rumours")
        self.assertEqual(job.year, "1977")
        self.assertEqual(job.crc_id, "abc-123")
        self.assertTrue(job.hasnicetitle)

    def test_music_release_found_under_ean13_form(self):
        release = {"id": "def-456", "title": "Rumours", "artist-credit-phrase": "Fleetwood Mac", "date": "1977"}
        fake_mb = mock.Mock()
        fake_mb.search_releases.side_effect = lambda barcode, limit: {
            "release-list": [release] if barcode == "0081227973308" else []}
        fake_mb.WebServiceError = Exception
        job = _job(disctype="music", disc_barcode="081227973308")
        with mock.patch.dict("sys.modules", {"musicbrainzngs": fake_mb}):
            self.assertTrue(identify.identify_from_barcode(job))
        self.assertEqual([c.kwargs["barcode"] for c in fake_mb.search_releases.call_args_list],
                         ["081227973308", "0081227973308"])
        self.assertEqual(job.title, "Fleetwood Mac Rumours")
        self.assertEqual(job.crc_id, "def-456")

    def test_music_no_release(self):
        fake_mb = mock.Mock()
        fake_mb.search_releases.return_value = {"release-list": []}
        fake_mb.WebServiceError = Exception
        job = _job(disctype="music")
        with mock.patch.dict("sys.modules", {"musicbrainzngs": fake_mb}):
            self.assertFalse(identify.identify_from_barcode(job))
        self.assertEqual(fake_mb.search_releases.call_count, 2, "both UPC-A and EAN-13 spellings are tried")
        self.assertEqual(job.title, "not identified")


if __name__ == '__main__':
    unittest.main()
