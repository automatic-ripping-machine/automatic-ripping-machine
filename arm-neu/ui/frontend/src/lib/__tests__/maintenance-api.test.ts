import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
	fetchSummary,
	fetchOrphanLogs,
	fetchOrphanFolders,
	deleteLog,
	deleteFolder,
	bulkDeleteLogs,
	bulkDeleteFolders,
	dismissAllNotifications,
	purgeNotifications,
	cleanupTranscoder,
	clearRaw,
	fetchImageCacheStats,
	clearImageCache
} from '$lib/api/maintenance';

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

function ok(data: unknown) {
	return { ok: true, json: () => Promise.resolve(data) } as Response;
}

beforeEach(() => mockFetch.mockReset());

describe('maintenance API', () => {
	it('fetchSummary calls GET /api/maintenance/summary', async () => {
		const data = {
			orphan_logs: 3,
			orphan_folders: 5,
			unseen_notifications: 12,
			cleared_notifications: 45,
			stale_transcoder_jobs: 8
		};
		mockFetch.mockResolvedValueOnce(ok(data));
		const result = await fetchSummary();
		expect(result).toEqual(data);
		expect(mockFetch).toHaveBeenCalledWith(
			'/api/maintenance/summary',
			expect.objectContaining({
				headers: expect.objectContaining({ 'Content-Type': 'application/json' })
			})
		);
	});

	it('fetchOrphanLogs calls GET /api/maintenance/orphan-logs', async () => {
		const data = { root: '/tmp', total_size_bytes: 100, files: [] };
		mockFetch.mockResolvedValueOnce(ok(data));
		const result = await fetchOrphanLogs();
		expect(result).toEqual(data);
	});

	it('fetchOrphanFolders calls GET /api/maintenance/orphan-folders', async () => {
		const data = { total_size_bytes: 0, folders: [] };
		mockFetch.mockResolvedValueOnce(ok(data));
		const result = await fetchOrphanFolders();
		expect(result).toEqual(data);
	});

	it('deleteLog calls POST with path', async () => {
		mockFetch.mockResolvedValueOnce(ok({ success: true }));
		await deleteLog('/tmp/test.log');
		expect(mockFetch).toHaveBeenCalledWith(
			'/api/maintenance/delete-log',
			expect.objectContaining({
				method: 'POST',
				body: JSON.stringify({ path: '/tmp/test.log' })
			})
		);
	});

	it('deleteFolder calls POST with path', async () => {
		mockFetch.mockResolvedValueOnce(ok({ success: true }));
		await deleteFolder('/raw/orphan');
		expect(mockFetch).toHaveBeenCalledWith(
			'/api/maintenance/delete-folder',
			expect.objectContaining({
				method: 'POST',
				body: JSON.stringify({ path: '/raw/orphan' })
			})
		);
	});

	it('bulkDeleteLogs calls POST with paths array', async () => {
		mockFetch.mockResolvedValueOnce(ok({ removed: ['/a.log'], errors: [] }));
		await bulkDeleteLogs(['/a.log', '/b.log']);
		expect(mockFetch).toHaveBeenCalledWith(
			'/api/maintenance/bulk-delete-logs',
			expect.objectContaining({
				method: 'POST',
				body: JSON.stringify({ paths: ['/a.log', '/b.log'] })
			})
		);
	});

	it('bulkDeleteFolders calls POST with paths array', async () => {
		mockFetch.mockResolvedValueOnce(ok({ removed: [], errors: [] }));
		await bulkDeleteFolders(['/raw/a']);
		expect(mockFetch).toHaveBeenCalledWith(
			'/api/maintenance/bulk-delete-folders',
			expect.objectContaining({
				method: 'POST',
				body: JSON.stringify({ paths: ['/raw/a'] })
			})
		);
	});

	it('dismissAllNotifications calls POST', async () => {
		mockFetch.mockResolvedValueOnce(ok({ success: true, count: 5 }));
		const result = await dismissAllNotifications();
		expect(result.count).toBe(5);
	});

	it('purgeNotifications calls POST', async () => {
		mockFetch.mockResolvedValueOnce(ok({ success: true, count: 10 }));
		const result = await purgeNotifications();
		expect(result.count).toBe(10);
	});

	it('cleanupTranscoder calls POST', async () => {
		mockFetch.mockResolvedValueOnce(ok({ success: true, deleted: 3, errors: [] }));
		const result = await cleanupTranscoder();
		expect(result.deleted).toBe(3);
	});

	it('fetchImageCacheStats calls GET /api/maintenance/image-cache-stats', async () => {
		const data = { count: 42, size_bytes: 52428800, size_mb: '50.0', oldest: '2026-01-01', path: '/home/arm/cache' };
		mockFetch.mockResolvedValueOnce(ok(data));
		const result = await fetchImageCacheStats();
		expect(result).toEqual(data);
		expect(mockFetch).toHaveBeenCalledWith(
			'/api/maintenance/image-cache-stats',
			expect.objectContaining({
				headers: expect.objectContaining({ 'Content-Type': 'application/json' })
			})
		);
	});

	it('clearImageCache calls POST and returns cleared count', async () => {
		mockFetch.mockResolvedValueOnce(ok({ success: true, cleared: 42, freed_bytes: 52428800 }));
		const result = await clearImageCache();
		expect(mockFetch).toHaveBeenCalledWith(
			'/api/maintenance/clear-image-cache',
			expect.objectContaining({ method: 'POST' })
		);
		expect(result.cleared).toBe(42);
		expect(result.freed_bytes).toBe(52428800);
	});

	it('clearRaw calls POST and returns cleared count', async () => {
		mockFetch.mockResolvedValueOnce(ok({ success: true, cleared: 5, freed_bytes: 1048576, errors: [], path: '/home/arm/media/raw' }));
		const result = await clearRaw();
		expect(mockFetch).toHaveBeenCalledWith(
			'/api/maintenance/clear-raw',
			expect.objectContaining({ method: 'POST' })
		);
		expect(result.cleared).toBe(5);
		expect(result.freed_bytes).toBe(1048576);
		expect(result.path).toBe('/home/arm/media/raw');
	});
});
