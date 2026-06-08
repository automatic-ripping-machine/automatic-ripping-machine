import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderComponent, screen, fireEvent, cleanup, waitFor } from '$lib/test-utils';
import DiscReviewWidget from '../DiscReviewWidget.svelte';

vi.mock('$lib/api/jobs', () => ({
	fetchJob: vi.fn(() => Promise.resolve({
		job_id: 1, tracks: [], config: { MANUAL_WAIT_TIME: 60, MINLENGTH: 120 },
		title: 'Test Movie', year: '2025', video_type: 'movie',
		disctype: 'bluray', status: 'waiting'
	})),
	cancelWaitingJob: vi.fn(() => Promise.resolve()),
	startWaitingJob: vi.fn(() => Promise.resolve()),
	pauseWaitingJob: vi.fn(() => Promise.resolve()),
	updateJobTitle: vi.fn(() => Promise.resolve()),
	toggleMultiTitle: vi.fn(() => Promise.resolve()),
	updateTrack: vi.fn(() => Promise.resolve()),
	fetchNamingPreview: vi.fn(() => Promise.resolve({
		success: true, job_title: 'Test Movie (2025)',
		job_folder: 'Test Movie (2025)', tracks: []
	}))
}));

vi.mock('$lib/api/maintenance', () => ({
	fetchSummary: vi.fn(() => Promise.resolve({}))
}));

const mockJob = {
	job_id: 1, title: 'Test Movie', title_auto: 'Test Movie', year: '2025', year_auto: '2025',
	video_type: 'movie', disctype: 'bluray', status: 'waiting', label: 'TEST_DISC',
	imdb_id: '', poster_url: '', path: 'Test Movie (2025)', hasnicetitle: true,
	crc_id: '', multi_title: false, disc_number: null, disc_total: null,
	artist: '', album: '', season: '', episode: ''
};

function renderWidget(overrides = {}) {
	return renderComponent(DiscReviewWidget, {
		props: { job: { ...mockJob, ...overrides }, driveNames: {}, paused: false }
	});
}

/** Open the Info panel and wait for the Title field to appear. */
async function openInfoPanel() {
	await fireEvent.click(screen.getByText('Info'));
	await waitFor(() => {
		expect(screen.getByText('Title')).toBeInTheDocument();
	});
}

/** Open Info panel and edit the title field, triggering the save bar. */
async function editTitleField(newValue = 'Changed Title') {
	await openInfoPanel();
	const titleLabel = screen.getByText('Title');
	const titleInput = titleLabel.closest('label')!.querySelector('input')!;
	await fireEvent.input(titleInput, { target: { value: newValue } });
	await waitFor(() => {
		expect(screen.queryAllByText('Unsaved changes').length).toBeGreaterThanOrEqual(1);
	});
}

describe('DiscReviewWidget', () => {
	afterEach(() => {
		cleanup();
		vi.clearAllMocks();
	});

	describe('save bar', () => {
		it('does not show save bar on initial load', async () => {
			renderWidget();
			await openInfoPanel();
			expect(screen.queryByText('Unsaved changes')).not.toBeInTheDocument();
		});

		it('shows save bar when field is edited', async () => {
			renderWidget();
			await editTitleField();
		});

		it('save bar has Reset and Save buttons', async () => {
			renderWidget();
			await editTitleField();
			expect(screen.queryAllByText('Reset').length).toBeGreaterThanOrEqual(1);
			expect(screen.queryAllByText('Save').length).toBeGreaterThanOrEqual(1);
		});
	});

	describe('button order', () => {
		it('Cancel button appears before Start button', () => {
			renderWidget();
			const cancelBtn = screen.getAllByText('Cancel')[0];
			const startBtn = screen.getAllByText('Start')[0];
			// Cancel should appear before Start in DOM order
			expect(cancelBtn.compareDocumentPosition(startBtn) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
		});
	});

	describe('output path', () => {
		it('shows Output Path label in info panel', async () => {
			renderWidget();
			await fireEvent.click(screen.getByText('Info'));
			await waitFor(() => {
				expect(screen.getByText('Output Path')).toBeInTheDocument();
			});
		});
	});

	describe('naming preview error handling', () => {
		it('falls back gracefully when fetchNamingPreview fails', async () => {
			const { fetchNamingPreview } = await import('$lib/api/jobs');
			vi.mocked(fetchNamingPreview).mockRejectedValueOnce(new Error('API unavailable'));

			renderWidget();
			await fireEvent.click(screen.getByText('Info'));
			await waitFor(() => {
				expect(screen.getByText('Title')).toBeInTheDocument();
			});
			// Widget should still render without crashing — title input shows raw title as fallback
			const titleLabel = screen.getByText('Title');
			expect(titleLabel).toBeInTheDocument();
		});
	});
});
