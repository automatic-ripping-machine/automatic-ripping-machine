import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('$lib/api/client', () => ({
	apiFetch: vi.fn().mockResolvedValue({})
}));

import { apiFetch } from '$lib/api/client';
import {
	fetchRoots, fetchDirectory, renameFile, moveFile,
	createDirectory, fixPermissions, deleteFile
} from '../api/files';

const mockApiFetch = vi.mocked(apiFetch);

beforeEach(() => {
	mockApiFetch.mockClear();
});

describe('fetchRoots', () => {
	it('calls /api/files/roots', async () => {
		await fetchRoots();
		expect(mockApiFetch).toHaveBeenCalledWith('/api/files/roots');
	});
});

describe('fetchDirectory', () => {
	it('encodes path in query param', async () => {
		await fetchDirectory('/media/my folder');
		expect(mockApiFetch).toHaveBeenCalledWith(
			'/api/files/list?path=%2Fmedia%2Fmy%20folder'
		);
	});

	it('handles simple paths', async () => {
		await fetchDirectory('/home/arm');
		expect(mockApiFetch).toHaveBeenCalledWith(
			'/api/files/list?path=%2Fhome%2Farm'
		);
	});
});

describe('renameFile', () => {
	it('POSTs with path and new_name', async () => {
		await renameFile('/media/old.mkv', 'new.mkv');
		expect(mockApiFetch).toHaveBeenCalledWith('/api/files/rename', {
			method: 'POST',
			body: JSON.stringify({ path: '/media/old.mkv', new_name: 'new.mkv' })
		});
	});
});

describe('moveFile', () => {
	it('POSTs with path and destination', async () => {
		await moveFile('/media/file.mkv', '/archive/');
		expect(mockApiFetch).toHaveBeenCalledWith('/api/files/move', {
			method: 'POST',
			body: JSON.stringify({ path: '/media/file.mkv', destination: '/archive/' })
		});
	});
});

describe('createDirectory', () => {
	it('POSTs with path and name', async () => {
		await createDirectory('/media', 'new-dir');
		expect(mockApiFetch).toHaveBeenCalledWith('/api/files/mkdir', {
			method: 'POST',
			body: JSON.stringify({ path: '/media', name: 'new-dir' })
		});
	});
});

describe('fixPermissions', () => {
	it('POSTs with path', async () => {
		await fixPermissions('/media/dir');
		expect(mockApiFetch).toHaveBeenCalledWith('/api/files/fix-permissions', {
			method: 'POST',
			body: JSON.stringify({ path: '/media/dir' })
		});
	});
});

describe('deleteFile', () => {
	it('DELETEs with path in body', async () => {
		await deleteFile('/media/file.mkv');
		expect(mockApiFetch).toHaveBeenCalledWith('/api/files/delete', {
			method: 'DELETE',
			body: JSON.stringify({ path: '/media/file.mkv' })
		});
	});
});
