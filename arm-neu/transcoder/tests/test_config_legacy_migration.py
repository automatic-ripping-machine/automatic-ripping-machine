"""Tests for legacy ConfigOverrideDB row handling in load_config_overrides.

Legacy rows are those whose keys were removed from UPDATABLE_KEYS by the
preset rollout (flat encoding keys). On startup they must:
  1. Emit a WARN log naming the dropped key and value
  2. Be DELETEd from the table so the warning does not repeat
  3. Not affect valid rows in the same pass
"""
import logging
from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import load_config_overrides, settings
from models import Base, ConfigOverrideDB


@pytest_asyncio.fixture
async def override_db(tmp_dirs):
    """Create a test database with config_overrides table."""
    db_path = tmp_dirs["db_path"]
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine, session_factory

    await engine.dispose()


def _patch_get_db(session_factory):
    """Patch database.get_db to yield sessions from the given factory."""

    @asynccontextmanager
    async def mock_get_db():
        async with session_factory() as session:
            yield session

    return patch("database.get_db", mock_get_db)


@pytest.mark.asyncio
async def test_legacy_rows_are_deleted_with_warning(override_db, caplog):
    """Legacy keys trigger DELETE + WARN log."""
    _, session_factory = override_db
    async with session_factory() as session:
        session.add(ConfigOverrideDB(key="video_encoder", value="nvenc_h265"))
        session.add(ConfigOverrideDB(key="handbrake_preset", value="H.264 MKV 1080p30"))
        await session.commit()

    with caplog.at_level(logging.WARNING):
        with _patch_get_db(session_factory):
            await load_config_overrides()

    # Each legacy key emits one WARN naming the key and value
    messages = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    joined = "\n".join(messages)
    assert "video_encoder" in joined
    assert "nvenc_h265" in joined
    assert "handbrake_preset" in joined
    assert "preset" in joined.lower() or "reconfigure" in joined.lower()

    # Rows are gone
    async with session_factory() as session:
        result = await session.execute(select(ConfigOverrideDB))
        remaining = result.scalars().all()
    assert remaining == []


@pytest.mark.asyncio
async def test_valid_rows_are_preserved(override_db, caplog):
    """Rows with current keys are kept and applied to settings."""
    _, session_factory = override_db
    async with session_factory() as session:
        session.add(ConfigOverrideDB(key="log_level", value="DEBUG"))
        await session.commit()

    original = settings.log_level
    try:
        with caplog.at_level(logging.WARNING):
            with _patch_get_db(session_factory):
                await load_config_overrides()

        # No warnings for valid rows
        warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert warnings == [], f"Unexpected warnings: {[w.getMessage() for w in warnings]}"

        # Row still present
        async with session_factory() as session:
            result = await session.execute(
                select(ConfigOverrideDB).where(ConfigOverrideDB.key == "log_level")
            )
            row = result.scalar_one_or_none()
        assert row is not None
        assert settings.log_level == "DEBUG"
    finally:
        settings.log_level = original


@pytest.mark.asyncio
async def test_mixed_rows_partitioned_correctly(override_db, caplog):
    """One pass handles legacy + valid rows correctly."""
    _, session_factory = override_db
    async with session_factory() as session:
        session.add(ConfigOverrideDB(key="video_encoder", value="x265"))       # legacy
        session.add(ConfigOverrideDB(key="log_level", value="INFO"))           # valid
        session.add(ConfigOverrideDB(key="max_retry_count", value="5"))        # valid
        await session.commit()

    original_log_level = settings.log_level
    original_retry = settings.max_retry_count
    try:
        with caplog.at_level(logging.WARNING):
            with _patch_get_db(session_factory):
                await load_config_overrides()

        async with session_factory() as session:
            result = await session.execute(select(ConfigOverrideDB.key))
            keys = set(result.scalars().all())
        assert keys == {"log_level", "max_retry_count"}, f"Got keys: {keys}"
    finally:
        settings.log_level = original_log_level
        settings.max_retry_count = original_retry


@pytest.mark.asyncio
async def test_second_startup_produces_no_warnings(override_db, caplog):
    """After first startup drops legacy rows, second startup is silent."""
    _, session_factory = override_db
    async with session_factory() as session:
        session.add(ConfigOverrideDB(key="video_encoder", value="nvenc_h265"))
        await session.commit()

    with _patch_get_db(session_factory):
        await load_config_overrides()  # first run drops + warns

    caplog.clear()
    with caplog.at_level(logging.WARNING):
        with _patch_get_db(session_factory):
            await load_config_overrides()

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert warnings == [], (
        f"Second startup should be silent; got {[w.getMessage() for w in warnings]}"
    )
