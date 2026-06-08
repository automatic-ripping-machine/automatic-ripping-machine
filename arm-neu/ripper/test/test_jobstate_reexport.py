"""Verify JobState moves to contracts but stays importable from arm.models."""


def test_jobstate_importable_from_arm_models_job():
    from arm.models.job import JobState
    from arm_contracts.enums import JobState as ContractsJobState
    assert JobState is ContractsJobState


def test_jobstate_status_sets_unchanged():
    from arm.models.job import (
        JobState, JOB_STATUS_FINISHED, JOB_STATUS_RIPPING,
        JOB_STATUS_TRANSCODING, JOB_STATUS_SCANNING,
    )
    assert JOB_STATUS_FINISHED == {JobState.SUCCESS, JobState.FAILURE}
    assert JobState.VIDEO_RIPPING in JOB_STATUS_RIPPING
    assert JobState.TRANSCODE_ACTIVE in JOB_STATUS_TRANSCODING
    assert JOB_STATUS_SCANNING == {JobState.IDENTIFYING}
