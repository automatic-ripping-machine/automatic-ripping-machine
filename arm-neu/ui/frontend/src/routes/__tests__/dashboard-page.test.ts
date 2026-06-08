import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderComponent, screen, cleanup, waitFor, fireEvent } from '$lib/test-utils';
import DashboardPage from '../+page.svelte';

// --- Shared mock job fixtures ---
const ACTIVE_JOB = {
	job_id: 1, title: 'Ripping Movie', status: 'ripping', video_type: 'movie', year: '2024',
	disctype: 'bluray', label: 'TEST', start_time: '2025-06-15T10:00:00Z', stop_time: null,
	job_length: null, devpath: '/dev/sr0', imdb_id: null, poster_url: null, errors: null,
	stage: 'Ripping', no_of_titles: 3, logfile: null, track_counts: null,
	wait_start_time: null
};

const COMPLETED_JOB = {
	job_id: 2, title: 'Old Movie', status: 'success', video_type: 'movie', year: '2023',
	disctype: 'dvd', label: 'OLD', start_time: '2025-06-14T10:00:00Z',
	stop_time: '2025-06-14T11:00:00Z', job_length: '1h', devpath: '/dev/sr0', imdb_id: null,
	poster_url: null, errors: null, stage: null, no_of_titles: 1, logfile: null,
	track_counts: null
};

const DEFAULT_JOBS_RESPONSE = {
	jobs: [COMPLETED_JOB], total: 1, page: 1, per_page: 25, pages: 1
};

const DEFAULT_STATS = { total: 1, active: 0, success: 1, fail: 0, waiting: 0 };

vi.mock('$lib/api/dashboard', () => ({
	fetchDashboard: vi.fn(() => Promise.resolve({
		db_available: true, arm_online: true,
		active_jobs: [ACTIVE_JOB],
		system_info: null, drives_online: 1, drive_names: { '/dev/sr0': 'Main Drive' },
		notification_count: 2, ripping_enabled: true,
		transcoder_online: false, transcoder_stats: null, transcoder_system_stats: null,
		active_transcodes: [], system_stats: null, transcoder_info: null
	}))
}));

vi.mock('$lib/api/jobs', () => ({
	fetchJobs: vi.fn(() => Promise.resolve(DEFAULT_JOBS_RESPONSE)),
	fetchJobProgress: vi.fn(() => Promise.resolve({ progress: null, tracks_ripped: 0, tracks_total: 0, no_of_titles: 0 })),
	fetchJobStats: vi.fn(() => Promise.resolve(DEFAULT_STATS)),
	bulkDeleteJobs: vi.fn(() => Promise.resolve({ deleted: 0, errors: [] })),
	bulkPurgeJobs: vi.fn(() => Promise.resolve({ purged: 0, errors: [] })),
	abandonJob: vi.fn(),
	deleteJob: vi.fn(),
	fixJobPermissions: vi.fn()
}));

vi.mock('$lib/api/logs', () => ({
	fetchStructuredLogContent: vi.fn(() => Promise.resolve({ entries: [] }))
}));

/** Render dashboard and wait for initial data to load */
async function renderDashboard() {
	renderComponent(DashboardPage);
	await waitFor(() => expect(screen.getByText('Dashboard')).toBeInTheDocument());
}

/** Render dashboard, wait for jobs, then switch to table view */
async function renderDashboardTable() {
	await renderDashboard();
	await fireEvent.click(screen.getByText('Table'));
	await waitFor(() => expect(screen.getByText('Title')).toBeInTheDocument());
}

/** Find and click the gear/Actions button */
async function openGearMenu() {
	const actionsBtns = screen.getAllByText(/Actions/);
	const gearBtn = actionsBtns.find(el => el.tagName === 'BUTTON');
	if (!gearBtn) throw new Error('Gear button not found');
	await fireEvent.click(gearBtn);
}

/** Select all via first checkbox in table view */
async function selectAllInTable() {
	const checkboxes = screen.getAllByRole('checkbox');
	await fireEvent.click(checkboxes[0]);
	await waitFor(() => expect(screen.getByText('1 selected')).toBeInTheDocument());
}

describe('Dashboard job grouping logic', () => {
	function groupJobs(jobs: Array<{ status: string | null; job_id: number }>) {
		const scanning = jobs.filter(j => j.status?.toLowerCase() === 'identifying');
		const waiting = jobs.filter(j => j.status?.toLowerCase() === 'waiting');
		const active = jobs.filter(j => {
			const s = j.status?.toLowerCase();
			return s !== 'waiting' && s !== 'transcoding' && s !== 'waiting_transcode' && s !== 'identifying';
		});
		return { scanning, waiting, active };
	}

	it('identifying jobs go to scanning group, not active', () => {
		const jobs = [
			{ job_id: 1, status: 'identifying' },
			{ job_id: 2, status: 'ripping' },
		];
		const { scanning, active } = groupJobs(jobs);
		expect(scanning).toHaveLength(1);
		expect(scanning[0].job_id).toBe(1);
		expect(active).toHaveLength(1);
		expect(active[0].job_id).toBe(2);
	});

	it('no scanning jobs produces empty scanning group', () => {
		const jobs = [{ job_id: 1, status: 'ripping' }];
		const { scanning } = groupJobs(jobs);
		expect(scanning).toHaveLength(0);
	});

	it('multiple scanning jobs all grouped together', () => {
		const jobs = [
			{ job_id: 1, status: 'identifying' },
			{ job_id: 2, status: 'identifying' },
			{ job_id: 3, status: 'ripping' },
		];
		const { scanning, active } = groupJobs(jobs);
		expect(scanning).toHaveLength(2);
		expect(active).toHaveLength(1);
	});

	it('waiting jobs excluded from both scanning and active', () => {
		const jobs = [
			{ job_id: 1, status: 'identifying' },
			{ job_id: 2, status: 'waiting' },
			{ job_id: 3, status: 'ripping' },
		];
		const { scanning, waiting, active } = groupJobs(jobs);
		expect(scanning).toHaveLength(1);
		expect(waiting).toHaveLength(1);
		expect(active).toHaveLength(1);
	});
});

describe('Dashboard Page', () => {
	afterEach(() => cleanup());

	describe('rendering', () => {
		it.each([
			['Dashboard', 'dashboard heading'],
			['Ripping Movie', 'active jobs'],
			['Old Movie', 'completed jobs'],
			['All Jobs', 'All Jobs heading']
		])('renders "%s" (%s)', async (text) => {
			await renderDashboard();
			await waitFor(() => expect(screen.getByText(text)).toBeInTheDocument());
		});
	});

	describe('stats panel', () => {
		afterEach(() => cleanup());

		it.each(['Total', 'Active', 'Success', 'Failed', 'Waiting'])(
			'shows %s stat label', async (label) => {
				await renderDashboard();
				await waitFor(() => expect(screen.getAllByText(label).length).toBeGreaterThanOrEqual(1));
			}
		);

		it('displays correct stat values from fetchJobStats', async () => {
			await renderDashboard();
			// fetchJobStats returns { total: 1, active: 0, success: 1, fail: 0, waiting: 0 }
			await waitFor(() => expect(screen.getAllByText('1').length).toBeGreaterThanOrEqual(1));
		});
	});

	describe('view mode toggle', () => {
		afterEach(() => cleanup());

		it('renders Cards and Table toggle buttons', async () => {
			await renderDashboard();
			expect(screen.getByText('Cards')).toBeInTheDocument();
			expect(screen.getByText('Table')).toBeInTheDocument();
		});

		it.each(['Title', 'Year', 'Status', 'Type', 'Device', 'Started', 'Actions'])(
			'table view shows %s column header', async (header) => {
				await renderDashboardTable();
				expect(screen.getByText(header)).toBeInTheDocument();
			}
		);
	});

	describe('filter dropdowns', () => {
		afterEach(() => cleanup());

		it('renders filter dropdowns for status, type, disc, and days', async () => {
			await renderDashboard();
			const selects = screen.getAllByRole('combobox');
			expect(selects.length).toBeGreaterThanOrEqual(4);
		});

		it('renders search input', async () => {
			await renderDashboard();
			expect(screen.getByPlaceholderText('Search titles...')).toBeInTheDocument();
		});

		it('changing type dropdown calls fetchJobs with video_type', async () => {
			const { fetchJobs } = await import('$lib/api/jobs');
			await renderDashboard();
			const selects = screen.getAllByRole('combobox');
			// Type dropdown is the second select
			const typeSelect = selects[1];
			await fireEvent.change(typeSelect, { target: { value: 'movie' } });
			await waitFor(() => {
				expect(fetchJobs).toHaveBeenCalledWith(expect.objectContaining({ video_type: 'movie' }));
			});
		});

		it('changing disc dropdown calls fetchJobs with disctype', async () => {
			const { fetchJobs } = await import('$lib/api/jobs');
			await renderDashboard();
			const selects = screen.getAllByRole('combobox');
			// Disc dropdown is the third select
			const discSelect = selects[2];
			await fireEvent.change(discSelect, { target: { value: 'bluray' } });
			await waitFor(() => {
				expect(fetchJobs).toHaveBeenCalledWith(expect.objectContaining({ disctype: 'bluray' }));
			});
		});

		it('changing status dropdown calls fetchJobs with status', async () => {
			const { fetchJobs } = await import('$lib/api/jobs');
			await renderDashboard();
			const selects = screen.getAllByRole('combobox');
			// Status dropdown is the first select
			const statusSelect = selects[0];
			await fireEvent.change(statusSelect, { target: { value: 'fail' } });
			await waitFor(() => {
				expect(fetchJobs).toHaveBeenCalledWith(expect.objectContaining({ status: 'fail' }));
			});
		});
	});

	describe('search', () => {
		afterEach(() => cleanup());

		it('renders search input', async () => {
			await renderDashboard();
			expect(screen.getByPlaceholderText('Search titles...')).toBeInTheDocument();
		});

		it('search input triggers debounced fetchJobs', async () => {
			vi.useFakeTimers();
			const { fetchJobs } = await import('$lib/api/jobs');
			await renderDashboard();
			await fireEvent.input(screen.getByPlaceholderText('Search titles...'), { target: { value: 'test' } });
			vi.advanceTimersByTime(350);
			await waitFor(() => {
				expect(fetchJobs).toHaveBeenCalledWith(expect.objectContaining({ search: 'test' }));
			});
			vi.useRealTimers();
		});
	});

	describe('days filter', () => {
		afterEach(() => cleanup());

		it.each(['All Time', '7 days', '30 days', '90 days'])(
			'renders %s option', async (label) => {
				await renderDashboard();
				expect(screen.getByText(label)).toBeInTheDocument();
			}
		);
	});

	describe('table view sorting', () => {
		afterEach(() => cleanup());

		it('clicking a column header toggles sort', async () => {
			const { fetchJobs } = await import('$lib/api/jobs');
			await renderDashboardTable();
			const titleButton = screen.getByText('Title').closest('button');
			if (titleButton) {
				await fireEvent.click(titleButton);
				await waitFor(() => {
					expect(fetchJobs).toHaveBeenCalledWith(
						expect.objectContaining({ sort_by: 'title', sort_dir: 'desc' })
					);
				});
			}
		});
	});

	describe('checkbox selection', () => {
		afterEach(() => cleanup());

		it('table view has a select-all checkbox', async () => {
			await renderDashboardTable();
			expect(screen.getAllByRole('checkbox').length).toBeGreaterThanOrEqual(1);
		});

		it('clicking select-all shows selection count', async () => {
			await renderDashboardTable();
			await selectAllInTable();
		});
	});

	describe('gear menu / bulk actions', () => {
		afterEach(() => cleanup());

		it('renders the Actions gear button', async () => {
			await renderDashboard();
			expect(screen.getAllByText(/Actions/).length).toBeGreaterThanOrEqual(1);
		});

		it.each(['Bulk Actions', 'Delete All Failed', 'Purge All Failed', 'Delete All Successful'])(
			'gear menu shows "%s"', async (label) => {
				await renderDashboard();
				await openGearMenu();
				await waitFor(() => expect(screen.getByText(new RegExp(label))).toBeInTheDocument());
			}
		);

		it('shows selected job actions when jobs are selected', async () => {
			await renderDashboardTable();
			await selectAllInTable();
			await openGearMenu();
			await waitFor(() => {
				expect(screen.getByText('Delete Selected')).toBeInTheDocument();
				expect(screen.getByText('Purge Selected')).toBeInTheDocument();
			});
		});
	});

	describe('pagination', () => {
		afterEach(() => cleanup());

		it('does not show pagination when only 1 page', async () => {
			await renderDashboard();
			expect(screen.queryByText('Prev')).not.toBeInTheDocument();
			expect(screen.queryByText('Next')).not.toBeInTheDocument();
		});

		it('shows pagination when multiple pages', async () => {
			const { fetchJobs } = await import('$lib/api/jobs');
			(fetchJobs as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
				jobs: [{ ...COMPLETED_JOB, job_id: 10, title: 'Page Movie', label: 'PG' }],
				total: 50, page: 1, per_page: 25, pages: 2
			});

			renderComponent(DashboardPage);
			await waitFor(() => expect(screen.getByText('Page Movie')).toBeInTheDocument());
			await waitFor(() => {
				expect(screen.getByText('Prev')).toBeInTheDocument();
				expect(screen.getByText('Next')).toBeInTheDocument();
				expect(screen.getByText(/Showing 1/)).toBeInTheDocument();
			});
		});
	});

	it('shows active rips section when ripping jobs exist', async () => {
		await renderDashboard();
		await waitFor(() => expect(screen.getByText('Ripping Movie')).toBeInTheDocument());
	});

	it('shows no jobs found when job list is empty', async () => {
		const { fetchJobs } = await import('$lib/api/jobs');
		(fetchJobs as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
			jobs: [], total: 0, page: 1, per_page: 25, pages: 1
		});
		renderComponent(DashboardPage);
		await waitFor(() => expect(screen.getByText('No jobs found.')).toBeInTheDocument());
	});

	it('polls progress for jobs in copying status and renders the copy bar', async () => {
		// Repro: hifi job in JobState.COPYING shows just the "Copying" label
		// with no bar today; this test asserts copy_progress is fetched and
		// rendered. The mock fetchJobProgress returns copy_progress=47.0 and
		// copy_stage='scratch-to-media'; the dashboard should display 47%.
		const COPYING_JOB = {
			job_id: 42, title: 'Annihilation', status: 'copying',
			disctype: 'bluray4k', source_type: 'folder', video_type: 'movie',
			year: '2018', label: 'ANNI', start_time: '2026-05-09T18:00:00Z',
			stop_time: null, job_length: null, devpath: '/dev/sr0',
			imdb_id: null, poster_url: null, errors: null, stage: null,
			no_of_titles: 0, logfile: null, track_counts: null,
			wait_start_time: null
		};

		const { fetchDashboard } = await import('$lib/api/dashboard');
		(fetchDashboard as ReturnType<typeof vi.fn>).mockResolvedValue({
			db_available: true, arm_online: true,
			active_jobs: [COPYING_JOB],
			system_info: null, drives_online: 1, drive_names: { '/dev/sr0': 'Main Drive' },
			notification_count: 2, ripping_enabled: true,
			transcoder_online: false, transcoder_stats: null, transcoder_system_stats: null,
			active_transcodes: [], system_stats: null, transcoder_info: null
		});

		const { fetchJobProgress } = await import('$lib/api/jobs');
		(fetchJobProgress as ReturnType<typeof vi.fn>).mockResolvedValue({
			progress: null, stage: null,
			tracks_total: 0, tracks_ripped: 0, no_of_titles: null,
			copy_progress: 47.0, copy_stage: 'scratch-to-media',
		});

		renderComponent(DashboardPage);
		await waitFor(() => {
			expect(screen.getByText('Annihilation')).toBeInTheDocument();
		});

		// Wait for the progress poll to land - ProgressBar renders "47%"
		await waitFor(() => {
			const matches = screen.queryAllByText(/47/);
			expect(matches.length).toBeGreaterThan(0);
		}, { timeout: 5000 });
	});
});
