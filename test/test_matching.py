"""Tests for the matching system (arm.services.matching)."""

import asyncio
import unittest.mock

import pytest

from arm.services.matching.base import MatchResult, MatchStrategy, TrackMatch
from arm.services.matching.tvdb_matcher import (
    TvdbMatcher,
    _get_known_season,
    match_tracks_to_episodes,
    match_tracks_best_season,
)
from arm.services.matching.registry import (
    _MATCHERS,
    _build_track_data,
    get_matchers,
    match_job,
    register,
    select_matcher,
)


class TestMatchResult:
    """Test the MatchResult dataclass."""

    def test_success_with_matches(self):
        r = MatchResult(matcher="tvdb", match_count=3, matches=[
            TrackMatch("0", 1, "Ep 1"),
            TrackMatch("1", 2, "Ep 2"),
            TrackMatch("2", 3, "Ep 3"),
        ])
        assert r.success is True

    def test_failure_with_error(self):
        r = MatchResult(matcher="tvdb", error="No IMDb ID")
        assert r.success is False

    def test_no_matches_is_not_success(self):
        r = MatchResult(matcher="tvdb", match_count=0)
        assert r.success is False


class TestCrossDiscExclusion:
    """Test exclude_episodes parameter in matching functions."""

    def test_excludes_episodes(self):
        episodes = [
            {"number": 1, "name": "Ep 1", "runtime": 3600},
            {"number": 2, "name": "Ep 2", "runtime": 3600},
            {"number": 3, "name": "Ep 3", "runtime": 3600},
            {"number": 4, "name": "Ep 4", "runtime": 3600},
            {"number": 5, "name": "Ep 5", "runtime": 3600},
        ]
        tracks = [
            {"track_number": "0", "length": 3550},
            {"track_number": "1", "length": 3560},
        ]
        # Exclude episodes 1-3 (already matched on disc 1)
        matches = match_tracks_to_episodes(
            tracks, episodes, tolerance=300,
            exclude_episodes={1, 2, 3},
        )
        eps = {m["episode_number"] for m in matches}
        assert eps == {4, 5}

    def test_exclude_all_returns_empty(self):
        episodes = [
            {"number": 1, "name": "Ep 1", "runtime": 3600},
            {"number": 2, "name": "Ep 2", "runtime": 3600},
        ]
        tracks = [{"track_number": "0", "length": 3550}]
        matches = match_tracks_to_episodes(
            tracks, episodes, tolerance=300,
            exclude_episodes={1, 2},
        )
        assert matches == []

    def test_exclude_none_matches_all(self):
        episodes = [
            {"number": 1, "name": "Ep 1", "runtime": 3600},
            {"number": 2, "name": "Ep 2", "runtime": 3600},
        ]
        tracks = [
            {"track_number": "0", "length": 3550},
            {"track_number": "1", "length": 3560},
        ]
        matches = match_tracks_to_episodes(
            tracks, episodes, tolerance=300,
            exclude_episodes=None,
        )
        assert len(matches) == 2

    def test_exclude_with_disc_number_combined(self):
        """Cross-disc exclusion + position bias work together."""
        episodes = [
            {"number": 1, "name": "Speedy Death", "runtime": 5400},
            {"number": 2, "name": "Death at the Opera", "runtime": 3600},
            {"number": 3, "name": "The Rising of the Moon", "runtime": 3600},
            {"number": 4, "name": "Laurels Are Poison", "runtime": 3600},
            {"number": 5, "name": "The Worsted Viper", "runtime": 3600},
        ]
        # Disc 2: E01-E03 already matched on disc 1
        tracks = [
            {"track_number": "0", "length": 3407},
            {"track_number": "1", "length": 3535},
        ]
        matches = match_tracks_to_episodes(
            tracks, episodes, tolerance=300,
            disc_number=2, disc_total=2,
            exclude_episodes={1, 2, 3},
        )
        eps = {m["episode_number"] for m in matches}
        assert eps == {4, 5}

    def test_best_season_with_exclusion(self):
        """match_tracks_best_season passes exclude through."""
        tracks = [{"track_number": "0", "length": 3550}]
        seasons = {
            1: [
                {"number": 1, "name": "Ep 1", "runtime": 3600},
                {"number": 2, "name": "Ep 2", "runtime": 3600},
                {"number": 3, "name": "Ep 3", "runtime": 3600},
            ],
        }
        # Without exclusion: matches ep 1
        r1 = match_tracks_best_season(tracks, seasons, tolerance=300)
        assert r1["matches"][0]["episode_number"] == 1

        # With exclusion: skips ep 1, matches ep 2
        r2 = match_tracks_best_season(
            tracks, seasons, tolerance=300,
            exclude_episodes={1},
        )
        assert r2["matches"][0]["episode_number"] == 2


class TestRegistry:
    """Test matcher registration and selection."""

    def test_tvdb_registered(self):
        names = [m.name for m in _MATCHERS]
        assert "tvdb" in names

    def test_select_matcher_for_series(self):
        job = unittest.mock.MagicMock()
        job.video_type = "series"
        job.imdb_id = "tt1234567"
        job.imdb_id_auto = None

        with unittest.mock.patch("arm.config.config.arm_config", {"TVDB_API_KEY": "test"}):
            matcher = select_matcher(job)
        assert matcher is not None
        assert matcher.name == "tvdb"

    def test_select_matcher_for_movie_returns_none(self):
        job = unittest.mock.MagicMock()
        job.video_type = "movie"
        job.imdb_id = "tt1234567"

        matcher = select_matcher(job)
        assert matcher is None

    def test_select_matcher_no_api_key_returns_none(self):
        job = unittest.mock.MagicMock()
        job.video_type = "series"
        job.imdb_id = "tt1234567"

        with unittest.mock.patch("arm.config.config.arm_config", {}):
            matcher = select_matcher(job)
        assert matcher is None

    def test_custom_matcher_registration(self):
        """Custom matchers can be registered and selected."""

        class DummyMatcher(MatchStrategy):
            @property
            def name(self):
                return "dummy"

            def can_handle(self, job):
                return getattr(job, "video_type", None) == "test"

            def match(self, job, tracks, **kwargs):
                return MatchResult(
                    matcher="dummy",
                    matches=[TrackMatch("0", 1, "Test Ep")],
                    match_count=1,
                )

        dummy = DummyMatcher()
        register(dummy)
        try:
            job = unittest.mock.MagicMock()
            job.video_type = "test"
            matcher = select_matcher(job)
            assert matcher is not None
            assert matcher.name == "dummy"
        finally:
            _MATCHERS.remove(dummy)


class TestTvdbMatcherCanHandle:
    """Test TvdbMatcher.can_handle()."""

    def _make_job(self, video_type="series", imdb_id="tt123"):
        job = unittest.mock.MagicMock()
        job.video_type = video_type
        job.imdb_id = imdb_id
        job.imdb_id_auto = None
        return job

    def test_series_with_key_and_imdb(self):
        with unittest.mock.patch("arm.config.config.arm_config", {"TVDB_API_KEY": "k"}):
            assert TvdbMatcher().can_handle(self._make_job()) is True

    def test_movie_rejected(self):
        with unittest.mock.patch("arm.config.config.arm_config", {"TVDB_API_KEY": "k"}):
            assert TvdbMatcher().can_handle(self._make_job(video_type="movie")) is False

    def test_no_api_key_rejected(self):
        with unittest.mock.patch("arm.config.config.arm_config", {}):
            assert TvdbMatcher().can_handle(self._make_job()) is False

    def test_no_imdb_rejected(self):
        with unittest.mock.patch("arm.config.config.arm_config", {"TVDB_API_KEY": "k"}):
            assert TvdbMatcher().can_handle(self._make_job(imdb_id=None)) is False

    def test_imdb_auto_fallback(self):
        job = self._make_job(imdb_id=None)
        job.imdb_id_auto = "tt999"
        with unittest.mock.patch("arm.config.config.arm_config", {"TVDB_API_KEY": "k"}):
            assert TvdbMatcher().can_handle(job) is True


# ======================================================================
# _async_compat tests (run_async)
# ======================================================================


class TestAsyncCompat:
    """Test run_async helper for sync/async bridging."""

    def test_run_async_no_loop(self):
        """When no event loop is running, uses asyncio.run()."""
        from arm.services.matching._async_compat import run_async

        async def add(a, b):
            return a + b

        assert run_async(add(2, 3)) == 5

    def test_run_async_inside_loop(self):
        """When called from inside an event loop, spawns a thread."""
        from arm.services.matching._async_compat import run_async

        async def multiply(a, b):
            return a * b

        async def outer():
            return run_async(multiply(4, 5))

        result = asyncio.run(outer())
        assert result == 20

    def test_run_async_propagates_exception_no_loop(self):
        """Exceptions from coroutine propagate when no loop is running."""
        from arm.services.matching._async_compat import run_async

        async def fail():
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            run_async(fail())

    def test_run_async_propagates_exception_inside_loop(self):
        """Exceptions from coroutine propagate when inside a loop."""
        from arm.services.matching._async_compat import run_async

        async def fail():
            raise RuntimeError("kaboom")

        async def outer():
            return run_async(fail())

        with pytest.raises(RuntimeError, match="kaboom"):
            asyncio.run(outer())


# ======================================================================
# _tvdb_resolve tests
# ======================================================================


class TestTvdbResolve:
    """Test resolve_tvdb_id helper."""

    def test_returns_cached_tvdb_id(self):
        """If job.tvdb_id is set, returns it without API call."""
        from arm.services.matching._tvdb_resolve import resolve_tvdb_id

        job = unittest.mock.MagicMock()
        job.tvdb_id = 12345
        result = resolve_tvdb_id(job, "tt0000001")
        assert result == 12345

    def test_queries_api_when_no_cached_id(self):
        """Falls back to API when job.tvdb_id is not set."""
        from arm.services.matching._tvdb_resolve import resolve_tvdb_id

        job = unittest.mock.MagicMock()
        job.tvdb_id = None

        with unittest.mock.patch(
            "arm.services.matching._tvdb_resolve._run_async", return_value=99999
        ):
            result = resolve_tvdb_id(job, "tt0000001")
        assert result == 99999

    def test_returns_none_when_api_returns_nothing(self):
        """Returns None when TVDB API finds no series."""
        from arm.services.matching._tvdb_resolve import resolve_tvdb_id

        job = unittest.mock.MagicMock()
        job.tvdb_id = None

        with unittest.mock.patch(
            "arm.services.matching._tvdb_resolve._run_async", return_value=None
        ):
            result = resolve_tvdb_id(job, "tt0000001")
        assert result is None

    def test_returns_cached_zero_is_falsy(self):
        """tvdb_id=0 is falsy, so it falls through to API."""
        from arm.services.matching._tvdb_resolve import resolve_tvdb_id

        job = unittest.mock.MagicMock()
        job.tvdb_id = 0

        with unittest.mock.patch(
            "arm.services.matching._tvdb_resolve._run_async", return_value=42
        ):
            result = resolve_tvdb_id(job, "tt0000001")
        assert result == 42


# ======================================================================
# cross_disc tests (get_excluded_episodes with DB)
# ======================================================================


class TestCrossDiscDB:
    """Test cross_disc.get_excluded_episodes with real DB queries."""

    def test_no_tvdb_id_returns_empty(self):
        """Returns empty set if job has no tvdb_id."""
        from arm.services.matching.cross_disc import get_excluded_episodes

        job = unittest.mock.MagicMock(spec=[])  # no tvdb_id attribute
        assert get_excluded_episodes(job) == set()

    def test_tvdb_id_none_returns_empty(self):
        from arm.services.matching.cross_disc import get_excluded_episodes

        job = unittest.mock.MagicMock()
        job.tvdb_id = None
        assert get_excluded_episodes(job) == set()

    def test_db_query_with_sibling_jobs(self, app_context):
        """Finds episode numbers from sibling jobs with same tvdb_id."""
        from arm.database import db
        from arm.models.job import Job
        from arm.models.track import Track
        from arm.services.matching.cross_disc import get_excluded_episodes

        # Create two jobs with same tvdb_id
        with unittest.mock.patch.object(Job, 'parse_udev'), \
             unittest.mock.patch.object(Job, 'get_pid'):
            job1 = Job('/dev/sr0')
            job2 = Job('/dev/sr1')

        job1.tvdb_id = 300
        job1.season = "1"
        job1.title = "Show"
        job1.video_type = "series"
        job2.tvdb_id = 300
        job2.season = "1"
        job2.title = "Show"
        job2.video_type = "series"

        db.session.add(job1)
        db.session.add(job2)
        db.session.flush()

        # Add tracks with episode_number to job1
        t1 = Track(job1.job_id, "0", 3600, "16:9", 23.976, False, "mkv", "t0", "t0.mkv")
        t1.episode_number = "1"
        t2 = Track(job1.job_id, "1", 3600, "16:9", 23.976, False, "mkv", "t1", "t1.mkv")
        t2.episode_number = "2"
        db.session.add_all([t1, t2])
        db.session.commit()

        # job2 should see episodes from job1 as excluded (no season filter
        # to avoid db.or_ which isn't in our custom _DB class)
        excluded = get_excluded_episodes(job2)
        assert excluded == {1, 2}

    def test_db_query_excludes_own_job(self, app_context):
        """Does not include episodes from the job itself."""
        from arm.database import db
        from arm.models.job import Job
        from arm.models.track import Track
        from arm.services.matching.cross_disc import get_excluded_episodes

        with unittest.mock.patch.object(Job, 'parse_udev'), \
             unittest.mock.patch.object(Job, 'get_pid'):
            job1 = Job('/dev/sr0')

        job1.tvdb_id = 400
        job1.title = "Show"
        job1.video_type = "series"
        db.session.add(job1)
        db.session.flush()

        t = Track(job1.job_id, "0", 3600, "16:9", 23.976, False, "mkv", "t0", "t0.mkv")
        t.episode_number = "5"
        db.session.add(t)
        db.session.commit()

        # Should be empty since there are no other jobs
        excluded = get_excluded_episodes(job1)
        assert excluded == set()

    def test_db_exception_returns_empty(self):
        """Returns empty set on DB errors (no crash)."""
        from arm.services.matching.cross_disc import get_excluded_episodes

        job = unittest.mock.MagicMock()
        job.tvdb_id = 500
        job.job_id = 1

        with unittest.mock.patch(
            "arm.services.matching.cross_disc.db"
        ) as mock_db:
            mock_db.session.query.side_effect = Exception("DB error")
            mock_db.or_ = unittest.mock.MagicMock()
            result = get_excluded_episodes(job, season=1)
        assert result == set()

    def test_invalid_episode_number_skipped(self, app_context):
        """Non-integer episode_number values are silently skipped."""
        from arm.database import db
        from arm.models.job import Job
        from arm.models.track import Track
        from arm.services.matching.cross_disc import get_excluded_episodes

        with unittest.mock.patch.object(Job, 'parse_udev'), \
             unittest.mock.patch.object(Job, 'get_pid'):
            job1 = Job('/dev/sr0')
            job2 = Job('/dev/sr1')

        job1.tvdb_id = 600
        job1.title = "Show"
        job1.video_type = "series"
        job2.tvdb_id = 600
        job2.title = "Show"
        job2.video_type = "series"
        db.session.add_all([job1, job2])
        db.session.flush()

        t = Track(job1.job_id, "0", 3600, "16:9", 23.976, False, "mkv", "t0", "t0.mkv")
        t.episode_number = "not_a_number"
        db.session.add(t)
        db.session.commit()

        excluded = get_excluded_episodes(job2)
        assert excluded == set()


# ======================================================================
# TvdbMatcher.match() tests (lines 49-84, 97-109, 121-149)
# ======================================================================


class TestTvdbMatcherMatch:
    """Test TvdbMatcher.match() method with mocked dependencies."""

    def _make_job(self, imdb_id="tt123", season=None, season_auto=None,
                  disc_number=None, disc_total=None, tvdb_id=None):
        job = unittest.mock.MagicMock()
        job.video_type = "series"
        job.imdb_id = imdb_id
        job.imdb_id_auto = None
        job.season = season
        job.season_auto = season_auto
        job.disc_number = disc_number
        job.disc_total = disc_total
        job.tvdb_id = tvdb_id
        return job

    def test_match_no_imdb_returns_error(self):
        """Returns error when no IMDb ID is available."""
        job = self._make_job(imdb_id=None)
        job.imdb_id_auto = None
        matcher = TvdbMatcher()
        config = {"TVDB_API_KEY": "k", "TVDB_MATCH_TOLERANCE": "300", "TVDB_MAX_SEASON_SCAN": "10"}
        with unittest.mock.patch("arm.config.config.arm_config", config):
            result = matcher.match(job, [])
        assert result.error == "No IMDb ID"

    def test_match_no_tvdb_series_returns_error(self):
        """Returns error when TVDB can't find a series."""
        job = self._make_job()
        config = {"TVDB_API_KEY": "k", "TVDB_MATCH_TOLERANCE": "300", "TVDB_MAX_SEASON_SCAN": "10"}
        with unittest.mock.patch("arm.config.config.arm_config", config), \
             unittest.mock.patch(
                 "arm.services.matching._tvdb_resolve.resolve_tvdb_id", return_value=None
             ):
            result = TvdbMatcher().match(job, [])
        assert result.error is not None
        assert "No TVDB series" in result.error

    def test_match_single_season_path(self):
        """When season is known, takes single-season path."""
        job = self._make_job(season="2", tvdb_id=100)
        episodes = [
            {"number": 1, "name": "Ep 1", "runtime": 3600},
            {"number": 2, "name": "Ep 2", "runtime": 3600},
        ]
        tracks = [{"track_number": "0", "length": 3550}]
        config = {"TVDB_API_KEY": "k", "TVDB_MATCH_TOLERANCE": "300", "TVDB_MAX_SEASON_SCAN": "10"}

        async def mock_get_season(tid, s):
            return episodes

        with unittest.mock.patch("arm.config.config.arm_config", config), \
             unittest.mock.patch(
                 "arm.services.matching._tvdb_resolve.resolve_tvdb_id", return_value=100
             ), \
             unittest.mock.patch(
                 "arm.services.matching.tvdb_matcher._run_async", return_value=episodes
             ), \
             unittest.mock.patch(
                 "arm.services.matching.tvdb_matcher.get_excluded_episodes", return_value=set()
             ):
            result = TvdbMatcher().match(job, tracks)

        assert result.season == 2
        assert result.tvdb_id == 100
        assert result.match_count > 0

    def test_match_single_season_no_episodes(self):
        """When TVDB returns no episodes for the season."""
        job = self._make_job(season="1", tvdb_id=100)
        config = {"TVDB_API_KEY": "k", "TVDB_MATCH_TOLERANCE": "300", "TVDB_MAX_SEASON_SCAN": "10"}

        with unittest.mock.patch("arm.config.config.arm_config", config), \
             unittest.mock.patch(
                 "arm.services.matching._tvdb_resolve.resolve_tvdb_id", return_value=100
             ), \
             unittest.mock.patch(
                 "arm.services.matching.tvdb_matcher._run_async", return_value=[]
             ), \
             unittest.mock.patch(
                 "arm.services.matching.tvdb_matcher.get_excluded_episodes", return_value=set()
             ):
            result = TvdbMatcher().match(job, [{"track_number": "0", "length": 3600}])

        assert result.match_count == 0
        assert result.season == 1

    def test_match_best_season_path(self):
        """When no season is known, scans all seasons."""
        job = self._make_job(season=None, season_auto=None, tvdb_id=200)
        seasons_data = {
            1: [{"number": 1, "name": "S1E1", "runtime": 3600}],
            2: [{"number": 1, "name": "S2E1", "runtime": 3550}],
        }
        tracks = [{"track_number": "0", "length": 3560}]
        config = {"TVDB_API_KEY": "k", "TVDB_MATCH_TOLERANCE": "300", "TVDB_MAX_SEASON_SCAN": "10"}

        with unittest.mock.patch("arm.config.config.arm_config", config), \
             unittest.mock.patch(
                 "arm.services.matching._tvdb_resolve.resolve_tvdb_id", return_value=200
             ), \
             unittest.mock.patch(
                 "arm.services.matching.tvdb_matcher._run_async", return_value=seasons_data
             ), \
             unittest.mock.patch(
                 "arm.services.matching.tvdb_matcher.get_excluded_episodes", return_value=set()
             ):
            result = TvdbMatcher().match(job, tracks)

        assert result.tvdb_id == 200
        assert result.match_count > 0
        # Best season should be S2 (closer runtime)
        assert result.season == 2

    def test_match_best_season_no_episodes(self):
        """When no seasons have any episodes."""
        job = self._make_job(season=None, season_auto=None, tvdb_id=300)
        config = {"TVDB_API_KEY": "k", "TVDB_MATCH_TOLERANCE": "300", "TVDB_MAX_SEASON_SCAN": "10"}

        with unittest.mock.patch("arm.config.config.arm_config", config), \
             unittest.mock.patch(
                 "arm.services.matching._tvdb_resolve.resolve_tvdb_id", return_value=300
             ), \
             unittest.mock.patch(
                 "arm.services.matching.tvdb_matcher._run_async", return_value={}
             ), \
             unittest.mock.patch(
                 "arm.services.matching.tvdb_matcher.get_excluded_episodes", return_value=set()
             ):
            result = TvdbMatcher().match(job, [{"track_number": "0", "length": 3600}])

        assert result.match_count == 0
        assert result.tvdb_id == 300

    def test_match_uses_imdb_id_auto_fallback(self):
        """Uses imdb_id_auto when imdb_id is empty."""
        job = self._make_job(imdb_id="", season="1", tvdb_id=100)
        job.imdb_id_auto = "tt9999"
        config = {"TVDB_API_KEY": "k", "TVDB_MATCH_TOLERANCE": "300", "TVDB_MAX_SEASON_SCAN": "10"}

        with unittest.mock.patch("arm.config.config.arm_config", config), \
             unittest.mock.patch(
                 "arm.services.matching._tvdb_resolve.resolve_tvdb_id", return_value=100
             ) as mock_resolve, \
             unittest.mock.patch(
                 "arm.services.matching.tvdb_matcher._run_async",
                 return_value=[{"number": 1, "name": "Ep1", "runtime": 3600}]
             ), \
             unittest.mock.patch(
                 "arm.services.matching.tvdb_matcher.get_excluded_episodes", return_value=set()
             ):
            result = TvdbMatcher().match(job, [{"track_number": "0", "length": 3550}])

        mock_resolve.assert_called_once_with(job, "tt9999")


# ======================================================================
# _get_known_season tests (lines 315-322)
# ======================================================================


class TestGetKnownSeason:
    """Test _get_known_season helper."""

    def test_returns_season_from_season_field(self):
        job = unittest.mock.MagicMock()
        job.season = "3"
        job.season_auto = None
        assert _get_known_season(job) == 3

    def test_returns_season_from_season_auto(self):
        job = unittest.mock.MagicMock()
        job.season = None
        job.season_auto = "5"
        assert _get_known_season(job) == 5

    def test_prefers_season_over_season_auto(self):
        job = unittest.mock.MagicMock()
        job.season = "2"
        job.season_auto = "7"
        assert _get_known_season(job) == 2

    def test_returns_none_when_both_none(self):
        job = unittest.mock.MagicMock()
        job.season = None
        job.season_auto = None
        assert _get_known_season(job) is None

    def test_returns_none_for_non_numeric(self):
        job = unittest.mock.MagicMock()
        job.season = "abc"
        job.season_auto = "xyz"
        assert _get_known_season(job) is None

    def test_returns_none_when_no_attributes(self):
        job = unittest.mock.MagicMock(spec=[])  # no season attrs
        assert _get_known_season(job) is None


# ======================================================================
# match_tracks_best_season edge cases (line 288 — empty scored list)
# ======================================================================


class TestMatchTracksBestSeasonEdgeCases:
    """Additional edge cases for match_tracks_best_season."""

    def test_empty_tracks(self):
        result = match_tracks_best_season([], {1: [{"number": 1, "name": "E1", "runtime": 3600}]})
        assert result["season"] == 0
        assert result["matches"] == []

    def test_empty_seasons(self):
        result = match_tracks_best_season([{"track_number": "0", "length": 3600}], {})
        assert result["season"] == 0
        assert result["matches"] == []

    def test_no_matches_in_any_season(self):
        """All seasons fail to match — tolerance too tight."""
        tracks = [{"track_number": "0", "length": 100}]  # too short, <120 cutoff
        seasons = {1: [{"number": 1, "name": "E1", "runtime": 3600}]}
        result = match_tracks_best_season(tracks, seasons, tolerance=10)
        # track is <120 so it's skipped; scored list has 0-match entry
        assert result["match_count"] == 0

    def test_alternatives_populated(self):
        """Second-best seasons appear in alternatives."""
        tracks = [
            {"track_number": "0", "length": 3600},
            {"track_number": "1", "length": 3600},
        ]
        seasons = {
            1: [
                {"number": 1, "name": "S1E1", "runtime": 3600},
                {"number": 2, "name": "S1E2", "runtime": 3600},
            ],
            2: [
                {"number": 1, "name": "S2E1", "runtime": 3600},
            ],
        }
        result = match_tracks_best_season(tracks, seasons, tolerance=300)
        # S1 should win (2 matches vs 1)
        assert result["season"] == 1
        assert result["match_count"] == 2
        assert len(result["alternatives"]) == 1
        assert result["alternatives"][0]["season"] == 2


# ======================================================================
# Registry: match_job, _build_track_data, get_matchers (lines 47-72)
# ======================================================================


class TestRegistryMatchJob:
    """Test registry.match_job and helpers."""

    def test_match_job_no_matcher(self):
        """Returns error when no matcher can handle the job."""
        job = unittest.mock.MagicMock()
        job.video_type = "movie"
        job.job_id = 1
        result = match_job(job)
        assert result.matcher == "none"
        assert result.error is not None
        assert "No matcher" in result.error

    def test_match_job_builds_tracks_from_job(self):
        """When tracks=None, builds from job.tracks."""
        job = unittest.mock.MagicMock()
        job.video_type = "series"
        job.imdb_id = "tt123"
        job.imdb_id_auto = None
        job.job_id = 1

        # Create mock tracks
        mock_track = unittest.mock.MagicMock()
        mock_track.track_number = "0"
        mock_track.length = 3600
        job.tracks = [mock_track]

        mock_result = MatchResult(matcher="tvdb", match_count=1,
                                  matches=[TrackMatch("0", 1, "Ep1")])

        with unittest.mock.patch("arm.config.config.arm_config", {"TVDB_API_KEY": "k"}), \
             unittest.mock.patch.object(TvdbMatcher, "match", return_value=mock_result) as mock_match:
            result = match_job(job)

        # Verify tracks were built from job.tracks
        call_tracks = mock_match.call_args[0][1]
        assert call_tracks == [{"track_number": "0", "length": 3600}]

    def test_match_job_matcher_exception(self):
        """When matcher raises, returns error result."""
        job = unittest.mock.MagicMock()
        job.video_type = "series"
        job.imdb_id = "tt123"
        job.imdb_id_auto = None
        job.job_id = 1

        with unittest.mock.patch("arm.config.config.arm_config", {"TVDB_API_KEY": "k"}), \
             unittest.mock.patch.object(TvdbMatcher, "match", side_effect=RuntimeError("oops")):
            result = match_job(job, tracks=[{"track_number": "0", "length": 3600}])

        assert result.error == "oops"
        assert result.matcher == "tvdb"

    def test_get_matchers_returns_copy(self):
        """get_matchers returns a copy, not the internal list."""
        matchers = get_matchers()
        assert isinstance(matchers, list)
        assert matchers is not _MATCHERS

    def test_build_track_data(self):
        """_build_track_data converts ORM tracks to dicts."""
        mock_track = unittest.mock.MagicMock()
        mock_track.track_number = "2"
        mock_track.length = 5000
        job = unittest.mock.MagicMock()
        job.tracks = [mock_track]

        result = _build_track_data(job)
        assert result == [{"track_number": "2", "length": 5000}]

    def test_build_track_data_none_length(self):
        """_build_track_data treats None length as 0."""
        mock_track = unittest.mock.MagicMock()
        mock_track.track_number = "0"
        mock_track.length = None
        job = unittest.mock.MagicMock()
        job.tracks = [mock_track]

        result = _build_track_data(job)
        assert result == [{"track_number": "0", "length": 0}]
