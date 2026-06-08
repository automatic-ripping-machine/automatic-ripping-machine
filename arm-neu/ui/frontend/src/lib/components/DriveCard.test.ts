import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderComponent, screen, fireEvent, cleanup } from '$lib/test-utils';
import DriveCard from './DriveCard.svelte';
import type { DriveSchema as Drive } from '$lib/types/api.gen';
vi.mock('$lib/api/drives', () => ({
	updateDrive: vi.fn(() => Promise.resolve()),
	scanDrive: vi.fn(() => Promise.resolve()),
	deleteDrive: vi.fn(() => Promise.resolve()),
	ejectDrive: vi.fn(() => Promise.resolve())
}));

function createDrive(overrides: Partial<Drive> = {}): Drive {
	return {
		drive_id: 1, name: 'Main Drive', mount: '/dev/sr0',
		job_id_current: null, job_id_previous: null, description: null, drive_mode: null,
		maker: 'LG', model: 'WH16NS40', serial: null, connection: null,
		capabilities: ['CD', 'DVD', 'BD'],
		firmware: null, stale: false,
		uhd_capable: false, current_job: null, rip_speed: null,
		prescan_cache_mb: null, prescan_timeout: null, prescan_retries: null, disc_enum_timeout: null,
		...overrides
	};
}

function renderDrive(overrides: Partial<Drive> = {}) {
	return renderComponent(DriveCard, { props: { drive: createDrive(overrides) } });
}

describe('DriveCard', () => {
	afterEach(() => cleanup());

	describe('rendering', () => {
		it('renders drive name, maker/model, capabilities, and action bar', () => {
			renderDrive();
			expect(screen.getByText('Main Drive')).toBeInTheDocument();
			expect(screen.getByText('Idle')).toBeInTheDocument();
			expect(screen.getByText('CD')).toBeInTheDocument();
			expect(screen.getByText('DVD')).toBeInTheDocument();
			expect(screen.getByText('Blu-ray')).toBeInTheDocument();
			// Action bar buttons
			expect(screen.getByText('Eject')).toBeInTheDocument();
			expect(screen.getByText('Insert')).toBeInTheDocument();
			expect(screen.getByText('Scan')).toBeInTheDocument();
			expect(screen.queryByText('Remove')).not.toBeInTheDocument();
		});

		it('shows drive info fields when available', () => {
			renderDrive({ connection: 'USB 3.0', firmware: '1.03' });
			expect(screen.getByText(/USB 3\.0/)).toBeInTheDocument();
			expect(screen.getByText(/FW 1\.03/)).toBeInTheDocument();
		});

		it('shows 4K tag for Blu-ray drives', () => {
			renderDrive({ capabilities: ['CD', 'DVD', 'BD'] });
			expect(screen.getByText('4K')).toBeInTheDocument();
		});

		it('hides 4K tag for non-Blu-ray drives', () => {
			renderDrive({ capabilities: ['CD', 'DVD'] });
			expect(screen.queryByText('4K')).not.toBeInTheDocument();
		});

		it('falls back to mount path when no name', () => {
			renderDrive({ name: null });
			const matches = screen.getAllByText('/dev/sr0');
			expect(matches.find(el => el.tagName === 'H3')).toBeDefined();
		});

		it('falls back to Drive ID when no name or mount', () => {
			renderDrive({ name: null, mount: null });
			expect(screen.getByText('Drive 1')).toBeInTheDocument();
		});

		it('shows Stale badge and Remove button for stale drives', () => {
			renderDrive({ stale: true });
			expect(screen.getByText('Stale')).toBeInTheDocument();
			expect(screen.getByText('Remove')).toBeInTheDocument();
		});
	});

	describe('prescan overrides badge', () => {
		it('shows custom badge when prescan overrides are set', () => {
			renderDrive({ prescan_cache_mb: 64, prescan_timeout: 600, connection: 'USB' });
			expect(screen.getByText('2 custom')).toBeInTheDocument();
		});

		it('hides custom badge when no prescan overrides', () => {
			renderDrive({ connection: 'USB' });
			expect(screen.queryByText(/custom/)).not.toBeInTheDocument();
		});
	});

	describe('prescan settings panel', () => {
		it('shows prescan inputs in settings panel', async () => {
			renderDrive();
			await fireEvent.click(screen.getByTitle('Drive settings'));
			expect(screen.getByText('Drive Settings')).toBeInTheDocument();
			expect(screen.getByText('Pre-scan Cache')).toBeInTheDocument();
			expect(screen.getByText('Pre-scan Timeout')).toBeInTheDocument();
			expect(screen.getByText('Pre-scan Retries')).toBeInTheDocument();
			expect(screen.getByText('Enum Timeout')).toBeInTheDocument();
		});

		it('shows tooltips for prescan fields', async () => {
			renderDrive();
			await fireEvent.click(screen.getByTitle('Drive settings'));
			expect(screen.getByText(/Community recommends 64-128/)).toBeInTheDocument();
			expect(screen.getByText(/Community recommends 600/)).toBeInTheDocument();
			expect(screen.getByText(/Community recommends 3-5/)).toBeInTheDocument();
			expect(screen.getByText(/Community recommends 120/)).toBeInTheDocument();
		});

		it('populates prescan inputs from drive values', async () => {
			renderDrive({ prescan_cache_mb: 128, prescan_retries: 5 });
			await fireEvent.click(screen.getByTitle('Drive settings'));
			const cacheInput = screen.getByLabelText(/Pre-scan Cache/) as HTMLInputElement;
			const retriesInput = screen.getByLabelText(/Pre-scan Retries/) as HTMLInputElement;
			expect(cacheInput.value).toBe('128');
			expect(retriesInput.value).toBe('5');
		});

		it('saves prescan field on blur', async () => {
			const { updateDrive } = await import('$lib/api/drives');
			renderDrive();
			await fireEvent.click(screen.getByTitle('Drive settings'));
			const cacheInput = screen.getByLabelText(/Pre-scan Cache/) as HTMLInputElement;
			await fireEvent.input(cacheInput, { target: { value: '64' } });
			await fireEvent.blur(cacheInput);
			expect(updateDrive).toHaveBeenCalledWith(1, { prescan_cache_mb: 64 });
		});
	});

	describe('interactions', () => {
		it('enters and exits edit mode via Rename button', async () => {
			renderDrive();
			await fireEvent.click(screen.getByText('Rename'));
			expect(screen.getByDisplayValue('Main Drive')).toBeInTheDocument();
			expect(screen.getByText('Save')).toBeInTheDocument();
			await fireEvent.click(screen.getByText('Cancel'));
			expect(screen.getByText('Rename')).toBeInTheDocument();
		});
	});

	describe('skeleton', () => {
		it('renders a SkeletonCard when drive prop is omitted', () => {
			const { container } = renderComponent(DriveCard, { props: {} });
			expect(container.querySelector('[aria-busy="true"]')).not.toBeNull();
		});
	});
});
