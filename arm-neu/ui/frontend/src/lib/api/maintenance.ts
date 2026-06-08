import { apiFetch } from './client';
import type {
	MaintenanceSummary,
	OrphanLogList,
	OrphanFolderList,
	OrphanLogEntry,
	OrphanFolderEntry,
	MaintenanceDeleteResult,
	MaintenanceBulkDeleteResult,
	ClearRawResult,
	ImageCacheStats,
	CleanupTranscoderResult,
} from '$lib/types/api.gen';

export type {
	MaintenanceSummary,
	OrphanLogList,
	OrphanFolderList,
	OrphanLogEntry,
	OrphanFolderEntry,
	ClearRawResult,
	ImageCacheStats,
	CleanupTranscoderResult,
};

// Legacy aliases - the surrounding pages import these names. The generated
// equivalents are MaintenanceDeleteResult / MaintenanceBulkDeleteResult /
// OrphanLogList / OrphanFolderList; these aliases keep the call sites
// untouched.
export type OrphanLog = OrphanLogEntry;
export type OrphanFolder = OrphanFolderEntry;
export type OrphanLogsResponse = OrphanLogList;
export type OrphanFoldersResponse = OrphanFolderList;
export type DeleteResult = MaintenanceDeleteResult;
export type BulkDeleteResult = MaintenanceBulkDeleteResult;

export function fetchSummary(): Promise<MaintenanceSummary> {
	return apiFetch('/api/maintenance/summary');
}

export function fetchOrphanLogs(): Promise<OrphanLogList> {
	return apiFetch('/api/maintenance/orphan-logs');
}

export function fetchOrphanFolders(): Promise<OrphanFolderList> {
	return apiFetch('/api/maintenance/orphan-folders');
}

export function deleteLog(path: string): Promise<MaintenanceDeleteResult> {
	return apiFetch('/api/maintenance/delete-log', { method: 'POST', body: JSON.stringify({ path }) });
}

export function deleteFolder(path: string): Promise<MaintenanceDeleteResult> {
	return apiFetch('/api/maintenance/delete-folder', { method: 'POST', body: JSON.stringify({ path }) });
}

export function bulkDeleteLogs(paths: string[]): Promise<MaintenanceBulkDeleteResult> {
	return apiFetch('/api/maintenance/bulk-delete-logs', { method: 'POST', body: JSON.stringify({ paths }) });
}

export function bulkDeleteFolders(paths: string[]): Promise<MaintenanceBulkDeleteResult> {
	return apiFetch('/api/maintenance/bulk-delete-folders', { method: 'POST', body: JSON.stringify({ paths }) });
}

export function dismissAllNotifications(): Promise<{ success: boolean; count: number }> {
	return apiFetch('/api/maintenance/dismiss-all-notifications', { method: 'POST' });
}

export function purgeNotifications(): Promise<{ success: boolean; count: number }> {
	return apiFetch('/api/maintenance/purge-notifications', { method: 'POST' });
}

export function cleanupTranscoder(): Promise<CleanupTranscoderResult> {
	return apiFetch('/api/maintenance/cleanup-transcoder', { method: 'POST' });
}

export function fetchImageCacheStats(): Promise<ImageCacheStats> {
	return apiFetch('/api/maintenance/image-cache-stats');
}

export function clearImageCache(): Promise<ImageCacheStats> {
	return apiFetch('/api/maintenance/clear-image-cache', { method: 'POST' });
}

export function clearRaw(): Promise<ClearRawResult> {
	return apiFetch('/api/maintenance/clear-raw', { method: 'POST' });
}
