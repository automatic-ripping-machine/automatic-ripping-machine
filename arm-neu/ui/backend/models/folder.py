"""Folder scan / create request shapes."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class FolderScanRequest(BaseModel):
    path: str


class FolderCreateRequest(BaseModel):
    source_path: str
    title: str
    year: str | None = None
    video_type: str
    disctype: str
    imdb_id: str | None = None
    poster_url: str | None = None
    multi_title: bool = False
    season: int | None = None
    disc_number: int | None = None
    disc_total: int | None = None


class FolderScanResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    success: bool = True
    disc_type: str | None = None
    label: str | None = None
    title_suggestion: str | None = None
    year_suggestion: str | None = None
    folder_size_bytes: int = 0
    stream_count: int = 0
    disc_number: int | None = None
    disc_total: int | None = None
    season: int | None = None


class FolderCreateResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    success: bool = True
    job_id: int | None = None
    status: str | None = None
    source_type: str | None = None
    source_path: str | None = None
