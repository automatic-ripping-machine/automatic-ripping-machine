"""Backwards-compat re-exports from backend.models per-domain modules.

This module preserves the existing `from backend.models.schemas import X`
import path used throughout the codebase. New imports should target the
per-domain module directly (e.g. `from backend.models.job import JobSchema`).

Scheduled for removal once all callers migrate to per-domain imports.
"""

from arm_contracts import (
    JobSummary,
)
from arm_contracts import (
    Track as TrackSchema,
)
from arm_contracts import (
    TrackCounts as TrackCountsSchema,
)

from backend.models.config import RuntimeConfigResponse
from backend.models.dashboard import DashboardResponse
from backend.models.drive import DriveEjectResult, DriveSchema, DriveUpdateRequest
from backend.models.files import (
    DirectoryListing,
    FileEntry,
    FileRoot,
    OperationResult,
)
from backend.models.folder import (
    FolderCreateRequest,
    FolderCreateResponse,
    FolderScanRequest,
    FolderScanResult,
)
from backend.models.job import (
    TRANSCODE_OVERRIDES_ALLOWLIST,
    JobConfigSnapshot,
    JobDetailSchema,
    JobListResponse,
    JobSchema,
    JobTranscodeOverridesUpdate,
)
from backend.models.logs import (
    LogContentResponse,
    LogEntrySchema,
    LogFileSchema,
    StructuredLogResponse,
)
from backend.models.maintenance import (
    CleanupTranscoderResult,
    ClearRawResult,
    ImageCacheStats,
    MaintenanceBulkDeleteResult,
    MaintenanceDeleteResult,
    MaintenanceSummary,
    OrphanFolderEntry,
    OrphanFolderList,
    OrphanLogEntry,
    OrphanLogList,
)
from backend.models.metadata import (
    JobConfigUpdateRequest,
    MediaDetailSchema,
    MusicDetailSchema,
    MusicSearchResponse,
    MusicSearchResultSchema,
    NamingPreviewRequest,
    NamingPreviewResponse,
    SearchResponse,
    SearchResultSchema,
    TitleUpdateRequest,
    TrackTitleUpdateRequest,
)
from backend.models.notification import NotificationSchema
from backend.models.preset import (
    AdvancedField,
    Encoder,
    Overrides,
    Preset,
    PresetCreateRequest,
    PresetEditorState,
    PresetListResponse,
    PresetUpdateRequest,
    Scheme,
)
from backend.models.settings import SettingsResponse
from backend.models.setup import SetupStatus
from backend.models.system import (
    GpuSnapshotSchema,
    HardwareInfoSchema,
    JobStatsResponse,
    MemoryInfoSchema,
    PreflightFixResult,
    PreflightResult,
    RestartResponse,
    RippingEnabledResponse,
    StoragePathSchema,
    SystemInfoSchema,
    SystemStatsSchema,
)
from backend.models.transcoder import (
    TranscoderAuthStatus,
    TranscoderConfig,
    TranscoderJob,
    TranscoderJobListResponse,
    TranscoderStatsResponse,
    TranscoderStatsSummary,
    WorkerStatus,
    WorkersResponse,
)

__all__ = [
    "TRANSCODE_OVERRIDES_ALLOWLIST",
    "AdvancedField",
    "CleanupTranscoderResult",
    "ClearRawResult",
    "MaintenanceBulkDeleteResult",
    "MaintenanceDeleteResult",
    "DashboardResponse",
    "DirectoryListing",
    "DriveEjectResult",
    "DriveSchema",
    "DriveUpdateRequest",
    "Encoder",
    "FileEntry",
    "FileRoot",
    "FolderCreateRequest",
    "FolderCreateResponse",
    "FolderScanRequest",
    "FolderScanResult",
    "GpuSnapshotSchema",
    "HardwareInfoSchema",
    "ImageCacheStats",
    "JobConfigSnapshot",
    "JobConfigUpdateRequest",
    "JobDetailSchema",
    "JobListResponse",
    "JobSchema",
    "JobStatsResponse",
    "JobTranscodeOverridesUpdate",
    "JobSummary",
    "LogContentResponse",
    "LogEntrySchema",
    "LogFileSchema",
    "MaintenanceSummary",
    "MediaDetailSchema",
    "MusicSearchResponse",
    "SearchResponse",
    "MemoryInfoSchema",
    "MusicDetailSchema",
    "MusicSearchResultSchema",
    "NamingPreviewRequest",
    "NamingPreviewResponse",
    "NotificationSchema",
    "OperationResult",
    "OrphanFolderEntry",
    "OrphanFolderList",
    "OrphanLogEntry",
    "OrphanLogList",
    "Overrides",
    "PreflightFixResult",
    "PreflightResult",
    "Preset",
    "PresetCreateRequest",
    "PresetEditorState",
    "PresetListResponse",
    "PresetUpdateRequest",
    "RestartResponse",
    "RippingEnabledResponse",
    "RuntimeConfigResponse",
    "Scheme",
    "SearchResultSchema",
    "SettingsResponse",
    "SetupStatus",
    "StoragePathSchema",
    "StructuredLogResponse",
    "SystemInfoSchema",
    "SystemStatsSchema",
    "TitleUpdateRequest",
    "TrackCountsSchema",
    "TrackTitleUpdateRequest",
    "TrackSchema",
    "TranscoderAuthStatus",
    "TranscoderConfig",
    "TranscoderJob",
    "TranscoderJobListResponse",
    "TranscoderStatsResponse",
    "TranscoderStatsSummary",
    "WorkerStatus",
    "WorkersResponse",
]
