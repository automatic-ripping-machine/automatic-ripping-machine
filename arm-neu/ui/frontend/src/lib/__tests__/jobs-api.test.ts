import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('$lib/api/client', () => ({
	apiFetch: vi.fn().mockResolvedValue({})
}));

import { apiFetch } from '$lib/api/client';
import {
	fetchJobs, fetchJob, abandonJob, cancelWaitingJob, startWaitingJob,
	pauseWaitingJob, deleteJob, fixJobPermissions, searchMetadata,
	fetchMediaDetail, searchMusicMetadata, fetchMusicDetail, setJobTracks,
	updateJobTitle, updateJobConfig, fetchCrcLookup, submitToCrcDb,
	fetchJobProgress, updateJobTranscodeConfig, retranscodeJob
} from '../api/jobs';

const mockApiFetch = vi.mocked(apiFetch);

beforeEach(() => {
	mockApiFetch.mockClear();
});

describe('fetchJobs', () => {
	it('calls /api/jobs with no params', async () => {
		await fetchJobs();
		expect(mockApiFetch).toHaveBeenCalledWith('/api/jobs');
	});

	it('builds query string from all params', async () => {
		await fetchJobs({ page: 2, per_page: 10, status: 'active', search: 'test', video_type: 'movie' });
		const url = mockApiFetch.mock.calls[0][0] as string;
		expect(url).toContain('page=2');
		expect(url).toContain('per_page=10');
		expect(url).toContain('status=active');
		expect(url).toContain('search=test');
		expect(url).toContain('video_type=movie');
	});

	it('omits falsy params', async () => {
		await fetchJobs({ page: 0, status: '' });
		expect(mockApiFetch).toHaveBeenCalledWith('/api/jobs');
	});
});

describe('simple job endpoints', () => {
	it('fetchJob', async () => {
		await fetchJob(42);
		expect(mockApiFetch).toHaveBeenCalledWith('/api/jobs/42');
	});

	it('abandonJob POSTs', async () => {
		await abandonJob(1);
		expect(mockApiFetch).toHaveBeenCalledWith('/api/jobs/1/abandon', { method: 'POST' });
	});

	it('cancelWaitingJob POSTs', async () => {
		await cancelWaitingJob(1);
		expect(mockApiFetch).toHaveBeenCalledWith('/api/jobs/1/cancel', { method: 'POST' });
	});

	it('startWaitingJob POSTs', async () => {
		await startWaitingJob(1);
		expect(mockApiFetch).toHaveBeenCalledWith('/api/jobs/1/start', { method: 'POST' });
	});

	it('pauseWaitingJob POSTs', async () => {
		await pauseWaitingJob(1);
		expect(mockApiFetch).toHaveBeenCalledWith('/api/jobs/1/pause', {
			method: 'POST',
			body: undefined,
		});
	});

	it('pauseWaitingJob sends explicit paused=true in body', async () => {
		await pauseWaitingJob(1, true);
		expect(mockApiFetch).toHaveBeenCalledWith('/api/jobs/1/pause', expect.objectContaining({
			method: 'POST',
			body: JSON.stringify({ paused: true }),
		}));
	});

	it('pauseWaitingJob sends explicit paused=false in body', async () => {
		await pauseWaitingJob(1, false);
		expect(mockApiFetch).toHaveBeenCalledWith('/api/jobs/1/pause', expect.objectContaining({
			method: 'POST',
			body: JSON.stringify({ paused: false }),
		}));
	});

	it('deleteJob DELETEs', async () => {
		await deleteJob(1);
		expect(mockApiFetch).toHaveBeenCalledWith('/api/jobs/1', { method: 'DELETE' });
	});

	it('fixJobPermissions POSTs', async () => {
		await fixJobPermissions(1);
		expect(mockApiFetch).toHaveBeenCalledWith('/api/jobs/1/fix-permissions', { method: 'POST' });
	});

	it('fetchCrcLookup', async () => {
		await fetchCrcLookup(5);
		expect(mockApiFetch).toHaveBeenCalledWith('/api/jobs/5/crc-lookup');
	});

	it('submitToCrcDb POSTs', async () => {
		await submitToCrcDb(5);
		expect(mockApiFetch).toHaveBeenCalledWith('/api/jobs/5/crc-submit', { method: 'POST' });
	});

	it('fetchJobProgress', async () => {
		await fetchJobProgress(5);
		expect(mockApiFetch).toHaveBeenCalledWith('/api/jobs/5/progress');
	});

	it('retranscodeJob POSTs', async () => {
		await retranscodeJob(5);
		expect(mockApiFetch).toHaveBeenCalledWith('/api/jobs/5/retranscode', { method: 'POST' });
	});
});

describe('searchMetadata', () => {
	it('builds params with query', async () => {
		await searchMetadata('Matrix');
		const url = mockApiFetch.mock.calls[0][0] as string;
		expect(url).toContain('/api/metadata/search?');
		expect(url).toContain('q=Matrix');
	});

	it('includes year when provided', async () => {
		await searchMetadata('Matrix', '1999');
		const url = mockApiFetch.mock.calls[0][0] as string;
		expect(url).toContain('year=1999');
	});
});

describe('fetchMediaDetail', () => {
	it('calls correct path', async () => {
		await fetchMediaDetail('tt0133093');
		expect(mockApiFetch).toHaveBeenCalledWith('/api/metadata/tt0133093');
	});
});

describe('searchMusicMetadata', () => {
	it('builds params with query only', async () => {
		await searchMusicMetadata('Beatles');
		const url = mockApiFetch.mock.calls[0][0] as string;
		expect(url).toContain('q=Beatles');
	});

	it('includes all filters', async () => {
		await searchMusicMetadata('Beatles', {
			artist: 'The Beatles', release_type: 'album',
			format: 'CD', country: 'US', status: 'official', tracks: 12
		});
		const url = mockApiFetch.mock.calls[0][0] as string;
		expect(url).toContain('artist=The+Beatles');
		expect(url).toContain('release_type=album');
		expect(url).toContain('format=CD');
		expect(url).toContain('country=US');
		expect(url).toContain('status=official');
		expect(url).toContain('tracks=12');
	});

	it('includes offset when > 0', async () => {
		await searchMusicMetadata('Beatles', undefined, 25);
		const url = mockApiFetch.mock.calls[0][0] as string;
		expect(url).toContain('offset=25');
	});

	it('omits offset when 0', async () => {
		await searchMusicMetadata('Beatles');
		const url = mockApiFetch.mock.calls[0][0] as string;
		expect(url).not.toContain('offset');
	});
});

describe('fetchMusicDetail', () => {
	it('calls correct path', async () => {
		await fetchMusicDetail('abc-123');
		expect(mockApiFetch).toHaveBeenCalledWith('/api/metadata/music/abc-123');
	});
});

describe('mutation endpoints with bodies', () => {
	it('setJobTracks PUTs tracks', async () => {
		const tracks = [{ track_number: '1', title: 'Song', length_ms: 1000 }];
		await setJobTracks(1, tracks);
		expect(mockApiFetch).toHaveBeenCalledWith('/api/jobs/1/tracks', {
			method: 'PUT', body: JSON.stringify(tracks)
		});
	});

	it('updateJobTitle PUTs title', async () => {
		await updateJobTitle(1, { title: 'New Title' } as any);
		expect(mockApiFetch).toHaveBeenCalledWith('/api/jobs/1/title', {
			method: 'PUT', body: JSON.stringify({ title: 'New Title' })
		});
	});

	it('updateJobConfig PATCHes config', async () => {
		await updateJobConfig(1, { MINLENGTH: '600' } as any);
		expect(mockApiFetch).toHaveBeenCalledWith('/api/jobs/1/config', {
			method: 'PATCH', body: JSON.stringify({ MINLENGTH: '600' })
		});
	});

	it('updateJobTranscodeConfig PATCHes overrides', async () => {
		const overrides = { codec: 'h265' };
		await updateJobTranscodeConfig(1, overrides);
		expect(mockApiFetch).toHaveBeenCalledWith('/api/jobs/1/transcode-config', {
			method: 'PATCH', body: JSON.stringify(overrides)
		});
	});
});
