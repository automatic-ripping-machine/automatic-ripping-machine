import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

function jsonResponse(data: unknown, ok = true) {
	return { ok, status: ok ? 200 : 500, statusText: ok ? 'OK' : 'Error', json: () => Promise.resolve(data) };
}

import { fetchAbcdeConfig, saveAbcdeConfig, testTranscoderConnection, testTranscoderWebhook, fetchSystemInfo, fetchTranscoderScheme, fetchTranscoderPresets, createCustomPreset } from '../api/settings';

beforeEach(() => mockFetch.mockReset());

describe('fetchAbcdeConfig', () => {
	it('GETs /api/settings/abcde', async () => {
		mockFetch.mockResolvedValue(jsonResponse({ content: 'CDROM=/dev/sr0', path: '/etc/abcde.conf', exists: true }));
		const result = await fetchAbcdeConfig();
		expect(result.content).toBe('CDROM=/dev/sr0');
		expect(result.exists).toBe(true);
	});
});

describe('saveAbcdeConfig', () => {
	it('PUTs content to /api/settings/abcde', async () => {
		mockFetch.mockResolvedValue(jsonResponse({ success: true }));
		await saveAbcdeConfig('CDROM=/dev/sr1');
		expect(mockFetch).toHaveBeenCalledWith('/api/settings/abcde', expect.objectContaining({
			method: 'PUT',
			body: JSON.stringify({ content: 'CDROM=/dev/sr1' })
		}));
	});
});

describe('testTranscoderConnection', () => {
	it('POSTs to /api/settings/transcoder/test-connection', async () => {
		mockFetch.mockResolvedValue(jsonResponse({ reachable: true, auth_ok: true, auth_required: false, gpu_support: null, worker_running: true, queue_size: 0, error: null }));
		const result = await testTranscoderConnection();
		expect(result.reachable).toBe(true);
	});
});

describe('testTranscoderWebhook', () => {
	it('POSTs secret to /api/settings/transcoder/test-webhook', async () => {
		mockFetch.mockResolvedValue(jsonResponse({ reachable: true, secret_ok: true, secret_required: true, error: null }));
		const result = await testTranscoderWebhook('my-secret');
		expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining('/test-webhook'), expect.objectContaining({
			method: 'POST',
			body: JSON.stringify({ webhook_secret: 'my-secret' })
		}));
		expect(result.secret_ok).toBe(true);
	});
});

describe('fetchSystemInfo', () => {
	it('GETs /api/settings/system-info', async () => {
		mockFetch.mockResolvedValue(jsonResponse({ versions: {}, endpoints: {}, paths: [], database: {}, drives: [] }));
		const result = await fetchSystemInfo();
		expect(result.versions).toBeDefined();
	});
});

describe('fetchTranscoderScheme', () => {
	it('GETs /api/settings/transcoder/scheme and returns scheme', async () => {
		const scheme = {
			slug: 'nvidia',
			name: 'NVIDIA NVENC',
			supported_encoders: [],
			supported_audio_encoders: [],
			supported_subtitle_modes: [],
			advanced_fields: {}
		};
		mockFetch.mockResolvedValue(jsonResponse(scheme));
		const result = await fetchTranscoderScheme();
		expect(result).toEqual(scheme);
		expect(mockFetch).toHaveBeenCalledWith('/api/settings/transcoder/scheme', expect.any(Object));
	});

	it('returns null when backend returns 502 unreachable', async () => {
		mockFetch.mockResolvedValue({
			ok: false,
			status: 502,
			statusText: 'Bad Gateway',
			json: () => Promise.resolve({ detail: 'Transcoder service unreachable' })
		});
		const result = await fetchTranscoderScheme();
		expect(result).toBeNull();
	});

	it('rethrows non-502 errors', async () => {
		mockFetch.mockResolvedValue({
			ok: false,
			status: 500,
			statusText: 'Internal Server Error',
			json: () => Promise.resolve({ detail: 'boom' })
		});
		await expect(fetchTranscoderScheme()).rejects.toThrow(/boom/);
	});
});

describe('fetchTranscoderPresets', () => {
	it('GETs /api/settings/transcoder/presets', async () => {
		mockFetch.mockResolvedValue(jsonResponse({ presets: [{ slug: 'a', name: 'A', builtin: true, shared: {}, tiers: {}, scheme: 'nvidia', description: '' }] }));
		const result = await fetchTranscoderPresets();
		expect(result?.presets).toHaveLength(1);
		expect(mockFetch).toHaveBeenCalledWith('/api/settings/transcoder/presets', expect.any(Object));
	});

	it('returns null when backend returns 502 unreachable', async () => {
		mockFetch.mockResolvedValue({
			ok: false,
			status: 502,
			statusText: 'Bad Gateway',
			json: () => Promise.resolve({ detail: 'Transcoder service unreachable' })
		});
		const result = await fetchTranscoderPresets();
		expect(result).toBeNull();
	});

	it('rethrows non-502 errors', async () => {
		mockFetch.mockResolvedValue({
			ok: false,
			status: 500,
			statusText: 'Internal Server Error',
			json: () => Promise.resolve({ detail: 'db error' })
		});
		await expect(fetchTranscoderPresets()).rejects.toThrow(/db error/);
	});
});

describe('createCustomPreset', () => {
	it('POSTs the body to /api/settings/transcoder/presets', async () => {
		const created = {
			slug: 'my-anime', name: 'My Anime', scheme: 'nvidia',
			description: '', builtin: false, parent_slug: 'nvidia_balanced',
			shared: {}, tiers: { dvd: {}, bluray: {}, uhd: {} }
		};
		mockFetch.mockResolvedValue(jsonResponse(created));
		const body = {
			name: 'My Anime',
			parent_slug: 'nvidia_balanced',
			overrides: { shared: { audio_encoder: 'aac' }, tiers: {} }
		};
		const result = await createCustomPreset(body);
		expect(result.slug).toBe('my-anime');
		expect(mockFetch).toHaveBeenCalledWith(
			'/api/settings/transcoder/presets',
			expect.objectContaining({ method: 'POST', body: JSON.stringify(body) })
		);
	});
});
