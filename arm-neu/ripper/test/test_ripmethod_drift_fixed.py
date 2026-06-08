"""Regression: backup_dvd was rejected by the API config endpoint
before the enum extraction. All three RipMethod values must now
round-trip through PATCH /api/v1/jobs/<id>/config."""
import unittest.mock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(app_context):
    from arm.app import app
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.mark.parametrize("value", ["mkv", "backup", "backup_dvd"])
def test_ripmethod_round_trips_via_api(client, sample_job, app_context, value):
    """The API must accept every RipMethod value. Before the fix,
    backup_dvd hit a 400 with 'RIPMETHOD must be one of ...'."""
    resp = client.patch(
        f"/api/v1/jobs/{sample_job.job_id}/config",
        json={"RIPMETHOD": value},
    )
    # The failure mode we care about is the 400 with that specific
    # message. backup_dvd previously failed this; mkv and backup did not.
    assert resp.status_code == 200, (
        f"RIPMETHOD={value!r} got {resp.status_code} "
        f"(expected 200): {resp.text}"
    )
    data = resp.json()
    assert data["success"] is True


def test_ripmethod_invalid_still_rejected(client, sample_job, app_context):
    """Defence-in-depth: a value not in the enum still 400s."""
    resp = client.patch(
        f"/api/v1/jobs/{sample_job.job_id}/config",
        json={"RIPMETHOD": "rsync"},
    )
    assert resp.status_code == 400
    assert "RIPMETHOD" in resp.json().get("error", "")
