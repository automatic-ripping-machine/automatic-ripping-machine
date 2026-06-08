import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderComponent, screen, cleanup } from '$lib/test-utils';
import Layout from '../+layout.svelte';
import { createRawSnippet } from 'svelte';

vi.mock('$app/stores', async () => {
	const { readable } = await import('svelte/store');
	return { page: readable({ url: { pathname: '/' }, params: {} }) };
});

vi.mock('$lib/stores/theme', async () => {
	const { writable } = await import('svelte/store');
	return { theme: writable('dark'), toggleTheme: vi.fn() };
});

vi.mock('$lib/stores/colorScheme', async () => {
	const { writable } = await import('svelte/store');
	return {
		colorScheme: writable('default'),
		schemeLocksMode: writable(false),
		loadThemesFromApi: vi.fn()
	};
});

vi.mock('$lib/stores/dashboard', async () => {
	const { writable } = await import('svelte/store');
	const store = writable({
		db_available: true, arm_online: true, active_jobs: [], system_info: null,
		drives_online: 0, drive_names: {}, notification_count: 0, ripping_enabled: true,
		transcoder_online: false, transcoder_stats: null, transcoder_system_stats: null,
		active_transcodes: [], system_stats: null, transcoder_info: null
	});
	return { dashboard: { ...store, start: vi.fn(), stop: vi.fn(), error: writable(null) } };
});

vi.mock('$lib/api/dashboard', () => ({
	setRippingEnabled: vi.fn(() => Promise.resolve())
}));

function childSnippet() {
	return createRawSnippet(() => ({
		render: () => '<p>Page Content</p>'
	}));
}

describe('Layout', () => {
	afterEach(() => cleanup());

	it('renders navigation links', () => {
		renderComponent(Layout, { props: { children: childSnippet() } });
		expect(screen.getByText('Dashboard')).toBeInTheDocument();
		expect(screen.getByText('Logs')).toBeInTheDocument();
		expect(screen.getByText('Files')).toBeInTheDocument();
		expect(screen.getByText('Settings')).toBeInTheDocument();
	});

	it('renders children content', () => {
		renderComponent(Layout, { props: { children: childSnippet() } });
		expect(screen.getByText('Page Content')).toBeInTheDocument();
	});

	it('renders ARM logo', () => {
		renderComponent(Layout, { props: { children: childSnippet() } });
		const logos = screen.getAllByAltText('ARM');
		expect(logos.length).toBeGreaterThanOrEqual(1);
	});

	it('topnav ripping count excludes transcoding jobs', async () => {
		const { dashboard } = await import('$lib/stores/dashboard');

		// Set active_jobs with one ripping and one transcoding job
		dashboard.update(() => ({
			db_available: true, arm_online: true,
			active_jobs: [
				{ job_id: 1, status: 'ripping', title: 'Movie A' },
				{ job_id: 2, status: 'transcoding', title: 'Movie B' },
			] as never[],
			system_info: null, drives_online: 1, drive_names: {},
			notification_count: 0, ripping_enabled: true,
			makemkv_key_valid: null, makemkv_key_checked_at: null,
			transcoder_online: false, transcoder_stats: null,
			transcoder_system_stats: null, active_transcodes: [],
			system_stats: null, transcoder_info: null
		}));

		renderComponent(Layout, { props: { children: childSnippet() } });

		// Should show "1 ripping", not "2 ripping"
		const rippingBadges = screen.getAllByText(/ripping/i);
		const rippingBadge = rippingBadges.find(el => el.textContent?.match(/^\d+ ripping$/));
		expect(rippingBadge?.textContent).toBe('1 ripping');
	});
});
