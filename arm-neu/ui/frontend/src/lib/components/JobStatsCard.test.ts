import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderComponent, cleanup } from '$lib/test-utils';
import JobStatsCard from './JobStatsCard.svelte';

vi.mock('$lib/api/system', () => ({
	fetchJobStats: vi.fn(() => new Promise(() => {})) // never resolves — simulates loading
}));

describe('JobStatsCard', () => {
	afterEach(() => cleanup());

	it('displays em-dash placeholders while stats are loading', () => {
		const { container } = renderComponent(JobStatsCard, { props: {} });
		expect(container.textContent).toContain('—');
	});

	it('renders Total Rips label while loading', () => {
		const { container } = renderComponent(JobStatsCard, { props: {} });
		expect(container.textContent).toContain('Total Rips');
	});

	it('renders Success label while loading', () => {
		const { container } = renderComponent(JobStatsCard, { props: {} });
		expect(container.textContent).toContain('Success');
	});

	it('renders Failed label while loading', () => {
		const { container } = renderComponent(JobStatsCard, { props: {} });
		expect(container.textContent).toContain('Failed');
	});

	it('renders Active label while loading', () => {
		const { container } = renderComponent(JobStatsCard, { props: {} });
		expect(container.textContent).toContain('Active');
	});
});
