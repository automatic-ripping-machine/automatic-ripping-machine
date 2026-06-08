"""ExpectedTitle ORM smoke tests."""

import pytest

from arm.database import db


def test_expected_title_create_and_query(app_context, sample_job):
    from arm.models.expected_title import ExpectedTitle

    et = ExpectedTitle(
        job_id=sample_job.job_id,
        source="omdb",
        title="Inception",
        runtime_seconds=8880,
        external_id="tt1375666",
    )
    db.session.add(et)
    db.session.commit()

    rows = db.session.query(ExpectedTitle).filter_by(job_id=sample_job.job_id).all()
    assert len(rows) == 1
    assert rows[0].source == "omdb"
    assert rows[0].title == "Inception"
    assert rows[0].runtime_seconds == 8880
    assert rows[0].season is None
    assert rows[0].episode_number is None


def test_expected_title_tv_shape(app_context, sample_job):
    from arm.models.expected_title import ExpectedTitle

    for ep in range(1, 4):
        db.session.add(ExpectedTitle(
            job_id=sample_job.job_id,
            source="tvdb",
            title=f"Episode {ep}",
            season=1,
            episode_number=ep,
            runtime_seconds=2820 + ep,  # avoid round numbers
        ))
    db.session.commit()

    rows = (db.session.query(ExpectedTitle)
            .filter_by(job_id=sample_job.job_id)
            .order_by(ExpectedTitle.episode_number)
            .all())
    assert len(rows) == 3
    assert all(r.season == 1 for r in rows)
    assert [r.episode_number for r in rows] == [1, 2, 3]
    assert [r.runtime_seconds for r in rows] == [2821, 2822, 2823]


def test_expected_title_runtime_can_be_null(app_context, sample_job):
    from arm.models.expected_title import ExpectedTitle

    et = ExpectedTitle(
        job_id=sample_job.job_id,
        source="omdb",
        title="Obscure Film",
        runtime_seconds=None,
    )
    db.session.add(et)
    db.session.commit()
    assert db.session.query(ExpectedTitle).filter_by(runtime_seconds=None).count() == 1


def test_job_expected_titles_relationship(app_context, sample_job):
    """Verify the back-relationship: job.expected_titles returns the rows."""
    from arm.models.expected_title import ExpectedTitle

    db.session.add_all([
        ExpectedTitle(
            job_id=sample_job.job_id, source="omdb",
            title="Movie A", runtime_seconds=5712,
        ),
        ExpectedTitle(
            job_id=sample_job.job_id, source="tmdb",
            title="Movie A (alt)", runtime_seconds=5701,
        ),
    ])
    db.session.commit()
    db.session.refresh(sample_job)

    titles = sorted(et.title for et in sample_job.expected_titles)
    assert titles == ["Movie A", "Movie A (alt)"]


def test_expected_title_null_title_works(app_context, sample_job):
    """Title is nullable; metadata sources may not always return one."""
    from arm.models.expected_title import ExpectedTitle

    et = ExpectedTitle(
        job_id=sample_job.job_id,
        source="omdb",
        title=None,
        runtime_seconds=8880,
    )
    db.session.add(et)
    db.session.commit()

    row = db.session.query(ExpectedTitle).filter_by(runtime_seconds=8880).one()
    assert row.title is None
    # __repr__ must not crash on null title
    assert "omdb" in repr(row)
