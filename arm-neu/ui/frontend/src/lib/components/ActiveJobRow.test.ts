import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderComponent, screen, cleanup } from '$lib/test-utils';
import ActiveJobRow from './ActiveJobRow.svelte';
import { createJob } from './__fixtures__/job';

describe('ActiveJobRow', () => {
	beforeEach(() => {
		vi.useFakeTimers();
		vi.setSystemTime(new Date('2025-06-15T12:00:00Z'));
	});

	afterEach(() => {
		cleanup();
		vi.useRealTimers();
	});

	describe('rendering', () => {
		it('renders job title', () => {
			renderComponent(ActiveJobRow, { props: { job: createJob() } });
			expect(screen.getByText('Test Movie')).toBeInTheDocument();
		});

		it('renders Untitled when no title or label', () => {
			renderComponent(ActiveJobRow, {
				props: { job: createJob({ title: null, label: null }) }
			});
			expect(screen.getAllByText('Untitled').length).toBeGreaterThan(0);
		});

		it('renders status badge', () => {
			renderComponent(ActiveJobRow, {
				props: { job: createJob({ status: 'success' }) }
			});
			expect(screen.getAllByText('Success').length).toBeGreaterThan(0);
		});

		it('renders year when present', () => {
			renderComponent(ActiveJobRow, { props: { job: createJob() } });
			expect(screen.getByText('2024')).toBeInTheDocument();
		});
	});

	describe('props', () => {
		it('renders drive name from driveNames map', () => {
			renderComponent(ActiveJobRow, {
				props: {
					job: createJob({ devpath: '/dev/sr0' }),
					driveNames: { '/dev/sr0': 'Main Drive' }
				}
			});
			expect(screen.getAllByText('Main Drive').length).toBeGreaterThan(0);
		});

		it('falls back to devpath when no drive name', () => {
			renderComponent(ActiveJobRow, {
				props: {
					job: createJob({ devpath: '/dev/sr1' }),
					driveNames: {}
				}
			});
			expect(screen.getAllByText('/dev/sr1').length).toBeGreaterThan(0);
		});

		it('shows indeterminate bar when active with no progress', () => {
			const { container } = renderComponent(ActiveJobRow, {
				props: { job: createJob({ status: 'ripping' }) }
			});
			expect(container.querySelector('.animate-indeterminate')).toBeInTheDocument();
		});
	});

	describe('skeleton', () => {
		it('renders skeleton placeholder when job prop is omitted', () => {
			const { container } = renderComponent(ActiveJobRow, { props: {} });
			const placeholder = container.querySelector('[aria-busy="true"], [data-variant="line"]');
			expect(placeholder).not.toBeNull();
		});
	});
});
