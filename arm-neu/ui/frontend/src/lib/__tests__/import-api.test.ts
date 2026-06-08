import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('$lib/api/client', () => ({
	apiFetch: vi.fn().mockResolvedValue({})
}));

import { apiFetch } from '$lib/api/client';
import {
	scanFolder, createFolderJob, fetchIngressDirectory, fetchIngressRoot
} from '../api/import-jobs';

const mockApiFetch = vi.mocked(apiFetch);

beforeEach(() => {
	mockApiFetch.mockClear();
});

describe('scanFolder', () => {
	it('POSTs path to /api/jobs/folder/scan', async () => {
		await scanFolder('/media/movies/MyMovie');
		expect(mockApiFetch).toHaveBeenCalledWith('/api/jobs/folder/scan', {
			method: 'POST',
			body: JSON.stringify({ path: '/media/movies/MyMovie' })
		});
	});
});

describe('createFolderJob', () => {
	it('POSTs job data to /api/jobs/folder', async () => {
		const data = {
			source_path: '/media/ingress/MyMovie',
			title: 'My Movie',
			year: '2024',
			video_type: 'movie',
			disctype: 'bluray',
			imdb_id: 'tt1234567'
		};
		await createFolderJob(data);
		expect(mockApiFetch).toHaveBeenCalledWith('/api/jobs/folder', {
			method: 'POST',
			body: JSON.stringify(data)
		});
	});
});

describe('fetchIngressDirectory', () => {
	it('encodes path in query param', async () => {
		await fetchIngressDirectory('/media/my folder');
		expect(mockApiFetch).toHaveBeenCalledWith(
			'/api/files/list?path=%2Fmedia%2Fmy%20folder'
		);
	});

	it('handles simple paths', async () => {
		await fetchIngressDirectory('/media/ingress');
		expect(mockApiFetch).toHaveBeenCalledWith(
			'/api/files/list?path=%2Fmedia%2Fingress'
		);
	});
});

describe('fetchIngressRoot', () => {
	it('calls /api/files/roots', async () => {
		await fetchIngressRoot();
		expect(mockApiFetch).toHaveBeenCalledWith('/api/files/roots');
	});
});
