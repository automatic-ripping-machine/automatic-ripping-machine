import type { DashboardResponse as DashboardData } from '$lib/types/api.gen';
import { apiFetch } from './client';

export function fetchDashboard(): Promise<DashboardData> {
	return apiFetch<DashboardData>('/api/dashboard');
}

export function checkMakemkvKey(): Promise<{ key_valid: boolean; checked_at: string | null; message: string }> {
	return apiFetch('/api/dashboard/makemkv-key-check', { method: 'POST' });
}

export function setRippingEnabled(enabled: boolean): Promise<unknown> {
	return apiFetch('/api/system/ripping-enabled', {
		method: 'POST',
		body: JSON.stringify({ enabled })
	});
}
