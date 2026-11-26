import sys
import unittest
from unittest import mock

import psutil

sys.path.insert(0, '/opt/arm')

from arm.models.job import JobState  # noqa: E402
from arm.ripper import utils  # noqa: E402

DEV_PATH = "/dev/sr0"
LIVE_HASH = 1234


def make_job(status=JobState.VIDEO_RIPPING.value, finished=False, pid=4242, pid_hash=LIVE_HASH):
    job = mock.MagicMock()
    job.job_id = 17
    job.status = status
    job.finished = finished
    job.pid = pid
    job.pid_hash = pid_hash
    job.run_time = 600
    return job


class TestDuplicateRunCheck(unittest.TestCase):
    """duplicate_run_check() must only refuse a disc while the drive's job is really running"""

    def setUp(self):
        self.drive = mock.MagicMock()
        self.drive.processing = True

        drives = mock.patch.object(utils, "SystemDrives")
        self.system_drives = drives.start()
        self.system_drives.query.filter_by.return_value.first.return_value = self.drive

        database = mock.patch.object(utils, "db")
        self.db = database.start()

        ps = mock.patch.object(utils, "psutil")
        self.psutil = ps.start()
        self.psutil.NoSuchProcess = psutil.NoSuchProcess
        self.psutil.pid_exists.return_value = True
        self.process = mock.MagicMock()
        self.process.__hash__ = mock.Mock(return_value=LIVE_HASH)
        self.psutil.Process.return_value = self.process

        self.addCleanup(mock.patch.stopall)

    def run_check(self, job):
        self.drive.job_current = job
        utils.duplicate_run_check(DEV_PATH)

    def assert_released(self, job, expected_status):
        self.drive.release_current_job.assert_called_once()
        self.db.session.commit.assert_called()
        self.assertEqual(job.status, expected_status)

    def test_live_job_still_refuses_the_disc(self):
        job = make_job()
        with self.assertRaises(utils.RipperException):
            self.run_check(job)
        self.drive.release_current_job.assert_not_called()
        self.assertEqual(job.status, JobState.VIDEO_RIPPING.value)

    def test_dead_pid_releases_the_drive(self):
        self.psutil.pid_exists.return_value = False
        job = make_job()
        self.run_check(job)
        self.assert_released(job, JobState.FAILURE.value)

    def test_reused_pid_releases_the_drive(self):
        self.process.__hash__.return_value = LIVE_HASH + 1
        job = make_job()
        self.run_check(job)
        self.assert_released(job, JobState.FAILURE.value)

    def test_pid_gone_while_checking_releases_the_drive(self):
        self.psutil.Process.side_effect = psutil.NoSuchProcess(4242)
        job = make_job()
        self.run_check(job)
        self.assert_released(job, JobState.FAILURE.value)

    def test_finished_job_still_attached_releases_the_drive(self):
        job = make_job(status=JobState.SUCCESS.value, finished=True)
        self.run_check(job)
        self.assert_released(job, JobState.SUCCESS.value)

    def test_idle_drive_continues(self):
        self.drive.processing = False
        utils.duplicate_run_check(DEV_PATH)
        self.drive.release_current_job.assert_not_called()


class TestCleanOldJobs(unittest.TestCase):
    """clean_old_jobs() must fail jobs whose PID now belongs to another process"""

    def setUp(self):
        database = mock.patch.object(utils, "db")
        self.db = database.start()

        ps = mock.patch.object(utils, "psutil")
        self.psutil = ps.start()
        self.psutil.NoSuchProcess = psutil.NoSuchProcess
        self.psutil.pid_exists.return_value = True
        self.process = mock.MagicMock()
        self.process.__hash__ = mock.Mock(return_value=LIVE_HASH)
        self.psutil.Process.return_value = self.process

        updater = mock.patch.object(utils, "database_updater")
        self.updater = updater.start()

        self.addCleanup(mock.patch.stopall)

    def run_clean(self, job):
        self.db.session.query.return_value.filter.return_value.all.return_value = [job]
        utils.clean_old_jobs()

    def test_hash_mismatch_marks_job_failed(self):
        self.process.__hash__.return_value = LIVE_HASH + 1
        job = make_job()
        self.run_clean(job)
        self.assertEqual(job.status, JobState.FAILURE.value)
        self.updater.assert_called_once_with({'status': JobState.FAILURE.value}, job)

    def test_running_job_is_left_alone(self):
        job = make_job()
        self.run_clean(job)
        self.assertEqual(job.status, JobState.VIDEO_RIPPING.value)
        self.updater.assert_not_called()


if __name__ == '__main__':
    unittest.main()
