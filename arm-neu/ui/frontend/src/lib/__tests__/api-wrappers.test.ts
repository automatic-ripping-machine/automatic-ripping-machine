import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('$lib/api/client', () => ({
	apiFetch: vi.fn().mockResolvedValue({})
}));

import { apiFetch } from '$lib/api/client';
import { fetchDashboard, setRippingEnabled } from '../api/dashboard';
import { fetchDrives, updateDrive } from '../api/drives';
import { fetchNotifications } from '../api/notifications';

const mockApiFetch = vi.mocked(apiFetch);

beforeEach(() => {
	mockApiFetch.mockClear();
});

describe('dashboard API', () => {
	it('fetchDashboard calls /api/dashboard', async () => {
		await fetchDashboard();
		expect(mockApiFetch).toHaveBeenCalledWith('/api/dashboard');
	});

	it('setRippingEnabled POSTs enabled=true', async () => {
		await setRippingEnabled(true);
		expect(mockApiFetch).toHaveBeenCalledWith('/api/system/ripping-enabled', {
			method: 'POST',
			body: JSON.stringify({ enabled: true })
		});
	});

	it('setRippingEnabled POSTs enabled=false', async () => {
		await setRippingEnabled(false);
		expect(mockApiFetch).toHaveBeenCalledWith('/api/system/ripping-enabled', {
			method: 'POST',
			body: JSON.stringify({ enabled: false })
		});
	});
});

describe('drives API', () => {
	it('fetchDrives calls /api/drives', async () => {
		await fetchDrives();
		expect(mockApiFetch).toHaveBeenCalledWith('/api/drives');
	});

	it('updateDrive PATCHes with data', async () => {
		await updateDrive(1, { name: 'My Drive', uhd_capable: true });
		expect(mockApiFetch).toHaveBeenCalledWith('/api/drives/1', {
			method: 'PATCH',
			body: JSON.stringify({ name: 'My Drive', uhd_capable: true })
		});
	});
});

describe('notifications API', () => {
	it('fetchNotifications calls /api/notifications', async () => {
		await fetchNotifications();
		expect(mockApiFetch).toHaveBeenCalledWith('/api/notifications');
	});
});
