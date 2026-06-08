"""
Tests for main.py - FastAPI API endpoint integration tests.
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio


# ─── App fixture with mocked worker and real DB ─────────────────────────────


@pytest.fixture
def mock_worker():
    """Create a mock TranscodeWorker."""
    worker = MagicMock()
    worker.is_running = True
    worker.queue_size = 0
    worker.current_job = None
    worker.queue_job = AsyncMock(return_value=(1, True))
    worker.shutdown = MagicMock()
    return worker


@pytest_asyncio.fixture
async def client(mock_worker, tmp_path):
    """Create an async test client with initialized test DB."""
    db_path = str(tmp_path / "test.db")

    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from models import Base

    test_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    test_session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    @asynccontextmanager
    async def test_get_db():
        async with test_session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    from tests.api_test_helpers import patched_app_client
    async with patched_app_client(mock_worker, test_get_db) as (ac, _main):
        yield ac

    # Cleanup
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


# ─── Health Check ────────────────────────────────────────────────────────────


class TestHealthEndpoint:
    """Tests for GET /health."""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Health check should return status."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "worker_running" in data
        assert "queue_size" in data


# ─── Webhook Endpoint ───────────────────────────────────────────────────────


class TestWebhookEndpoint:
    """Tests for POST /webhook/arm."""

    @pytest.mark.asyncio
    async def test_valid_completion_webhook(self, client, mock_worker):
        """Valid completion webhook should queue a job."""
        payload = {
            "title": "ARM notification",
            "body": "Rip of Test Movie (2024) complete",
            "input_path": "movies/Test Movie (2024)",
            "output_path": "Movies/0.Rips/Test Movie (2024)",
            "type": "info",
            "job_id": 1,
        }
        response = await client.post("/webhook/arm", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
        mock_worker.queue_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_webhook_with_input_path(self, client, mock_worker):
        """Webhook with explicit input_path should use it."""
        payload = {
            "title": "Rip complete",
            "input_path": "movies/Movie Title (2024)",
            "output_path": "Movies/0.Rips/Movie Title (2024)",
            "status": "success",
            "job_id": 2,
        }
        response = await client.post("/webhook/arm", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "queued"
        mock_worker.queue_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_webhook_title_fallback_body(self, client, mock_worker):
        """When body has no parseable pattern, use body text as media title."""
        payload = {
            "title": "Rip complete",
            "input_path": "movies/Movie Title (2024)",
            "output_path": "Movies/0.Rips/Movie Title (2024)",
            "body": "some unrecognized format",
            "status": "success",
            "job_id": 3,
        }
        response = await client.post("/webhook/arm", json=payload)
        assert response.status_code == 200
        call_kwargs = mock_worker.queue_job.call_args
        assert call_kwargs.kwargs["title"] == "some unrecognized format"

    @pytest.mark.asyncio
    async def test_apprise_message_field(self, client, mock_worker):
        """Apprise json:// sends 'message' instead of 'body' - should still
        be queued so long as input_path is present."""
        payload = {
            "version": "1.0",
            "title": "ARM notification",
            "message": "Test Movie (2024) rip complete. Starting transcode.",
            "input_path": "movies/Test Movie (2024)",
            "output_path": "Movies/0.Rips/Test Movie (2024)",
            "type": "info",
            "job_id": 4,
        }
        response = await client.post("/webhook/arm", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
        mock_worker.queue_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_arm_rip_notification_format(self, client, mock_worker):
        """ARM's actual NOTIFY_RIP format with input_path/output_path."""
        payload = {
            "title": "ARM notification",
            "body": "Movie Title (2024) rip complete. Starting transcode.",
            "input_path": "movies/Movie Title (2024)",
            "output_path": "Movies/0.Rips/Movie Title (2024)",
            "type": "info",
            "job_id": 5,
        }
        response = await client.post("/webhook/arm", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
        assert data["input_path"] == "movies/Movie Title (2024)"
        mock_worker.queue_job.assert_called_once()
        # Job title should be the extracted media title, not "ARM notification"
        call_kwargs = mock_worker.queue_job.call_args
        assert call_kwargs.kwargs["title"] == "Movie Title (2024)"

    @pytest.mark.asyncio
    async def test_arm_processing_complete_format(self, client, mock_worker):
        """ARM's NOTIFY_TRANSCODE format with input_path/output_path."""
        payload = {
            "title": "ARM notification",
            "body": "Movie Title (2024) processing complete.",
            "input_path": "movies/Movie Title (2024)",
            "output_path": "Movies/0.Rips/Movie Title (2024)",
            "type": "info",
            "job_id": 6,
        }
        response = await client.post("/webhook/arm", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
        assert data["input_path"] == "movies/Movie Title (2024)"

    @pytest.mark.asyncio
    async def test_webhook_returns_503_when_worker_not_ready(self, client):
        """Webhook should return 503 when worker is None or not running."""
        import main as main_module
        saved_worker = main_module.app.state.worker
        main_module.app.state.worker = None
        try:
            payload = {
                "title": "ARM notification",
                "body": "Rip of Test Movie (2024) complete",
                "input_path": "movies/Test Movie (2024)",
                "output_path": "Movies/0.Rips/Test Movie (2024)",
                "type": "info",
                "job_id": 7,
            }
            response = await client.post("/webhook/arm", json=payload)
            assert response.status_code == 503
            assert "not ready" in response.json()["detail"].lower()
        finally:
            main_module.app.state.worker = saved_worker

    @pytest.mark.asyncio
    async def test_non_completion_ignored(self, client):
        """Non-completion webhooks should be ignored."""
        payload = {
            "title": "ARM notification",
            "body": "Rip started for some movie",
            "type": "info",
            "job_id": 8,
        }
        response = await client.post("/webhook/arm", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "ignored"

    @pytest.mark.asyncio
    async def test_non_completion_apprise_ignored(self, client):
        """Non-completion Apprise notifications should be ignored."""
        payload = {
            "version": "1.0",
            "title": "ARM notification",
            "message": "Found data disc. Copying data.",
            "type": "info",
            "job_id": 9,
        }
        response = await client.post("/webhook/arm", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "ignored"

    @pytest.mark.asyncio
    async def test_webhook_missing_input_path(self, client):
        """Webhook without input_path returns error - the field is now required
        for any job-bound webhook."""
        payload = {
            "title": "Something complete",
            "job_id": 10,
        }
        response = await client.post("/webhook/arm", json=payload)
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "error"
        assert body["reason"] == "input_path required"

    @pytest.mark.asyncio
    async def test_webhook_invalid_payload(self, client):
        """Invalid payload (missing title) should return 422 with field errors."""
        response = await client.post("/webhook/arm", json={"body": "no title"})
        assert response.status_code == 422
        detail = response.json()["detail"]
        assert detail["message"] == "Invalid webhook payload"
        # Field-level errors mention the missing field.
        assert any("title" in e["loc"] for e in detail["errors"])

    @pytest.mark.asyncio
    async def test_webhook_input_path_traversal_rejected_at_contracts(self, client):
        """input_path with `..` traversal is rejected by the contracts
        validator - the request returns 422 before the handler runs."""
        payload = {
            "title": "Rip complete",
            "input_path": "../../../etc/passwd",
            "output_path": "Movies/0.Rips/X",
            "status": "success",
            "job_id": 11,
        }
        response = await client.post("/webhook/arm", json=payload)
        # 422 from Pydantic ValidationError on the contract-level guard.
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_webhook_input_path_with_subdirectory_accepted(self, client, mock_worker):
        """Relative subdirectory paths are accepted (e.g. movies/Title (Year))."""
        payload = {
            "title": "Rip complete",
            "input_path": "movies/The Babysitter (1969)",
            "output_path": "Movies/0.Rips/The Babysitter (1969)",
            "status": "success",
            "job_id": 12,
        }
        response = await client.post("/webhook/arm", json=payload)
        data = response.json()
        assert data.get("status") == "queued"

    @pytest.mark.asyncio
    async def test_webhook_input_path_absolute_rejected(self, client):
        """Absolute paths (with leading / or \\) are rejected by the
        contracts validator."""
        payload = {
            "title": "Rip complete",
            "input_path": "/some/abs/path",
            "output_path": "Movies/0.Rips/X",
            "status": "success",
            "job_id": 13,
        }
        response = await client.post("/webhook/arm", json=payload)
        assert response.status_code == 422


# ─── Jobs Endpoint ──────────────────────────────────────────────────────────


class TestJobsEndpoint:
    """Tests for GET /jobs."""

    @pytest.mark.asyncio
    async def test_list_jobs_empty(self, client):
        """Should return empty job list."""
        response = await client.get("/jobs")
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert data["jobs"] == []
        assert "total" in data
        assert "limit" in data
        assert "offset" in data

    @pytest.mark.asyncio
    async def test_list_jobs_pagination_defaults(self, client):
        """Default pagination should be limit=50, offset=0."""
        response = await client.get("/jobs")
        data = response.json()
        assert data["limit"] == 50
        assert data["offset"] == 0

    @pytest.mark.asyncio
    async def test_list_jobs_limit_capped(self, client):
        """Limit should be capped at 500."""
        response = await client.get("/jobs?limit=1000")
        data = response.json()
        assert data["limit"] == 500

    @pytest.mark.asyncio
    async def test_list_jobs_negative_offset_clamped(self, client):
        """Negative offset should be clamped to 0."""
        response = await client.get("/jobs?offset=-5")
        data = response.json()
        assert data["offset"] == 0


# ─── Retry Endpoint ─────────────────────────────────────────────────────────


class TestRetryEndpoint:
    """Tests for POST /jobs/{id}/retry."""

    @pytest.mark.asyncio
    async def test_retry_returns_503_when_worker_not_ready(self, client):
        """Retry should return 503 when worker is None."""
        import main as main_module

        saved_worker = main_module.app.state.worker
        main_module.app.state.worker = None
        try:
            response = await client.post("/jobs/1/retry")
            assert response.status_code == 503
            assert "not ready" in response.json()["detail"].lower()
        finally:
            main_module.app.state.worker = saved_worker

    @pytest.mark.asyncio
    async def test_retry_nonexistent_job(self, client):
        """Retrying non-existent job should return 404."""
        response = await client.post("/jobs/99999/retry")
        assert response.status_code == 404


# ─── Delete Endpoint ────────────────────────────────────────────────────────


class TestDeleteEndpoint:
    """Tests for DELETE /jobs/{id}."""

    @pytest.mark.asyncio
    async def test_delete_nonexistent_job(self, client):
        """Deleting non-existent job should return 404."""
        response = await client.delete("/jobs/99999")
        assert response.status_code == 404


# ─── Stats Endpoint ─────────────────────────────────────────────────────────


class TestStatsEndpoint:
    """Tests for GET /stats."""

    @pytest.mark.asyncio
    async def test_get_stats(self, client):
        """Stats endpoint should return status counts."""
        response = await client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        assert "pending" in data
        assert "processing" in data
        assert "completed" in data
        assert "failed" in data
        assert "cancelled" in data
        assert "worker_running" in data


class TestRestartEndpoint:
    """Tests for POST /system/restart."""

    @pytest.mark.asyncio
    async def test_restart_returns_success(self, client, mock_worker):
        """Restart endpoint should return success and schedule shutdown."""
        with patch("os.killpg"):
            response = await client.post("/system/restart")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "restarting" in data["message"].lower()


class TestWebhookConfigOverridesTyped:
    """After the TranscodeJobConfig integration, webhook config_overrides
    must be parsed into a typed model at the handler boundary and bad
    payloads must be rejected with 422 rather than silently accepted."""

    @pytest.mark.asyncio
    async def test_webhook_accepts_well_shaped_config(self, client):
        """Webhook with a valid TranscodeJobConfig shape queues the job."""
        payload = {
            "title": "Test Movie",
            "job_id": 9991,
            "input_path": "movies/Test Movie",
            "output_path": "Movies/0.Rips/Test Movie",
            "status": "success",
            "config_overrides": {
                "preset_slug": "software-balanced",
                "overrides": {
                    "shared": {"audio_encoder": "aac"},
                    "tiers": {"dvd": {"video_quality": 20}},
                },
                "delete_source": False,
                "output_extension": "mkv",
            },
        }
        resp = await client.post("/webhook/arm", json=payload)
        assert resp.status_code in (200, 202), resp.text

    @pytest.mark.asyncio
    async def test_webhook_rejects_invalid_preset_slug(self, client):
        """Uppercase/bad-regex preset_slug in config_overrides -> 422."""
        payload = {
            "title": "Test Movie",
            "job_id": 9992,
            "input_path": "movies/Test Movie",
            "output_path": "Movies/0.Rips/Test Movie",
            "status": "success",
            "config_overrides": {
                "preset_slug": "INVALID UPPERCASE",
                "overrides": {},
            },
        }
        resp = await client.post("/webhook/arm", json=payload)
        assert resp.status_code == 422, resp.text

    @pytest.mark.asyncio
    async def test_webhook_rejects_unknown_top_level_config_key(self, client):
        """Extra top-level key in config_overrides -> 422."""
        payload = {
            "title": "Test Movie",
            "job_id": 9993,
            "input_path": "movies/Test Movie",
            "output_path": "Movies/0.Rips/Test Movie",
            "status": "success",
            "config_overrides": {
                "preset_slug": "software-balanced",
                "overrides": {},
                "bogus_key": "nope",
            },
        }
        resp = await client.post("/webhook/arm", json=payload)
        assert resp.status_code == 422, resp.text

    @pytest.mark.asyncio
    async def test_webhook_accepts_missing_config_overrides(self, client):
        """Back-compat: a webhook without config_overrides is still accepted
        (transcoder falls back to scheme defaults). Tests the Optional[...] path."""
        payload = {
            "title": "Test Movie",
            "job_id": 9994,
            "input_path": "movies/Test Movie",
            "output_path": "Movies/0.Rips/Test Movie",
            "status": "success",
        }
        resp = await client.post("/webhook/arm", json=payload)
        assert resp.status_code in (200, 202), resp.text
