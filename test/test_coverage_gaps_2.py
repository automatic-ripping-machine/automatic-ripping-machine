"""Tests covering coverage gaps in webhook payload, transcode callback,
job config new fields, and custom abcde config with disc folder patterns.

Targets:
- arm/ripper/utils.py: _build_webhook_payload (multi-title, custom titles, overrides, None job)
- arm/api/v1/jobs.py: transcode_callback (partial, completed with track_results, unknown status)
- arm/api/v1/jobs.py: change_job_config (MUSIC_MULTI_DISC_SUBFOLDERS, MUSIC_DISC_FOLDER_PATTERN)
- arm/ripper/utils.py: _build_custom_abcde_config (disc_folder_pattern, default pattern, speed only)
"""
import json
import os
import tempfile
import unittest.mock

import pytest

from arm.database import db
from arm.models.job import Job, JobState
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


# ── _build_webhook_payload tests ─────────────────────────────────────────


class TestBuildWebhookPayload:
    """Test _build_webhook_payload in arm/ripper/utils.py."""

    def test_basic_payload_no_multi_title(self, app_context, sample_job):
        """Job with multi_title=False still includes track manifest (ARM controls naming)."""
        from arm.ripper.utils import _build_webhook_payload

        sample_job.multi_title = False
        db.session.commit()

        payload = _build_webhook_payload("Rip done", "body text", sample_job, "SERIAL_MOM")
        assert payload["title"] == "Rip done"
        assert payload["body"] == "body text"
        assert payload["path"] == "SERIAL_MOM"
        assert payload["job_id"] == str(sample_job.job_id)
        assert payload["video_type"] == "movie"
        assert payload["year"] == "1994"
        # multi_title flag not set when job.multi_title is False
        assert "multi_title" not in payload

    def test_single_title_with_tracks_includes_manifest(self, app_context, job_with_tracks):
        """Single-title job with tracks still includes track manifest for naming."""
        from arm.ripper.utils import _build_webhook_payload

        job, tracks = job_with_tracks
        job.multi_title = False
        db.session.commit()
        db.session.refresh(job)

        payload = _build_webhook_payload("Rip done", "body", job, "raw_dir")
        assert "multi_title" not in payload
        # Tracks are always included — ARM controls naming
        assert "tracks" in payload
        assert len(payload["tracks"]) == 3
        # Each track has title_name from naming engine
        for t_meta in payload["tracks"]:
            assert "title_name" in t_meta
            assert "folder_name" in t_meta
            assert "filename" in t_meta

    def test_multi_title_with_custom_titles(self, app_context, job_with_tracks):
        """Multi-title job with per-track custom titles includes tracks metadata."""
        from arm.ripper.utils import _build_webhook_payload

        job, tracks = job_with_tracks
        job.multi_title = True
        # Set custom title on track 1 only
        tracks[0].title = "Custom Movie"
        tracks[0].year = "2020"
        tracks[0].video_type = "movie"
        db.session.commit()
        db.session.refresh(job)

        payload = _build_webhook_payload("Rip done", "body", job, "raw_dir")
        assert payload["multi_title"] is True
        assert "tracks" in payload
        assert len(payload["tracks"]) == 3

        # Track 1 has custom title
        t1_meta = payload["tracks"][0]
        assert t1_meta["title"] == "Custom Movie"
        assert t1_meta["year"] == "2020"
        assert t1_meta["video_type"] == "movie"
        assert t1_meta["has_custom_title"] is True

    def test_multi_title_without_custom_titles(self, app_context, job_with_tracks):
        """Multi-title tracks without custom titles inherit job-level values."""
        from arm.ripper.utils import _build_webhook_payload

        job, tracks = job_with_tracks
        job.multi_title = True
        # No custom titles on any tracks — they should inherit job-level
        db.session.commit()
        db.session.refresh(job)

        payload = _build_webhook_payload("Rip done", "body", job, "raw_dir")
        assert payload["multi_title"] is True
        assert len(payload["tracks"]) == 3

        for t_meta in payload["tracks"]:
            # Inherits job title/year/video_type
            assert t_meta["title"] == job.title
            assert t_meta["year"] == str(job.year)
            assert t_meta["video_type"] == str(job.video_type)
            assert t_meta["has_custom_title"] is False

    def test_job_with_transcode_overrides(self, app_context, sample_job):
        """Transcode overrides JSON is included in payload."""
        from arm.ripper.utils import _build_webhook_payload

        overrides = {"video_encoder": "nvenc_h265", "video_quality": 22}
        sample_job.transcode_overrides = json.dumps(overrides)
        db.session.commit()

        payload = _build_webhook_payload("Rip done", "body", sample_job, "raw_dir")
        assert "config_overrides" in payload
        assert payload["config_overrides"]["video_encoder"] == "nvenc_h265"
        assert payload["config_overrides"]["video_quality"] == 22

    def test_job_is_none(self):
        """When job is None, payload has only basic fields."""
        from arm.ripper.utils import _build_webhook_payload

        payload = _build_webhook_payload("Test", "body", None, "some_path")
        assert payload["title"] == "Test"
        assert payload["body"] == "body"
        assert payload["path"] == "some_path"
        assert "job_id" not in payload
        assert "tracks" not in payload

    def test_no_raw_basename(self, app_context, sample_job):
        """When raw_basename is empty, no path key in payload."""
        from arm.ripper.utils import _build_webhook_payload

        payload = _build_webhook_payload("Test", "body", sample_job, "")
        assert "path" not in payload


# ── transcode_callback tests ─────────────────────────────────────────────


class TestTranscodeCallback:
    """Test POST /jobs/{id}/transcode-callback endpoint."""

    def test_partial_status_with_track_results(self, app_context, job_with_tracks, client):
        """status=partial sets job status to success with error message."""
        job, tracks = job_with_tracks

        resp = client.post(
            f"/api/v1/jobs/{job.job_id}/transcode-callback",
            json={
                "status": "partial",
                "error": "Track 3 failed",
                "track_results": [
                    {"track_number": "1", "status": "completed"},
                    {"track_number": "2", "status": "completed"},
                    {"track_number": "3", "status": "failed", "error": "codec error"},
                ],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["status"] == JobState.SUCCESS.value

        db.session.expire_all()
        refreshed_job = Job.query.get(job.job_id)
        assert refreshed_job.errors == "Track 3 failed"

        # Verify track statuses updated
        t1 = Track.query.filter_by(job_id=job.job_id, track_number='1').first()
        assert t1.status == "transcoded"
        t3 = Track.query.filter_by(job_id=job.job_id, track_number='3').first()
        assert "transcode_failed" in t3.status

    def test_completed_with_track_results(self, app_context, job_with_tracks, client):
        """status=completed with track_results updates per-track statuses."""
        job, tracks = job_with_tracks

        resp = client.post(
            f"/api/v1/jobs/{job.job_id}/transcode-callback",
            json={
                "status": "completed",
                "track_results": [
                    {"track_number": "1", "status": "completed"},
                    {"track_number": "2", "status": "completed"},
                ],
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == JobState.SUCCESS.value

        db.session.expire_all()
        t1 = Track.query.filter_by(job_id=job.job_id, track_number='1').first()
        t2 = Track.query.filter_by(job_id=job.job_id, track_number='2').first()
        assert t1.status == "transcoded"
        assert t2.status == "transcoded"

    def test_track_results_nonmatching_ignored(self, app_context, job_with_tracks, client):
        """track_results with non-matching track numbers are silently ignored."""
        job, tracks = job_with_tracks
        original_status = tracks[0].status

        resp = client.post(
            f"/api/v1/jobs/{job.job_id}/transcode-callback",
            json={
                "status": "completed",
                "track_results": [
                    {"track_number": "999", "status": "completed"},
                    {"track_number": "888", "status": "failed", "error": "nope"},
                ],
            },
        )
        assert resp.status_code == 200

        # Existing tracks should be unchanged
        db.session.expire_all()
        t1 = Track.query.filter_by(job_id=job.job_id, track_number='1').first()
        assert t1.status == original_status

    def test_unknown_status_returns_400(self, app_context, sample_job, client):
        """Unknown status value returns 400."""
        resp = client.post(
            f"/api/v1/jobs/{sample_job.job_id}/transcode-callback",
            json={"status": "banana"},
        )
        assert resp.status_code == 400
        assert "Unknown status" in resp.json()["error"]

    def test_nonexistent_job_returns_404(self, app_context, client):
        """Callback for nonexistent job returns 404."""
        resp = client.post(
            "/api/v1/jobs/99999/transcode-callback",
            json={"status": "completed"},
        )
        assert resp.status_code == 404


# ── change_job_config new fields tests ───────────────────────────────────


class TestChangeJobConfigNewFields:
    """Test MUSIC_MULTI_DISC_SUBFOLDERS and MUSIC_DISC_FOLDER_PATTERN in change_job_config."""

    def test_multi_disc_subfolders_true(self, app_context, sample_job, client):
        """Setting MUSIC_MULTI_DISC_SUBFOLDERS=true succeeds."""
        resp = client.patch(
            f"/api/v1/jobs/{sample_job.job_id}/config",
            json={"MUSIC_MULTI_DISC_SUBFOLDERS": True},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_multi_disc_subfolders_false(self, app_context, sample_job, client):
        """Setting MUSIC_MULTI_DISC_SUBFOLDERS=false succeeds."""
        resp = client.patch(
            f"/api/v1/jobs/{sample_job.job_id}/config",
            json={"MUSIC_MULTI_DISC_SUBFOLDERS": False},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_disc_folder_pattern_valid(self, app_context, sample_job, client):
        """Valid pattern containing {num} is accepted."""
        resp = client.patch(
            f"/api/v1/jobs/{sample_job.job_id}/config",
            json={"MUSIC_DISC_FOLDER_PATTERN": "CD {num}"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_disc_folder_pattern_missing_num_returns_400(self, app_context, sample_job, client):
        """Pattern without {num} placeholder returns 400."""
        resp = client.patch(
            f"/api/v1/jobs/{sample_job.job_id}/config",
            json={"MUSIC_DISC_FOLDER_PATTERN": "Disc"},
        )
        assert resp.status_code == 400
        assert "{num}" in resp.json()["error"]

    def test_disc_folder_pattern_empty_returns_400(self, app_context, sample_job, client):
        """Empty pattern returns 400."""
        resp = client.patch(
            f"/api/v1/jobs/{sample_job.job_id}/config",
            json={"MUSIC_DISC_FOLDER_PATTERN": ""},
        )
        assert resp.status_code == 400


# ── _build_custom_abcde_config tests ─────────────────────────────────────


class TestBuildCustomAbcdeConfig:
    """Test _build_custom_abcde_config with disc_folder_pattern and speed_profile."""

    @pytest.fixture
    def base_config(self, tmp_path):
        """Create a temporary base abcde config file."""
        config = tmp_path / "abcde.conf"
        config.write_text(
            "# abcde config\n"
            "OUTPUTFORMAT='${ARTISTFILE}/${ALBUMFILE}/${TRACKNUM} - ${TRACKFILE}'\n"
            "VAOUTPUTFORMAT='Various/${ALBUMFILE}/${TRACKNUM} - ${TRACKFILE}'\n"
            "CDROM=/dev/sr0\n"
        )
        return str(config)

    def test_disc_number_with_custom_pattern(self, base_config):
        """disc_number with custom disc_folder_pattern like 'CD {num}'."""
        from arm.ripper.utils import _build_custom_abcde_config

        result = _build_custom_abcde_config(
            base_config, disc_number=2, disc_folder_pattern="CD {num}"
        )
        assert result is not None

        try:
            with open(result, "r") as f:
                content = f.read()
            assert "CD 2" in content
            # Check that the disc dir is injected after ALBUMFILE
            assert "${ALBUMFILE}/CD 2/" in content
        finally:
            os.unlink(result)

    def test_disc_number_with_default_pattern(self, base_config):
        """disc_number with None pattern defaults to 'Disc {num}'."""
        from arm.ripper.utils import _build_custom_abcde_config

        result = _build_custom_abcde_config(
            base_config, disc_number=3, disc_folder_pattern=None
        )
        assert result is not None

        try:
            with open(result, "r") as f:
                content = f.read()
            assert "Disc 3" in content
            assert "${ALBUMFILE}/Disc 3/" in content
        finally:
            os.unlink(result)

    def test_disc_number_injects_into_va_output(self, base_config):
        """disc_number is also injected into VAOUTPUTFORMAT."""
        from arm.ripper.utils import _build_custom_abcde_config

        result = _build_custom_abcde_config(
            base_config, disc_number=1, disc_folder_pattern="Part {num}"
        )
        assert result is not None

        try:
            with open(result, "r") as f:
                content = f.read()
            assert "VAOUTPUTFORMAT=" in content
            assert "${ALBUMFILE}/Part 1/" in content
        finally:
            os.unlink(result)

    def test_speed_profile_only(self, base_config):
        """speed_profile without disc_number appends CDPARANOIAOPTS."""
        from arm.ripper.utils import _build_custom_abcde_config

        result = _build_custom_abcde_config(
            base_config, speed_profile="fast"
        )
        assert result is not None

        try:
            with open(result, "r") as f:
                content = f.read()
            assert 'CDPARANOIAOPTS="-Y"' in content
            # Should NOT inject disc folders
            assert "Disc " not in content
        finally:
            os.unlink(result)

    def test_speed_profile_safe_no_opts(self, base_config):
        """Safe speed profile has empty opts, so no CDPARANOIAOPTS line added."""
        from arm.ripper.utils import _build_custom_abcde_config

        result = _build_custom_abcde_config(
            base_config, speed_profile="safe"
        )
        assert result is not None

        try:
            with open(result, "r") as f:
                content = f.read()
            assert "CDPARANOIAOPTS" not in content
        finally:
            os.unlink(result)

    def test_nonexistent_base_config_returns_none(self):
        """Missing base config file returns None."""
        from arm.ripper.utils import _build_custom_abcde_config

        result = _build_custom_abcde_config(
            "/nonexistent/abcde.conf", disc_number=1
        )
        assert result is None
