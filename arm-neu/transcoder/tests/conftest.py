"""
Shared fixtures for ARM Transcoder tests.
"""

import atexit
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Create a secure, process-private temp root (mode 0o700) for all session paths.
# This replaces hard-coded /tmp/... literals to satisfy SonarCloud S5443.
_SESSION_TMPDIR = tempfile.mkdtemp(prefix="arm_transcoder_test_")
atexit.register(lambda: __import__("shutil").rmtree(_SESSION_TMPDIR, ignore_errors=True))

# Set test environment variables before importing app modules
os.environ.setdefault("RAW_PATH", os.path.join(_SESSION_TMPDIR, "raw"))
os.environ.setdefault("COMPLETED_PATH", os.path.join(_SESSION_TMPDIR, "completed"))
os.environ.setdefault("WORK_PATH", os.path.join(_SESSION_TMPDIR, "work"))
os.environ.setdefault("DB_PATH", os.path.join(_SESSION_TMPDIR, "test_transcoder.db"))
os.environ.setdefault("REQUIRE_API_AUTH", "false")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("LOG_PATH", os.path.join(_SESSION_TMPDIR, "logs"))
# Force software scheme before any app imports so GPU probing is deterministic.
os.environ.setdefault("GPU_VENDOR", "")


@pytest.fixture
def mock_worker():
    """Mock TranscodeWorker for API tests."""
    worker = MagicMock()
    worker.is_running = True
    worker.queue_size = 0
    worker.current_job = None
    worker.gpu_support = {}
    worker.active_count = 0
    worker.queue_job = AsyncMock(return_value=(1, True))
    worker.shutdown = MagicMock()
    return worker


@pytest.fixture
def tmp_dirs(tmp_path):
    """Create temporary directory structure for tests."""
    raw = tmp_path / "raw"
    completed = tmp_path / "completed"
    work = tmp_path / "work"
    db_dir = tmp_path / "db"

    for d in [raw, completed, work, db_dir]:
        d.mkdir()

    return {
        "root": tmp_path,
        "raw": raw,
        "completed": completed,
        "work": work,
        "db_dir": db_dir,
        "db_path": str(db_dir / "test.db"),
    }


@pytest.fixture
def sample_mkv_dir(tmp_dirs):
    """Create a sample directory with fake MKV files."""
    movie_dir = tmp_dirs["raw"] / "Test Movie (2024)"
    movie_dir.mkdir()

    # Create fake MKV files of different sizes
    main_feature = movie_dir / "title_main.mkv"
    main_feature.write_bytes(b"\x00" * 10000)  # 10KB "main feature"

    extra = movie_dir / "title_extra.mkv"
    extra.write_bytes(b"\x00" * 2000)  # 2KB "extra"

    return {
        "dir": movie_dir,
        "main_feature": main_feature,
        "extra": extra,
    }


@pytest.fixture
def path_validator(tmp_dirs):
    """Create a PathValidator with test directories."""
    from utils import PathValidator

    return PathValidator([str(tmp_dirs["raw"]), str(tmp_dirs["completed"])])


@pytest_asyncio.fixture
async def test_db(tmp_dirs):
    """Create a test database with async engine."""
    from models import Base

    db_url = f"sqlite+aiosqlite:///{tmp_dirs['db_path']}"
    engine = create_async_engine(db_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine, session_factory

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
def mock_subprocess():
    """Mock subprocess for HandBrake/FFmpeg calls."""
    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.stdout = AsyncMock()
    mock_proc.stdout.__aiter__ = lambda self: self
    mock_proc.stdout.__anext__ = AsyncMock(side_effect=StopAsyncIteration)
    # _stream_progress_lines reads stdout in fixed chunks; b"" means EOF.
    mock_proc.stdout.read = AsyncMock(return_value=b"")
    mock_proc.wait = AsyncMock(return_value=0)
    mock_proc.communicate = AsyncMock(return_value=(b"3600.0", b""))
    return mock_proc
