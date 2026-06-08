import { apiFetch } from './client';
import type { SetupStatus } from '$lib/types/api.gen';
export function fetchSetupStatus(): Promise<SetupStatus> {
	return apiFetch<SetupStatus>('/api/setup/status');
}

export function completeSetup(): Promise<{ success: boolean }> {
	return apiFetch('/api/setup/complete', { method: 'POST' });
}
