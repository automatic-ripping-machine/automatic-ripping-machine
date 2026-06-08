"""
Tests for config.py - settings validation and config override loading.
"""

import json
import os
from unittest.mock import patch, AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

from config import (
    Settings,
    UPDATABLE_KEYS,
)
from models import Base, ConfigOverrideDB


# --- Settings Validation ---


class TestSettingsValidation:
    """Tests for Settings field validators."""

    def test_log_level_uppercase_normalization(self):
        s = Settings(log_level="debug")
        assert s.log_level == "DEBUG"

    def test_log_level_libraries_uppercase(self):
        s = Settings(log_level_libraries="error")
        assert s.log_level_libraries == "ERROR"

    def test_invalid_log_level_rejected(self):
        with pytest.raises(Exception, match="Invalid log level"):
            Settings(log_level="TRACE")

    def test_selected_preset_slug_default(self):
        s = Settings()
        assert s.selected_preset_slug == ""

    def test_global_overrides_default(self):
        s = Settings()
        assert s.global_overrides == "{}"


# --- Config Override Loading ---


class TestLoadConfigOverrides:
    """Tests for load_config_overrides()."""

    @pytest_asyncio.fixture
    async def override_db(self, tmp_dirs):
        """Create a test database with config_overrides table."""
        db_path = tmp_dirs["db_path"]
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        yield engine, session_factory

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_loads_string_override(self, override_db):
        engine, session_factory = override_db
        from config import settings, load_config_overrides

        async with session_factory() as session:
            session.add(ConfigOverrideDB(key="selected_preset_slug", value="nvidia_quality"))
            await session.commit()

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_get_db():
            async with session_factory() as session:
                yield session

        original = settings.selected_preset_slug
        try:
            with patch("database.get_db", mock_get_db):
                await load_config_overrides()
            assert settings.selected_preset_slug == "nvidia_quality"
        finally:
            settings.selected_preset_slug = original

    @pytest.mark.asyncio
    async def test_loads_bool_override(self, override_db):
        engine, session_factory = override_db
        from config import settings, load_config_overrides

        async with session_factory() as session:
            session.add(ConfigOverrideDB(key="delete_source", value="false"))
            await session.commit()

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_get_db():
            async with session_factory() as session:
                yield session

        original = settings.delete_source
        try:
            with patch("database.get_db", mock_get_db):
                await load_config_overrides()
            assert settings.delete_source is False
        finally:
            settings.delete_source = original

    @pytest.mark.asyncio
    async def test_loads_int_override(self, override_db):
        engine, session_factory = override_db
        from config import settings, load_config_overrides

        async with session_factory() as session:
            session.add(ConfigOverrideDB(key="max_concurrent", value="4"))
            await session.commit()

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_get_db():
            async with session_factory() as session:
                yield session

        original = settings.max_concurrent
        try:
            with patch("database.get_db", mock_get_db):
                await load_config_overrides()
            assert settings.max_concurrent == 4
        finally:
            settings.max_concurrent = original

    @pytest.mark.asyncio
    async def test_loads_float_override(self, override_db):
        engine, session_factory = override_db
        from config import settings, load_config_overrides

        async with session_factory() as session:
            session.add(ConfigOverrideDB(key="minimum_free_space_gb", value="25.5"))
            await session.commit()

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_get_db():
            async with session_factory() as session:
                yield session

        original = settings.minimum_free_space_gb
        try:
            with patch("database.get_db", mock_get_db):
                await load_config_overrides()
            assert settings.minimum_free_space_gb == pytest.approx(25.5)
        finally:
            settings.minimum_free_space_gb = original

    @pytest.mark.asyncio
    async def test_skips_non_updatable_key(self, override_db):
        engine, session_factory = override_db
        from config import settings, load_config_overrides

        async with session_factory() as session:
            session.add(ConfigOverrideDB(key="db_path", value="/evil/path"))
            await session.commit()

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_get_db():
            async with session_factory() as session:
                yield session

        original = settings.db_path
        with patch("database.get_db", mock_get_db):
            await load_config_overrides()
        assert settings.db_path == original

    @pytest.mark.asyncio
    async def test_skips_invalid_value(self, override_db):
        engine, session_factory = override_db
        from config import settings, load_config_overrides

        async with session_factory() as session:
            session.add(ConfigOverrideDB(key="max_concurrent", value="not_a_number"))
            await session.commit()

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_get_db():
            async with session_factory() as session:
                yield session

        original = settings.max_concurrent
        try:
            with patch("database.get_db", mock_get_db):
                await load_config_overrides()
            # Should not have changed since "not_a_number" can't be cast to int
            assert settings.max_concurrent == original
        finally:
            settings.max_concurrent = original
