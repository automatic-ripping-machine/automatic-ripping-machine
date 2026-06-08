"""Schema tests for PendingCallbackDB."""
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker


@pytest.mark.asyncio
async def test_pending_callback_insert_and_select(tmp_path):
    from models import Base, PendingCallbackDB

    db_path = str(tmp_path / "test.db")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    now = datetime.now(timezone.utc)
    async with factory() as session:
        row = PendingCallbackDB(
            job_id=42,
            status="completed",
            error=None,
            track_results_json='[{"track_number": 1, "status": "completed"}]',
            next_attempt_at=now,
            attempt_count=0,
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        assert row.id is not None
        assert row.delivered_at is None
        assert row.permanent_failure_at is None

    async with factory() as session:
        result = await session.execute(
            select(PendingCallbackDB).where(PendingCallbackDB.job_id == 42)
        )
        fetched = result.scalar_one()
        assert fetched.status == "completed"
        assert fetched.attempt_count == 0

    await engine.dispose()


@pytest.mark.asyncio
async def test_pending_callback_update_delivered(tmp_path):
    from models import Base, PendingCallbackDB

    db_path = str(tmp_path / "test.db")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    now = datetime.now(timezone.utc)
    async with factory() as session:
        row = PendingCallbackDB(
            job_id=1, status="completed",
            next_attempt_at=now, attempt_count=0,
        )
        session.add(row)
        await session.commit()

    async with factory() as session:
        result = await session.execute(
            select(PendingCallbackDB).where(PendingCallbackDB.job_id == 1)
        )
        fetched = result.scalar_one()
        fetched.delivered_at = now
        await session.commit()

    async with factory() as session:
        result = await session.execute(
            select(PendingCallbackDB).where(PendingCallbackDB.job_id == 1)
        )
        fetched = result.scalar_one()
        assert fetched.delivered_at is not None

    await engine.dispose()
