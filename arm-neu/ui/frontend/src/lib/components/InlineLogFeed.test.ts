import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderComponent, screen, fireEvent, cleanup, waitFor } from '$lib/test-utils';
import InlineLogFeed from './InlineLogFeed.svelte';

const mockEntries = [
	{ level: 'error', event: 'Something failed', timestamp: '2025-06-15T12:00:01Z' },
	{ level: 'warning', event: 'Disk space low', timestamp: '2025-06-15T12:00:02Z' },
	{ level: 'info', event: 'Job started', timestamp: '2025-06-15T12:00:03Z' }
];

function createFetchFn(entries = mockEntries) {
	return vi.fn(() => Promise.resolve({ entries }));
}

describe('InlineLogFeed', () => {
	afterEach(() => cleanup());

	describe('rendering', () => {
		it('renders title and entry count after loading', async () => {
			renderComponent(InlineLogFeed, {
				props: { logfile: 'test.log', fetchFn: createFetchFn(), autoRefresh: false }
			});
			await waitFor(() => {
				expect(screen.getByText('Recent Log')).toBeInTheDocument();
				expect(screen.getByText('3 entries')).toBeInTheDocument();
			});
		});

		it('renders custom title', async () => {
			renderComponent(InlineLogFeed, {
				props: { logfile: 'test.log', fetchFn: createFetchFn(), autoRefresh: false, title: 'Job Log' }
			});
			await waitFor(() => {
				expect(screen.getByText('Job Log')).toBeInTheDocument();
			});
		});

		it('shows error count badge', async () => {
			renderComponent(InlineLogFeed, {
				props: { logfile: 'test.log', fetchFn: createFetchFn(), autoRefresh: false }
			});
			await waitFor(() => {
				expect(screen.getByText('1 error')).toBeInTheDocument();
			});
		});

		it('shows warning count badge', async () => {
			renderComponent(InlineLogFeed, {
				props: { logfile: 'test.log', fetchFn: createFetchFn(), autoRefresh: false }
			});
			await waitFor(() => {
				expect(screen.getByText('1 warning')).toBeInTheDocument();
			});
		});

		it('renders nothing when entries are empty', async () => {
			const { container } = renderComponent(InlineLogFeed, {
				props: { logfile: 'test.log', fetchFn: createFetchFn([]), autoRefresh: false }
			});
			await waitFor(() => {
				expect(container.querySelector('.rounded-lg')).toBeNull();
			});
		});

		it('shows error message on fetch failure', async () => {
			const fetchFn = vi.fn(() => Promise.reject(new Error('Failed')));
			renderComponent(InlineLogFeed, {
				props: { logfile: 'test.log', fetchFn, autoRefresh: false }
			});
			await waitFor(() => {
				expect(screen.getByText('Failed')).toBeInTheDocument();
			});
		});
	});

	describe('interactions', () => {
		it('expands to show log entries when clicked', async () => {
			renderComponent(InlineLogFeed, {
				props: { logfile: 'test.log', fetchFn: createFetchFn(), autoRefresh: false }
			});
			await waitFor(() => {
				expect(screen.getByText('Recent Log')).toBeInTheDocument();
			});
			await fireEvent.click(screen.getByText('Recent Log'));
			expect(screen.getByText('Something failed')).toBeInTheDocument();
			expect(screen.getByText('Disk space low')).toBeInTheDocument();
		});

		it('shows view full log link when expanded', async () => {
			renderComponent(InlineLogFeed, {
				props: { logfile: 'test.log', fetchFn: createFetchFn(), autoRefresh: false }
			});
			await waitFor(() => {
				expect(screen.getByText('Recent Log')).toBeInTheDocument();
			});
			await fireEvent.click(screen.getByText('Recent Log'));
			const link = screen.getByText(/View full log/);
			expect(link.closest('a')).toHaveAttribute('href', '/logs/test.log');
		});
	});

	describe('filtering', () => {
		it('renders level dropdown and search input when expanded', async () => {
			renderComponent(InlineLogFeed, {
				props: { logfile: 'test.log', fetchFn: createFetchFn(), autoRefresh: false }
			});
			await waitFor(() => expect(screen.getByText('3 entries')).toBeInTheDocument());
			await fireEvent.click(screen.getByText('Recent Log'));

			expect(screen.getByLabelText('Minimum log level')).toBeInTheDocument();
			expect(screen.getByLabelText('Search log entries')).toBeInTheDocument();
		});

		it('passes selected level to fetchFn on change', async () => {
			const fetchFn = createFetchFn();
			renderComponent(InlineLogFeed, {
				props: { logfile: 'test.log', fetchFn, autoRefresh: false }
			});
			await waitFor(() => expect(screen.getByText('3 entries')).toBeInTheDocument());
			await fireEvent.click(screen.getByText('Recent Log'));

			const select = screen.getByLabelText('Minimum log level') as HTMLSelectElement;
			// Use the shared test pattern from PresetEditor: set value, dispatch change.
			select.value = 'error';
			await fireEvent.change(select);

			expect(select.value).toBe('error');

			await waitFor(() => {
				const calls = fetchFn.mock.calls;
				const hasLevelCall = calls.some((c: any[]) => c[3] === 'error');
				expect(hasLevelCall).toBe(true);
			});
		});

		it('shows "filtered" badge when a filter is active', async () => {
			renderComponent(InlineLogFeed, {
				props: { logfile: 'test.log', fetchFn: createFetchFn(), autoRefresh: false }
			});
			await waitFor(() => expect(screen.getByText('3 entries')).toBeInTheDocument());
			await fireEvent.click(screen.getByText('Recent Log'));

			const select = screen.getByLabelText('Minimum log level') as HTMLSelectElement;
			await fireEvent.change(select, { target: { value: 'warning' } });

			await waitFor(() => {
				expect(screen.getByText('filtered')).toBeInTheDocument();
			});
		});

		it('shows "No entries match" when filter returns zero entries', async () => {
			let callCount = 0;
			const fetchFn = vi.fn((_f: string, _m: string, _l: number, level?: string) => {
				callCount++;
				if (level === 'critical') return Promise.resolve({ entries: [] });
				return Promise.resolve({ entries: mockEntries });
			});
			renderComponent(InlineLogFeed, {
				props: { logfile: 'test.log', fetchFn, autoRefresh: false }
			});
			await waitFor(() => expect(screen.getByText('3 entries')).toBeInTheDocument());
			await fireEvent.click(screen.getByText('Recent Log'));

			const select = screen.getByLabelText('Minimum log level') as HTMLSelectElement;
			await fireEvent.change(select, { target: { value: 'critical' } });

			await waitFor(() => {
				expect(screen.getByText(/No entries match/i)).toBeInTheDocument();
			});
			expect(callCount).toBeGreaterThan(1);
			// Panel stays visible so user can clear the filter
			expect(screen.getByRole('button', { name: /clear/i })).toBeInTheDocument();
		});

		it('clears filters via Clear button', async () => {
			const fetchFn = createFetchFn();
			renderComponent(InlineLogFeed, {
				props: { logfile: 'test.log', fetchFn, autoRefresh: false }
			});
			await waitFor(() => expect(screen.getByText('3 entries')).toBeInTheDocument());
			await fireEvent.click(screen.getByText('Recent Log'));

			const select = screen.getByLabelText('Minimum log level') as HTMLSelectElement;
			await fireEvent.change(select, { target: { value: 'error' } });
			expect(select.value).toBe('error');

			await waitFor(() => {
				expect(screen.getByRole('button', { name: /clear/i })).toBeInTheDocument();
			});
			await fireEvent.click(screen.getByRole('button', { name: /clear/i }));

			expect((screen.getByLabelText('Minimum log level') as HTMLSelectElement).value).toBe('');
		});
	});
});
