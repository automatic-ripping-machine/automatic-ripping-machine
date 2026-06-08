"""
Database setup and session management
"""

import os
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from config import settings
from models import Base

# Ensure database directory exists
os.makedirs(os.path.dirname(settings.db_path), exist_ok=True)

# Create async engine
engine = create_async_engine(
    f"sqlite+aiosqlite:///{settings.db_path}",
    echo=False,
)

# Session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """Initialize database tables and add any missing columns."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Add columns that may be missing in existing databases.
        # SQLite's CREATE_ALL won't alter existing tables.
        await conn.run_sync(_add_missing_columns)


def _add_missing_columns(conn):
    """Add columns to existing tables if they don't exist yet.

    Also handles schema migration from old arm_job_id-based schema to
    unified ID schema (drops and recreates table — historical data not important).
    """
    from sqlalchemy import inspect, text

    inspector = inspect(conn)
    if "transcode_jobs" in inspector.get_table_names():
        existing = {c["name"] for c in inspector.get_columns("transcode_jobs")}

        # Migrate from old schema: arm_job_id present means old layout
        if "arm_job_id" in existing:
            conn.execute(text("DROP TABLE transcode_jobs"))
            Base.metadata.create_all(conn)
            return

        migrations = [
            ("disctype", "VARCHAR(50)"),
            ("logfile", "VARCHAR(255)"),
            ("poster_url", "VARCHAR(500)"),
            ("config_overrides", "TEXT"),
            ("multi_title", "INTEGER DEFAULT 0"),
            ("track_metadata", "TEXT"),
            ("title_name", "VARCHAR(500)"),
            ("current_fps", "FLOAT"),
            ("phase", "VARCHAR(50) DEFAULT 'queued'"),
            # output_path supersedes the legacy folder_name. ARM now sends
            # the full subdir + leaf via the webhook output_path field,
            # which we persist verbatim.
            ("output_path", "VARCHAR(500)"),
        ]
        for col_name, col_type in migrations:
            if col_name not in existing:
                conn.execute(text(
                    f"ALTER TABLE transcode_jobs ADD COLUMN {col_name} {col_type}"
                ))

        # If a legacy folder_name column exists, copy its content into
        # output_path on a one-shot basis (idempotent: only fills NULLs).
        if "folder_name" in existing:
            conn.execute(text(
                "UPDATE transcode_jobs SET output_path = folder_name "
                "WHERE output_path IS NULL AND folder_name IS NOT NULL"
            ))


@asynccontextmanager
async def get_db():
    """Get database session context manager."""
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
