"""Tests for Job state properties and computed attributes."""
import datetime as dt


class TestJobFinished:
    """Test job.finished hybrid property."""

    def test_success_is_finished(self, sample_job):
        sample_job.status = "success"
        assert sample_job.finished is True

    def test_fail_is_finished(self, sample_job):
        sample_job.status = "fail"
        assert sample_job.finished is True

    def test_ready_not_finished(self, sample_job):
        sample_job.status = "ready"
        assert sample_job.finished is False

    def test_ripping_not_finished(self, sample_job):
        sample_job.status = "ripping"
        assert sample_job.finished is False

    def test_transcoding_not_finished(self, sample_job):
        sample_job.status = "transcoding"
        assert sample_job.finished is False


class TestJobIdle:
    """Test job.idle property."""

    def test_ready_is_idle(self, sample_job):
        sample_job.status = "ready"
        assert sample_job.idle is True

    def test_ripping_not_idle(self, sample_job):
        sample_job.status = "ripping"
        assert sample_job.idle is False

    def test_success_not_idle(self, sample_job):
        sample_job.status = "success"
        assert sample_job.idle is False


class TestJobRipping:
    """Test job.ripping property."""

    def test_ripping_state(self, sample_job):
        sample_job.status = "ripping"
        assert sample_job.ripping is True

    def test_waiting_state(self, sample_job):
        sample_job.status = "waiting"
        assert sample_job.ripping is True

    def test_ready_not_ripping(self, sample_job):
        sample_job.status = "ready"
        assert sample_job.ripping is False

    def test_transcoding_not_ripping(self, sample_job):
        sample_job.status = "transcoding"
        assert sample_job.ripping is False


class TestJobRippingFinished:
    """Test job.ripping_finished property."""

    def test_finished_job(self, sample_job):
        sample_job.status = "success"
        assert sample_job.ripping_finished is True

    def test_ready_job_not_ripping(self, sample_job):
        """Ready/idle is not ripping, so ripping is considered finished."""
        sample_job.status = "ready"
        assert sample_job.ripping_finished is True

    def test_ejected_job(self, sample_job):
        sample_job.status = "ripping"
        sample_job.ejected = True
        assert sample_job.ripping_finished is True

    def test_no_drive_job(self, sample_job):
        sample_job.status = "ripping"
        sample_job.drive = None
        assert sample_job.ripping_finished is True


class TestJobRunTime:
    """Test job.run_time property."""

    def test_run_time_returns_seconds(self, sample_job):
        sample_job.start_time = dt.datetime.now() - dt.timedelta(hours=1)
        run_time = sample_job.run_time
        # Should be approximately 3600 seconds (1 hour)
        assert 3590 < run_time < 3610

    def test_run_time_recent(self, sample_job):
        sample_job.start_time = dt.datetime.now() - dt.timedelta(seconds=5)
        assert sample_job.run_time < 10


class TestJobGetD:
    """Test job.get_d() dictionary export."""

    def test_returns_dict(self, sample_job):
        result = sample_job.get_d()
        assert isinstance(result, dict)

    def test_contains_title(self, sample_job):
        result = sample_job.get_d()
        assert "title" in result
        assert result["title"] == "SERIAL_MOM"

    def test_contains_video_type(self, sample_job):
        result = sample_job.get_d()
        assert "video_type" in result
        assert result["video_type"] == "movie"

    def test_contains_path_columns(self, sample_job):
        result = sample_job.get_d()
        assert "raw_path" in result
        assert "transcode_path" in result
        assert "path" in result
