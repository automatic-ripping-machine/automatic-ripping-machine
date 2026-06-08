import { describe, it, expect } from 'vitest';
import { EVENT_KEYS, isCatalogField } from '$lib/types/notifications';

describe('notification types', () => {
	it('exposes the six closed event keys', () => {
		expect(EVENT_KEYS).toEqual([
			'job.started',
			'job.rip_complete',
			'job.transcode_complete',
			'job.failed',
			'job.manual_wait_required',
			'job.duplicate_detected'
		]);
	});

	it('isCatalogField accepts a well-formed field', () => {
		expect(isCatalogField({ key: 'tts', label: 'TTS', type: 'bool', private: false, required: false })).toBe(true);
	});

	it('isCatalogField rejects a missing key', () => {
		expect(isCatalogField({ label: 'TTS', type: 'bool' })).toBe(false);
	});
});
