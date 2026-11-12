"""
Some drives send the udev "change" event before udev has probed the disc, so
udev's record has no ID_FS_LABEL. Job should then read the label from the disc.
"""
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, '/opt/arm')
from arm.models import job as job_module  # noqa: E402

UDEV_WITHOUT_MEDIA = {"DEVNAME": "/dev/sr1", "ID_CDROM": "1", "ID_TYPE": "cd"}
UDEV_DVD = dict(UDEV_WITHOUT_MEDIA, ID_CDROM_MEDIA_DVD="1", ID_FS_LABEL="IT_CHAPTER_TWO")
UDEV_CD = dict(UDEV_WITHOUT_MEDIA, ID_CDROM_MEDIA_TRACK_COUNT_AUDIO="12")


def blkid(stdout="", returncode=0):
    return subprocess.CompletedProcess(["blkid"], returncode, stdout=stdout, stderr="")


def make_job(udev_properties, blkid_result):
    """Job("/dev/sr1") with udev and blkid mocked; returns (job, blkid mock)"""
    with patch.object(job_module.pyudev.Devices, "from_device_file", return_value=udev_properties), \
            patch.object(job_module.subprocess, "run", return_value=blkid_result) as run, \
            patch.object(job_module.subprocess, "check_output", return_value=b""):
        return job_module.Job("/dev/sr1"), run


class TestLabelFallback(unittest.TestCase):

    def test_label_read_from_disc_when_udev_has_none(self):
        """CHECK the label comes from blkid when udev's record has none"""
        job, run = make_job(UDEV_WITHOUT_MEDIA, blkid("IT_CHAPTER_TWO\n"))
        self.assertEqual(job.label, "IT_CHAPTER_TWO")
        self.assertEqual(run.call_args.args[0], ["blkid", "-p", "-s", "LABEL", "-o", "value", "/dev/sr1"])

    def test_whitespace_becomes_underscore(self):
        """CHECK a label with spaces is stored like udev's ID_FS_LABEL"""
        job, _run = make_job(UDEV_WITHOUT_MEDIA, blkid("My Movie  Disc\n"))
        self.assertEqual(job.label, "My_Movie_Disc")

    def test_udev_label_is_used_without_blkid(self):
        """CHECK blkid isn't run when udev has the label"""
        job, run = make_job(UDEV_DVD, blkid("SOMETHING_ELSE"))
        self.assertEqual(job.label, "IT_CHAPTER_TWO")
        run.assert_not_called()

    def test_no_label_anywhere_stays_none(self):
        """CHECK a disc without a label still has none (blkid prints nothing, exit 2)"""
        job, _run = make_job(UDEV_WITHOUT_MEDIA, blkid("", returncode=2))
        self.assertIsNone(job.label)

    def test_blkid_missing_is_ignored(self):
        """CHECK a missing blkid doesn't break job creation"""
        with patch.object(job_module.pyudev.Devices, "from_device_file", return_value=UDEV_WITHOUT_MEDIA), \
                patch.object(job_module.subprocess, "run", side_effect=FileNotFoundError("blkid")):
            self.assertIsNone(job_module.Job("/dev/sr1").label)

    def test_audio_cd_is_not_probed(self):
        """CHECK audio CDs (no filesystem) skip blkid"""
        job, run = make_job(UDEV_CD, blkid("SHOULD_NOT_BE_USED"))
        self.assertEqual(job.disctype, "music")
        run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
