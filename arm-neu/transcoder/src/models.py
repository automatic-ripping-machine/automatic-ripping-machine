"""
Data models for ARM Transcoder
"""

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Enum as SQLEnum
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class JobStatus(str, Enum):
    """Transcode job status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ConfigOverrideDB(Base):
    """Persisted runtime config overrides (key-value)."""
    __tablename__ = "config_overrides"

    key = Column(String(100), primary_key=True)
    value = Column(String(1000), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class CustomPresetDB(Base):
    """User-created preset stored as a diff against a built-in parent."""
    __tablename__ = "custom_presets"

    slug = Column(String(100), primary_key=True)
    name = Column(String(200), nullable=False)
    scheme = Column(String(50), nullable=False)
    parent_slug = Column(String(100), nullable=False)
    overrides_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))


class PendingCallbackDB(Base):
    """Durable queue of pending ARM-callback POSTs.

    Populated by _notify_arm_callback when a terminal status
    (completed/partial/failed) needs delivery and settings.arm_callback_url
    is configured. Drained by TranscodeCallbackDrainer in callback_drainer.py.
    Rows outlive the TranscodeJobDB job row to preserve audit history.
    """
    __tablename__ = "pending_callbacks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, nullable=False, index=True)
    status = Column(String(50), nullable=False)
    error = Column(String(500), nullable=True)
    track_results_json = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False,
                        default=lambda: datetime.now(timezone.utc))
    next_attempt_at = Column(DateTime, nullable=False, index=True,
                             default=lambda: datetime.now(timezone.utc))
    attempt_count = Column(Integer, nullable=False, default=0)
    last_error = Column(String(500), nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    permanent_failure_at = Column(DateTime, nullable=True)


class TranscodeJobDB(Base):
    """Database model for transcode jobs."""
    __tablename__ = "transcode_jobs"

    id = Column(Integer, primary_key=True, autoincrement=False)
    title = Column(String(500), nullable=False)
    source_path = Column(String(1000), nullable=False)
    output_path = Column(String(1000), nullable=True)
    status = Column(SQLEnum(JobStatus), default=JobStatus.PENDING, nullable=False)
    # phase is a fine-grained sub-status inside JobStatus.processing - lets the
    # UI surface "Copying source files" or "Finalizing" instead of an empty 0%
    # bar during periods where no encoder progress is being reported. Wire
    # values come from arm_contracts.TranscodePhase. Stored as a plain string
    # so adding new members on the contracts side doesn't require a DB migration.
    phase = Column(String(50), nullable=True, default="queued")
    progress = Column(Float, default=0.0)
    current_fps = Column(Float, nullable=True)  # Most recent encoder FPS sample while processing
    error = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Metadata from source
    video_type = Column(String(50), nullable=True)  # movie, series, unknown
    year = Column(String(10), nullable=True)
    disctype = Column(String(50), nullable=True)  # dvd, bluray, bluray4k
    total_tracks = Column(Integer, default=0)
    main_feature_file = Column(String(500), nullable=True)
    logfile = Column(String(255), nullable=True)
    poster_url = Column(String(500), nullable=True)
    config_overrides = Column(Text, nullable=True)  # JSON dict of per-job transcode overrides
    multi_title = Column(Integer, default=0)  # Boolean: 1 if multi-title disc
    track_metadata = Column(Text, nullable=True)  # JSON list of per-track metadata dicts
    # ARM-resolved output directory relative to settings.completed_path.
    # Replaces the legacy folder_name (which was a leaf-only string and
    # left type-subdir partitioning to the transcoder). With contracts
    # v3.0.0 the field carries the full subdir + leaf, e.g.
    # "Movies/0.Rips/Foo (2024)".
    output_path = Column(String(500), nullable=True)
    title_name = Column(String(500), nullable=True)  # Pre-rendered file stem from ARM naming engine


class TranscodeJob(BaseModel):
    """Transcode job for queue."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    source_path: str
