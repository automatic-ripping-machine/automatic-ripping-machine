import type { TranscoderJobListResponse, TranscoderStatsResponse as TranscoderStats, WorkersResponse } from '$lib/types/api.gen';
import { apiFetch } from './client';

export function fetchTranscoderStats(): Promise<TranscoderStats> {
	return apiFetch<TranscoderStats>('/api/transcoder/stats');
}

export function fetchTranscoderWorkers(): Promise<WorkersResponse> {
	return apiFetch<WorkersResponse>('/api/transcoder/workers');
}

export function fetchTranscoderJobs(params?: {
	status?: string;
	limit?: number;
	offset?: number;
}): Promise<TranscoderJobListResponse> {
	const query = new URLSearchParams();
	if (params?.status) query.set('status', params.status);
	if (params?.limit) query.set('limit', String(params.limit));
	if (params?.offset) query.set('offset', String(params.offset));
	const qs = query.toString();
	return apiFetch<TranscoderJobListResponse>(`/api/transcoder/jobs${qs ? `?${qs}` : ''}`);
}

export function retryTranscoderJob(id: number): Promise<unknown> {
	return apiFetch(`/api/transcoder/jobs/${id}/retry`, { method: 'POST' });
}

export function deleteTranscoderJob(id: number): Promise<unknown> {
	return apiFetch(`/api/transcoder/jobs/${id}`, { method: 'DELETE' });
}

export function retranscodeTranscoderJob(id: number): Promise<{ status: string; message: string }> {
	return apiFetch(`/api/transcoder/jobs/${id}/retranscode`, { method: 'POST' });
}

export async function listHandbrakePresets(): Promise<Record<string, string[]>> {
	try {
		return await apiFetch<Record<string, string[]>>('/api/transcoder/handbrake-presets');
	} catch {
		// Endpoint missing (older transcoder), transcoder offline, or
		// network error. The PresetEditor falls back to free-text in
		// either case; an empty list is the agreed sentinel.
		return {};
	}
}
