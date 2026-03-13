"""Tests for TVDB v4 API episode matching."""

import asyncio
import unittest.mock

import pytest

from arm.services.tvdb import match_tracks_to_episodes


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


class TestTvdbAsync:
    """Test async TVDB functions with mocked HTTP."""

    def test_resolve_tvdb_id(self):
        from arm.services import tvdb

        mock_response = {
            "data": [{"tvdb_id": "71256", "id": "71256", "name": "Test Show"}]
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
