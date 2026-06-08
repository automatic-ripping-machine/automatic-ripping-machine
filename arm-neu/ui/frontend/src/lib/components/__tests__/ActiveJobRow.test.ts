import { describe, it, expect, afterEach } from 'vitest';
import { renderComponent, screen, fireEvent, cleanup, waitFor } from '$lib/test-utils';
import ActiveJobRow from '../ActiveJobRow.svelte';
import type { JobSchema as Job } from '$lib/types/api.gen';
function createJob(overrides: Partial<Job> = {}): Job {
	return {
		job_id: 1,
		status: 'ripping',
		title: 'Test Movie',
		year: '2024',
		video_type: 'movie',
		disctype: 'bluray',
		label: 'TEST_LABEL',
		start_time: '2025-06-15T10:00:00Z',
		stop_time: null,
		job_length: null,
		devpath: '/dev/sr0',
		imdb_id: null,
		poster_url: null,
		errors: null,
		stage: 'Ripping title 1',
		no_of_titles: 3,
		logfile: 'test.log',
		track_counts: { total: 3, ripped: 1 },
		wait_start_time: null,
		source_type: null,
		source_path: null,
		disc_number: null,
		disc_total: null,
		multi_title: false,
		...overrides,
	} as Job;
}

describe('ActiveJobRow', () => {
	afterEach(() => cleanup());

	describe('collapsed state', () => {
		it('renders title', () => {
			renderComponent(ActiveJobRow, { props: { job: createJob() } });
			expect(screen.getByText('Test Movie')).toBeInTheDocument();
		});

		it('renders year', () => {
			renderComponent(ActiveJobRow, { props: { job: createJob() } });
			expect(screen.getByText('2024')).toBeInTheDocument();
		});

		it('renders status badge', () => {
			renderComponent(ActiveJobRow, { props: { job: createJob() } });
			expect(screen.getByText('Ripping')).toBeInTheDocument();
		});

		it('renders drive name when provided', () => {
			renderComponent(ActiveJobRow, {
				props: { job: createJob(), driveNames: { '/dev/sr0': 'Main Drive' } }
			});
			expect(screen.getByText('Main Drive')).toBeInTheDocument();
		});

		it('shows error indicator when job has errors', () => {
			renderComponent(ActiveJobRow, {
				props: { job: createJob({ errors: 'Something went wrong' }) }
			});
			expect(screen.getByTitle('Something went wrong')).toBeInTheDocument();
		});

		it('does not show expanded detail by default', () => {
			renderComponent(ActiveJobRow, { props: { job: createJob() } });
			expect(screen.queryByText('Open details')).not.toBeInTheDocument();
		});
	});

	describe('expand/collapse', () => {
		it('shows expanded detail on click', async () => {
			renderComponent(ActiveJobRow, {
				props: { job: createJob({ imdb_id: 'tt1234567' }) }
			});
			// Click the row to expand
			await fireEvent.click(screen.getByText('Test Movie'));
			await waitFor(() => {
				expect(screen.getByText('Open details')).toBeInTheDocument();
			});
		});

		it('shows IMDb link when expanded', async () => {
			renderComponent(ActiveJobRow, {
				props: { job: createJob({ imdb_id: 'tt1234567' }) }
			});
			await fireEvent.click(screen.getByText('Test Movie'));
			await waitFor(() => {
				expect(screen.getByText('IMDb')).toBeInTheDocument();
			});
		});

		it('shows disc label when different from title', async () => {
			renderComponent(ActiveJobRow, {
				props: { job: createJob({ title: 'The Matrix', label: 'MATRIX_DISC1' }) }
			});
			await fireEvent.click(screen.getByText('The Matrix'));
			await waitFor(() => {
				expect(screen.getByText('MATRIX_DISC1')).toBeInTheDocument();
			});
		});

		it('shows track counts when expanded', async () => {
			renderComponent(ActiveJobRow, {
				props: { job: createJob({ track_counts: { total: 5, ripped: 2 } }) }
			});
			await fireEvent.click(screen.getByText('Test Movie'));
			await waitFor(() => {
				expect(screen.getByText('2 / 5 ripped')).toBeInTheDocument();
			});
		});

		it('shows errors with log link when expanded', async () => {
			renderComponent(ActiveJobRow, {
				props: { job: createJob({ errors: 'Read error on track 2', logfile: 'test.log' }) }
			});
			await fireEvent.click(screen.getByText('Test Movie'));
			await waitFor(() => {
				expect(screen.getByText('Read error on track 2')).toBeInTheDocument();
			});
		});

		it('expanded state has chevron rotated', async () => {
			renderComponent(ActiveJobRow, {
				props: { job: createJob() }
			});
			await fireEvent.click(screen.getByText('Test Movie'));
			await waitFor(() => {
				expect(screen.getByText('Open details')).toBeInTheDocument();
			});
		});
	});

	describe('folder import', () => {
		it('shows Folder Import badge when expanded', async () => {
			renderComponent(ActiveJobRow, {
				props: { job: createJob({ source_type: 'folder', source_path: '/media/imports/MOVIE' }) }
			});
			await fireEvent.click(screen.getByText('Test Movie'));
			await waitFor(() => {
				expect(screen.getByText('Folder Import')).toBeInTheDocument();
			});
		});

		it('shows importing status for folder rips', () => {
			renderComponent(ActiveJobRow, {
				props: { job: createJob({ source_type: 'folder', status: 'ripping' }) }
			});
			expect(screen.getByText('Processing')).toBeInTheDocument();
		});
	});
});
