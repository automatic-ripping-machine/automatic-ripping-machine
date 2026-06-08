import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderComponent, screen, cleanup, waitFor } from '$lib/test-utils';
import DriveScanStep from './DriveScanStep.svelte';

function mockFetchJson(data: unknown) {
	vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve(data) })));
}

const sampleDrive = { drive_id: 1, name: 'Main Drive', mount: '/dev/sr0', maker: 'LG', model: 'WH16NS40', capabilities: ['CD', 'DVD', 'BD'] };

describe('DriveScanStep', () => {
	afterEach(() => { cleanup(); vi.restoreAllMocks(); });

	it('renders heading and no-drives message when empty', async () => {
		mockFetchJson([]);
		renderComponent(DriveScanStep);
		expect(screen.getByText('Optical Drives')).toBeInTheDocument();
		await waitFor(() => expect(screen.getByText('No optical drives detected')).toBeInTheDocument());
	});

	it('shows drive info and capability badges', async () => {
		mockFetchJson([sampleDrive]);
		renderComponent(DriveScanStep);
		await waitFor(() => {
			expect(screen.getByText('Main Drive')).toBeInTheDocument();
			expect(screen.getByText('LG WH16NS40')).toBeInTheDocument();
			expect(screen.getByText('CD')).toBeInTheDocument();
			expect(screen.getByText('DVD')).toBeInTheDocument();
			expect(screen.getByText('Blu-ray')).toBeInTheDocument();
		});
	});

	it('renders scan again button', async () => {
		mockFetchJson([]);
		renderComponent(DriveScanStep);
		await waitFor(() => expect(screen.getByText('Scan Again')).toBeInTheDocument());
	});

	it('shows error on fetch failure', async () => {
		vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({ ok: false })));
		renderComponent(DriveScanStep);
		await waitFor(() => expect(screen.getByText('Failed to load drives')).toBeInTheDocument());
	});
});
