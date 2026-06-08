"""Tests for job status group definitions."""
from arm.models.job import (
    JobState,
    JOB_STATUS_RIPPING,
    JOB_STATUS_SCANNING,
    JOB_STATUS_FINISHED,
    JOB_STATUS_TRANSCODING,
)


class TestJobStatusGroups:
    def test_identifying_not_in_ripping(self):
        """IDENTIFYING should not be in the ripping group."""
        assert JobState.IDENTIFYING not in JOB_STATUS_RIPPING

    def test_identifying_in_scanning(self):
        """IDENTIFYING should be in the scanning group."""
        assert JobState.IDENTIFYING in JOB_STATUS_SCANNING

    def test_scanning_group_exists(self):
        """JOB_STATUS_SCANNING should be a non-empty set."""
        assert len(JOB_STATUS_SCANNING) > 0

    def test_no_overlap_scanning_ripping(self):
        """Scanning and ripping groups must not overlap."""
        assert JOB_STATUS_SCANNING.isdisjoint(JOB_STATUS_RIPPING)

    def test_no_overlap_scanning_finished(self):
        """Scanning and finished groups must not overlap."""
        assert JOB_STATUS_SCANNING.isdisjoint(JOB_STATUS_FINISHED)

    def test_no_overlap_scanning_transcoding(self):
        """Scanning and transcoding groups must not overlap."""
        assert JOB_STATUS_SCANNING.isdisjoint(JOB_STATUS_TRANSCODING)

    def test_ripping_still_contains_video_ripping(self):
        """VIDEO_RIPPING must remain in the ripping group."""
        assert JobState.VIDEO_RIPPING in JOB_STATUS_RIPPING

    def test_ripping_still_contains_audio_ripping(self):
        """AUDIO_RIPPING must remain in the ripping group."""
        assert JobState.AUDIO_RIPPING in JOB_STATUS_RIPPING
