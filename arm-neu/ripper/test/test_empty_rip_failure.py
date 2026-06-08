"""Empty-rip detection: zero ripped tracks -> FAILED with structured reason."""

from arm.database import db


def test_zero_ripped_tracks_marks_job_failed(app_context, sample_job):
    from arm.models.track import Track
    from arm.ripper.arm_ripper import check_empty_rip

    sample_job.no_of_titles = 7
    db.session.commit()

    for n, length, skip in [
        ("0", 4568, None),
        ("1", 33, "too_short"),
        ("2", 21, "too_short"),
        ("3", 60, "too_short"),
        ("4", 50, "too_short"),
        ("5", 11, "makemkv_skipped"),
        ("6", 0, "makemkv_skipped"),
    ]:
        t = Track(
            job_id=sample_job.job_id, track_number=n, length=length,
            aspect_ratio="4:3", fps=29.97, main_feature=False,
            source="MakeMKV", basename=f"t{n}", filename=f"t{n}.mkv",
        )
        t.ripped = False
        t.skip_reason = skip
        db.session.add(t)
    db.session.commit()

    is_empty = check_empty_rip(sample_job)
    assert is_empty is True
    assert "All 7 tracks" in (sample_job.errors or "")
    assert "4 too_short" in sample_job.errors
    assert "2 makemkv_skipped" in sample_job.errors


def test_at_least_one_ripped_track_does_not_fail(app_context, sample_job):
    from arm.models.track import Track
    from arm.ripper.arm_ripper import check_empty_rip

    t1 = Track(
        job_id=sample_job.job_id, track_number="0", length=4568,
        aspect_ratio="4:3", fps=29.97, main_feature=True,
        source="MakeMKV", basename="t0", filename="t0.mkv",
    )
    t1.ripped = True
    db.session.add(t1)
    db.session.commit()

    assert check_empty_rip(sample_job) is False


def test_no_tracks_at_all_does_not_fail(app_context, sample_job):
    """A job that reaches the check with zero Track rows is unusual but must not
    produce a confusing 'All 0 tracks were filtered: .' message."""
    from arm.ripper.arm_ripper import check_empty_rip

    assert check_empty_rip(sample_job) is False
    assert sample_job.errors in (None, "")
