import { describe, it, expect, vi, beforeEach } from 'vitest';
import { skipAndFinalize } from '$lib/api/jobs';

// Mock the global fetch
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

describe('skipAndFinalize', () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it('sends POST to /api/jobs/{id}/skip-and-finalize', async () => {
		const responseBody = { success: true, message: 'Job finalized' };
		mockFetch.mockResolvedValue({
			ok: true,
			status: 200,
			json: () => Promise.resolve(responseBody)
		});

		const result = await skipAndFinalize(42);

		expect(mockFetch).toHaveBeenCalledTimes(1);
		const [url, init] = mockFetch.mock.calls[0];
		expect(url).toBe('/api/jobs/42/skip-and-finalize');
		expect(init.method).toBe('POST');
		expect(result).toEqual(responseBody);
	});

	it('throws on non-ok response', async () => {
		mockFetch.mockResolvedValue({
			ok: false,
			status: 502,
			statusText: 'Bad Gateway',
			json: () => Promise.resolve({ detail: 'ARM error' })
		});

		await expect(skipAndFinalize(42)).rejects.toThrow('ARM error');
	});
});
