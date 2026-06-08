import { describe, it, expect, afterEach } from 'vitest';
import { renderComponent, cleanup } from '$lib/test-utils';
import JobStatsPanel from './JobStatsPanel.svelte';
import type { JobStats } from '$lib/api/jobs';

const noop = () => {};

const fullStats: JobStats = {
	total: 10,
	active: 2,
	success: 7,
	fail: 1,
	waiting: 0
};

describe('JobStatsPanel', () => {
	afterEach(() => cleanup());

	describe('skeleton state', () => {
		it('displays em-dash placeholder when stats prop is omitted', () => {
			const { container } = renderComponent(JobStatsPanel, {
				props: { statusFilter: '', onfilter: noop }
			});
			expect(container.textContent).toContain('—');
		});

		it('renders all stat labels when stats is undefined', () => {
			const { container } = renderComponent(JobStatsPanel, {
				props: { statusFilter: '', onfilter: noop }
			});
			expect(container.textContent).toContain('Total');
			expect(container.textContent).toContain('Active');
			expect(container.textContent).toContain('Success');
			expect(container.textContent).toContain('Failed');
			expect(container.textContent).toContain('Waiting');
		});
	});

	describe('with stats', () => {
		it('renders stat numbers when stats are provided', () => {
			const { container } = renderComponent(JobStatsPanel, {
				props: { stats: fullStats, statusFilter: '', onfilter: noop }
			});
			expect(container.textContent).toContain('10');
			expect(container.textContent).toContain('7');
			expect(container.textContent).toContain('1');
		});

		it('does not render em-dash when stats are provided', () => {
			const { container } = renderComponent(JobStatsPanel, {
				props: { stats: fullStats, statusFilter: '', onfilter: noop }
			});
			expect(container.textContent).not.toContain('—');
		});
	});
});
