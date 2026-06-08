import { apiFetch } from './client';

export interface JobStats {
	by_status: Record<string, number>;
	by_type: Record<string, number>;
	total: number;
}

export function fetchJobStats(): Promise<JobStats> {
	return apiFetch<JobStats>('/api/system/job-stats');
}

export function restartArm(): Promise<{ success: boolean }> {
	return apiFetch('/api/system/restart', { method: 'POST' });
}

export function restartTranscoder(): Promise<{ success: boolean; message: string }> {
	return apiFetch('/api/system/restart-transcoder', { method: 'POST' });
}

export interface PreflightCheck {
	name: string;
	success: boolean;
	message: string;
	fixable: boolean;
}

export interface PreflightPath {
	name: string;
	container_path: string;
	host_path: string | null;
	exists: boolean;
	writable: boolean;
	owner_uid: number | null;
	owner_gid: number | null;
	expected_uid: number;
	expected_gid: number;
	match: boolean;
	fixable: boolean;
	require_writable: boolean;
}

export interface PreflightResult {
	arm_uid: number;
	arm_gid: number;
	checks: PreflightCheck[];
	paths: PreflightPath[];
}

export function runPreflight(): Promise<PreflightResult> {
	return apiFetch<PreflightResult>('/api/system/preflight', { method: 'POST' });
}

export function fixPreflight(items: string[]): Promise<PreflightResult> {
	return apiFetch<PreflightResult>('/api/system/preflight/fix', {
		method: 'POST',
		body: JSON.stringify({ fix: items }),
	});
}
