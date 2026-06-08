import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('$lib/api/client', () => ({
	apiFetch: vi.fn().mockResolvedValue({})
}));

import { apiFetch } from '$lib/api/client';
import {
	fetchSettings, saveArmConfig, saveTranscoderConfig,
	testMetadataKey, testTranscoderConnection, testTranscoderWebhook, fetchSystemInfo
} from '../api/settings';

const mockApiFetch = vi.mocked(apiFetch);

beforeEach(() => {
	mockApiFetch.mockClear();
});

describe('fetchSettings', () => {
	it('calls /api/settings', async () => {
		await fetchSettings();
		expect(mockApiFetch).toHaveBeenCalledWith('/api/settings');
	});
});

describe('saveArmConfig', () => {
	it('PUTs config wrapped in { config }', async () => {
		const config = { RIPMETHOD: 'mkv' };
		await saveArmConfig(config);
		expect(mockApiFetch).toHaveBeenCalledWith('/api/settings/arm', {
			method: 'PUT',
			body: JSON.stringify({ config })
		});
	});
});

describe('saveTranscoderConfig', () => {
	it('PATCHes config directly', async () => {
		const config = { enabled: true };
		await saveTranscoderConfig(config);
		expect(mockApiFetch).toHaveBeenCalledWith('/api/settings/transcoder', {
			method: 'PATCH',
			body: JSON.stringify(config)
		});
	});
});

describe('testMetadataKey', () => {
	it('GETs /api/settings/test-metadata', async () => {
		await testMetadataKey();
		expect(mockApiFetch).toHaveBeenCalledWith('/api/settings/test-metadata');
	});
});

describe('testTranscoderConnection', () => {
	it('POSTs to test-connection', async () => {
		await testTranscoderConnection();
		expect(mockApiFetch).toHaveBeenCalledWith('/api/settings/transcoder/test-connection', {
			method: 'POST'
		});
	});
});

describe('testTranscoderWebhook', () => {
	it('POSTs with webhook_secret', async () => {
		await testTranscoderWebhook('my-secret');
		expect(mockApiFetch).toHaveBeenCalledWith('/api/settings/transcoder/test-webhook', {
			method: 'POST',
			body: JSON.stringify({ webhook_secret: 'my-secret' })
		});
	});
});

describe('fetchSystemInfo', () => {
	it('calls /api/settings/system-info', async () => {
		await fetchSystemInfo();
		expect(mockApiFetch).toHaveBeenCalledWith('/api/settings/system-info');
	});
});
