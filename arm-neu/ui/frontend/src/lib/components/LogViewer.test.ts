import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderComponent, screen, cleanup, waitFor } from '$lib/test-utils';
import LogViewer from './LogViewer.svelte';

describe('LogViewer', () => {
	afterEach(() => cleanup());

	describe('rendering', () => {
		it('shows loading state initially', () => {
			const fetchFn = vi.fn(() => new Promise(() => {})); // never resolves
			renderComponent(LogViewer, {
				props: { filename: 'test.log', fetchFn, autoRefresh: false }
			});
			expect(screen.getByText('Loading...')).toBeInTheDocument();
		});

		it('renders log content after fetch', async () => {
			const fetchFn = vi.fn(() => Promise.resolve({ content: 'Line 1\nLine 2' }));
			const { container } = renderComponent(LogViewer, {
				props: { filename: 'test.log', fetchFn, autoRefresh: false }
			});
			await waitFor(() => {
				const pre = container.querySelector('pre');
				expect(pre).toBeInTheDocument();
				expect(pre?.textContent).toContain('Line 1');
				expect(pre?.textContent).toContain('Line 2');
			});
		});

		it('renders error message on fetch failure', async () => {
			const fetchFn = vi.fn(() => Promise.reject(new Error('Network error')));
			renderComponent(LogViewer, {
				props: { filename: 'test.log', fetchFn, autoRefresh: false }
			});
			await waitFor(() => {
				expect(screen.getByText('Network error')).toBeInTheDocument();
			});
		});
	});

	describe('props', () => {
		it('passes filename, mode, and lines to fetchFn', async () => {
			const fetchFn = vi.fn(() => Promise.resolve({ content: '' }));
			renderComponent(LogViewer, {
				props: { filename: 'app.log', mode: 'full', lines: 500, fetchFn, autoRefresh: false }
			});
			await waitFor(() => {
				expect(fetchFn).toHaveBeenCalledWith('app.log', 'full', 500);
			});
		});
	});
});
