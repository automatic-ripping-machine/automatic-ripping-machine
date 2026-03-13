"""Tests for the matching system (arm.services.matching)."""

import unittest.mock

import pytest

from arm.services.matching.base import MatchResult, MatchStrategy, TrackMatch
from arm.services.matching.tvdb_matcher import (
    TvdbMatcher,
    match_tracks_to_episodes,
    match_tracks_best_season,
)
from arm.services.matching.registry import (
    _MATCHERS,
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
