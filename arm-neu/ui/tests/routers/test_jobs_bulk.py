"""Tests for POST /api/jobs/bulk-delete and /api/jobs/bulk-purge."""
from __future__ import annotations
from unittest.mock import AsyncMock, patch
from tests.factories import make_job_dict


async def test_bulk_delete_by_ids(app_client):
    mock_del = AsyncMock(return_value={"success": True})
    with patch("backend.routers.jobs.arm_client.delete_job", mock_del):
        resp = await app_client.post("/api/jobs/bulk-delete", json={"job_ids": [1, 2]})
    assert resp.status_code == 200
    assert resp.json()["deleted"] == 2
    assert mock_del.call_count == 2


async def test_bulk_delete_empty_ids(app_client):
    resp = await app_client.post("/api/jobs/bulk-delete", json={"job_ids": []})
    assert resp.status_code == 200
    assert resp.json()["deleted"] == 0


async def test_bulk_delete_by_status(app_client):
    paginated = {
        "jobs": [make_job_dict(job_id=i, status="fail") for i in range(1, 4)],
        "total": 3, "page": 1, "per_page": 100, "pages": 1,
    }
    mock_del = AsyncMock(return_value={"success": True})
    with patch(
        "backend.routers.jobs.arm_client.get_jobs_paginated",
        new_callable=AsyncMock, return_value=paginated,
    ), patch("backend.routers.jobs.arm_client.delete_job", mock_del):
        resp = await app_client.post("/api/jobs/bulk-delete", json={"status": "fail"})
    assert resp.status_code == 200
    assert resp.json()["deleted"] == 3


async def test_bulk_purge_by_ids(app_client):
    detail = {
        "job": make_job_dict(job_id=1, logfile="test.log",
                             raw_path="/raw", transcode_path="/trans", path="/done"),
        "config": None, "tracks": [], "track_counts": {"total": 0, "ripped": 0},
    }
    mock_del = AsyncMock(return_value={"success": True})
    mock_log = AsyncMock(return_value={"success": True})
    mock_folder = AsyncMock(return_value={"success": True})
    with patch(
        "backend.routers.jobs.arm_client.get_job_detail",
        new_callable=AsyncMock, return_value=detail,
    ), patch("backend.routers.jobs.arm_client.delete_job", mock_del), \
       patch("backend.routers.jobs.arm_client.delete_orphan_log", mock_log), \
       patch("backend.routers.jobs.arm_client.delete_orphan_folder", mock_folder):
        resp = await app_client.post("/api/jobs/bulk-purge", json={"job_ids": [1]})
    assert resp.status_code == 200
    assert resp.json()["purged"] == 1


async def test_bulk_purge_empty_ids(app_client):
    resp = await app_client.post("/api/jobs/bulk-purge", json={"job_ids": []})
    assert resp.status_code == 200
    assert resp.json()["purged"] == 0


async def test_bulk_delete_by_status_pages_under_per_page_cap(app_client):
    """ARM caps /jobs/paginated at per_page=100. The BFF must page through
    rather than ask for per_page=10000 (which 422s into a silent zero).

    Reproduces the 'Purge All Failed shows 0 purged' bug: 150 failed jobs
    spread across two ARM pages, BFF must catch all of them.
    """
    page_one = {
        "jobs": [make_job_dict(job_id=i, status="fail") for i in range(1, 101)],
        "total": 150, "page": 1, "per_page": 100, "pages": 2,
    }
    page_two = {
        "jobs": [make_job_dict(job_id=i, status="fail") for i in range(101, 151)],
        "total": 150, "page": 2, "per_page": 100, "pages": 2,
    }
    paginated_mock = AsyncMock(side_effect=[page_one, page_two])
    mock_del = AsyncMock(return_value={"success": True})
    with patch(
        "backend.routers.jobs.arm_client.get_jobs_paginated",
        paginated_mock,
    ), patch("backend.routers.jobs.arm_client.delete_job", mock_del):
        resp = await app_client.post("/api/jobs/bulk-delete", json={"status": "fail"})
    assert resp.status_code == 200
    assert resp.json()["deleted"] == 150
    assert paginated_mock.call_count == 2
    # Must request at-or-under ARM's le=100 cap, not the old per_page=10000
    for call in paginated_mock.call_args_list:
        assert call.kwargs["per_page"] <= 100


async def test_bulk_delete_by_status_handles_arm_error(app_client):
    """If ARM returns an error dict (e.g. validation failure), don't loop
    forever or silently treat it as 'no jobs'; surface zero with a logged
    warning. Regression guard for the silent-zero bug."""
    error_dict = {"success": False, "error": "ARM error (422): ..."}
    paginated_mock = AsyncMock(return_value=error_dict)
    mock_del = AsyncMock(return_value={"success": True})
    with patch(
        "backend.routers.jobs.arm_client.get_jobs_paginated",
        paginated_mock,
    ), patch("backend.routers.jobs.arm_client.delete_job", mock_del):
        resp = await app_client.post("/api/jobs/bulk-delete", json={"status": "fail"})
    assert resp.status_code == 200
    assert resp.json()["deleted"] == 0
    assert paginated_mock.call_count == 1  # one attempt, no retry loop
    assert mock_del.call_count == 0


async def test_bulk_delete_strips_crlf_from_logged_user_input(app_client, caplog):
    """User-controlled status + ARM error string must be CRLF-stripped before
    logging. Sonar python:S5145 (log injection): a malicious status containing
    \\n could otherwise forge fake log lines."""
    import logging
    error_dict = {"success": False, "error": "boom\nFAKE LOG LINE\rmore"}
    paginated_mock = AsyncMock(return_value=error_dict)
    with patch(
        "backend.routers.jobs.arm_client.get_jobs_paginated", paginated_mock,
    ), patch("backend.routers.jobs.arm_client.delete_job", AsyncMock()), \
         caplog.at_level(logging.WARNING, logger="backend.routers.jobs"):
        resp = await app_client.post(
            "/api/jobs/bulk-delete",
            json={"status": "fail\ninjected"},
        )
    assert resp.status_code == 200
    msgs = [r.getMessage() for r in caplog.records]
    assert msgs, "expected warning to be emitted"
    combined = "\n".join(msgs)
    # The warning text itself uses \n as a record separator between log
    # records; the assertion is that no individual record contains an
    # embedded \n or \r from the user-controlled fields.
    for record in caplog.records:
        assert "\n" not in record.getMessage()
        assert "\r" not in record.getMessage()
    # And the sanitized values still appear, just without the CRLF.
    assert "failinjected" in combined
    assert "boomFAKE LOG LINEmore" in combined
