"""Tests that successful identification writes ExpectedTitle rows."""

from arm.database import db


def test_write_movie_expected_title_creates_row(app_context, sample_job):
    from arm.models.expected_title import ExpectedTitle
    from arm.ripper.identify import _write_movie_expected_title

    _write_movie_expected_title(
        sample_job,
        title="Inception",
        imdb_id="tt1375666",
        runtime_seconds=8880,
        source="omdb",
    )

    rows = db.session.query(ExpectedTitle).filter_by(job_id=sample_job.job_id).all()
    assert len(rows) == 1
    assert rows[0].source == "omdb"
    assert rows[0].title == "Inception"
    assert rows[0].external_id == "tt1375666"
    assert rows[0].runtime_seconds == 8880
    assert rows[0].season is None
    assert rows[0].episode_number is None


def test_write_movie_expected_title_with_null_runtime(app_context, sample_job):
    """CRC fast path provides no runtime; row is still written."""
    from arm.models.expected_title import ExpectedTitle
    from arm.ripper.identify import _write_movie_expected_title

    _write_movie_expected_title(
        sample_job,
        title="Obscure",
        imdb_id="tt0000001",
        runtime_seconds=None,
        source="manual",
    )

    rows = db.session.query(ExpectedTitle).filter_by(job_id=sample_job.job_id).all()
    assert len(rows) == 1
    assert rows[0].runtime_seconds is None
    assert rows[0].source == "manual"


def test_write_movie_expected_title_idempotent(app_context, sample_job):
    """Calling twice replaces, does not duplicate."""
    from arm.models.expected_title import ExpectedTitle
    from arm.ripper.identify import _write_movie_expected_title

    _write_movie_expected_title(
        sample_job, title="V1", imdb_id="tt1", runtime_seconds=5712, source="omdb"
    )
    _write_movie_expected_title(
        sample_job, title="V2", imdb_id="tt2", runtime_seconds=8523, source="tmdb"
    )

    rows = db.session.query(ExpectedTitle).filter_by(job_id=sample_job.job_id).all()
    assert len(rows) == 1
    assert rows[0].title == "V2"
    assert rows[0].source == "tmdb"
    assert rows[0].runtime_seconds == 8523


def test_update_job_skips_expected_title_for_series(app_context, sample_job):
    """update_job should NOT write a movie ExpectedTitle for series matches.
    TV ExpectedTitle rows are populated by the TVDB path in A6."""
    from unittest.mock import MagicMock, patch
    from arm.models.expected_title import ExpectedTitle
    from arm.ripper.identify import update_job

    # Construct a minimal MatchSelection-like return that update_job consumes.
    best = MagicMock()
    best.title = "Some Series"
    best.year = "2020"
    best.type = "series"
    best.imdb_id = "tt9999999"
    best.poster_url = ""
    best.score = 0.95
    best.title_score = 0.95
    best.year_score = 1.0
    best.type_score = 1.0
    best.raw_result = {"runtime_seconds": 2820}

    selection = MagicMock()
    selection.hasnicetitle = True
    selection.best = best
    selection.label_info = None
    selection.all_scored = [best]

    with patch("arm.ripper.arm_matcher.match_disc", return_value=selection):
        update_job(sample_job, {"Search": [{"_": "_"}]})

    # No ExpectedTitle row should be written for a series match.
    rows = db.session.query(ExpectedTitle).filter_by(
        job_id=sample_job.job_id
    ).all()
    assert rows == []


def test_update_job_writes_expected_title_for_movie(app_context, sample_job):
    """update_job SHOULD write a movie ExpectedTitle for movie matches."""
    from unittest.mock import MagicMock, patch
    from arm.models.expected_title import ExpectedTitle
    from arm.ripper.identify import update_job

    best = MagicMock()
    best.title = "Inception"
    best.year = "2010"
    best.type = "movie"
    best.imdb_id = "tt1375666"
    best.poster_url = ""
    best.score = 0.95
    best.title_score = 0.95
    best.year_score = 1.0
    best.type_score = 1.0
    best.raw_result = {"runtime_seconds": 8880}

    selection = MagicMock()
    selection.hasnicetitle = True
    selection.best = best
    selection.label_info = None
    selection.all_scored = [best]

    with patch("arm.ripper.arm_matcher.match_disc", return_value=selection):
        update_job(sample_job, {"Search": [{"_": "_"}]})

    rows = db.session.query(ExpectedTitle).filter_by(
        job_id=sample_job.job_id
    ).all()
    assert len(rows) == 1
    assert rows[0].title == "Inception"
    assert rows[0].runtime_seconds == 8880
