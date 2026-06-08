"""Log file and structured log response shapes."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class LogFileSchema(BaseModel):
    filename: str
    size: int
    modified: datetime


class LogContentResponse(BaseModel):
    filename: str
    content: str
    lines: int


class LogEntrySchema(BaseModel):
    timestamp: str
    level: str
    logger: str
    event: str
    job_id: int | None = None
    label: str | None = None
    raw: str


class StructuredLogResponse(BaseModel):
    filename: str
    entries: list[LogEntrySchema]
    lines: int
