"""Version-handshake tests for /api/v1/jobs/{id}/transcode-callback.

Mirrors transcoder/tests/test_version_handshake.py for the opposite
direction. Currently runs in lenient mode
(ACCEPT_MISSING_VERSION_HEADER = True). The 'strict mode' test is
skipped until F1 ships and we flip the flag.

Audit reference:
docs/superpowers/specs/2026-04-29-cross-service-contract-drift-audit-design.md G2.
"""
from __future__ import annotations

import pytest


@pytest.fixture
def client(app_context):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from arm.api.v1.jobs import router

    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as c:
        yield c


_VALID_BODY = {"status": "transcoding"}


def test_callback_accepts_version_2(client, sample_job):
    """X-Api-Version: 2 is accepted."""
    response = client.post(
        f"/api/v1/jobs/{sample_job.job_id}/transcode-callback",
        json=_VALID_BODY,
        headers={"X-Api-Version": "2"},
    )
    assert response.status_code in (200, 204), response.text


def test_callback_rejects_version_1(client, sample_job):
    """X-Api-Version: 1 is rejected with 400."""
    response = client.post(
        f"/api/v1/jobs/{sample_job.job_id}/transcode-callback",
        json=_VALID_BODY,
        headers={"X-Api-Version": "1"},
    )
    assert response.status_code == 400
    assert "Unsupported X-Api-Version" in response.text


def test_callback_lenient_on_missing_header(client, sample_job):
    """Missing header is currently accepted (ACCEPT_MISSING_VERSION_HEADER=True).

    This test documents lenient mode. Flip to expect 400 when the strict-mode
    fix lands.
    """
    response = client.post(
        f"/api/v1/jobs/{sample_job.job_id}/transcode-callback",
        json=_VALID_BODY,
    )
    # Must NOT be 400. Other 4xx (e.g. 422 for malformed body, which our body
    # is not) would also indicate a different bug.
    assert response.status_code in (200, 204), response.text


@pytest.mark.skip(
    reason="F2 strict-mode flip is a separate one-line follow-up. "
    "Enable when ACCEPT_MISSING_VERSION_HEADER flips to False."
)
def test_callback_rejects_missing_header_in_strict_mode(client, sample_job):
    """When ACCEPT_MISSING_VERSION_HEADER=False, missing header is 400."""
    response = client.post(
        f"/api/v1/jobs/{sample_job.job_id}/transcode-callback",
        json=_VALID_BODY,
    )
    assert response.status_code == 400
    assert "X-Api-Version header is required" in response.text
