import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

function jsonResponse(data: unknown, ok = true) {
	return { ok, status: ok ? 200 : 500, statusText: ok ? 'OK' : 'Error', json: () => Promise.resolve(data) };
}

import { fetchNotifications, dismissNotification } from '../api/notifications';

beforeEach(() => mockFetch.mockReset());

describe('fetchNotifications', () => {
	it('GETs /api/notifications', async () => {
		mockFetch.mockResolvedValue(jsonResponse([{ id: 1, message: 'test' }]));
		const result = await fetchNotifications();
		expect(result).toEqual([{ id: 1, message: 'test' }]);
	});
});

describe('dismissNotification', () => {
	it('PATCHes /api/notifications/:id', async () => {
		mockFetch.mockResolvedValue(jsonResponse({ success: true }));
		await dismissNotification(5);
		expect(mockFetch).toHaveBeenCalledWith('/api/notifications/5', expect.objectContaining({ method: 'PATCH' }));
	});
});
