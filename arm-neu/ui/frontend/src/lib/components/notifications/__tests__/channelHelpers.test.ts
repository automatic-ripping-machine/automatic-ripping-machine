import { describe, it, expect } from 'vitest';
import { channelStatus, relativeTime, typeLabel, isReady, missingRequirements } from '../channelHelpers';
import type { Channel, CatalogService } from '$lib/types/notifications';

const base: Channel = {
	id: 1, type: 'apprise', name: 'X', enabled: true,
	config: { type: 'apprise', url: 'discord://a/b' },
	subscribed_events: ['job.started'], templates: {},
	last_fired_at: null, last_success_at: null, last_error: null
};

describe('channelStatus', () => {
	it('returns off when disabled', () => {
		expect(channelStatus({ ...base, enabled: false })).toBe('off');
	});
	it('returns error when last_error set and enabled', () => {
		expect(channelStatus({ ...base, last_error: 'HTTP 500' })).toBe('error');
	});
	it('returns ok otherwise', () => {
		expect(channelStatus(base)).toBe('ok');
	});
});

describe('relativeTime', () => {
	it('returns "never" for null', () => {
		expect(relativeTime(null)).toBe('never');
	});
	it('formats minutes ago', () => {
		const tenMinAgo = new Date(Date.now() - 10 * 60 * 1000).toISOString();
		expect(relativeTime(tenMinAgo)).toMatch(/10m ago/);
	});
});

describe('typeLabel', () => {
	it('maps types to human labels', () => {
		expect(typeLabel('apprise')).toBe('Service (Apprise)');
		expect(typeLabel('webhook')).toBe('Webhook');
		expect(typeLabel('bash')).toBe('Bash script');
	});
});

const svc: CatalogService = {
	id: 'discord', name: 'Discord', docs_url: '', url_scheme: 'discord',
	required_fields: [{ key: 'webhook_id', label: 'Webhook ID', type: 'string', private: false, required: true }],
	advanced_fields: []
};

describe('missingRequirements', () => {
	it('flags blank label, unfilled required field, and no events', () => {
		const m = missingRequirements({
			type: 'apprise', name: '  ', config: {}, events: [], service: svc
		});
		expect(m).toContain('channel label');
		expect(m).toContain('required fields');
		expect(m).toContain('at least one event');
	});

	it('is empty when all requirements are met', () => {
		const m = missingRequirements({
			type: 'apprise', name: 'My Discord',
			config: { webhook_id: '123' }, events: ['job.started'], service: svc
		});
		expect(m).toEqual([]);
	});

	it('webhook requires a url', () => {
		expect(missingRequirements({ type: 'webhook', name: 'H', config: {}, events: ['job.started'], service: null }))
			.toContain('required fields');
		expect(missingRequirements({ type: 'webhook', name: 'H', config: { url: 'https://x' }, events: ['job.started'], service: null }))
			.toEqual([]);
	});
});

describe('isReady', () => {
	it('true only when nothing missing', () => {
		expect(isReady({ type: 'webhook', name: 'H', config: { url: 'https://x' }, events: ['job.started'], service: null })).toBe(true);
		expect(isReady({ type: 'webhook', name: '', config: {}, events: [], service: null })).toBe(false);
	});
});
