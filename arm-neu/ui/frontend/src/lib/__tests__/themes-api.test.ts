import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

function jsonResponse(data: unknown, ok = true, status = 200) {
	return { ok, status, statusText: ok ? 'OK' : 'Error', json: () => Promise.resolve(data) };
}

import { fetchThemes, fetchTheme, uploadTheme, fetchThemeCss, deleteTheme } from '../api/themes';

beforeEach(() => mockFetch.mockReset());

describe('fetchThemes', () => {
	it('calls /api/themes', async () => {
		mockFetch.mockResolvedValue(jsonResponse([{ id: 'default', label: 'Default' }]));
		const result = await fetchThemes();
		expect(result).toEqual([{ id: 'default', label: 'Default' }]);
	});
});

describe('fetchTheme', () => {
	it('calls /api/themes/:id', async () => {
		mockFetch.mockResolvedValue(jsonResponse({ id: 'dark', css: ':root{}' }));
		const result = await fetchTheme('dark');
		expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining('/api/themes/dark'), expect.any(Object));
		expect(result).toEqual({ id: 'dark', css: ':root{}' });
	});
});

describe('uploadTheme', () => {
	it('POSTs FormData to /api/themes', async () => {
		mockFetch.mockResolvedValue(jsonResponse({ id: 'custom', css: '' }));
		const file = new File(['{}'], 'theme.json', { type: 'application/json' });
		await uploadTheme(file, 'body{}');
		expect(mockFetch).toHaveBeenCalledWith('/api/themes', expect.objectContaining({ method: 'POST' }));
	});
});

describe('fetchThemeCss', () => {
	it('returns CSS text', async () => {
		mockFetch.mockResolvedValue({ ok: true, text: () => Promise.resolve(':root{--a:1}') });
		const css = await fetchThemeCss('dark');
		expect(css).toBe(':root{--a:1}');
	});

	it('throws on non-ok response', async () => {
		mockFetch.mockResolvedValue({ ok: false });
		await expect(fetchThemeCss('missing')).rejects.toThrow("No CSS for theme 'missing'");
	});
});

describe('deleteTheme', () => {
	it('DELETEs /api/themes/:id', async () => {
		mockFetch.mockResolvedValue(jsonResponse(null));
		await deleteTheme('custom');
		expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining('/api/themes/custom'), expect.objectContaining({ method: 'DELETE' }));
	});
});
