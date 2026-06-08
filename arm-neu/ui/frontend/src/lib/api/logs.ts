import type { LogContentResponse as LogContent, LogFileSchema as LogFile, StructuredLogResponse as StructuredLogContent } from '$lib/types/api.gen';
import { apiFetch } from './client';

export function fetchLogs(): Promise<LogFile[]> {
	return apiFetch<LogFile[]>('/api/logs');
}

export function fetchLogContent(
	filename: string,
	mode: 'tail' | 'full' = 'tail',
	lines: number = 100
): Promise<LogContent> {
	return apiFetch<LogContent>(`/api/logs/${encodeURIComponent(filename)}?mode=${mode}&lines=${lines}`);
}

export function fetchStructuredLogContent(
	filename: string,
	mode: 'tail' | 'full' = 'tail',
	lines: number = 100,
	level?: string,
	search?: string
): Promise<StructuredLogContent> {
	const params = new URLSearchParams({ mode, lines: String(lines) });
	if (level) params.set('level', level);
	if (search) params.set('search', search);
	return apiFetch<StructuredLogContent>(
		`/api/logs/${encodeURIComponent(filename)}/structured?${params}`
	);
}

export function fetchTranscoderLogs(): Promise<LogFile[]> {
	return apiFetch<LogFile[]>('/api/transcoder/logs');
}

export function fetchTranscoderLogContent(
	filename: string,
	mode: 'tail' | 'full' = 'tail',
	lines: number = 100
): Promise<LogContent> {
	return apiFetch<LogContent>(
		`/api/transcoder/logs/${encodeURIComponent(filename)}?mode=${mode}&lines=${lines}`
	);
}

export function fetchStructuredTranscoderLogContent(
	filename: string,
	mode: 'tail' | 'full' = 'tail',
	lines: number = 100,
	level?: string,
	search?: string
): Promise<StructuredLogContent> {
	const params = new URLSearchParams({ mode, lines: String(lines) });
	if (level) params.set('level', level);
	if (search) params.set('search', search);
	return apiFetch<StructuredLogContent>(
		`/api/transcoder/logs/${encodeURIComponent(filename)}/structured?${params}`
	);
}

export function deleteLog(filename: string): Promise<{ success: boolean; filename: string }> {
	return apiFetch(`/api/logs/${encodeURIComponent(filename)}`, { method: 'DELETE' });
}

export function logDownloadUrl(filename: string): string {
	return `/api/logs/${encodeURIComponent(filename)}/download`;
}

export async function fetchTranscoderLogForArmJob(
	armJobId: number
): Promise<{
	found: boolean;
	logfile?: string;
	transcoder_job_id?: number;
	status?: string;
	/** Sub-status inside JobStatus.processing — surfaces what the worker is doing
	 * during periods where no encoder progress is being reported. Wire values
	 * come from arm_contracts.TranscodePhase. */
	phase?: string | null;
	progress?: number | null;
	current_fps?: number | null;
}> {
	return apiFetch(`/api/transcoder/job-for-arm/${armJobId}`);
}
