"""
Identification edge cases: Blu-rays without a label must not be titled "None",
and the ARM disc-ID lookup must not hang the rip.
"""
import io
import json
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import mock_open, patch

sys.path.insert(0, '/opt/arm')
from arm.ripper import identify  # noqa: E402


def bluray_job(label=None):
    return SimpleNamespace(label=label, mountpoint="/mnt/dev/sr1", title=None, title_auto=None,
                           year=None, year_auto=None)


class TestBlurayWithoutLabel(unittest.TestCase):

    def test_no_label_no_xml_is_not_titled_none(self):
        """CHECK a Blu-ray without label or bdmt_eng.xml isn't titled "None" """
        job = bluray_job()
        with patch("builtins.open", side_effect=FileNotFoundError(2, "No such file")), \
                patch.object(identify.db.session, "commit"):
            self.assertFalse(identify.identify_bluray(job))
        self.assertNotEqual(job.title, "None")

    def test_xml_without_title_and_no_label_is_not_titled_none(self):
        """CHECK bdmt_eng.xml without a title and no label doesn't give the title "None" """
        job = bluray_job()
        with patch("builtins.open", mock_open(read_data=b"<disclib></disclib>")), \
                patch.object(identify.os.path, "getmtime", return_value=1400000000), \
                patch.object(identify.db.session, "commit"):
            identify.identify_bluray(job)
        self.assertNotIn("None", job.title)

    def test_label_still_used_when_xml_missing(self):
        """CHECK a Blu-ray label is still used as the title without bdmt_eng.xml"""
        job = bluray_job("PRINCESS_MONONOKE")
        with patch("builtins.open", side_effect=FileNotFoundError(2, "No such file")), \
                patch.object(identify.db.session, "commit"):
            self.assertTrue(identify.identify_bluray(job))
        self.assertEqual(job.title, "Princess Mononoke")


class TestDiscIdLookupTimeout(unittest.TestCase):

    def test_crc_lookup_has_a_timeout(self):
        """CHECK the ARM disc-ID (CRC64) lookup can't hang forever"""
        job = SimpleNamespace(label="DONT_BREATHE", mountpoint="/mnt/dev/sr0", devpath="/dev/sr0", title=None,
                              year=None, crc_id=None, hasnicetitle=False, has_track_99=False)
        job.pretty_table = lambda: ""
        response = io.BytesIO(json.dumps({"success": False, "results": {}}).encode())
        with patch.object(identify.pydvdid, "compute", return_value="abc"), \
                patch.object(identify.urllib.request, "urlopen", return_value=response) as urlopen, \
                patch.object(identify, "metadata_selector", return_value=None), \
                patch.object(identify, "identify_loop"), \
                patch.object(identify, "arm_subprocess", return_value=None):
            identify.identify_dvd(job)
        self.assertIn("1337server", urlopen.call_args.args[0])
        self.assertEqual(urlopen.call_args.kwargs.get("timeout"), 30)


if __name__ == '__main__':
    unittest.main()
