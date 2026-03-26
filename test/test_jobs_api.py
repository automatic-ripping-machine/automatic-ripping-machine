"""Tests for arm/api/v1/jobs.py — job config, multi-title, and track endpoints."""
import json
import unittest.mock

import pytest

from arm.database import db
from arm.models.job import Job
from arm.models.track import Track
from arm.models.config import Config


@pytest.fixture
def client(app_context):
    """Create a test client with DB context."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from arm.api.v1.jobs import router

    app = FastAPI()
    app.include_router(router)

    with TestClient(app) as c:
        yield c


@pytest.fixture
def job_with_tracks(sample_job):
    """Create a job with several tracks for testing."""
    t1 = Track(sample_job.job_id, '1', 3600, '16:9', 24.0, False, 'makemkv',
               'title_t00.mkv', 'title_t00.mkv', chapters=20, filesize=5000000)
    t2 = Track(sample_job.job_id, '2', 1800, '16:9', 24.0, False, 'makemkv',
               'title_t01.mkv', 'title_t01.mkv', chapters=10, filesize=2500000)
    t3 = Track(sample_job.job_id, '3', 600, '16:9', 24.0, False, 'makemkv',
               'title_t02.mkv', 'title_t02.mkv', chapters=5, filesize=800000)
    db.session.add_all([t1, t2, t3])
    db.session.commit()
    db.session.refresh(sample_job)
    return sample_job, [t1, t2, t3]


class TestAutoFlagTracks:
    """Test _auto_flag_tracks() behavior for MAINFEATURE toggle."""

    def test_mainfeature_on_single_title_enables_best_only(self, app_context, job_with_tracks, client):
        job, tracks = job_with_tracks
        job.video_type = 'movie'
        job.multi_title = False
        db.session.commit()

        resp = client.patch(
            f"/api/v1/jobs/{job.job_id}/config",
            json={"MAINFEATURE": True},
        )
        assert resp.status_code == 200

        db.session.expire_all()
        refreshed = Track.query.filter_by(job_id=job.job_id).order_by(Track.track_number).all()
        enabled_tracks = [t for t in refreshed if t.enabled]
        assert len(enabled_tracks) == 1
        # Best track has most chapters (t1 = 20 chapters)
        assert enabled_tracks[0].track_number == '1'

    def test_mainfeature_off_enables_all(self, app_context, job_with_tracks, client):
        job, tracks = job_with_tracks

        # First turn on
        client.patch(f"/api/v1/jobs/{job.job_id}/config", json={"MAINFEATURE": True})
        # Then turn off
        resp = client.patch(f"/api/v1/jobs/{job.job_id}/config", json={"MAINFEATURE": False})
        assert resp.status_code == 200

        db.session.expire_all()
        refreshed = Track.query.filter_by(job_id=job.job_id).all()
        assert all(t.enabled for t in refreshed)

    def test_mainfeature_on_multi_title_enables_all(self, app_context, job_with_tracks, client):
        job, tracks = job_with_tracks
        job.video_type = 'movie'
        job.multi_title = True
        db.session.commit()

        resp = client.patch(
            f"/api/v1/jobs/{job.job_id}/config",
            json={"MAINFEATURE": True},
        )
        assert resp.status_code == 200

        db.session.expire_all()
        refreshed = Track.query.filter_by(job_id=job.job_id).all()
        assert all(t.enabled for t in refreshed)

    def test_mainfeature_on_series_enables_all(self, app_context, job_with_tracks, client):
        job, tracks = job_with_tracks
        job.video_type = 'series'
        db.session.commit()

        resp = client.patch(
            f"/api/v1/jobs/{job.job_id}/config",
            json={"MAINFEATURE": True},
        )
        assert resp.status_code == 200

        db.session.expire_all()
        refreshed = Track.query.filter_by(job_id=job.job_id).all()
        assert all(t.enabled for t in refreshed)


class TestAudioFormatConfig:
    """Test AUDIO_FORMAT validation in change_job_config()."""

    def test_valid_format_accepted(self, app_context, sample_job, client):
        resp = client.patch(
            f"/api/v1/jobs/{sample_job.job_id}/config",
            json={"AUDIO_FORMAT": "flac"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_mp3_format_accepted(self, app_context, sample_job, client):
        resp = client.patch(
            f"/api/v1/jobs/{sample_job.job_id}/config",
            json={"AUDIO_FORMAT": "mp3"},
        )
        assert resp.status_code == 200

    def test_invalid_format_rejected(self, app_context, sample_job, client):
        resp = client.patch(
            f"/api/v1/jobs/{sample_job.job_id}/config",
            json={"AUDIO_FORMAT": "invalid_format"},
        )
        assert resp.status_code == 400
        assert "AUDIO_FORMAT" in resp.json()["error"]

    def test_format_case_insensitive(self, app_context, sample_job, client):
        resp = client.patch(
            f"/api/v1/jobs/{sample_job.job_id}/config",
            json={"AUDIO_FORMAT": "FLAC"},
        )
        assert resp.status_code == 200

    def test_nonexistent_job_returns_404(self, app_context, client):
        resp = client.patch(
            "/api/v1/jobs/99999/config",
            json={"AUDIO_FORMAT": "flac"},
        )
        assert resp.status_code == 404


class TestToggleMultiTitle:
    """Test POST /jobs/{id}/multi-title endpoint."""

    def test_toggle_on(self, app_context, sample_job, client):
        resp = client.post(
            f"/api/v1/jobs/{sample_job.job_id}/multi-title",
            json={"enabled": True},
        )
        assert resp.status_code == 200
        assert resp.json()["multi_title"] is True

    def test_toggle_off(self, app_context, sample_job, client):
        resp = client.post(
            f"/api/v1/jobs/{sample_job.job_id}/multi-title",
            json={"enabled": False},
        )
        assert resp.status_code == 200
        assert resp.json()["multi_title"] is False

    def test_nonexistent_job_returns_404(self, app_context, client):
        resp = client.post(
            "/api/v1/jobs/99999/multi-title",
            json={"enabled": True},
        )
        assert resp.status_code == 404


class TestUpdateTrackTitle:
    """Test PUT /jobs/{id}/tracks/{id}/title endpoint."""

    def test_set_title(self, app_context, job_with_tracks, client):
        job, tracks = job_with_tracks
        track = tracks[0]
        original_filename = track.filename
        resp = client.put(
            f"/api/v1/jobs/{job.job_id}/tracks/{track.track_id}/title",
            json={"title": "My Movie"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["updated"]["title"] == "My Movie"
        # Filename should NOT be overwritten — stays as MakeMKV original
        # so the transcoder can match output files back to track metadata
        assert "filename" not in data["updated"]
        db.session.expire(track)
        assert track.filename == original_filename

    def test_set_multiple_fields(self, app_context, job_with_tracks, client):
        job, tracks = job_with_tracks
        resp = client.put(
            f"/api/v1/jobs/{job.job_id}/tracks/{tracks[0].track_id}/title",
            json={"title": "Test Movie", "year": "2020", "video_type": "movie"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["updated"]["title"] == "Test Movie"
        assert data["updated"]["year"] == "2020"

    def test_no_fields_returns_400(self, app_context, job_with_tracks, client):
        job, tracks = job_with_tracks
        resp = client.put(
            f"/api/v1/jobs/{job.job_id}/tracks/{tracks[0].track_id}/title",
            json={},
        )
        assert resp.status_code == 400

    def test_nonexistent_track_returns_404(self, app_context, sample_job, client):
        resp = client.put(
            f"/api/v1/jobs/{sample_job.job_id}/tracks/99999/title",
            json={"title": "Test"},
        )
        assert resp.status_code == 404

    def test_track_wrong_job_returns_404(self, app_context, job_with_tracks, client):
        job, tracks = job_with_tracks
        # Use track from this job but wrong job_id in URL
        resp = client.put(
            f"/api/v1/jobs/99999/tracks/{tracks[0].track_id}/title",
            json={"title": "Test"},
        )
        assert resp.status_code == 404


class TestClearTrackTitle:
    """Test DELETE /jobs/{id}/tracks/{id}/title endpoint."""

    def test_clears_all_metadata(self, app_context, job_with_tracks, client):
        job, tracks = job_with_tracks
        track = tracks[0]
        track.title = "Custom Title"
        track.year = "2020"
        track.imdb_id = "tt1234567"
        db.session.commit()

        resp = client.delete(
            f"/api/v1/jobs/{job.job_id}/tracks/{track.track_id}/title",
        )
        assert resp.status_code == 200

        db.session.expire_all()
        refreshed = Track.query.get(track.track_id)
        assert refreshed.title is None
        assert refreshed.year is None
        assert refreshed.imdb_id is None
        assert refreshed.filename == refreshed.basename

    def test_nonexistent_job_returns_404(self, app_context, client):
        resp = client.delete("/api/v1/jobs/99999/tracks/1/title")
        assert resp.status_code == 404

    def test_nonexistent_track_returns_404(self, app_context, sample_job, client):
        resp = client.delete(
            f"/api/v1/jobs/{sample_job.job_id}/tracks/99999/title",
        )
        assert resp.status_code == 404


class TestTrackFieldUpdates:
    """Test PATCH /api/v1/jobs/{job_id}/tracks/{track_id}."""

    def test_patch_track_enabled(self, app_context, job_with_tracks, client):
        job, tracks = job_with_tracks
        resp = client.patch(
            f"/api/v1/jobs/{job.job_id}/tracks/{tracks[0].track_id}",
            json={"enabled": False},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        db.session.expire_all()
        refreshed = Track.query.get(tracks[0].track_id)
        assert refreshed.enabled is False

    def test_patch_track_filename(self, app_context, job_with_tracks, client):
        job, tracks = job_with_tracks
        resp = client.patch(
            f"/api/v1/jobs/{job.job_id}/tracks/{tracks[0].track_id}",
            json={"filename": "new-name.mkv"},
        )
        assert resp.status_code == 200
        assert resp.json()["updated"]["filename"] == "new-name.mkv"

    def test_patch_track_invalid_field(self, app_context, job_with_tracks, client):
        job, tracks = job_with_tracks
        resp = client.patch(
            f"/api/v1/jobs/{job.job_id}/tracks/{tracks[0].track_id}",
            json={"bad_field": True},
        )
        assert resp.status_code == 400

    def test_patch_track_not_found(self, app_context, sample_job, client):
        resp = client.patch(
            f"/api/v1/jobs/{sample_job.job_id}/tracks/99999",
            json={"enabled": True},
        )
        assert resp.status_code == 404

    def test_patch_episode_name_syncs_title(self, app_context, job_with_tracks, client):
        """Setting episode_name via PATCH must also update track.title so the
        webhook payload uses the correct name for the output filename."""
        job, tracks = job_with_tracks
        track = tracks[0]
        track.title = "Stale Auto-Match Name"
        db.session.commit()

        resp = client.patch(
            f"/api/v1/jobs/{job.job_id}/tracks/{track.track_id}",
            json={"episode_number": "6", "episode_name": "Firefall"},
        )
        assert resp.status_code == 200
        db.session.expire_all()
        refreshed = Track.query.get(track.track_id)
        assert refreshed.episode_name == "Firefall"
        assert refreshed.episode_number == "6"
        # title must be synced to episode_name
        assert refreshed.title == "Firefall"

    def test_patch_empty_episode_name_preserves_title(self, app_context, job_with_tracks, client):
        """Empty episode_name should NOT overwrite an existing track.title."""
        job, tracks = job_with_tracks
        track = tracks[0]
        track.title = "Original Title"
        db.session.commit()

        resp = client.patch(
            f"/api/v1/jobs/{job.job_id}/tracks/{track.track_id}",
            json={"episode_name": ""},
        )
        assert resp.status_code == 200
        db.session.expire_all()
        refreshed = Track.query.get(track.track_id)
        assert refreshed.episode_name == ""
        # title should NOT be overwritten with empty string
        assert refreshed.title == "Original Title"

    def test_patch_episode_name_only_without_number(self, app_context, job_with_tracks, client):
        """Patching episode_name alone (no episode_number) still syncs title."""
        job, tracks = job_with_tracks
        track = tracks[0]
        track.title = "Old Name"
        db.session.commit()

        resp = client.patch(
            f"/api/v1/jobs/{job.job_id}/tracks/{track.track_id}",
            json={"episode_name": "New Episode"},
        )
        assert resp.status_code == 200
        db.session.expire_all()
        refreshed = Track.query.get(track.track_id)
        assert refreshed.episode_name == "New Episode"
        assert refreshed.title == "New Episode"


class TestTvdbMatch:
    """Test POST /jobs/{id}/tvdb-match disc override logic."""

    def test_disc_overrides_set_on_job_before_matching(self, app_context, sample_job, client):
        """disc_number and disc_total from request body are set on the job before matching."""
        sample_job.disc_number = 1
        sample_job.disc_total = 1
        sample_job.status = "waiting"
        db.session.commit()

        captured_disc_number = None
        captured_disc_total = None

        def fake_match(job, season=None, tolerance=None, apply=False):
            nonlocal captured_disc_number, captured_disc_total
            captured_disc_number = job.disc_number
            captured_disc_total = job.disc_total
            return {"success": True, "matches": [], "preview": True}

        with unittest.mock.patch("arm.services.tvdb_sync.match_episodes_for_api", side_effect=fake_match):
            resp = client.post(
                f"/api/v1/jobs/{sample_job.job_id}/tvdb-match",
                json={"season": 2, "disc_number": 3, "disc_total": 6, "apply": False},
            )

        assert resp.status_code == 200
        # The matcher should have seen the overridden values
        assert captured_disc_number == 3
        assert captured_disc_total == 6

    def test_preview_mode_restores_originals(self, app_context, sample_job, client):
        """In preview mode (apply=false), original disc values are restored after matching."""
        sample_job.disc_number = 1
        sample_job.disc_total = 2
        sample_job.status = "waiting"
        db.session.commit()

        def fake_match(job, season=None, tolerance=None, apply=False):
            return {"success": True, "matches": [], "preview": True}

        with unittest.mock.patch("arm.services.tvdb_sync.match_episodes_for_api", side_effect=fake_match):
            resp = client.post(
                f"/api/v1/jobs/{sample_job.job_id}/tvdb-match",
                json={"season": 1, "disc_number": 5, "disc_total": 10, "apply": False},
            )

        assert resp.status_code == 200
        # Originals should be restored
        db.session.expire(sample_job)
        assert sample_job.disc_number == 1
        assert sample_job.disc_total == 2

    def test_apply_mode_persists_overrides(self, app_context, sample_job, client):
        """In apply mode (apply=true), disc overrides persist on the job."""
        sample_job.disc_number = 1
        sample_job.disc_total = 2
        sample_job.status = "waiting"
        db.session.commit()

        def fake_match(job, season=None, tolerance=None, apply=False):
            return {"success": True, "matches": [], "applied": True}

        with unittest.mock.patch("arm.services.tvdb_sync.match_episodes_for_api", side_effect=fake_match):
            resp = client.post(
                f"/api/v1/jobs/{sample_job.job_id}/tvdb-match",
                json={"season": 1, "disc_number": 5, "disc_total": 10, "apply": True},
            )

        assert resp.status_code == 200
        # Overrides should persist (not restored)
        db.session.expire(sample_job)
        assert sample_job.disc_number == 5
        assert sample_job.disc_total == 10

    def test_tvdb_match_job_not_found(self, app_context, client):
        """Non-existent job returns 404."""
        resp = client.post(
            "/api/v1/jobs/99999/tvdb-match",
            json={"season": 1},
        )
        assert resp.status_code == 404


class TestNamingPreviewForJob:
    """Test GET /api/v1/jobs/{job_id}/naming-preview."""

    def test_returns_rendered_titles_for_tracks(self, app_context, job_with_tracks, client):
        job, tracks = job_with_tracks
        job.video_type = 'series'
        job.season = '1'
        tracks[0].episode_number = '1'
        tracks[0].episode_name = 'Pilot'
        tracks[0].title = 'Pilot'
        db.session.commit()

        resp = client.get(f"/api/v1/jobs/{job.job_id}/naming-preview")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "job_title" in data
        assert "job_folder" in data
        assert len(data["tracks"]) == 3
        # First track should have rendered title with episode info
        t0 = data["tracks"][0]
        assert "rendered_title" in t0
        assert "rendered_folder" in t0
        assert t0["track_number"] is not None

    def test_returns_404_for_missing_job(self, app_context, client):
        resp = client.get("/api/v1/jobs/99999/naming-preview")
        assert resp.status_code == 404

    def test_empty_tracks(self, app_context, sample_job, client):
        resp = client.get(f"/api/v1/jobs/{sample_job.job_id}/naming-preview")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tracks"] == []
