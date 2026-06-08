"""Tests for JSON field round-trip in ConfigOverrideDB.

global_overrides (and any other dict/list-typed setting) must survive
a PATCH -> restart -> GET cycle with the nested structure intact. Prior
behavior stored Python repr() via str(dict), which json.loads would
reject on read.

Note: In this codebase the Settings.global_overrides field is declared
as ``str`` (JSON-encoded), so the round-trip invariant is that the
stored DB row is valid JSON that downstream consumers can json.loads.
Downstream consumers (transcoder.py) rely on settings.global_overrides
being a JSON string they can parse.
"""
import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker


@pytest_asyncio.fixture
async def patched_db(tmp_path):
    """Provide a clean SQLite DB and patch routers/config get_db to use it.

    Yields (test_get_db, test_session_factory) so individual tests can seed
    rows directly as well as drive the app via AsyncClient.
    """
    import database as db_module
    from models import Base

    db_path = str(tmp_path / "test.db")
    test_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    test_session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False,
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

    with (
        patch.object(db_module, "get_db", test_get_db),
        patch("routers.config.get_db", test_get_db),
        patch("main.init_db", AsyncMock()),
    ):
        yield test_get_db, test_session_factory

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def client(mock_worker, patched_db):
    """Async HTTP client bound to the patched DB."""
    import main as main_module
    from presets import load_active_scheme

    main_module.active_scheme = load_active_scheme()
    main_module.app.state.worker = mock_worker

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="https://test") as ac:
        yield ac

    main_module.app.state.worker = None


@pytest.fixture(autouse=True)
def reset_global_overrides():
    """Snapshot and restore the in-memory singleton."""
    from config import settings
    original = settings.global_overrides
    yield
    settings.global_overrides = original


@pytest.mark.asyncio
async def test_patch_global_overrides_round_trip(client, patched_db):
    """PATCH a nested dict -> load_config_overrides -> value reconstructs exactly."""
    from config import settings, load_config_overrides
    from models import ConfigOverrideDB
    from sqlalchemy import select

    _, session_factory = patched_db

    payload = {
        "global_overrides": {
            "shared": {"audio_encoder": "aac"},
            "tiers": {
                "dvd": {"video_quality": 22},
                "bluray": {"video_quality": 20, "handbrake_extra_args": ["--foo"]},
            },
        }
    }

    response = await client.patch("/config", json=payload)
    assert response.status_code == 200, response.text

    # The DB row must be valid JSON that parses back to the original dict.
    async with session_factory() as session:
        result = await session.execute(
            select(ConfigOverrideDB).where(ConfigOverrideDB.key == "global_overrides")
        )
        row = result.scalar_one()
    stored = row.value
    # Must be valid JSON (not Python repr with single quotes).
    parsed = json.loads(stored)
    assert parsed == payload["global_overrides"], (
        f"Stored DB value is not round-trip JSON. Got: {stored!r}"
    )

    # Simulate app restart: wipe in-memory settings and reload from DB.
    settings.global_overrides = "{}"
    await load_config_overrides()

    # Settings field is typed as ``str``; downstream consumers json.loads it.
    assert isinstance(settings.global_overrides, str)
    assert json.loads(settings.global_overrides) == payload["global_overrides"], (
        f"Round-trip failed. Got: {settings.global_overrides!r}"
    )


@pytest.mark.asyncio
async def test_legacy_python_repr_string_is_skipped(patched_db):
    """A row stored as Python repr (pre-fix corruption) must not corrupt settings.

    Documents the failure mode so future regressions surface in logs.
    """
    from config import settings, load_config_overrides
    from models import ConfigOverrideDB

    _, session_factory = patched_db

    # Seed a row with Python-repr style storage (single quotes = invalid JSON).
    bad_value = "{'shared': {'audio_encoder': 'aac'}}"
    async with session_factory() as session:
        session.add(ConfigOverrideDB(key="global_overrides", value=bad_value))
        await session.commit()

    # Snapshot default before load (the autouse fixture restores afterwards).
    settings.global_overrides = "{}"
    await load_config_overrides()

    # Settings should not be set to the invalid repr string - either it kept
    # the default or the invalid row was skipped by the coercion guard.
    # The strict assertion: whatever is in settings must be valid JSON.
    try:
        parsed = json.loads(settings.global_overrides)
    except (ValueError, TypeError) as exc:
        pytest.fail(
            f"Invalid DB row was assigned to settings.global_overrides: "
            f"{settings.global_overrides!r} ({exc})"
        )
    # It should have parsed to something dict-ish (or at least not the bad repr).
    assert parsed == {} or isinstance(parsed, dict)


@pytest.mark.asyncio
async def test_valid_json_string_in_db_loads(patched_db):
    """A row stored as valid JSON loads cleanly and parses to the original dict."""
    from config import settings, load_config_overrides
    from models import ConfigOverrideDB

    _, session_factory = patched_db

    valid = {"shared": {"subtitle_mode": "all"}, "tiers": {}}
    async with session_factory() as session:
        session.add(ConfigOverrideDB(key="global_overrides", value=json.dumps(valid)))
        await session.commit()

    settings.global_overrides = "{}"
    await load_config_overrides()

    assert isinstance(settings.global_overrides, str)
    assert json.loads(settings.global_overrides) == valid


@pytest.mark.asyncio
async def test_startup_lifespan_loads_global_overrides_from_db(patched_db):
    """App startup (lifespan) reads global_overrides from DB as valid JSON.

    This mirrors the production flow: lifespan calls load_config_overrides
    against the real DB, and settings.global_overrides must end up as a
    JSON string that downstream consumers can json.loads.

    Everything else in the lifespan (worker, GPU probe, scheme loader) is
    mocked - we only care that the persisted config override round-trips.
    """
    from fastapi import FastAPI
    from config import settings
    from models import ConfigOverrideDB
    from presets import Preset, Scheme, Encoder

    _, session_factory = patched_db

    valid = {"shared": {"audio_encoder": "aac"}, "tiers": {"dvd": {"video_quality": 22}}}
    async with session_factory() as session:
        session.add(ConfigOverrideDB(key="global_overrides", value=json.dumps(valid)))
        await session.commit()

    # Reset the in-memory value so we know it really came from the DB.
    settings.global_overrides = "{}"

    # Minimal scheme so load_active_scheme has something to return.
    mock_scheme = Scheme(
        slug="test", name="Test",
        supported_encoders=[Encoder(slug="x265", name="x265")],
        supported_audio_encoders=["copy"], supported_subtitle_modes=["all"],
        built_in_presets=[Preset(
            slug="test", name="Test", scheme="test",
            shared={"video_encoder": "x265", "audio_encoder": "copy", "subtitle_mode": "all"},
            tiers={
                "dvd": {"handbrake_preset": "Test 720p", "video_quality": 22},
                "bluray": {"handbrake_preset": "Test 1080p", "video_quality": 22},
                "uhd": {"handbrake_preset": "Test 2160p 4K", "video_quality": 22},
            },
        )],
    )

    mock_worker = MagicMock()
    mock_worker.run = AsyncMock(return_value=None)
    mock_worker.shutdown = MagicMock()
    mock_worker.queue_sentinel = AsyncMock()

    with (
        patch("main.init_db", AsyncMock()),
        patch("main.load_active_scheme", return_value=mock_scheme),
        patch("main.TranscodeWorker", return_value=mock_worker),
        patch("transcoder.check_gpu_support", return_value={}),
        patch("main.create_gpu_monitor", return_value=None),
    ):
        from main import lifespan
        app = FastAPI()
        async with lifespan(app):
            # Lifespan has finished its startup phase - load_config_overrides
            # has already run against the patched DB.
            assert isinstance(settings.global_overrides, str)
            assert json.loads(settings.global_overrides) == valid
