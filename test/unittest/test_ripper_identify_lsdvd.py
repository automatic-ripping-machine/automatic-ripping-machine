"""
Track 99 detection parses ``lsdvd -Oy``. libdvdread prints warnings on stderr;
they must not break parsing of the dict on stdout.
"""
import io
import json
import subprocess
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, '/opt/arm')
from arm.ripper import identify  # noqa: E402

WARNING = "libdvdread: CHECK_VALUE failed in src/ifo_read.c:1272 for vts_ptt_srpt->title[i].ptt[j].pgn != 0\n"


def lsdvd_stdout(titles):
    tracks = ", ".join(f"{{'ix' : {i}, 'length' : 1.5}}" for i in range(1, titles + 1))
    return f"lsdvd = {{\n  'device' : '/dev/sr0',\n  'title' : 'KIKIS_DELIVERY_SERVICE',\n  'track' : [{tracks}],\n}}\n"


def completed(stdout, stderr=WARNING, returncode=0):
    return subprocess.CompletedProcess(["lsdvd"], returncode, stdout=stdout, stderr=stderr)


def make_job():
    job = SimpleNamespace(label="KIKIS_DELIVERY_SERVICE", mountpoint="/mnt/dev/sr0", devpath="/dev/sr0",
                          title=None, year=None, crc_id=None, hasnicetitle=False, has_track_99=False)
    job.pretty_table = lambda: ""
    return job


class TestLsdvdTracks(unittest.TestCase):

    def test_warnings_on_stderr_are_ignored(self):
        """CHECK the dict on stdout parses even when libdvdread warns on stderr"""
        with patch.object(identify.subprocess, "run", return_value=completed(lsdvd_stdout(12))):
            self.assertEqual(len(identify.lsdvd_tracks("/dev/sr0")), 12)

    def test_unparseable_output_returns_none(self):
        """CHECK garbage output is logged and returns None instead of raising"""
        failed = completed("Can't open disc /dev/sr0!", returncode=2)
        with patch.object(identify.subprocess, "run", return_value=failed):
            self.assertIsNone(identify.lsdvd_tracks("/dev/sr0"))

    def test_missing_lsdvd_returns_none(self):
        """CHECK a missing lsdvd binary returns None"""
        with patch.object(identify.subprocess, "run", side_effect=FileNotFoundError("lsdvd")):
            self.assertIsNone(identify.lsdvd_tracks("/dev/sr0"))


class TestTrack99Detection(unittest.TestCase):

    def run_identify_dvd(self, titles, prevent_99=False):
        """identify_dvd() with the online lookups mocked out and lsdvd warning on stderr"""
        job = make_job()
        out = lsdvd_stdout(titles)
        crc_api = io.BytesIO(json.dumps({"success": False, "results": {}}).encode())
        with patch.object(identify.pydvdid, "compute", return_value="abc123"), \
                patch.object(identify.urllib.request, "urlopen", return_value=crc_api), \
                patch.object(identify, "metadata_selector", return_value=None), \
                patch.object(identify, "identify_loop"), \
                patch.object(identify, "arm_subprocess", return_value=WARNING + out), \
                patch.object(identify.subprocess, "run", return_value=completed(out)), \
                patch.dict(identify.cfg.arm_config, {"PREVENT_99": prevent_99}):
            identify.identify_dvd(job)
        return job

    def test_99_titles_detected_despite_warnings(self):
        """CHECK a 99-title disc is flagged although libdvdread printed a warning"""
        self.assertTrue(self.run_identify_dvd(99).has_track_99)

    def test_normal_disc_not_flagged(self):
        """CHECK a disc with fewer titles isn't flagged"""
        self.assertFalse(self.run_identify_dvd(12).has_track_99)

    def test_prevent_99_still_stops_the_rip(self):
        """CHECK PREVENT_99 still raises for a 99-title disc"""
        with self.assertRaises(identify.utils.RipperException):
            self.run_identify_dvd(99, prevent_99=True)


if __name__ == '__main__':
    unittest.main()
