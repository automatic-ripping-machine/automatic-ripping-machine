import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderComponent, screen, cleanup, waitFor } from '$lib/test-utils';
import StructuredLogViewer from './StructuredLogViewer.svelte';

const mockEntries = [
	{ level: 'error', event: 'Rip failed', timestamp: '2025-06-15T12:00:03Z', logger: 'arm.ripper', job_id: 1, label: 'DISC' },
	{ level: 'info', event: 'Job started', timestamp: '2025-06-15T12:00:01Z', logger: 'arm.main', job_id: 1, label: null },
	{ level: 'warning', event: 'Disc dirty', timestamp: '2025-06-15T12:00:02Z', logger: 'arm.ripper', job_id: 1, label: null }
];

function createFetchFn(entries = mockEntries) {
	return vi.fn(() => Promise.resolve({ entries }));
}

describe('StructuredLogViewer', () => {
	afterEach(() => cleanup());

	describe('rendering', () => {
		it('shows loading state initially', () => {
			const fetchFn = vi.fn(() => new Promise(() => {}));
			renderComponent(StructuredLogViewer, {
				props: { filename: 'test.log', fetchFn, autoRefresh: false }
			});
			expect(screen.getByText('Loading...')).toBeInTheDocument();
		});

		it('renders table with entries after fetch', async () => {
			renderComponent(StructuredLogViewer, {
				props: { filename: 'test.log', fetchFn: createFetchFn(), autoRefresh: false }
			});
			await waitFor(() => {
				expect(screen.getByText('Rip failed')).toBeInTheDocument();
				expect(screen.getByText('Job started')).toBeInTheDocument();
				expect(screen.getByText('Disc dirty')).toBeInTheDocument();
			});
		});

		it('shows entry count', async () => {
			renderComponent(StructuredLogViewer, {
				props: { filename: 'test.log', fetchFn: createFetchFn(), autoRefresh: false }
			});
			await waitFor(() => {
				expect(screen.getByText('3 entries')).toBeInTheDocument();
			});
		});

		it('renders error message on fetch failure', async () => {
			const fetchFn = vi.fn(() => Promise.reject(new Error('Connection failed')));
			renderComponent(StructuredLogViewer, {
				props: { filename: 'test.log', fetchFn, autoRefresh: false }
			});
			await waitFor(() => {
				expect(screen.getByText('Connection failed')).toBeInTheDocument();
			});
		});

		it('renders level filter dropdown', () => {
			renderComponent(StructuredLogViewer, {
				props: { filename: 'test.log', fetchFn: createFetchFn(), autoRefresh: false }
			});
			expect(screen.getByText('All Levels')).toBeInTheDocument();
		});

		it('renders search input', () => {
			renderComponent(StructuredLogViewer, {
				props: { filename: 'test.log', fetchFn: createFetchFn(), autoRefresh: false }
			});
			expect(screen.getByPlaceholderText('Search log events...')).toBeInTheDocument();
		});
	});

	describe('interactions', () => {
		it('renders sortable column headers', async () => {
			renderComponent(StructuredLogViewer, {
				props: { filename: 'test.log', fetchFn: createFetchFn(), autoRefresh: false }
			});
			await waitFor(() => {
				expect(screen.getByText('Rip failed')).toBeInTheDocument();
			});
			expect(screen.getByText('Time')).toBeInTheDocument();
			expect(screen.getByText('Level')).toBeInTheDocument();
			expect(screen.getByText('Logger')).toBeInTheDocument();
			expect(screen.getByText('Event')).toBeInTheDocument();
		});
	});
});
