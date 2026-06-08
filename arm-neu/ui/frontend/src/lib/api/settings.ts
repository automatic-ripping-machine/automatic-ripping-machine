import type { SettingsResponse as SettingsData } from '$lib/types/api.gen';
import type { Scheme, Preset, Overrides } from '$lib/types/api.gen';
import { apiFetch } from './client';

export function fetchSettings(): Promise<SettingsData> {
	return apiFetch<SettingsData>('/api/settings');
}

export function saveArmConfig(config: Record<string, string | null>): Promise<{ success: boolean; warning?: string }> {
	return apiFetch('/api/settings/arm', {
		method: 'PUT',
		body: JSON.stringify({ config })
	});
}

export function saveTranscoderConfig(config: Record<string, unknown>): Promise<{ success: boolean; applied?: Record<string, unknown> }> {
	return apiFetch('/api/settings/transcoder', {
		method: 'PATCH',
		body: JSON.stringify(config)
	});
}

export interface AbcdeConfigData {
	content: string;
	path: string;
	exists: boolean;
}

export function fetchAbcdeConfig(): Promise<AbcdeConfigData> {
	return apiFetch<AbcdeConfigData>('/api/settings/abcde');
}

export function saveAbcdeConfig(content: string): Promise<{ success: boolean }> {
	return apiFetch('/api/settings/abcde', {
		method: 'PUT',
		body: JSON.stringify({ content })
	});
}

export function testMetadataKey(key?: string, provider?: string): Promise<{ success: boolean; message: string; provider: string }> {
	const params = new URLSearchParams();
	if (key) params.set('key', key);
	if (provider) params.set('provider', provider);
	const qs = params.toString();
	const url = qs ? '/api/settings/test-metadata?' + qs : '/api/settings/test-metadata';
	return apiFetch(url);
}

export interface ConnectionTestResult {
	reachable: boolean;
	auth_ok: boolean;
	auth_required: boolean;
	gpu_support: Record<string, boolean> | null;
	worker_running: boolean;
	queue_size: number;
	error: string | null;
}

export interface WebhookTestResult {
	reachable: boolean;
	secret_ok: boolean;
	secret_required: boolean;
	error: string | null;
}

export function testTranscoderConnection(): Promise<ConnectionTestResult> {
	return apiFetch<ConnectionTestResult>('/api/settings/transcoder/test-connection', {
		method: 'POST'
	});
}

export function testTranscoderWebhook(secret: string): Promise<WebhookTestResult> {
	return apiFetch<WebhookTestResult>('/api/settings/transcoder/test-webhook', {
		method: 'POST',
		body: JSON.stringify({ webhook_secret: secret })
	});
}

export interface SystemInfoData {
	versions: Record<string, string>;
	endpoints: Record<string, { url: string; reachable: boolean }>;
	paths: Array<{
		setting: string;
		path: string;
		exists: boolean;
		writable: boolean;
	}>;
	database: {
		path: string | null;
		size_bytes: number | null;
		available: boolean;
		migration_current: string | null;
		migration_head: string | null;
		up_to_date: boolean | null;
	};
	drives: Array<{
		name: string | null;
		mount: string | null;
		maker: string | null;
		model: string | null;
		capabilities: string[];
		firmware: string | null;
	}>;
}

export function fetchSystemInfo(): Promise<SystemInfoData> {
	return apiFetch<SystemInfoData>('/api/settings/system-info');
}

export async function fetchTranscoderScheme(): Promise<Scheme | null> {
	try {
		return await apiFetch<Scheme>('/api/settings/transcoder/scheme');
	} catch (e: unknown) {
		if (e instanceof Error && (e.message.includes('502') || e.message.includes('Transcoder service unreachable'))) return null;
		throw e;
	}
}

export async function fetchTranscoderPresets(): Promise<{ presets: Preset[] } | null> {
	try {
		return await apiFetch<{ presets: Preset[] }>('/api/settings/transcoder/presets');
	} catch (e: unknown) {
		if (e instanceof Error && (e.message.includes('502') || e.message.includes('Transcoder service unreachable'))) return null;
		throw e;
	}
}

export function createCustomPreset(body: { name: string; parent_slug: string; overrides: Overrides }): Promise<Preset> {
	return apiFetch<Preset>('/api/settings/transcoder/presets', {
		method: 'POST',
		body: JSON.stringify(body)
	});
}
