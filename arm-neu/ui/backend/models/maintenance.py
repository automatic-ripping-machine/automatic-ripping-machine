"""BFF response shapes for the maintenance surface.

Mirrors the invariant wire shapes shipped in arm-neu PR #322
(feat/maintenance-shape-cleanup): success/failure paths emit the same keys,
delete_* always include `error: str | None`, bulk_delete_* always include
`success: bool`, clear_raw failure path emits the full success-shape with
zero defaults plus `error`, and orphan-folders carries `roots: list[str]`
for symmetry with orphan-logs (`root: str`).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class MaintenanceSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    orphan_logs: int | None = None
    orphan_folders: int | None = None
    unseen_notifications: int | None = None
    cleared_notifications: int | None = None
    stale_transcoder_jobs: int | None = None


class OrphanLogEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    path: str
    relative_path: str
    size_bytes: int


class OrphanLogList(BaseModel):
    """Orphan logs from arm-neu /api/v1/maintenance/orphan-logs."""
    model_config = ConfigDict(extra="ignore")

    root: str
    total_size_bytes: int
    files: list[OrphanLogEntry]


class OrphanFolderEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    path: str
    name: str
    category: str
    size_bytes: int


class OrphanFolderList(BaseModel):
    """Orphan folders from arm-neu /api/v1/maintenance/orphan-folders.

    `roots` carries both scanned roots (RAW + COMPLETED) since orphan-folders
    spans two trees, mirroring the single `root` on orphan-logs.
    """
    model_config = ConfigDict(extra="ignore")

    roots: list[str]
    total_size_bytes: int
    folders: list[OrphanFolderEntry]


class MaintenanceDeleteResult(BaseModel):
    """Single-target delete result (delete-log / delete-folder).

    Wire shape is invariant across success/failure: `error` is always
    present, `None` on success, `str` on failure. Named with a
    Maintenance prefix to disambiguate from transcoder.DeleteResult.
    """
    model_config = ConfigDict(extra="ignore")

    success: bool
    path: str
    error: str | None


class MaintenanceBulkDeleteResult(BaseModel):
    """Bulk delete result (bulk-delete-logs / bulk-delete-folders).

    `success` is True only when no entries failed; partial-failure surfaces
    as `success=False` with the failed paths in `errors`. Maintenance
    prefix mirrors MaintenanceDeleteResult for grep-friendly cohabitation.
    """
    model_config = ConfigDict(extra="ignore")

    success: bool
    removed: list[str]
    errors: list[str]


class ImageCacheStats(BaseModel):
    """Image cache snapshot. ``stats()`` returns count, size_bytes, size_mb,
    oldest, path. ``clear()`` returns success, cleared, freed_bytes. The
    superset is modeled with optional fields so a single shape serves both
    endpoints."""
    model_config = ConfigDict(extra="ignore")

    count: int | None = None
    size_bytes: int | None = None
    size_mb: float | None = None
    oldest: float | None = None
    path: str | None = None
    success: bool | None = None
    cleared: int | None = None
    freed_bytes: int | None = None


class CleanupTranscoderResult(BaseModel):
    """Cleanup-transcoder counts deleted jobs.

    Handler always emits all three fields, so they are required in the
    typed shape (no `= ...` defaults that would make codegen mark them
    optional).
    """
    model_config = ConfigDict(extra="ignore")

    success: bool
    deleted: int
    errors: list[str]


class ClearRawResult(BaseModel):
    """Clear-raw cleared count, bytes freed, and any errors.

    Wire shape is invariant across success/failure (arm-neu PR #322).
    """
    model_config = ConfigDict(extra="ignore")

    success: bool
    cleared: int
    freed_bytes: int
    errors: list[str]
    path: str
    error: str | None
