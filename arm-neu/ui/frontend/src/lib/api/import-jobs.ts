import { apiFetch } from './client';
import type {
	FolderScanResult,
	FolderCreateRequest,
	FolderCreateResponse,
	IsoScanResult,
	IsoCreateRequest,
	IsoCreateResponse,
	DirectoryListing,
	FileRoot
} from '../types/api.gen';

export type { IsoScanResult, IsoCreateRequest, IsoCreateResponse };

export function scanFolder(path: string): Promise<FolderScanResult> {
	return apiFetch('/api/jobs/folder/scan', {
		method: 'POST',
		body: JSON.stringify({ path })
	});
}

export function createFolderJob(data: FolderCreateRequest): Promise<FolderCreateResponse> {
	return apiFetch('/api/jobs/folder', {
		method: 'POST',
		body: JSON.stringify(data)
	});
}

export function scanIso(path: string): Promise<IsoScanResult> {
	return apiFetch('/api/jobs/iso/scan', {
		method: 'POST',
		body: JSON.stringify({ path })
	});
}

export function createIsoJob(data: IsoCreateRequest): Promise<IsoCreateResponse> {
	return apiFetch('/api/jobs/iso', {
		method: 'POST',
		body: JSON.stringify(data)
	});
}

export function fetchIngressDirectory(path: string): Promise<DirectoryListing> {
	return apiFetch(`/api/files/list?path=${encodeURIComponent(path)}`);
}

export function fetchIngressRoot(): Promise<FileRoot[]> {
	return apiFetch('/api/files/roots');
}
