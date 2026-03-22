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
