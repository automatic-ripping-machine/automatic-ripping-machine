import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderComponent, screen, fireEvent, cleanup, waitFor } from '$lib/test-utils';
import JobActions from './JobActions.svelte';
import { createJob } from './__fixtures__/job';

// Mock the API module
vi.mock('$lib/api/jobs', () => ({
	abandonJob: vi.fn(() => Promise.resolve()),
	deleteJob: vi.fn(() => Promise.resolve()),
	fixJobPermissions: vi.fn(() => Promise.resolve()),
	bulkPurgeJobs: vi.fn(() => Promise.resolve({ purged: 1, errors: [] }))
}));

import { abandonJob, deleteJob, fixJobPermissions, bulkPurgeJobs } from '$lib/api/jobs';
const mockAbandon = vi.mocked(abandonJob);
const mockDelete = vi.mocked(deleteJob);
const mockFixPerms = vi.mocked(fixJobPermissions);
const mockPurge = vi.mocked(bulkPurgeJobs);

// Mock window.confirm
vi.stubGlobal('confirm', vi.fn(() => true));

describe('JobActions', () => {
	afterEach(() => {
		cleanup();
		vi.clearAllMocks();
		vi.mocked(confirm).mockReturnValue(true);
	});

	describe('rendering', () => {
		it('shows Abandon button for active jobs', () => {
			renderComponent(JobActions, {
				props: { job: createJob({ status: 'ripping' }) }
			});
			expect(screen.getByText('Abandon')).toBeInTheDocument();
		});

		it('shows Delete button for completed jobs', () => {
			renderComponent(JobActions, {
				props: { job: createJob({ status: 'success' }) }
			});
			expect(screen.getByText('Delete')).toBeInTheDocument();
		});

		it('shows Delete button for failed jobs', () => {
			renderComponent(JobActions, {
				props: { job: createJob({ status: 'fail' }) }
			});
			expect(screen.getByText('Delete')).toBeInTheDocument();
		});

		it('shows Fix Permissions button only for success status', () => {
			renderComponent(JobActions, {
				props: { job: createJob({ status: 'success' }) }
			});
			expect(screen.getByText('Fix Permissions')).toBeInTheDocument();
		});

		it('does not show Fix Permissions for failed jobs', () => {
			renderComponent(JobActions, {
				props: { job: createJob({ status: 'fail' }) }
			});
			expect(screen.queryByText('Fix Permissions')).not.toBeInTheDocument();
		});

		it('renders nothing for jobs with no available actions', () => {
			renderComponent(JobActions, {
				props: { job: createJob({ status: 'identifying' }) }
			});
			// identifying is active, so Abandon should show
			expect(screen.getByText('Abandon')).toBeInTheDocument();
		});

		it('does not show any buttons for cancelled status', () => {
			renderComponent(JobActions, {
				props: { job: createJob({ status: 'cancelled' }) }
			});
			expect(screen.queryByText('Abandon')).not.toBeInTheDocument();
			expect(screen.queryByText('Delete')).not.toBeInTheDocument();
			expect(screen.queryByText('Fix Permissions')).not.toBeInTheDocument();
		});
	});

	describe('interactions', () => {
		it('calls abandonJob when Abandon is clicked and confirmed', async () => {
			const onaction = vi.fn();
			renderComponent(JobActions, {
				props: { job: createJob({ status: 'ripping' }), onaction }
			});
			await fireEvent.click(screen.getByText('Abandon'));
			await waitFor(() => {
				expect(mockAbandon).toHaveBeenCalledWith(1);
				expect(onaction).toHaveBeenCalled();
			});
		});

		it('calls deleteJob when Delete is clicked and confirmed', async () => {
			const onaction = vi.fn();
			renderComponent(JobActions, {
				props: { job: createJob({ status: 'success' }), onaction }
			});
			await fireEvent.click(screen.getByText('Delete'));
			await waitFor(() => {
				expect(mockDelete).toHaveBeenCalledWith(1);
			});
		});

		it('calls fixJobPermissions when Fix Permissions is clicked', async () => {
			const onaction = vi.fn();
			renderComponent(JobActions, {
				props: { job: createJob({ status: 'success' }), onaction }
			});
			await fireEvent.click(screen.getByText('Fix Permissions'));
			await waitFor(() => {
				expect(mockFixPerms).toHaveBeenCalledWith(1);
				expect(onaction).toHaveBeenCalled();
			});
		});

		it('shows success feedback after action', async () => {
			renderComponent(JobActions, {
				props: { job: createJob({ status: 'ripping' }) }
			});
			await fireEvent.click(screen.getByText('Abandon'));
			await waitFor(() => {
				expect(screen.getByText('Job abandoned')).toBeInTheDocument();
			});
		});

		it('shows error feedback on API failure', async () => {
			mockAbandon.mockRejectedValueOnce(new Error('Server error'));
			renderComponent(JobActions, {
				props: { job: createJob({ status: 'ripping' }) }
			});
			await fireEvent.click(screen.getByText('Abandon'));
			await waitFor(() => {
				expect(screen.getByText('Server error')).toBeInTheDocument();
			});
		});

		it('does not call API when confirm is cancelled', async () => {
			vi.mocked(confirm).mockReturnValueOnce(false);
			renderComponent(JobActions, {
				props: { job: createJob({ status: 'ripping' }) }
			});
			await fireEvent.click(screen.getByText('Abandon'));
			expect(mockAbandon).not.toHaveBeenCalled();
		});

		it('shows Delete button for waiting_transcode status', () => {
			renderComponent(JobActions, {
				props: { job: createJob({ status: 'waiting_transcode' }) }
			});
			expect(screen.getByText('Delete')).toBeInTheDocument();
		});

		it('calls ondelete callback instead of onaction when deleting', async () => {
			const ondelete = vi.fn();
			const onaction = vi.fn();
			renderComponent(JobActions, {
				props: { job: createJob({ status: 'success' }), ondelete, onaction }
			});
			await fireEvent.click(screen.getByText('Delete'));
			await waitFor(() => {
				expect(ondelete).toHaveBeenCalled();
				expect(onaction).not.toHaveBeenCalled();
			});
		});

		it('calls ondelete after purge so detail page redirects (job is gone)', async () => {
			// Bug guard: Purge wipes the job record, so the detail page must
			// navigate away via ondelete just like Delete does. Without this
			// the user sees a stale detail page that 404s on next refresh.
			const ondelete = vi.fn();
			const onaction = vi.fn();
			renderComponent(JobActions, {
				props: { job: createJob({ status: 'fail' }), ondelete, onaction }
			});
			await fireEvent.click(screen.getByText('Purge'));
			await waitFor(() => {
				expect(mockPurge).toHaveBeenCalledWith({ job_ids: [1] });
				expect(ondelete).toHaveBeenCalled();
				expect(onaction).not.toHaveBeenCalled();
			});
		});
	});

	describe('props', () => {
		it('renders compact buttons when compact is true', () => {
			renderComponent(JobActions, {
				props: { job: createJob({ status: 'success' }), compact: true }
			});
			const deleteBtn = screen.getByText('Delete');
			expect(deleteBtn).toHaveClass('text-xs');
		});

		it('renders standard buttons when compact is false', () => {
			renderComponent(JobActions, {
				props: { job: createJob({ status: 'success' }), compact: false }
			});
			const deleteBtn = screen.getByText('Delete');
			expect(deleteBtn).toHaveClass('text-xs');
		});
	});
});
