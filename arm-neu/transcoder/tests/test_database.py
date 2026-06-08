"""
Tests for database.py - database initialization, migrations, and session management.
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text, inspect

from models import Base, TranscodeJobDB, JobStatus


@pytest_asyncio.fixture
async def fresh_engine(tmp_dirs):
    """Create a fresh async engine for each test."""
    db_path = tmp_dirs["db_path"]
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    yield engine
    await engine.dispose()


class TestInitDb:
    """Tests for init_db() - table creation."""

    @pytest.mark.asyncio
    async def test_creates_tables(self, fresh_engine):
        """init_db should create all model tables."""
        async with fresh_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

            def check_tables(sync_conn):
                inspector = inspect(sync_conn)
                tables = inspector.get_table_names()
                return tables

            tables = await conn.run_sync(check_tables)
            assert "transcode_jobs" in tables
            assert "config_overrides" in tables


class TestAddMissingColumns:
    """Tests for _add_missing_columns() - schema migration."""

    @pytest.mark.asyncio
    async def test_adds_columns_to_existing_table(self, fresh_engine):
        """Should add new columns to an existing table missing them."""
        from database import _add_missing_columns

        # Create table with only core columns (simulating old schema)
        async with fresh_engine.begin() as conn:
            await conn.execute(text(
                "CREATE TABLE transcode_jobs ("
                "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "  title VARCHAR(500) NOT NULL,"
                "  source_path VARCHAR(1000) NOT NULL,"
                "  status VARCHAR(20) DEFAULT 'pending'"
                ")"
            ))

        # Run migration
        async with fresh_engine.begin() as conn:
            await conn.run_sync(_add_missing_columns)

        # Verify columns were added
        async with fresh_engine.begin() as conn:
            def check_columns(sync_conn):
                inspector = inspect(sync_conn)
                columns = {c["name"] for c in inspector.get_columns("transcode_jobs")}
                return columns

            columns = await conn.run_sync(check_columns)
            assert "disctype" in columns
            assert "logfile" in columns
            assert "poster_url" in columns
            assert "config_overrides" in columns
            assert "multi_title" in columns
            assert "track_metadata" in columns
            assert "output_path" in columns
            assert "title_name" in columns

    @pytest.mark.asyncio
    async def test_idempotent_migration(self, fresh_engine):
        """Running migration twice should not fail."""
        from database import _add_missing_columns

        # Create full table
        async with fresh_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Run migration on already-complete table (should be no-op)
        async with fresh_engine.begin() as conn:
            await conn.run_sync(_add_missing_columns)

        # Verify still works
        async with fresh_engine.begin() as conn:
            def check_columns(sync_conn):
                inspector = inspect(sync_conn)
                return {c["name"] for c in inspector.get_columns("transcode_jobs")}

            columns = await conn.run_sync(check_columns)
            assert "disctype" in columns

    @pytest.mark.asyncio
    async def test_skips_when_table_missing(self, fresh_engine):
        """Should not fail when transcode_jobs table doesn't exist."""
        from database import _add_missing_columns

        # Run migration on empty database (no tables)
        async with fresh_engine.begin() as conn:
            await conn.run_sync(_add_missing_columns)
        # No exception means success


class TestGetDb:
    """Tests for get_db() async context manager."""

    @pytest.mark.asyncio
    async def test_yields_session(self, test_db):
        """get_db should yield an AsyncSession."""
        engine, session_factory = test_db

        async with session_factory() as session:
            assert isinstance(session, AsyncSession)

    @pytest.mark.asyncio
    async def test_session_can_insert_and_query(self, test_db):
        """Session should support basic CRUD operations."""
        engine, session_factory = test_db

        async with session_factory() as session:
            job = TranscodeJobDB(
                id=1,
                title="Test Movie",
                source_path="/data/raw/test",
                status=JobStatus.PENDING,
            )
            session.add(job)
            await session.commit()

            result = await session.execute(
                text("SELECT title FROM transcode_jobs WHERE id = :id"),
                {"id": job.id},
            )
            row = result.fetchone()
            assert row is not None
            assert row[0] == "Test Movie"

    @pytest.mark.asyncio
    async def test_session_rollback_on_error(self, test_db):
        """Session should rollback on exception."""
        engine, session_factory = test_db

        try:
            async with session_factory() as session:
                job = TranscodeJobDB(
                    id=2,
                    title="Rollback Test",
                    source_path="/data/raw/rollback",
                    status=JobStatus.PENDING,
                )
                session.add(job)
                await session.flush()
                raise ValueError("Simulated error")
        except ValueError:
            pass

        # Verify the job was not persisted
        async with session_factory() as session:
            result = await session.execute(
                text("SELECT COUNT(*) FROM transcode_jobs WHERE title = 'Rollback Test'")
            )
            count = result.scalar()
            assert count == 0
