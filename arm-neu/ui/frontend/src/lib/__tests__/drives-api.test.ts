import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

function jsonResponse(data: unknown, ok = true) {
	return { ok, status: ok ? 200 : 500, statusText: ok ? 'OK' : 'Error', json: () => Promise.resolve(data) };
}

import { updateDrive, scanDrive, deleteDrive, fetchDriveDiagnostic } from '../api/drives';

beforeEach(() => mockFetch.mockReset());

describe('updateDrive', () => {
	it('PATCHes /api/drives/:id', async () => {
		mockFetch.mockResolvedValue(jsonResponse({ success: true, drive_id: 1 }));
		const result = await updateDrive(1, { name: 'New Name' });
		expect(mockFetch).toHaveBeenCalledWith('/api/drives/1', expect.objectContaining({
			method: 'PATCH',
			body: JSON.stringify({ name: 'New Name' })
		}));
		expect(result).toEqual({ success: true, drive_id: 1 });
	});
});

describe('scanDrive', () => {
	it('POSTs /api/drives/:id/scan', async () => {
		mockFetch.mockResolvedValue(jsonResponse({ success: true, drive_id: 1, devname: 'sr0' }));
		const result = await scanDrive(1);
		expect(mockFetch).toHaveBeenCalledWith('/api/drives/1/scan', expect.objectContaining({ method: 'POST' }));
		expect(result).toEqual({ success: true, drive_id: 1, devname: 'sr0' });
	});
});

describe('deleteDrive', () => {
	it('DELETEs /api/drives/:id', async () => {
		mockFetch.mockResolvedValue(jsonResponse({ success: true, drive_id: 1 }));
		await deleteDrive(1);
		expect(mockFetch).toHaveBeenCalledWith('/api/drives/1', expect.objectContaining({ method: 'DELETE' }));
	});
});

describe('fetchDriveDiagnostic', () => {
	it('GETs /api/drives/diagnostic', async () => {
		mockFetch.mockResolvedValue(jsonResponse({ success: true, drives: [], issues: [], udevd_running: true, kernel_drives: [] }));
		const result = await fetchDriveDiagnostic();
		expect(result.success).toBe(true);
	});
});
