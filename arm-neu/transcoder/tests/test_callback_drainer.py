"""Unit tests for callback drainer components."""
import httpx
import pytest


# ── is_permanent_error ─────────────────────────────────────────────────

@pytest.mark.parametrize("code", [400, 401, 403, 404, 410, 422])
def test_permanent_error_for_terminal_4xx_codes(code):
    from callback_drainer import is_permanent_error
    response = httpx.Response(code)
    assert is_permanent_error(response) is True


@pytest.mark.parametrize("code", [408, 429, 500, 502, 503, 504])
def test_retriable_for_non_terminal_error_codes(code):
    from callback_drainer import is_permanent_error
    response = httpx.Response(code)
    assert is_permanent_error(response) is False


@pytest.mark.parametrize("code", [200, 201, 202, 204])
def test_not_permanent_for_success_codes(code):
    """Success isn't classified as permanent failure; the caller checks
    status_code < 300 separately before reaching this function."""
    from callback_drainer import is_permanent_error
    response = httpx.Response(code)
    assert is_permanent_error(response) is False


def test_network_exception_is_retriable():
    from callback_drainer import is_permanent_error
    exc = httpx.ConnectError("refused")
    assert is_permanent_error(exc) is False


def test_timeout_exception_is_retriable():
    from callback_drainer import is_permanent_error
    exc = httpx.ReadTimeout("timed out")
    assert is_permanent_error(exc) is False


# ── backoff_seconds ─────────────────────────────────────────────────────

@pytest.mark.parametrize("attempt, expected", [
    (1, 5),
    (2, 10),
    (3, 20),
    (4, 40),
    (5, 80),
    (6, 160),
    (7, 320),
    (8, 640),
    (9, 1280),
    (10, 1800),
    (11, 1800),
    (100, 1800),
])
def test_backoff_schedule(attempt, expected):
    """Exponential 5s doubling, capped at 1800s (30 min). No ceiling on attempts."""
    from callback_drainer import backoff_seconds
    assert backoff_seconds(attempt) == expected


def test_backoff_zero_attempts_returns_zero():
    """Attempt 0 means 'send immediately'; used as the default for fresh rows."""
    from callback_drainer import backoff_seconds
    assert backoff_seconds(0) == 0


# ── Drainer send_one ───────────────────────────────────────────────────

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker


@pytest_asyncio.fixture
async def drainer_db(tmp_path):
    """A test DB with Base.metadata.create_all applied."""
    from models import Base

    db_path = str(tmp_path / "test.db")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    @asynccontextmanager
    async def get_db():
        async with factory() as session:
            yield session

    yield factory, get_db

    await engine.dispose()


@pytest_asyncio.fixture
async def pending_row(drainer_db):
    """Insert one pending row with status=completed and return its id."""
    from models import PendingCallbackDB
    factory, _ = drainer_db
    async with factory() as session:
        row = PendingCallbackDB(
            job_id=1, status="completed",
            next_attempt_at=datetime.now(timezone.utc),
            attempt_count=0,
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return row.id


@pytest.mark.asyncio
async def test_send_one_marks_delivered_on_2xx(drainer_db, pending_row):
    from callback_drainer import TranscodeCallbackDrainer
    from models import PendingCallbackDB

    factory, get_db = drainer_db

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post.return_value = httpx.Response(200)

    drainer = TranscodeCallbackDrainer(
        get_db=get_db,
        callback_url="https://arm.example/callback",
        http_client_factory=lambda: mock_client,
    )

    await drainer.send_one(pending_row)

    # F1: callbacks must include X-Api-Version header (audit 2026-04-29)
    assert mock_client.post.call_count == 1
    call_kwargs = mock_client.post.call_args.kwargs
    assert call_kwargs.get("headers") == {"X-Api-Version": "2"}, (
        f"expected X-Api-Version: 2 header, got {call_kwargs.get('headers')!r}"
    )

    async with factory() as session:
        result = await session.execute(
            select(PendingCallbackDB).where(PendingCallbackDB.id == pending_row)
        )
        row = result.scalar_one()
        assert row.delivered_at is not None
        assert row.permanent_failure_at is None


@pytest.mark.asyncio
async def test_send_one_marks_permanent_failure_on_400(drainer_db, pending_row):
    from callback_drainer import TranscodeCallbackDrainer
    from models import PendingCallbackDB

    factory, get_db = drainer_db

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post.return_value = httpx.Response(400, text="bad payload")

    drainer = TranscodeCallbackDrainer(
        get_db=get_db,
        callback_url="https://arm.example/callback",
        http_client_factory=lambda: mock_client,
    )

    await drainer.send_one(pending_row)

    async with factory() as session:
        result = await session.execute(
            select(PendingCallbackDB).where(PendingCallbackDB.id == pending_row)
        )
        row = result.scalar_one()
        assert row.delivered_at is None
        assert row.permanent_failure_at is not None
        assert "400" in row.last_error


@pytest.mark.asyncio
async def test_send_one_retriable_on_503(drainer_db, pending_row):
    from callback_drainer import TranscodeCallbackDrainer
    from models import PendingCallbackDB

    factory, get_db = drainer_db

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post.return_value = httpx.Response(503)

    before = datetime.now(timezone.utc)
    drainer = TranscodeCallbackDrainer(
        get_db=get_db,
        callback_url="https://arm.example/callback",
        http_client_factory=lambda: mock_client,
    )

    await drainer.send_one(pending_row)

    async with factory() as session:
        result = await session.execute(
            select(PendingCallbackDB).where(PendingCallbackDB.id == pending_row)
        )
        row = result.scalar_one()
        assert row.delivered_at is None
        assert row.permanent_failure_at is None
        assert row.attempt_count == 1
        # Next attempt should be at least 5s after now (first backoff).
        # SQLite stores naive datetimes; strip tzinfo from before for comparison.
        before_naive = before.replace(tzinfo=None)
        next_at = row.next_attempt_at.replace(tzinfo=None) if row.next_attempt_at.tzinfo else row.next_attempt_at
        assert next_at >= before_naive + timedelta(seconds=5)


@pytest.mark.asyncio
async def test_send_one_retriable_on_network_error(drainer_db, pending_row):
    from callback_drainer import TranscodeCallbackDrainer
    from models import PendingCallbackDB

    factory, get_db = drainer_db

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post.side_effect = httpx.ConnectError("refused")

    drainer = TranscodeCallbackDrainer(
        get_db=get_db,
        callback_url="https://arm.example/callback",
        http_client_factory=lambda: mock_client,
    )

    await drainer.send_one(pending_row)

    async with factory() as session:
        result = await session.execute(
            select(PendingCallbackDB).where(PendingCallbackDB.id == pending_row)
        )
        row = result.scalar_one()
        assert row.delivered_at is None
        assert row.permanent_failure_at is None
        assert row.attempt_count == 1
        assert row.last_error is not None
        assert "refused" in row.last_error


# ── Drainer sweep_once ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sweep_once_sends_all_due_rows(drainer_db):
    from callback_drainer import TranscodeCallbackDrainer
    from models import PendingCallbackDB

    factory, get_db = drainer_db
    now = datetime.now(timezone.utc)

    async with factory() as session:
        for i in range(3):
            session.add(PendingCallbackDB(
                job_id=100 + i, status="completed",
                next_attempt_at=now, attempt_count=0,
            ))
        await session.commit()

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post.return_value = httpx.Response(200)

    drainer = TranscodeCallbackDrainer(
        get_db=get_db,
        callback_url="https://arm.example/callback",
        http_client_factory=lambda: mock_client,
    )

    await drainer.sweep_once()

    async with factory() as session:
        result = await session.execute(select(PendingCallbackDB))
        rows = list(result.scalars())
        assert len(rows) == 3
        assert all(r.delivered_at is not None for r in rows)


@pytest.mark.asyncio
async def test_sweep_once_skips_not_yet_due(drainer_db):
    from callback_drainer import TranscodeCallbackDrainer
    from models import PendingCallbackDB

    factory, get_db = drainer_db
    now = datetime.now(timezone.utc)

    async with factory() as session:
        session.add(PendingCallbackDB(
            job_id=1, status="completed",
            next_attempt_at=now + timedelta(seconds=60),  # not due yet
            attempt_count=1,
        ))
        await session.commit()

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post.return_value = httpx.Response(200)

    drainer = TranscodeCallbackDrainer(
        get_db=get_db,
        callback_url="https://arm.example/callback",
        http_client_factory=lambda: mock_client,
    )

    await drainer.sweep_once()

    mock_client.post.assert_not_called()

    async with factory() as session:
        result = await session.execute(select(PendingCallbackDB))
        row = result.scalar_one()
        assert row.delivered_at is None  # Not sent yet


@pytest.mark.asyncio
async def test_sweep_once_skips_already_delivered(drainer_db):
    from callback_drainer import TranscodeCallbackDrainer
    from models import PendingCallbackDB

    factory, get_db = drainer_db
    now = datetime.now(timezone.utc)

    async with factory() as session:
        session.add(PendingCallbackDB(
            job_id=1, status="completed",
            next_attempt_at=now, attempt_count=1,
            delivered_at=now,  # Already delivered
        ))
        await session.commit()

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post.return_value = httpx.Response(200)

    drainer = TranscodeCallbackDrainer(
        get_db=get_db,
        callback_url="https://arm.example/callback",
        http_client_factory=lambda: mock_client,
    )

    await drainer.sweep_once()

    mock_client.post.assert_not_called()


@pytest.mark.asyncio
async def test_sweep_once_skips_permanent_failure(drainer_db):
    from callback_drainer import TranscodeCallbackDrainer
    from models import PendingCallbackDB

    factory, get_db = drainer_db
    now = datetime.now(timezone.utc)

    async with factory() as session:
        session.add(PendingCallbackDB(
            job_id=1, status="completed",
            next_attempt_at=now, attempt_count=1,
            permanent_failure_at=now,
        ))
        await session.commit()

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post.return_value = httpx.Response(200)

    drainer = TranscodeCallbackDrainer(
        get_db=get_db,
        callback_url="https://arm.example/callback",
        http_client_factory=lambda: mock_client,
    )

    await drainer.sweep_once()

    mock_client.post.assert_not_called()


@pytest.mark.asyncio
async def test_sweep_once_concurrency_cap(drainer_db):
    """With 10 due rows and cap of 5 via LIMIT, one sweep sends 5; two sweeps send all 10."""
    from callback_drainer import TranscodeCallbackDrainer
    from models import PendingCallbackDB

    factory, get_db = drainer_db
    now = datetime.now(timezone.utc)

    async with factory() as session:
        for i in range(10):
            session.add(PendingCallbackDB(
                job_id=200 + i, status="completed",
                next_attempt_at=now, attempt_count=0,
            ))
        await session.commit()

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post.return_value = httpx.Response(200)

    drainer = TranscodeCallbackDrainer(
        get_db=get_db,
        callback_url="https://arm.example/callback",
        http_client_factory=lambda: mock_client,
    )

    await drainer.sweep_once()
    assert mock_client.post.call_count == 5

    await drainer.sweep_once()
    assert mock_client.post.call_count == 10


@pytest.mark.asyncio
async def test_sweep_once_cleans_up_old_delivered(drainer_db):
    from callback_drainer import TranscodeCallbackDrainer
    from models import PendingCallbackDB

    factory, get_db = drainer_db
    now = datetime.now(timezone.utc)

    async with factory() as session:
        session.add(PendingCallbackDB(
            job_id=1, status="completed",
            next_attempt_at=now - timedelta(days=30),
            attempt_count=1,
            delivered_at=now - timedelta(days=8),  # Older than 7d -> prune
        ))
        session.add(PendingCallbackDB(
            job_id=2, status="completed",
            next_attempt_at=now - timedelta(days=1),
            attempt_count=1,
            delivered_at=now - timedelta(days=1),  # Within 7d -> keep
        ))
        await session.commit()

    mock_client = AsyncMock()
    drainer = TranscodeCallbackDrainer(
        get_db=get_db,
        callback_url="https://arm.example/callback",
        http_client_factory=lambda: mock_client,
    )

    await drainer.sweep_once()

    async with factory() as session:
        result = await session.execute(select(PendingCallbackDB))
        rows = list(result.scalars())
        assert len(rows) == 1
        assert rows[0].job_id == 2


# ── Drainer run loop ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_loop_wakes_on_event(drainer_db):
    """Calling notify_new_row wakes the drainer from its 30s sleep."""
    from callback_drainer import TranscodeCallbackDrainer
    from models import PendingCallbackDB

    factory, get_db = drainer_db
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post.return_value = httpx.Response(200)

    drainer = TranscodeCallbackDrainer(
        get_db=get_db,
        callback_url="https://arm.example/callback",
        http_client_factory=lambda: mock_client,
    )

    # Start the loop as a background task, give it time to sleep
    loop_task = asyncio.create_task(drainer.run())
    await asyncio.sleep(0.1)

    # Insert a row then wake the drainer
    async with factory() as session:
        session.add(PendingCallbackDB(
            job_id=1, status="completed",
            next_attempt_at=datetime.now(timezone.utc),
            attempt_count=0,
        ))
        await session.commit()

    drainer.notify_new_row()

    # Wait up to 1s for the send to happen
    for _ in range(20):
        await asyncio.sleep(0.05)
        if mock_client.post.call_count > 0:
            break

    assert mock_client.post.call_count == 1

    drainer.stop()
    await loop_task


@pytest.mark.asyncio
async def test_run_loop_survives_exception_in_sweep(drainer_db, caplog):
    """If sweep_once raises, the loop logs it and keeps running."""
    import logging
    from callback_drainer import TranscodeCallbackDrainer

    factory, get_db = drainer_db
    drainer = TranscodeCallbackDrainer(
        get_db=get_db,
        callback_url="https://arm.example/callback",
    )

    # Monkeypatch sweep_once to raise once then succeed
    call_count = {"n": 0}

    async def flaky_sweep():
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("simulated drainer crash")
        # second call is fine

    drainer.sweep_once = flaky_sweep

    with caplog.at_level(logging.ERROR):
        loop_task = asyncio.create_task(drainer.run())
        # First iteration raises, retry sleep is 5s; we short-circuit
        # by poking notify_new_row after the exception so the next
        # iteration runs promptly.
        await asyncio.sleep(0.1)
        drainer.notify_new_row()
        # Wait long enough for the 5s retry sleep to pass
        for _ in range(120):
            await asyncio.sleep(0.05)
            if call_count["n"] >= 2:
                break

    drainer.stop()
    await loop_task

    assert call_count["n"] >= 2
    assert any(
        "simulated drainer crash" in r.getMessage() for r in caplog.records
    )
