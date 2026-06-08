import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderComponent, screen, fireEvent, cleanup, waitFor } from '$lib/test-utils';
import LogsPage from '../+page.svelte';

vi.mock('$lib/api/maintenance', () => ({
	fetchOrphanLogs: vi.fn(() => Promise.resolve({ root: '/tmp', total_size_bytes: 0, files: [] })),
	deleteLog: vi.fn(() => Promise.resolve({ success: true })),
	bulkDeleteLogs: vi.fn(() => Promise.resolve({ removed: [], errors: [] }))
}));

vi.mock('$lib/api/logs', () => ({
	fetchLogs: vi.fn(() => Promise.resolve([
		{ filename: 'job_001.log', size: 1024, modified: '2025-06-15T12:00:00Z' },
		{ filename: 'job_002.log', size: 2048, modified: '2025-06-14T10:00:00Z' }
	])),
	fetchTranscoderLogs: vi.fn(() => Promise.resolve([
		{ filename: 'transcode_001.log', size: 512, modified: '2025-06-15T11:00:00Z' }
	])),
	deleteLog: vi.fn(() => Promise.resolve({ success: true, filename: 'test.log' })),
	logDownloadUrl: vi.fn((f: string) => `/api/logs/${f}/download`),
}));

describe('Logs Page', () => {
	afterEach(() => cleanup());

	describe('rendering', () => {
		it('renders page title', async () => {
			renderComponent(LogsPage);
			expect(screen.getByText('Log Files')).toBeInTheDocument();
		});

		it('renders ARM and Transcoder tabs', () => {
			renderComponent(LogsPage);
			expect(screen.getByText('ARM Ripper')).toBeInTheDocument();
			expect(screen.getByText('Transcoder')).toBeInTheDocument();
		});

		it('renders ARM log files after loading', async () => {
			renderComponent(LogsPage);
			await waitFor(() => {
				expect(screen.getByText('job_001.log')).toBeInTheDocument();
				expect(screen.getByText('job_002.log')).toBeInTheDocument();
			});
		});

		it('renders log file links to /logs/:filename', async () => {
			renderComponent(LogsPage);
			await waitFor(() => {
				const link = screen.getByText('job_001.log');
				expect(link.closest('a')).toHaveAttribute('href', '/logs/job_001.log');
			});
		});

		it('renders sortable column headers', async () => {
			renderComponent(LogsPage);
			await waitFor(() => {
				expect(screen.getByText('Filename')).toBeInTheDocument();
				expect(screen.getByText('Size')).toBeInTheDocument();
				expect(screen.getByText('Last Modified')).toBeInTheDocument();
			});
		});
	});

	describe('interactions', () => {
		it('switches to transcoder tab', async () => {
			renderComponent(LogsPage);
			await waitFor(() => {
				expect(screen.getByText('job_001.log')).toBeInTheDocument();
			});
			await fireEvent.click(screen.getByText('Transcoder'));
			await waitFor(() => {
				expect(screen.getByText('transcode_001.log')).toBeInTheDocument();
			});
		});
	});

	describe('orphan logs modal', () => {
		it('shows Orphan Logs button in header', async () => {
			renderComponent(LogsPage);
			expect(screen.getByText('Orphan Logs')).toBeInTheDocument();
		});

		it('opens orphan modal and loads data when clicked', async () => {
			const { fetchOrphanLogs } = await import('$lib/api/maintenance');
			renderComponent(LogsPage);
			await fireEvent.click(screen.getByText('Orphan Logs'));
			await waitFor(() => {
				expect(fetchOrphanLogs).toHaveBeenCalled();
				expect(screen.getByText('Orphan Log Files')).toBeInTheDocument();
			});
		});

		it('displays orphan log files in modal', async () => {
			const { fetchOrphanLogs } = await import('$lib/api/maintenance');
			vi.mocked(fetchOrphanLogs).mockResolvedValueOnce({
				root: '/var/log/arm',
				total_size_bytes: 4096,
				files: [
					{ path: '/var/log/arm/orphan1.log', relative_path: 'orphan1.log', size_bytes: 1024 },
					{ path: '/var/log/arm/orphan2.log', relative_path: 'orphan2.log', size_bytes: 3072 }
				]
			});
			renderComponent(LogsPage);
			await fireEvent.click(screen.getByText('Orphan Logs'));
			await waitFor(() => {
				expect(screen.getByText('orphan1.log')).toBeInTheDocument();
				expect(screen.getByText('orphan2.log')).toBeInTheDocument();
			});
		});

		it('can close orphan modal', async () => {
			renderComponent(LogsPage);
			await fireEvent.click(screen.getByText('Orphan Logs'));
			await waitFor(() => {
				expect(screen.getByText('Orphan Log Files')).toBeInTheDocument();
			});
			await fireEvent.click(screen.getByText('Close'));
			await waitFor(() => {
				expect(screen.queryByText('Orphan Log Files')).not.toBeInTheDocument();
			});
		});

		it('handles empty orphan logs', async () => {
			renderComponent(LogsPage);
			await fireEvent.click(screen.getByText('Orphan Logs'));
			await waitFor(() => {
				expect(screen.getByText('No orphan log files found.')).toBeInTheDocument();
			});
		});
	});
});
