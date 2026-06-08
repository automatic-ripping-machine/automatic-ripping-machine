import { describe, it, expect, vi } from 'vitest';
import { get } from 'svelte/store';

vi.mock('$app/environment', () => ({ browser: false }));

import { theme, toggleTheme } from '../stores/theme';

describe('theme store', () => {
	it('initial value is dark when browser is false', () => {
		expect(get(theme)).toBe('dark');
	});

	it('toggleTheme flips dark to light', () => {
		theme.set('dark');
		toggleTheme();
		expect(get(theme)).toBe('light');
	});

	it('toggleTheme flips light to dark', () => {
		theme.set('light');
		toggleTheme();
		expect(get(theme)).toBe('dark');
	});

	it('toggleTheme round-trips correctly', () => {
		theme.set('dark');
		toggleTheme();
		toggleTheme();
		expect(get(theme)).toBe('dark');
	});
});

describe('colorScheme - theme fetch dedup', () => {
	it('concurrent loadThemeCss calls for the same id only fetch once', async () => {
		// Simulate the real-world race: loadThemesFromApi() and the subscribe handler
		// both call loadThemeCss(id) at nearly the same time. Without an in-flight guard
		// both see cssCache.has(id) === false and issue separate network requests.
		const mockFetch = vi.fn((url: string) => {
			if (typeof url === 'string' && /\/api\/themes\/\w/.exec(url)) {
				return Promise.resolve({
					ok: true,
					json: () =>
						Promise.resolve({
							id: 'blue',
							label: 'Blue',
							swatch: '#3b82f6',
							tokens: {},
							css: 'body{}'
						})
				});
			}
			return Promise.resolve({
				ok: true,
				json: () =>
					Promise.resolve([{ id: 'blue', label: 'Blue', swatch: '#3b82f6', tokens: {} }])
			});
		});
		vi.stubGlobal('fetch', mockFetch);

		try {
			const { loadThemeCss } = await import('$lib/stores/colorScheme');

			// Fire two concurrent calls for the same id - mirroring the subscribe race
			await Promise.all([loadThemeCss('blue'), loadThemeCss('blue')]);

			const themeFetchCalls = mockFetch.mock.calls.filter(
				([url]) => typeof url === 'string' && /\/api\/themes\/\w/.test(url)
			);
			expect(themeFetchCalls.length).toBe(1);
		} finally {
			vi.unstubAllGlobals();
		}
	});

	it('writes fetched theme CSS to localStorage for later reuse', async () => {
		vi.resetModules();
		const mockFetch = vi.fn((url: string) => {
			if (typeof url === 'string' && /\/api\/themes\/\w/.exec(url)) {
				return Promise.resolve({
					ok: true,
					json: () =>
						Promise.resolve({
							id: 'blue',
							label: 'Blue',
							swatch: '#3b82f6',
							tokens: {},
							css: 'body { background: blue; }'
						})
				});
			}
			return Promise.resolve({ ok: true, json: () => Promise.resolve([]) });
		});
		vi.stubGlobal('fetch', mockFetch);
		const setItem = vi.spyOn(Storage.prototype, 'setItem');

		try {
			const mod = await import('$lib/stores/colorScheme');
			await mod.loadThemeCss('blue');

			expect(setItem).toHaveBeenCalledWith(
				'theme-cache-v1-blue',
				'body { background: blue; }'
			);
		} finally {
			vi.unstubAllGlobals();
		}
	});
});
