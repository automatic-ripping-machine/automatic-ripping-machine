import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderComponent, screen, cleanup, waitFor } from '$lib/test-utils';
import SettingsReviewStep from './SettingsReviewStep.svelte';

const mockConfig = {
	arm_config: {
		RAW_PATH: '/home/arm/media/raw/',
		COMPLETED_PATH: '/home/arm/media/completed/',
		TRANSCODE_PATH: '/home/arm/media/transcode/',
		RIPMETHOD: 'mkv',
		METADATA_PROVIDER: 'omdb'
	}
};

function stubSettings(data = mockConfig) {
	vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve(data) })));
}

describe('SettingsReviewStep', () => {
	afterEach(() => { cleanup(); vi.restoreAllMocks(); });

	it('renders heading and config values', async () => {
		stubSettings();
		renderComponent(SettingsReviewStep);
		expect(screen.getByText('Review Settings')).toBeInTheDocument();
		await waitFor(() => {
			expect(screen.getByText('/home/arm/media/raw/')).toBeInTheDocument();
			expect(screen.getByText('/home/arm/media/completed/')).toBeInTheDocument();
			expect(screen.getByText('mkv')).toBeInTheDocument();
			expect(screen.getByText('omdb')).toBeInTheDocument();
		});
	});

	it('shows edit settings link', async () => {
		stubSettings();
		renderComponent(SettingsReviewStep);
		await waitFor(() => {
			const link = screen.getByText(/Edit all settings/);
			expect(link.closest('a')).toHaveAttribute('href', '/settings');
		});
	});

	it('shows error when settings fail to load', async () => {
		vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('fail'))));
		renderComponent(SettingsReviewStep);
		await waitFor(() => expect(screen.getByText('Could not load settings.')).toBeInTheDocument());
	});
});
