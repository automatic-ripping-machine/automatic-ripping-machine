"""Tests for pre-scan regressions: timeout, no status mutation, track cleanup, drive release."""
import subprocess
import unittest.mock

import pytest

# conftest.py sets up ARM_CONFIG_FILE and stubs hardware modules before arm imports
from arm.database import db
from arm.models.job import Job, JobState
from arm.models.track import Track
from arm.ripper import makemkv


@pytest.fixture
def sample_job_with_drive(app_context):
    """Create a Job with an associated SystemDrives record."""
    from arm.models.config import Config
    from arm.models.system_drives import SystemDrives

    _, _ = app_context

    with unittest.mock.patch.object(Job, 'parse_udev'), \
         unittest.mock.patch.object(Job, 'get_pid'):
        job = Job('/dev/sr0')

    job.arm_version = "test"
    job.crc_id = ""
    job.logfile = "test.log"
    job.start_time = None
    job.stop_time = None
    job.job_length = ""
    job.status = "active"
    job.stage = ""
    job.no_of_titles = 0
    job.title = "TEST_DISC"
    job.title_auto = "TEST_DISC"
    job.video_type = "movie"
    job.devpath = "/dev/sr0"
    job.mountpoint = "/mnt/dev/sr0"
    job.hasnicetitle = False
    job.disctype = "bluray"
    job.label = "TEST_DISC"
    job.pid = 99999
    job.pid_hash = 0

    db.session.add(job)
    db.session.flush()

    config = Config({
        'RAW_PATH': '/tmp/raw',
        'TRANSCODE_PATH': '/tmp/transcode',
        'COMPLETED_PATH': '/tmp/completed',
        'LOGPATH': '/tmp/logs',
        'EXTRAS_SUB': 'extras',
        'MINLENGTH': '0',
        'MAXLENGTH': '99999',
        'MAINFEATURE': False,
        'RIPMETHOD': 'mkv',
        'NOTIFY_RIP': False,
        'NOTIFY_TRANSCODE': False,
        'WEBSERVER_PORT': 8080,
    }, job.job_id)
    db.session.add(config)

    drive = SystemDrives()
    drive.mount = "/dev/sr0"
    drive.job_id_current = job.job_id
    drive.job_id_previous = None
    drive.mdisc = None
    db.session.add(drive)
    db.session.commit()
    db.session.refresh(job)

    return job


class TestPrescanDiscInfo:
    """prescan_disc_info does not mutate job.status."""

    def test_no_status_mutation(self, sample_job_with_drive):
        job = sample_job_with_drive
        original_status = job.status

        # Mock Popen to emit one TCOUNT line then exit cleanly
        mock_stdout = iter(["TCOUNT:2\n"])
        mock_proc = unittest.mock.MagicMock()
        mock_proc.stdout = mock_stdout
        mock_proc.returncode = 0
        mock_proc.kill = unittest.mock.MagicMock()
        mock_proc.__enter__ = unittest.mock.MagicMock(return_value=mock_proc)
        mock_proc.__exit__ = unittest.mock.MagicMock(return_value=False)

        with unittest.mock.patch('subprocess.Popen', return_value=mock_proc), \
             unittest.mock.patch('shutil.which', return_value='/usr/bin/makemkvcon'):
            # Set mdisc so prescan_resolve_mdisc returns immediately
            job.drive.mdisc = 0
            db.session.commit()
            messages = list(makemkv.prescan_disc_info(job, timeout=10))

        assert len(messages) == 1
        assert job.status == original_status

    def test_timeout_raises(self, sample_job_with_drive):
        """prescan_disc_info raises TimeoutExpired when subprocess hangs."""
        job = sample_job_with_drive
        job.drive.mdisc = 0
        db.session.commit()

        # Mock Popen that blocks forever on stdout iteration
        import threading

        class BlockingStdout:
            def __iter__(self):
                return self

            def __next__(self):
                # Block until the timer kills us — simulate a hung process
                threading.Event().wait(timeout=10)
                raise StopIteration

        mock_proc = unittest.mock.MagicMock()
        mock_proc.stdout = BlockingStdout()
        mock_proc.returncode = -9  # killed by timer
        mock_proc.kill = unittest.mock.MagicMock()
        mock_proc.__enter__ = unittest.mock.MagicMock(return_value=mock_proc)
        mock_proc.__exit__ = unittest.mock.MagicMock(return_value=False)

        with unittest.mock.patch('subprocess.Popen', return_value=mock_proc), \
             unittest.mock.patch('shutil.which', return_value='/usr/bin/makemkvcon'):
            with pytest.raises(subprocess.TimeoutExpired):
                list(makemkv.prescan_disc_info(job, timeout=0.1))


class TestPrescanTrackInfo:
    """prescan_track_info clears existing tracks and populates new ones."""

    def test_clears_existing_tracks(self, sample_job_with_drive):
        job = sample_job_with_drive

        # Insert a pre-existing track
        old_track = Track(
            job.job_id, "0", 120, "16:9", "24.0", False,
            "MakeMKV", "old.mkv", "old.mkv", 1, 1000
        )
        db.session.add(old_track)
        db.session.commit()
        assert Track.query.filter_by(job_id=job.job_id).count() == 1

        # Mock prescan_disc_info to return no messages (empty disc)
        with unittest.mock.patch.object(makemkv, 'prescan_disc_info', return_value=iter([])), \
             unittest.mock.patch.object(makemkv, 'prescan_resolve_mdisc', return_value=0):
            makemkv.prescan_track_info(job, timeout=10)

        # Old track should be deleted
        assert Track.query.filter_by(job_id=job.job_id).count() == 0

    def test_populates_tracks_from_output(self, sample_job_with_drive):
        job = sample_job_with_drive
        job.drive.mdisc = 0
        db.session.commit()

        # Simulate MakeMKV output: TCOUNT + TINFO messages for 2 tracks
        # TInfo(id, code, value, tid) — extends CInfo(id, code, value)
        from arm.ripper.makemkv import Titles, TInfo, TrackID

        messages = [
            Titles('2'),
            TInfo(TrackID.FILENAME.value, 0, 'title_t00.mkv', 0),
            TInfo(TrackID.DURATION.value, 0, '1:30:00', 0),
            TInfo(TrackID.CHAPTERS.value, 0, '20', 0),
            TInfo(TrackID.FILESIZE.value, 0, '5000000', 0),
            TInfo(TrackID.FILENAME.value, 0, 'title_t01.mkv', 1),
            TInfo(TrackID.DURATION.value, 0, '0:05:00', 1),
            TInfo(TrackID.CHAPTERS.value, 0, '2', 1),
        ]

        with unittest.mock.patch.object(makemkv, 'prescan_disc_info', return_value=iter(messages)), \
             unittest.mock.patch.object(makemkv, 'prescan_resolve_mdisc', return_value=0):
            makemkv.prescan_track_info(job, timeout=10)

        tracks = Track.query.filter_by(job_id=job.job_id).all()
        assert len(tracks) == 2


class TestCleanOldJobsDriveRelease:
    """clean_old_jobs releases drive association for abandoned jobs."""

    def test_drive_released_on_abandoned_job(self, sample_job_with_drive):
        job = sample_job_with_drive
        # Ensure the drive is associated
        assert job.drive is not None
        assert job.drive.job_id_current == job.job_id

        # Set PID to something that doesn't exist
        job.pid = 99999
        job.pid_hash = 0
        db.session.commit()

        with unittest.mock.patch('psutil.pid_exists', return_value=False):
            from arm.ripper.utils import clean_old_jobs
            clean_old_jobs()

        db.session.refresh(job)
        assert job.status == JobState.FAILURE.value

        # Re-query the drive directly (relationship may be stale after release)
        from arm.models.system_drives import SystemDrives
        drive = SystemDrives.query.filter_by(mount="/dev/sr0").first()
        assert drive.job_id_current is None
        assert drive.job_id_previous == job.job_id
