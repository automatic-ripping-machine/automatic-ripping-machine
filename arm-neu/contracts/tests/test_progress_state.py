"""Tests for JobProgressState copy_progress / copy_stage wire fields.

Phase A of the unified rsync progress helper plan: arm_contracts exposes
copy_progress and copy_stage as optional fields on JobProgressState so
arm-neu can publish rsync copy-phase progress through the same
/jobs/{id}/progress-state contract that already carries rip_progress and
music_progress.
"""


def test_job_progress_state_has_copy_fields():
    """JobProgressState exposes copy_progress and copy_stage as optional
    fields that default to None for back-compat."""
    from arm_contracts import JobProgressState, TrackCounts
    state = JobProgressState(track_counts=TrackCounts(total=0, ripped=0))
    assert state.copy_progress is None
    assert state.copy_stage is None


def test_job_progress_state_accepts_copy_fields():
    """copy_progress and copy_stage round-trip through the model."""
    from arm_contracts import JobProgressState, TrackCounts
    state = JobProgressState(
        track_counts=TrackCounts(total=2, ripped=1),
        copy_progress=47.5,
        copy_stage="scratch-to-media",
    )
    dumped = state.model_dump(mode="json")
    assert dumped["copy_progress"] == 47.5
    assert dumped["copy_stage"] == "scratch-to-media"
    rehydrated = JobProgressState.model_validate(dumped)
    assert rehydrated.copy_progress == 47.5
    assert rehydrated.copy_stage == "scratch-to-media"
