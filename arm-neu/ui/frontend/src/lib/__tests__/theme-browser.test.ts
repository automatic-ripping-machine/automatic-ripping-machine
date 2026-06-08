import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock localStorage
const localStorageMock = {
	store: {} as Record<string, string>,
	getItem: vi.fn((key: string) => localStorageMock.store[key] ?? null),
	setItem: vi.fn((key: string, value: string) => { localStorageMock.store[key] = value; }),
	removeItem: vi.fn(),
	clear: vi.fn()
};
vi.stubGlobal('localStorage', localStorageMock);

// Mock browser = true so subscription fires
vi.mock('$app/environment', () => ({ browser: true }));

beforeEach(() => {
	localStorageMock.store = {};
	vi.clearAllMocks();
});

describe('theme store (browser)', () => {
	it('persists theme changes to localStorage', async () => {
		const { theme, toggleTheme } = await import('../stores/theme');
		const { get } = await import('svelte/store');

		// Toggle to light
		theme.set('dark');
		toggleTheme();
		expect(get(theme)).toBe('light');
		expect(localStorageMock.setItem).toHaveBeenCalledWith('theme', 'light');
	});

	it('toggles dark class on documentElement', async () => {
		const { theme } = await import('../stores/theme');

		theme.set('dark');
		expect(document.documentElement.classList.contains('dark')).toBe(true);

		theme.set('light');
		expect(document.documentElement.classList.contains('dark')).toBe(false);
	});
});
