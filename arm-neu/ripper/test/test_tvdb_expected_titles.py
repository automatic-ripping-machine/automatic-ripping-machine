"""Tests for TVDB ExpectedTitle population."""

from arm.database import db


def test_persist_expected_titles_from_episodes_writes_n_rows(app_context, sample_job):
    from arm.models.expected_title import ExpectedTitle
    from arm.services.tvdb_sync import persist_expected_titles_from_episodes

    episodes = [
        {"number": 1, "name": "Pilot", "runtime": 3300},
        {"number": 2, "name": "Episode 2", "runtime": 3083},
        {"number": 3, "name": "Episode 3", "runtime": 3017},
    ]
    persist_expected_titles_from_episodes(sample_job.job_id, season=1, episodes=episodes)

    rows = (db.session.query(ExpectedTitle)
            .filter_by(job_id=sample_job.job_id)
            .order_by(ExpectedTitle.episode_number)
            .all())
    assert len(rows) == 3
    assert all(r.source == "tvdb" for r in rows)
    assert all(r.season == 1 for r in rows)
    assert [r.episode_number for r in rows] == [1, 2, 3]
    assert [r.runtime_seconds for r in rows] == [3300, 3083, 3017]
    assert rows[0].title == "Pilot"


def test_persist_idempotent_replaces_rows(app_context, sample_job):
    from arm.models.expected_title import ExpectedTitle
    from arm.services.tvdb_sync import persist_expected_titles_from_episodes

    persist_expected_titles_from_episodes(
        sample_job.job_id, season=1,
        episodes=[
            {"number": 1, "name": "Old Pilot", "runtime": 3300},
            {"number": 2, "name": "Old Ep", "runtime": 3083},
        ],
    )
    persist_expected_titles_from_episodes(
        sample_job.job_id, season=2,
        episodes=[
            {"number": 1, "name": "New Pilot", "runtime": 2520},
        ],
    )

    rows = db.session.query(ExpectedTitle).filter_by(job_id=sample_job.job_id).all()
    assert len(rows) == 1
    assert rows[0].season == 2
    assert rows[0].title == "New Pilot"


def test_persist_handles_missing_runtime(app_context, sample_job):
    from arm.models.expected_title import ExpectedTitle
    from arm.services.tvdb_sync import persist_expected_titles_from_episodes

    episodes = [
        {"number": 1, "name": "Ep with runtime", "runtime": 3300},
        {"number": 2, "name": "Ep without runtime", "runtime": 0},
        {"number": 3, "name": "Ep with None", "runtime": None},
    ]
    persist_expected_titles_from_episodes(sample_job.job_id, season=1, episodes=episodes)

    rows = (db.session.query(ExpectedTitle)
            .filter_by(job_id=sample_job.job_id)
            .order_by(ExpectedTitle.episode_number)
            .all())
    assert len(rows) == 3
    assert rows[0].runtime_seconds == 3300
    assert rows[1].runtime_seconds is None
    assert rows[2].runtime_seconds is None
