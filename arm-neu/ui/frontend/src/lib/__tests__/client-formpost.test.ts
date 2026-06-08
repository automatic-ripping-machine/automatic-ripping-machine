import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

import { apiFormPost } from '../api/client';

beforeEach(() => mockFetch.mockReset());

describe('apiFormPost', () => {
	it('POSTs FormData and returns parsed JSON', async () => {
		mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ id: 1 }) });
		const form = new FormData();
		form.append('file', 'data');
		const result = await apiFormPost('/api/upload', form);
		expect(result).toEqual({ id: 1 });
		expect(mockFetch).toHaveBeenCalledWith('/api/upload', expect.objectContaining({ method: 'POST', body: form }));
	});

	it('throws with detail from error response', async () => {
		mockFetch.mockResolvedValue({
			ok: false, status: 400, statusText: 'Bad Request',
			json: () => Promise.resolve({ detail: 'Invalid file' })
		});
		await expect(apiFormPost('/api/upload', new FormData())).rejects.toThrow('Invalid file');
	});

	it('throws with status text when body is not JSON', async () => {
		mockFetch.mockResolvedValue({
			ok: false, status: 500, statusText: 'Internal Server Error',
			json: () => Promise.reject(new Error('not json'))
		});
		await expect(apiFormPost('/api/upload', new FormData())).rejects.toThrow('API 500: Internal Server Error');
	});
});
