import { describe, it, expect } from 'vitest';
import { get } from 'svelte/store';
import { COLOR_SCHEMES, colorScheme, schemeLocksMode } from '../stores/colorScheme';

const DARK_ONLY_IDS = [
	'glass', 'cinema', 'gaming', 'royale', 'lcars',
	'tactical', 'craft', 'terminal', 'blockbuster', 'hollywood-video-v2'
];

describe('COLOR_SCHEMES', () => {
	it('every scheme has required fields', () => {
		for (const scheme of COLOR_SCHEMES) {
			expect(scheme.id).toBeTypeOf('string');
			expect(scheme.label).toBeTypeOf('string');
			expect(scheme.swatch).toBeTypeOf('string');
			expect(scheme.tokens).toBeTypeOf('object');
			expect(Object.keys(scheme.tokens).length).toBeGreaterThan(0);
		}
	});

	it('mode values are only light, dark, or undefined', () => {
		for (const scheme of COLOR_SCHEMES) {
			if (scheme.mode !== undefined) {
				expect(['light', 'dark']).toContain(scheme.mode);
			}
		}
	});

	it('all dark-only themes have mode: dark', () => {
		for (const id of DARK_ONLY_IDS) {
			const scheme = COLOR_SCHEMES.find((s) => s.id === id);
			expect(scheme, `scheme '${id}' should exist`).toBeDefined();
			expect(scheme!.mode, `scheme '${id}' should be dark`).toBe('dark');
		}
	});

	it('no schemes have a forceDark property', () => {
		for (const scheme of COLOR_SCHEMES) {
			expect((scheme as unknown as Record<string, unknown>).forceDark).toBeUndefined();
		}
	});

	it('has at least one scheme without mode (user-selectable theme)', () => {
		const unlocked = COLOR_SCHEMES.filter((s) => s.mode === undefined);
		expect(unlocked.length).toBeGreaterThan(0);
	});

	it('every id is unique', () => {
		const ids = COLOR_SCHEMES.map((s) => s.id);
		expect(new Set(ids).size).toBe(ids.length);
	});

	it('every scheme includes a --radius token', () => {
		for (const scheme of COLOR_SCHEMES) {
			expect(scheme.tokens['--radius'], `scheme '${scheme.id}' should have --radius`).toBeDefined();
		}
	});

	it('--radius values are valid CSS lengths', () => {
		const validPattern = /^(\d+(\.\d+)?(rem|px|em)|0)$/;
		for (const scheme of COLOR_SCHEMES) {
			const radius = scheme.tokens['--radius'];
			expect(radius, `scheme '${scheme.id}' --radius '${radius}' should be a valid CSS length`).toMatch(validPattern);
		}
	});
});

describe('schemeLocksMode', () => {
	it('returns true for a scheme with mode set', () => {
		colorScheme.set('glass');
		expect(get(schemeLocksMode)).toBe(true);
	});

	it('returns false for a scheme without mode', () => {
		colorScheme.set('blue');
		expect(get(schemeLocksMode)).toBe(false);
	});

	it('returns false for an unknown scheme id', () => {
		colorScheme.set('nonexistent');
		expect(get(schemeLocksMode)).toBe(false);
	});
});
