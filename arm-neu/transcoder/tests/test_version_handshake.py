"""Tests for X-Api-Version handshake on the ARM webhook receiver.

As of release N+2, missing-header back-compat is dropped:
  - X-Api-Version: 2 -> 200
  - X-Api-Version: 1 -> 400 (explicit old-version rejection)
  - Missing header   -> 400 (header is now required)
  - GET /health returns {"api_version": "2", ...}
"""
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from models import Base


# Webhook payload shape that the current WebhookPayload Pydantic model accepts.
# Matches the v3.0.0 contract: title + body + input_path/output_path + job_id + status.
_VALID_PAYLOAD = {
    "title": "Rip complete",
    "input_path": "movies/Test Movie (2024)",
    "output_path": "Movies/0.Rips/Test Movie (2024)",
    "status": "success",
    "job_id": 1,
}

# Actual webhook route on the transcoder (registered in src/routers/jobs.py).
WEBHOOK_PATH = "/webhook/arm"


@pytest.fixture
def mock_worker():
    """Mock TranscodeWorker that accepts queued jobs."""
    worker = MagicMock()
    worker.is_running = True
    worker.queue_size = 0
    worker.current_job = None
    worker.gpu_support = {}
    worker.queue_job = AsyncMock(return_value=(1, True))
    worker.shutdown = MagicMock()
    return worker


@pytest_asyncio.fixture
async def client(mock_worker, tmp_path):
    """Async HTTP client bound to the FastAPI app with a test DB and mock worker."""
    db_path = str(tmp_path / "test.db")

    import database as db_module

    test_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    test_session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

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

    with patch.object(db_module, "get_db", test_get_db), \
         patch("routers.jobs.get_db", test_get_db), \
         patch("main.init_db", AsyncMock()):

        import main as main_module
        main_module.app.state.worker = mock_worker

        transport = ASGITransport(app=main_module.app)
        async with AsyncClient(transport=transport, base_url="https://test") as ac:
            yield ac

        main_module.app.state.worker = None

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_webhook_accepts_version_2(client):
    response = await client.post(
        WEBHOOK_PATH,
        json=_VALID_PAYLOAD,
        headers={"X-Api-Version": "2"},
    )
    assert response.status_code in (200, 202), response.text


@pytest.mark.asyncio
async def test_webhook_rejects_version_1(client):
    response = await client.post(
        WEBHOOK_PATH,
        json=_VALID_PAYLOAD,
        headers={"X-Api-Version": "1"},
    )
    assert response.status_code == 400
    body = response.json()
    detail = body.get("detail", body.get("error", ""))
    # Detail may be a string or list; coerce to string for substring match
    detail_str = str(detail).lower()
    assert "api version" in detail_str or "v2" in str(body).lower() \
        or "x-api-version" in detail_str


@pytest.mark.asyncio
async def test_webhook_rejects_missing_header(client):
    """As of release N+2, the X-Api-Version header is required; missing header 400s."""
    response = await client.post(WEBHOOK_PATH, json=_VALID_PAYLOAD)
    assert response.status_code == 400
    body = response.json()
    detail = body.get("detail", body.get("error", ""))
    detail_str = str(detail).lower()
    assert "required" in detail_str or "x-api-version" in detail_str


@pytest.mark.asyncio
async def test_health_exposes_api_version(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json().get("api_version") == "2"
