import type { DriveSchema as Drive } from '$lib/types/api.gen';
import { apiFetch } from './client';

export function fetchDrives(): Promise<Drive[]> {
	return apiFetch<Drive[]>('/api/drives');
}

export function ejectDrive(
	driveId: number,
	method: 'eject' | 'close' | 'toggle' = 'toggle'
): Promise<{ success: boolean; drive_id: number; method: string }> {
	return apiFetch(`/api/drives/${driveId}/eject?method=${method}`, { method: 'POST' });
}

export function updateDrive(
	driveId: number,
	data: {
		name?: string;
		description?: string;
		uhd_capable?: boolean;
		drive_mode?: string;
		rip_speed?: number | null;
		prescan_cache_mb?: number | null;
		prescan_timeout?: number | null;
		prescan_retries?: number | null;
		disc_enum_timeout?: number | null;
	}
): Promise<{ success: boolean; drive_id: number }> {
	return apiFetch(`/api/drives/${driveId}`, {
		method: 'PATCH',
		body: JSON.stringify(data)
	});
}

export function scanDrive(driveId: number): Promise<{ success: boolean; drive_id: number; devname: string }> {
	return apiFetch(`/api/drives/${driveId}/scan`, { method: 'POST' });
}

export function deleteDrive(driveId: number): Promise<{ success: boolean; drive_id: number }> {
	return apiFetch(`/api/drives/${driveId}`, { method: 'DELETE' });
}

export interface DriveDiagnostic {
	devname: string;
	status: 'ok' | 'warning';
	dev_node_exists: boolean;
	sysfs_exists: boolean;
	major_minor: string | null;
	in_kernel_cdrom: boolean;
	tray_status: number | null;
	tray_status_name: string | null;
	udevadm: Record<string, string>;
	arm_processing: boolean;
	in_database: boolean;
	db_name?: string;
	db_model?: string;
	db_connection?: string;
	issues: string[];
}

export interface DiagnosticResult {
	success: boolean;
	udevd_running: boolean;
	kernel_drives: string[];
	drives: DriveDiagnostic[];
	issues: string[];
}

export function fetchDriveDiagnostic(): Promise<DiagnosticResult> {
	return apiFetch<DiagnosticResult>('/api/drives/diagnostic');
}

export function rescanDrives(force = false): Promise<{ success: boolean }> {
	const params = force ? '?force=true' : '';
	return apiFetch(`/api/drives/rescan${params}`, { method: 'POST' });
}
