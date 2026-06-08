import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderComponent, screen, cleanup } from '$lib/test-utils';
import LogDetailPage from '../[filename]/+page.svelte';

vi.mock('$app/stores', async () => {
	const { readable } = await import('svelte/store');
	return {
		page: readable({ params: { filename: 'job_001.log' } })
	};
});

vi.mock('$lib/api/logs', () => ({
	fetchStructuredLogContent: vi.fn(() => Promise.resolve({ entries: [] }))
}));

describe('Log Detail Page', () => {
	afterEach(() => cleanup());

	it('renders the filename as heading', () => {
		renderComponent(LogDetailPage);
		expect(screen.getByText('job_001.log')).toBeInTheDocument();
	});

	it('renders Tail and Full mode buttons', () => {
		renderComponent(LogDetailPage);
		expect(screen.getByText('Tail')).toBeInTheDocument();
		expect(screen.getByText('Full')).toBeInTheDocument();
	});

	it('renders back link to /logs', () => {
		renderComponent(LogDetailPage);
		const link = screen.getByText('Logs');
		expect(link.closest('a')).toHaveAttribute('href', '/logs');
	});
});
