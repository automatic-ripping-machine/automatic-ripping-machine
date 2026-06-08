import { describe, it, expect, vi, beforeEach } from 'vitest';
import { apiFetch } from '../api/client';

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

function jsonResponse(data: unknown, ok = true, status = 200, statusText = 'OK') {
	return {
		ok,
		status,
		statusText,
		json: () => Promise.resolve(data)
	};
}

beforeEach(() => {
	mockFetch.mockReset();
});

describe('apiFetch', () => {
	it('returns parsed JSON on success', async () => {
		mockFetch.mockResolvedValue(jsonResponse({ id: 1 }));
		const result = await apiFetch('/api/test');
		expect(result).toEqual({ id: 1 });
	});

	it('sends Content-Type application/json by default', async () => {
		mockFetch.mockResolvedValue(jsonResponse({}));
		await apiFetch('/api/test');
		expect(mockFetch).toHaveBeenCalledWith(
			'/api/test',
			expect.objectContaining({
				headers: expect.objectContaining({ 'Content-Type': 'application/json' })
			})
		);
	});

	it('merges custom headers', async () => {
		mockFetch.mockResolvedValue(jsonResponse({}));
		await apiFetch('/api/test', { headers: { 'X-Custom': 'value' } });
		expect(mockFetch).toHaveBeenCalledWith(
			'/api/test',
			expect.objectContaining({
				headers: { 'Content-Type': 'application/json', 'X-Custom': 'value' }
			})
		);
	});

	it('passes through method and body', async () => {
		mockFetch.mockResolvedValue(jsonResponse({}));
		await apiFetch('/api/test', { method: 'POST', body: JSON.stringify({ key: 'val' }) });
		expect(mockFetch).toHaveBeenCalledWith(
			'/api/test',
			expect.objectContaining({
				method: 'POST',
				body: '{"key":"val"}'
			})
		);
	});

	it('throws with detail from error response body', async () => {
		mockFetch.mockResolvedValue(jsonResponse({ detail: 'Not found' }, false, 404, 'Not Found'));
		await expect(apiFetch('/api/missing')).rejects.toThrow('Not found');
	});

	it('throws with status text when body has no detail', async () => {
		mockFetch.mockResolvedValue(jsonResponse({}, false, 500, 'Internal Server Error'));
		await expect(apiFetch('/api/broken')).rejects.toThrow('API 500: Internal Server Error');
	});

	it('throws with status text when response body is not JSON', async () => {
		mockFetch.mockResolvedValue({
			ok: false,
			status: 502,
			statusText: 'Bad Gateway',
			json: () => Promise.reject(new Error('not json'))
		});
		await expect(apiFetch('/api/bad')).rejects.toThrow('API 502: Bad Gateway');
	});
});
