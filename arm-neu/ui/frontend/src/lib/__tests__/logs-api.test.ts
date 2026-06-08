import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('$lib/api/client', () => ({
	apiFetch: vi.fn().mockResolvedValue({})
}));

import { apiFetch } from '$lib/api/client';
import {
	fetchLogs, fetchLogContent, fetchStructuredLogContent,
	fetchTranscoderLogs, fetchTranscoderLogContent, fetchStructuredTranscoderLogContent
} from '../api/logs';

const mockApiFetch = vi.mocked(apiFetch);

beforeEach(() => {
	mockApiFetch.mockClear();
});

describe('fetchLogs', () => {
	it('calls /api/logs', async () => {
		await fetchLogs();
		expect(mockApiFetch).toHaveBeenCalledWith('/api/logs');
	});
});

describe('fetchLogContent', () => {
	it('encodes filename with spaces', async () => {
		await fetchLogContent('my log.txt');
		const url = mockApiFetch.mock.calls[0][0] as string;
		expect(url).toContain('/api/logs/my%20log.txt');
	});

	it('uses default mode=tail and lines=100', async () => {
		await fetchLogContent('test.log');
		expect(mockApiFetch).toHaveBeenCalledWith('/api/logs/test.log?mode=tail&lines=100');
	});

	it('accepts custom mode and lines', async () => {
		await fetchLogContent('test.log', 'full', 500);
		expect(mockApiFetch).toHaveBeenCalledWith('/api/logs/test.log?mode=full&lines=500');
	});
});

describe('fetchStructuredLogContent', () => {
	it('builds base params', async () => {
		await fetchStructuredLogContent('arm.log');
		const url = mockApiFetch.mock.calls[0][0] as string;
		expect(url).toContain('/api/logs/arm.log/structured?');
		expect(url).toContain('mode=tail');
		expect(url).toContain('lines=100');
	});

	it('includes level filter', async () => {
		await fetchStructuredLogContent('arm.log', 'tail', 100, 'ERROR');
		const url = mockApiFetch.mock.calls[0][0] as string;
		expect(url).toContain('level=ERROR');
	});

	it('includes search filter', async () => {
		await fetchStructuredLogContent('arm.log', 'tail', 100, undefined, 'keyword');
		const url = mockApiFetch.mock.calls[0][0] as string;
		expect(url).toContain('search=keyword');
		expect(url).not.toContain('level=');
	});

	it('includes both level and search', async () => {
		await fetchStructuredLogContent('arm.log', 'full', 50, 'WARN', 'disc');
		const url = mockApiFetch.mock.calls[0][0] as string;
		expect(url).toContain('mode=full');
		expect(url).toContain('lines=50');
		expect(url).toContain('level=WARN');
		expect(url).toContain('search=disc');
	});
});

describe('fetchTranscoderLogs', () => {
	it('calls /api/transcoder/logs', async () => {
		await fetchTranscoderLogs();
		expect(mockApiFetch).toHaveBeenCalledWith('/api/transcoder/logs');
	});
});

describe('fetchTranscoderLogContent', () => {
	it('encodes filename in URL', async () => {
		await fetchTranscoderLogContent('job 1.log');
		const url = mockApiFetch.mock.calls[0][0] as string;
		expect(url).toContain('/api/transcoder/logs/job%201.log');
	});

	it('uses default mode and lines', async () => {
		await fetchTranscoderLogContent('transcode.log');
		expect(mockApiFetch).toHaveBeenCalledWith(
			'/api/transcoder/logs/transcode.log?mode=tail&lines=100'
		);
	});
});

describe('fetchStructuredTranscoderLogContent', () => {
	it('builds params with optional filters', async () => {
		await fetchStructuredTranscoderLogContent('tc.log', 'full', 200, 'INFO', 'test');
		const url = mockApiFetch.mock.calls[0][0] as string;
		expect(url).toContain('/api/transcoder/logs/tc.log/structured?');
		expect(url).toContain('mode=full');
		expect(url).toContain('lines=200');
		expect(url).toContain('level=INFO');
		expect(url).toContain('search=test');
	});

	it('omits filters when not provided', async () => {
		await fetchStructuredTranscoderLogContent('tc.log');
		const url = mockApiFetch.mock.calls[0][0] as string;
		expect(url).not.toContain('level=');
		expect(url).not.toContain('search=');
	});
});
