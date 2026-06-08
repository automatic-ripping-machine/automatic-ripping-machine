import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderComponent, screen, cleanup } from '$lib/test-utils';
import JobRow from './JobRow.svelte';
import { createJob } from './__fixtures__/job';

// JobRow renders a <tr>, which needs a <table> parent for valid DOM
function renderInTable(props: Record<string, unknown>) {
	const { container, ...rest } = renderComponent(JobRow, { props });
	// Wrap in a table if the browser didn't auto-correct
	return { container, ...rest };
}

describe('JobRow', () => {
	beforeEach(() => {
		vi.useFakeTimers();
		vi.setSystemTime(new Date('2025-06-15T12:00:00Z'));
	});

	afterEach(() => {
		cleanup();
		vi.useRealTimers();
	});

	describe('rendering', () => {
		it('renders job title as a link', () => {
			renderInTable({ job: createJob() });
			const link = screen.getByText('Test Movie');
			expect(link).toBeInTheDocument();
			expect(link.closest('a')).toHaveAttribute('href', '/jobs/1');
		});

		it('renders Untitled when no title or label', () => {
			renderInTable({ job: createJob({ title: null, label: null }) });
			expect(screen.getByText('Untitled')).toBeInTheDocument();
		});

		it('renders status badge', () => {
			renderInTable({ job: createJob({ status: 'success' }) });
			expect(screen.getByText('Success')).toBeInTheDocument();
		});

		it('renders year when present', () => {
			renderInTable({ job: createJob() });
			expect(screen.getByText('2024')).toBeInTheDocument();
		});
	});

	describe('props', () => {
		it('renders drive name from driveNames map', () => {
			renderInTable({
				job: createJob({ devpath: '/dev/sr0' }),
				driveNames: { '/dev/sr0': 'Main Drive' }
			});
			expect(screen.getByText('Main Drive')).toBeInTheDocument();
		});

		it('falls back to devpath when no drive name', () => {
			renderInTable({
				job: createJob({ devpath: '/dev/sr1' }),
				driveNames: {}
			});
			expect(screen.getByText('/dev/sr1')).toBeInTheDocument();
		});

		it('shows IMDb link when imdb_id present', () => {
			renderInTable({ job: createJob({ imdb_id: 'tt1234567' }) });
			const imdbLink = screen.getByText('IMDb');
			expect(imdbLink.closest('a')).toHaveAttribute('href', 'https://www.imdb.com/title/tt1234567/');
		});

		it('shows disc label when it differs from title', () => {
			renderInTable({
				job: createJob({ title: 'My Movie', label: 'DISC_LABEL' })
			});
			expect(screen.getByText('DISC_LABEL')).toBeInTheDocument();
		});

		it('shows stage for active jobs', () => {
			renderInTable({
				job: createJob({ status: 'ripping', stage: 'Ripping track 3' })
			});
			expect(screen.getByText('Ripping track 3')).toBeInTheDocument();
		});

		it('shows errors indicator when job has errors', () => {
			renderInTable({
				job: createJob({ errors: 'Something went wrong', logfile: 'job_1.log' })
			});
			const errLink = screen.getByText('errors');
			expect(errLink.closest('a')).toHaveAttribute('href', '/logs/job_1.log');
		});
	});

	describe('skeleton', () => {
		it('renders skeleton cells when job prop is omitted', () => {
			const { container } = renderComponent(JobRow, { props: {} });
			const skeletonCells = container.querySelectorAll('[data-variant="line"]');
			expect(skeletonCells.length).toBeGreaterThan(0);
		});
	});
});
