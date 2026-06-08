import { apiFetch } from './client';
import type { FileRoot, DirectoryListing } from '$lib/types/api.gen';
export function fetchRoots(): Promise<FileRoot[]> {
	return apiFetch<FileRoot[]>('/api/files/roots');
}

export function fetchDirectory(path: string): Promise<DirectoryListing> {
	return apiFetch<DirectoryListing>(`/api/files/list?path=${encodeURIComponent(path)}`);
}

export function renameFile(
	path: string,
	newName: string
): Promise<{ success: boolean; new_path: string }> {
	return apiFetch('/api/files/rename', {
		method: 'POST',
		body: JSON.stringify({ path, new_name: newName })
	});
}

export function moveFile(
	path: string,
	destination: string
): Promise<{ success: boolean; new_path: string }> {
	return apiFetch('/api/files/move', {
		method: 'POST',
		body: JSON.stringify({ path, destination })
	});
}

export function createDirectory(
	path: string,
	name: string
): Promise<{ success: boolean; new_path: string }> {
	return apiFetch('/api/files/mkdir', {
		method: 'POST',
		body: JSON.stringify({ path, name })
	});
}

export function fixPermissions(path: string): Promise<{ success: boolean; fixed: number }> {
	return apiFetch('/api/files/fix-permissions', {
		method: 'POST',
		body: JSON.stringify({ path })
	});
}

export function deleteFile(path: string): Promise<{ success: boolean }> {
	return apiFetch('/api/files/delete', {
		method: 'DELETE',
		body: JSON.stringify({ path })
	});
}
