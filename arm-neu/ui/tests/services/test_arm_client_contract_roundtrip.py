"""Contract roundtrip tests for arm_client.

Each test sets up a mocked arm-neu HTTP response with a wire-shaped
JSON dict, calls the arm_client function, and validates the returned
data through the corresponding arm_contracts (or backend.models.schemas)
type. A REQUIRED-field rename in arm_contracts breaks these tests.

Coverage caveat (G9): contracts use extra='ignore' and most fields are
Optional, so optional-field renames slide through silently. Catching
those is the job of the deferred F6 / G9 snapshot test in the contracts
repo. These tests still catch:
- Required-field renames (job_id, track_id, etc.)
- Type incompatibilities on optional fields (e.g. int -> dict)
- Changes to JobSchema.transcode_overrides validator behavior

Audit reference:
docs/superpowers/specs/2026-04-29-cross-service-contract-drift-audit-design.md F4 (G5/G9).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from arm_contracts import (
    JobProgressState,
    JobSummary,
    Track as TrackContract,
    TrackCounts,
)
from backend.models.schemas import JobSchema
from backend.services import arm_client


def _mock_response(json_data, status_code: int = 200) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.is_success = 200 <= status_code < 300
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


@pytest.fixture()
def mock_client():
    client = AsyncMock(spec=httpx.AsyncClient)
    with patch.object(arm_client, "get_client", return_value=client):
        yield client


# Minimal Job dict matching arm_contracts.Job required fields plus a
# representative slice of optional fields. Update only when the contract
# intentionally changes - an accidental rename of `job_id` (the only
# required field) breaks every test below.
_MIN_JOB = {
    "job_id": 1,
    "title": "Test Movie",
    "year": "2026",
    "video_type": "movie",
    "status": "ripping",
    "disctype": "dvd",
    "no_of_titles": 1,
    "devpath": "/dev/sr0",
}

_MIN_TRACK = {
    "track_id": 1,
    "job_id": 1,
    "track_number": "1",
    "length": 3600,
    "filename": "title_t00.mkv",
    "ripped": False,
    "main_feature": False,
    "source": "makemkv",
    "basename": "title_t00.mkv",
    "orig_filename": "title_t00.mkv",
}


async def test_get_job_detail_parses_as_jobschema(mock_client):
    """A job-detail response from arm-neu round-trips through JobSchema.

    Renaming Job.job_id (required) breaks this. Other Job fields are
    optional, so renaming them silently passes - that's the F6/G9
    follow-up's job.
    """
    response_body = {"job": _MIN_JOB, "tracks": [_MIN_TRACK], "config": {}}
    mock_client.request.return_value = _mock_response(response_body)

    result = await arm_client.get_job_detail(1)

    assert result is not None
    JobSchema.model_validate(result["job"])
    TrackContract.model_validate(result["tracks"][0])


async def test_get_active_jobs_parses_as_jobschema(mock_client):
    """An active-jobs response round-trips through JobSchema + TrackCounts.

    Renaming TrackCounts.total / .ripped / .enabled (all required) breaks this.
    """
    response_body = {
        "jobs": [
            {
                **_MIN_JOB,
                "track_counts": {"total": 5, "ripped": 2, "enabled": 5},
            }
        ]
    }
    mock_client.request.return_value = _mock_response(response_body)

    result = await arm_client.get_active_jobs()

    assert result is not None
    for job in result["jobs"]:
        JobSchema.model_validate(job)
        if "track_counts" in job:
            TrackCounts.model_validate(job["track_counts"])


async def test_get_jobs_paginated_parses_as_jobschema(mock_client):
    """A paginated-jobs response round-trips through JobSchema."""
    response_body = {
        "jobs": [_MIN_JOB],
        "total": 1,
        "page": 1,
        "page_size": 25,
    }
    mock_client.request.return_value = _mock_response(response_body)

    result = await arm_client.get_jobs_paginated()

    assert result is not None
    for job in result["jobs"]:
        JobSchema.model_validate(job)


async def test_get_drives_with_jobs_parses_as_jobsummary(mock_client):
    """A drives-with-jobs response round-trips through JobSummary.

    Renaming JobSummary.job_id (required) breaks this.
    """
    response_body = {
        "drives": [
            {
                "drive_id": 1,
                "name": "DVD-RW",
                "mount": "/dev/sr0",
                "type": "dvd",
                "current_job": {
                    "job_id": 1,
                    "title": "Test",
                    "year": "2026",
                    "status": "ripping",
                    "video_type": "movie",
                    "no_of_titles": 1,
                    "track_counts": {"total": 5, "ripped": 2, "enabled": 5},
                },
            }
        ]
    }
    mock_client.request.return_value = _mock_response(response_body)

    result = await arm_client.get_drives_with_jobs()

    assert result is not None
    for drive in result["drives"]:
        if drive.get("current_job"):
            JobSummary.model_validate(drive["current_job"])


async def test_get_job_progress_state_parses_as_jobprogressstate(mock_client):
    """A progress-state response round-trips through JobProgressState."""
    response_body = {
        "job_id": 1,
        "status": "ripping",
        "stage": "rip",
        "progress": 50,
        "progress_round": 50,
        "rip_progress": 50,
        "music_progress": None,
        "track_counts": {"total": 5, "ripped": 2, "enabled": 5},
        "current_track": "1",
        "eta_seconds": None,
    }
    mock_client.request.return_value = _mock_response(response_body)

    result = await arm_client.get_job_progress_state(1)

    assert result is not None
    JobProgressState.model_validate(result)


async def test_jobschema_validator_strips_legacy_transcode_overrides(mock_client):
    """JobSchema's transcode_overrides validator strips pre-v15 keys.

    Catches drift in TRANSCODE_OVERRIDES_ALLOWLIST vs. TranscodeJobConfig.
    Unlike the other tests here, this one tests producer-shape behavior
    that the contract model alone cannot enforce.
    """
    legacy_job = {
        **_MIN_JOB,
        "transcode_overrides": {
            "preset_slug": "fast-1080p30",
            "video_encoder": "x264",  # legacy, must be stripped
            "handbrake_preset": "old",  # legacy, must be stripped
        },
    }
    response_body = {"job": legacy_job, "tracks": [], "config": {}}
    mock_client.request.return_value = _mock_response(response_body)

    result = await arm_client.get_job_detail(1)

    assert result is not None
    parsed = JobSchema.model_validate(result["job"])
    assert parsed.transcode_overrides == {"preset_slug": "fast-1080p30"}
