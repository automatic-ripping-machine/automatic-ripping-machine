"""Tests for TVDB v4 API episode matching."""

import asyncio
import unittest.mock

import pytest

from arm.services.tvdb import match_tracks_to_episodes, match_tracks_best_season


class TestMatchTracksToEpisodes:
    """Test the runtime-based track-to-episode matching algorithm."""

    def test_perfect_match(self):
        tracks = [
            {"track_number": "0", "length": 3400},
            {"track_number": "1", "length": 3500},
            {"track_number": "2", "length": 2200},
        ]
        episodes = [
            {"number": 1, "name": "Speedy Death", "runtime": 3420},
            {"number": 2, "name": "Death at the Opera", "runtime": 3480},
            {"number": 3, "name": "The Rising of the Moon", "runtime": 2160},
        ]
        matches = match_tracks_to_episodes(tracks, episodes, tolerance=300)
        assert len(matches) == 3
        by_track = {m["track_number"]: m for m in matches}
        assert by_track["0"]["episode_name"] == "Speedy Death"
        assert by_track["1"]["episode_name"] == "Death at the Opera"
        assert by_track["2"]["episode_name"] == "The Rising of the Moon"

    def test_tolerance_exceeded(self):
        tracks = [
            {"track_number": "0", "length": 3400},
            {"track_number": "1", "length": 100},   # way too short
        ]
        episodes = [
            {"number": 1, "name": "Episode 1", "runtime": 3420},
            {"number": 2, "name": "Episode 2", "runtime": 3500},
        ]
        matches = match_tracks_to_episodes(tracks, episodes, tolerance=300)
        # Track 1 (100s) is <120s so skipped as menu/intro
        assert len(matches) == 1
        assert matches[0]["episode_name"] == "Episode 1"

    def test_more_episodes_than_tracks(self):
        """Disc has fewer tracks than episodes in the season (normal for multi-disc)."""
        tracks = [
            {"track_number": "0", "length": 3400},
        ]
        episodes = [
            {"number": 1, "name": "Ep 1", "runtime": 3420},
            {"number": 2, "name": "Ep 2", "runtime": 3500},
            {"number": 3, "name": "Ep 3", "runtime": 3600},
        ]
        matches = match_tracks_to_episodes(tracks, episodes, tolerance=300)
        assert len(matches) == 1
        assert matches[0]["episode_number"] == 1

    def test_more_tracks_than_episodes(self):
        """Disc has extras/bonus tracks beyond episode count."""
        tracks = [
            {"track_number": "0", "length": 3400},
            {"track_number": "1", "length": 3500},
            {"track_number": "2", "length": 600},   # bonus/extra
        ]
        episodes = [
            {"number": 1, "name": "Ep 1", "runtime": 3420},
        ]
        matches = match_tracks_to_episodes(tracks, episodes, tolerance=300)
        assert len(matches) == 1
        assert matches[0]["track_number"] == "0"

    def test_empty_inputs(self):
        assert match_tracks_to_episodes([], [], tolerance=300) == []
        assert match_tracks_to_episodes([], [{"number": 1, "name": "X", "runtime": 3000}]) == []
        assert match_tracks_to_episodes([{"track_number": "0", "length": 3000}], []) == []

    def test_greedy_no_reuse(self):
        """Two tracks with similar runtimes shouldn't both claim the same episode."""
        tracks = [
            {"track_number": "0", "length": 3400},
            {"track_number": "1", "length": 3410},
        ]
        episodes = [
            {"number": 1, "name": "Ep 1", "runtime": 3400},
            {"number": 2, "name": "Ep 2", "runtime": 3500},
        ]
        matches = match_tracks_to_episodes(tracks, episodes, tolerance=300)
        assert len(matches) == 2
        eps = {m["episode_number"] for m in matches}
        assert eps == {1, 2}  # both episodes assigned, no duplicates

    def test_short_tracks_skipped(self):
        """Tracks under 120s (menus/intros) are excluded from matching."""
        tracks = [
            {"track_number": "0", "length": 12},
            {"track_number": "1", "length": 18},
            {"track_number": "2", "length": 66},
            {"track_number": "3", "length": 3400},
        ]
        episodes = [
            {"number": 1, "name": "Ep 1", "runtime": 3420},
        ]
        matches = match_tracks_to_episodes(tracks, episodes, tolerance=300)
        assert len(matches) == 1
        assert matches[0]["track_number"] == "3"


class TestMatchTracksBestSeason:
    """Test multi-season best-match selection."""

    def _make_tracks(self, lengths):
        return [{"track_number": str(i), "length": l} for i, l in enumerate(lengths)]

    def _make_episodes(self, runtimes):
        return [
            {"number": i + 1, "name": f"Ep {i + 1}", "runtime": r}
            for i, r in enumerate(runtimes)
        ]

    def test_picks_best_season(self):
        """Season 2 episodes match better than season 1."""
        tracks = self._make_tracks([3400, 3500, 2200])
        seasons = {
            1: self._make_episodes([2800, 2900, 3000]),  # poor match
            2: self._make_episodes([3420, 3480, 2160]),  # excellent match
        }
        result = match_tracks_best_season(tracks, seasons, tolerance=300)
        assert result["season"] == 2
        assert result["match_count"] == 3
        assert len(result["alternatives"]) >= 0

    def test_no_match_any_season(self):
        """No season matches within tolerance."""
        tracks = self._make_tracks([100, 200])  # too short, all skipped
        seasons = {
            1: self._make_episodes([3400, 3500]),
        }
        result = match_tracks_best_season(tracks, seasons, tolerance=300)
        assert result["match_count"] == 0

    def test_empty_inputs(self):
        result = match_tracks_best_season([], {}, tolerance=300)
        assert result["season"] == 0
        assert result["matches"] == []

    def test_single_season(self):
        tracks = self._make_tracks([3400])
        seasons = {1: self._make_episodes([3420])}
        result = match_tracks_best_season(tracks, seasons, tolerance=300)
        assert result["season"] == 1
        assert result["match_count"] == 1

    def test_tiebreaker_by_delta(self):
        """When match count is equal, prefer lower average delta."""
        tracks = self._make_tracks([3400])
        seasons = {
            1: self._make_episodes([3500]),  # delta = 100
            2: self._make_episodes([3410]),  # delta = 10 (better)
        }
        result = match_tracks_best_season(tracks, seasons, tolerance=300)
        assert result["season"] == 2

    def test_alternatives_only_include_nonzero_matches(self):
        """Alternatives list should exclude seasons with zero matches."""
        tracks = self._make_tracks([3400, 3500])
        seasons = {
            1: self._make_episodes([3420, 3480]),  # 2 matches
            2: self._make_episodes([9999, 8888]),  # 0 matches
            3: self._make_episodes([3450, 3550]),  # 2 matches but worse delta
        }
        result = match_tracks_best_season(tracks, seasons, tolerance=300)
        assert result["match_count"] == 2
        alt_seasons = {a["season"] for a in result["alternatives"]}
        assert 2 not in alt_seasons  # season 2 had 0 matches

    def test_never_mixes_episodes(self):
        """Each season is scored independently — no cross-season mixing."""
        tracks = self._make_tracks([3400, 5000])
        seasons = {
            1: self._make_episodes([3420]),       # matches track 0 only
            2: self._make_episodes([5020]),       # matches track 1 only
        }
        # If mixing were allowed, both tracks would match. But per-season,
        # each season can only match 1 track.
        result = match_tracks_best_season(tracks, seasons, tolerance=300)
        assert result["match_count"] == 1


class TestGetAllSeasonEpisodes:
    """Test the multi-season fetch function."""

    def test_fetches_until_empty(self):
        from arm.services import tvdb

        async def mock_get_season_episodes(tvdb_id, season):
            if season <= 3:
                return [{"number": 1, "name": f"S{season}E1", "runtime": 3000}]
            return []

        with unittest.mock.patch.object(
            tvdb, 'get_season_episodes', side_effect=mock_get_season_episodes
        ):
            result = asyncio.run(tvdb.get_all_season_episodes(12345, max_season=10))
        assert set(result.keys()) == {1, 2, 3}

    def test_respects_max_season(self):
        from arm.services import tvdb

        async def mock_get_season_episodes(tvdb_id, season):
            return [{"number": 1, "name": f"S{season}E1", "runtime": 3000}]

        with unittest.mock.patch.object(
            tvdb, 'get_season_episodes', side_effect=mock_get_season_episodes
        ):
            result = asyncio.run(tvdb.get_all_season_episodes(12345, max_season=3))
        assert set(result.keys()) == {1, 2, 3}


class TestTvdbAsync:
    """Test async TVDB functions with mocked HTTP."""

    def test_resolve_tvdb_id(self):
        from arm.services import tvdb

        mock_response = {
            "data": [{"series": {"id": "71256", "name": "Test Show"}}]
        }
        with unittest.mock.patch.object(tvdb, '_get', return_value=mock_response):
            result = asyncio.run(tvdb.resolve_tvdb_id("tt0167667"))
        assert result == 71256

    def test_resolve_tvdb_id_not_found(self):
        from arm.services import tvdb

        mock_response = {"data": []}
        with unittest.mock.patch.object(tvdb, '_get', return_value=mock_response):
            result = asyncio.run(tvdb.resolve_tvdb_id("tt9999999"))
        assert result is None

    def test_get_season_episodes_dvd_order(self):
        from arm.services import tvdb

        page0_response = {
            "data": {
                "series": {},
                "episodes": [
                    {"number": 1, "name": "Pilot", "runtime": 55, "aired": "2000-01-01"},
                    {"number": 2, "name": "Second", "runtime": 50, "aired": "2000-01-08"},
                ],
            }
        }
        page1_response = {"data": {"series": {}, "episodes": []}}
        with unittest.mock.patch.object(
            tvdb, '_get', side_effect=[page0_response, page1_response]
        ):
            eps = asyncio.run(tvdb.get_season_episodes(71256, 1))
        assert len(eps) == 2
        assert eps[0]["name"] == "Pilot"
        assert eps[0]["runtime"] == 55 * 60  # converted to seconds
        assert eps[1]["number"] == 2


class TestNamingWithEpisodeNumber:
    """Test that episode_number from TVDB feeds into the naming engine."""

    def test_episode_number_overrides_track_fallback(self, app_context):
        from arm.ripper.naming import _build_track_variables

        # Mock track with TVDB-matched episode_number
        track = unittest.mock.MagicMock()
        track.title = "Speedy Death"
        track.year = None
        track.video_type = "series"
        track.episode_number = "3"
        track.track_number = "0"

        job = unittest.mock.MagicMock()
        job.title = "Show"
        job.title_manual = None
        job.year = "1998"
        job.year_manual = None
        job.video_type = "series"
        job.season = "1"
        job.season_manual = None
        job.episode = None
        job.episode_manual = None
        job.artist = None
        job.artist_manual = None
        job.album = None
        job.album_manual = None
        job.label = "SHOW_S1D1"
        job.disc_number = 1

        variables = _build_track_variables(track, job)
        # Should use TVDB episode_number (3), not track_number+1 (1)
        assert variables['episode'] == '03'
        assert variables['title'] == 'Speedy Death'
