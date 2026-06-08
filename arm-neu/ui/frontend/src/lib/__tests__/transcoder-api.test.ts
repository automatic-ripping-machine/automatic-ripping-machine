import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('$lib/api/client', () => ({
	apiFetch: vi.fn().mockResolvedValue({})
}));

import { apiFetch } from '$lib/api/client';
import {
	fetchTranscoderStats, fetchTranscoderJobs,
	retryTranscoderJob, deleteTranscoderJob, retranscodeTranscoderJob
} from '../api/transcoder';

const mockApiFetch = vi.mocked(apiFetch);

beforeEach(() => {
	mockApiFetch.mockClear();
});

describe('fetchTranscoderStats', () => {
	it('calls /api/transcoder/stats', async () => {
		await fetchTranscoderStats();
		expect(mockApiFetch).toHaveBeenCalledWith('/api/transcoder/stats');
	});
});

describe('fetchTranscoderJobs', () => {
	it('calls with no params', async () => {
		await fetchTranscoderJobs();
		expect(mockApiFetch).toHaveBeenCalledWith('/api/transcoder/jobs');
	});

	it('builds query string from params', async () => {
		await fetchTranscoderJobs({ status: 'pending', limit: 10, offset: 20 });
		const url = mockApiFetch.mock.calls[0][0] as string;
		expect(url).toContain('status=pending');
		expect(url).toContain('limit=10');
		expect(url).toContain('offset=20');
	});

	it('omits empty params', async () => {
		await fetchTranscoderJobs({ status: '' });
		expect(mockApiFetch).toHaveBeenCalledWith('/api/transcoder/jobs');
	});
});

describe('retryTranscoderJob', () => {
	it('POSTs to retry', async () => {
		await retryTranscoderJob(3);
		expect(mockApiFetch).toHaveBeenCalledWith('/api/transcoder/jobs/3/retry', { method: 'POST' });
	});
});

describe('deleteTranscoderJob', () => {
	it('DELETEs job', async () => {
		await deleteTranscoderJob(3);
		expect(mockApiFetch).toHaveBeenCalledWith('/api/transcoder/jobs/3', { method: 'DELETE' });
	});
});

describe('retranscodeTranscoderJob', () => {
	it('POSTs to retranscode', async () => {
		await retranscodeTranscoderJob(3);
		expect(mockApiFetch).toHaveBeenCalledWith('/api/transcoder/jobs/3/retranscode', { method: 'POST' });
	});
});
