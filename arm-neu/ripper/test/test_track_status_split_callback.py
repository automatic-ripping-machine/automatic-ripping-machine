"""Verify the transcode-callback handler writes plain status + error
columns rather than the old transcode_failed:<msg> prefix smell.

Before this change, a track-level transcode failure would set
track.status = "transcode_failed: <error>" (truncated to 200 chars
because the column was String(32)). After: track.status holds the
plain enum value and the full error text goes in track.error (db.Text).
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(app_context):
    from arm.app import app
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


def test_callback_writes_split_status_and_error(client, sample_job, app_context):
    from arm.database import db
    from arm.models.track import Track
    from arm_contracts.enums import TrackStatus

    # Seed a track for the sample_job.
    track = Track(
        job_id=sample_job.job_id, track_number="1", length=7200,
        aspect_ratio="16:9", fps=23.976, main_feature=True,
        source="MakeMKV", basename="t.mkv", filename="t.mkv",
    )
    db.session.add(track)
    db.session.commit()

    # Long error message to verify Track.error is no longer 200-char
    # truncated (was a side-effect of jamming it into a String(32) status
    # field with the prefix).
    long_err = "codec X264 returned -1 at frame 9001 " + ("x" * 500)

    resp = client.post(
        f"/api/v1/jobs/{sample_job.job_id}/transcode-callback",
        json={
            "status": "failed",
            "error": "job-level error",
            "track_results": [{
                "track_number": "1",
                "status": "failed",
                "error": long_err,
            }],
        },
        headers={"X-Api-Version": "2"},
    )
    assert resp.status_code == 200, resp.text

    db.session.refresh(track)
    assert track.status == TrackStatus.transcode_failed.value
    assert track.error == long_err
    assert ":" not in track.status  # status MUST NOT carry the message


def test_callback_writes_transcoded_on_completed(client, sample_job, app_context):
    from arm.database import db
    from arm.models.track import Track
    from arm_contracts.enums import TrackStatus

    track = Track(
        job_id=sample_job.job_id, track_number="1", length=7200,
        aspect_ratio="16:9", fps=23.976, main_feature=True,
        source="MakeMKV", basename="t.mkv", filename="t.mkv",
    )
    db.session.add(track)
    db.session.commit()

    resp = client.post(
        f"/api/v1/jobs/{sample_job.job_id}/transcode-callback",
        json={
            "status": "completed",
            "track_results": [{
                "track_number": "1",
                "status": "completed",
            }],
        },
        headers={"X-Api-Version": "2"},
    )
    assert resp.status_code == 200, resp.text

    db.session.refresh(track)
    assert track.status == TrackStatus.transcoded.value
