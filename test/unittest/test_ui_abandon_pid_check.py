"""
"Abandon" must only signal the job's own ripper. After a container restart the
stored PID can belong to an unrelated process.
"""
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, '/opt/arm')
from arm.ui import json_api  # noqa: E402

JOB_HASH = 1234567


class FakeProcess:
    """psutil.Process stand-in whose hash is the identity ARM stored (or not)"""

    def __init__(self, identity):
        self.identity = identity

    def __hash__(self):
        return self.identity


def make_job():
    job = SimpleNamespace(job_id=17, pid=4786, pid_hash=JOB_HASH, status="ripping")
    job.eject = MagicMock()
    return job


class TestAbandonChecksPid(unittest.TestCase):

    def abandon(self, job, process):
        query = MagicMock()
        query.get.return_value = job
        with patch.object(json_api.Job, "query", query), \
                patch.object(json_api.psutil, "Process", process), \
                patch.object(json_api, "terminate_process") as terminate, \
                patch.object(json_api.db.session, "add"), \
                patch.object(json_api.db.session, "commit"):
            result = json_api.abandon_job("17")
        return result, terminate

    def test_own_ripper_is_terminated(self):
        """CHECK the job's own ripper (same PID and hash) still gets terminated"""
        job = make_job()
        result, terminate = self.abandon(job, MagicMock(return_value=FakeProcess(JOB_HASH)))
        terminate.assert_called_once_with(4786)
        self.assertTrue(result["success"])
        job.eject.assert_called_once()

    def test_reused_pid_is_not_signalled(self):
        """CHECK a PID that now belongs to another process isn't signalled, but the job is released"""
        job = make_job()
        result, terminate = self.abandon(job, MagicMock(return_value=FakeProcess(999)))
        terminate.assert_not_called()
        self.assertTrue(result["success"])
        self.assertEqual(job.status, "fail")
        job.eject.assert_called_once()

    def test_gone_process_releases_the_job(self):
        """CHECK a job whose process is gone is still marked failed and released"""
        job = make_job()
        gone = MagicMock(side_effect=json_api.psutil.NoSuchProcess(4786))
        result, terminate = self.abandon(job, gone)
        terminate.assert_not_called()
        self.assertTrue(result["success"])
        job.eject.assert_called_once()


if __name__ == '__main__':
    unittest.main()
