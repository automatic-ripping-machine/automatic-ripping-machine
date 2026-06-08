"""Tests for orphaned job cleanup on container startup."""

import unittest.mock
from unittest.mock import patch, MagicMock

import pytest

from arm.models.job import Job, JobState
from arm.database import db


@patch("arm.services.job_cleanup.clean_old_jobs")
class TestCleanupOrphanedJobs:
    """Test cleanup_orphaned_jobs() marks ARM-owned stuck jobs as failed."""

    def test_identifying_job_gets_failed(self, mock_clean, app_context, sample_job):
        sample_job.status = JobState.IDENTIFYING.value
        db.session.commit()

        from arm.services.job_cleanup import cleanup_orphaned_jobs
        count = cleanup_orphaned_jobs()

        db.session.refresh(sample_job)
        assert sample_job.status == JobState.FAILURE.value
        assert "ARM restarted" in sample_job.errors
        assert count == 1

    def test_ripping_job_gets_failed(self, mock_clean, app_context, sample_job):
        sample_job.status = JobState.VIDEO_RIPPING.value
        db.session.commit()

        from arm.services.job_cleanup import cleanup_orphaned_jobs
        count = cleanup_orphaned_jobs()

        db.session.refresh(sample_job)
        assert sample_job.status == JobState.FAILURE.value
        assert count == 1

    def test_waiting_job_gets_failed(self, mock_clean, app_context, sample_job):
        sample_job.status = JobState.MANUAL_PAUSED.value
        db.session.commit()

        from arm.services.job_cleanup import cleanup_orphaned_jobs
        count = cleanup_orphaned_jobs()

        db.session.refresh(sample_job)
        assert sample_job.status == JobState.FAILURE.value
        assert count == 1

    def test_ready_job_gets_failed(self, mock_clean, app_context, sample_job):
        sample_job.status = JobState.IDLE.value
        db.session.commit()

        from arm.services.job_cleanup import cleanup_orphaned_jobs
        count = cleanup_orphaned_jobs()

        db.session.refresh(sample_job)
        assert sample_job.status == JobState.FAILURE.value
        assert count == 1

    def test_ejecting_job_gets_failed(self, mock_clean, app_context, sample_job):
        sample_job.status = JobState.EJECTING.value
        db.session.commit()

        from arm.services.job_cleanup import cleanup_orphaned_jobs
        count = cleanup_orphaned_jobs()

        db.session.refresh(sample_job)
        assert sample_job.status == JobState.FAILURE.value
        assert count == 1

    def test_copying_job_gets_failed(self, mock_clean, app_context, sample_job):
        sample_job.status = JobState.COPYING.value
        db.session.commit()

        from arm.services.job_cleanup import cleanup_orphaned_jobs
        count = cleanup_orphaned_jobs()

        db.session.refresh(sample_job)
        assert sample_job.status == JobState.FAILURE.value
        assert count == 1

    def test_info_job_gets_failed(self, mock_clean, app_context, sample_job):
        sample_job.status = JobState.VIDEO_INFO.value
        db.session.commit()

        from arm.services.job_cleanup import cleanup_orphaned_jobs
        count = cleanup_orphaned_jobs()

        db.session.refresh(sample_job)
        assert sample_job.status == JobState.FAILURE.value
        assert count == 1

    def test_transcoding_job_not_touched(self, mock_clean, app_context, sample_job):
        sample_job.status = JobState.TRANSCODE_ACTIVE.value
        db.session.commit()

        from arm.services.job_cleanup import cleanup_orphaned_jobs
        count = cleanup_orphaned_jobs()

        db.session.refresh(sample_job)
        assert sample_job.status == JobState.TRANSCODE_ACTIVE.value
        assert count == 0

    def test_waiting_transcode_job_not_touched(self, mock_clean, app_context, sample_job):
        sample_job.status = JobState.TRANSCODE_WAITING.value
        db.session.commit()

        from arm.services.job_cleanup import cleanup_orphaned_jobs
        count = cleanup_orphaned_jobs()

        db.session.refresh(sample_job)
        assert sample_job.status == JobState.TRANSCODE_WAITING.value
        assert count == 0

    def test_success_job_not_touched(self, mock_clean, app_context, sample_job):
        sample_job.status = JobState.SUCCESS.value
        db.session.commit()

        from arm.services.job_cleanup import cleanup_orphaned_jobs
        count = cleanup_orphaned_jobs()

        db.session.refresh(sample_job)
        assert sample_job.status == JobState.SUCCESS.value
        assert count == 0

    def test_failed_job_not_touched(self, mock_clean, app_context, sample_job):
        sample_job.status = JobState.FAILURE.value
        db.session.commit()

        from arm.services.job_cleanup import cleanup_orphaned_jobs
        count = cleanup_orphaned_jobs()

        db.session.refresh(sample_job)
        assert sample_job.status == JobState.FAILURE.value
        assert count == 0

    def test_error_message_set(self, mock_clean, app_context, sample_job):
        sample_job.status = JobState.IDENTIFYING.value
        sample_job.errors = None
        db.session.commit()

        from arm.services.job_cleanup import cleanup_orphaned_jobs
        cleanup_orphaned_jobs()

        db.session.refresh(sample_job)
        assert sample_job.errors == "ARM restarted \u2014 process lost. Re-insert disc to retry."

    def test_drive_released(self, mock_clean, app_context, sample_job):
        mock_drive = MagicMock()
        sample_job.status = JobState.VIDEO_RIPPING.value
        db.session.commit()

        # Patch the drive attribute after commit to avoid SQLAlchemy
        # trying to persist the MagicMock as a relationship object.
        with patch.object(type(sample_job), 'drive',
                          new_callable=lambda: property(lambda self: mock_drive)):
            from arm.services.job_cleanup import cleanup_orphaned_jobs
            cleanup_orphaned_jobs()

        mock_drive.release_current_job.assert_called_once()

    def test_clean_old_jobs_called(self, mock_clean, app_context):
        from arm.services.job_cleanup import cleanup_orphaned_jobs
        cleanup_orphaned_jobs()
        mock_clean.assert_called_once()

    def test_no_orphans_returns_zero(self, mock_clean, app_context):
        from arm.services.job_cleanup import cleanup_orphaned_jobs
        count = cleanup_orphaned_jobs()
        assert count == 0

    def test_notification_sent_when_orphans_found(self, mock_clean, app_context, sample_job):
        sample_job.status = JobState.IDENTIFYING.value
        sample_job.title = "Test Movie"
        db.session.commit()

        from arm.services.job_cleanup import cleanup_orphaned_jobs
        from arm.models.notifications import Notifications
        cleanup_orphaned_jobs()

        rows = db.session.query(Notifications).all()
        # One summary row for the orphan cleanup.
        summary = [r for r in rows if "orphaned" in (r.title or "")]
        assert len(summary) == 1
        assert "1 orphaned" in summary[0].title
        assert "Test Movie" in summary[0].message

    def test_no_notification_when_no_orphans(self, mock_clean, app_context):
        from arm.services.job_cleanup import cleanup_orphaned_jobs
        from arm.models.notifications import Notifications
        cleanup_orphaned_jobs()

        rows = db.session.query(Notifications).filter(
            Notifications.title.like("%orphan%")
        ).all()
        assert rows == []

    def test_multiple_orphans(self, mock_clean, app_context):
        from arm.services.job_cleanup import cleanup_orphaned_jobs

        with unittest.mock.patch.object(Job, 'parse_udev'), \
             unittest.mock.patch.object(Job, 'get_pid'):
            job1 = Job('/dev/sr0')
        job1.status = JobState.IDENTIFYING.value
        job1.title = "Movie A"
        db.session.add(job1)

        with unittest.mock.patch.object(Job, 'parse_udev'), \
             unittest.mock.patch.object(Job, 'get_pid'):
            job2 = Job('/dev/sr1')
        job2.status = JobState.VIDEO_RIPPING.value
        job2.title = "Movie B"
        db.session.add(job2)
        db.session.commit()

        count = cleanup_orphaned_jobs()
        assert count == 2

        db.session.refresh(job1)
        db.session.refresh(job2)
        assert job1.status == JobState.FAILURE.value
        assert job2.status == JobState.FAILURE.value
