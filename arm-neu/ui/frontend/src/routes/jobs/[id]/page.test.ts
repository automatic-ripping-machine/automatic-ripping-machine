import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderComponent, screen, fireEvent, cleanup, waitFor, within } from '$lib/test-utils';
import Page from './+page.svelte';
import type { JobDetailSchema as JobDetail } from '$lib/types/api.gen';
// --- Mocks ---

const mockGoto = vi.fn();
vi.mock('$app/navigation', () => ({ goto: (...args: unknown[]) => mockGoto(...args) }));

vi.mock('$app/stores', () => ({
	page: {
		subscribe: (fn: (val: { params: { id: '42' } }) => void) => {
			fn({ params: { id: '42' } });
			return () => {};
		}
	}
}));

const baseJob: JobDetail = {
	job_id: 42,
	arm_version: '2.0',
	crc_id: null,
	logfile: null,
	start_time: '2025-06-15T10:00:00Z',
	stop_time: null,
	job_length: null,
	status: 'waiting_transcode',
	stage: null,
	no_of_titles: 1,
	title: 'Test Movie',
	title_auto: null,
	title_manual: null,
	year: '2024',
	year_auto: null,
	year_manual: null,
	video_type: 'movie',
	video_type_auto: null,
	video_type_manual: null,
	imdb_id: null,
	imdb_id_auto: null,
	imdb_id_manual: null,
	poster_url: null,
	poster_url_auto: null,
	poster_url_manual: null,
	devpath: '/dev/sr0',
	mountpoint: null,
	hasnicetitle: null,
	errors: null,
	disctype: 'bluray',
	label: 'TEST_MOVIE',
	path: null,
	raw_path: null,
	transcode_path: null,
	artist: null,
	artist_auto: null,
	artist_manual: null,
	album: null,
	album_auto: null,
	album_manual: null,
	season: null,
	season_auto: null,
	season_manual: null,
	episode: null,
	episode_auto: null,
	episode_manual: null,
	transcode_overrides: null,
	multi_title: null,
	title_pattern_override: null,
	folder_pattern_override: null,
	disc_number: null,
	disc_total: null,
	ejected: null,
	pid: null,
	manual_pause: null,
	wait_start_time: null,
	track_counts: null,
		tvdb_id: null,
	source_type: null,
	tracks: [],
	config: { MINLENGTH: '120' }
} as unknown as JobDetail;

vi.mock('$lib/api/jobs', () => ({
	fetchJob: vi.fn(() => Promise.resolve({ ...baseJob })),
	retranscodeJob: vi.fn(),
	skipAndFinalize: vi.fn(() => Promise.resolve({ success: true, message: 'Done' })),
	forceComplete: vi.fn(() => Promise.resolve({ success: true, message: 'Done' })),
	fetchMusicDetail: vi.fn(),
	toggleMultiTitle: vi.fn(),
	updateTrack: vi.fn(),
	fetchNamingPreview: vi.fn(() => Promise.resolve({ success: true, job_title: '', job_folder: '', tracks: [] })),
	searchMetadata: vi.fn(),
	fetchMediaDetail: vi.fn(),
	searchMusicMetadata: vi.fn(),
	setJobTracks: vi.fn(),
	fetchCrcLookup: vi.fn(),
	submitToCrcDb: vi.fn(),
	updateJobConfig: vi.fn(),
	updateJobTitle: vi.fn(),
	updateJobTranscodeConfig: vi.fn()
}));

vi.mock('$lib/api/logs', () => ({
	fetchStructuredLogContent: vi.fn(() => Promise.resolve({ entries: [] })),
	fetchStructuredTranscoderLogContent: vi.fn(() => Promise.resolve({ entries: [] })),
	fetchTranscoderLogForArmJob: vi.fn(() => Promise.resolve({ found: false })),
	fetchLogContent: vi.fn(() => Promise.resolve({ content: '' }))
}));

vi.mock('$lib/api/settings', () => ({
	fetchSettings: vi.fn(() => Promise.resolve({ transcoder_config: { config: {} } }))
}));

import { fetchJob, skipAndFinalize, forceComplete } from '$lib/api/jobs';
const mockFetchJob = vi.mocked(fetchJob);
const mockSkipAndFinalize = vi.mocked(skipAndFinalize);
const mockForceComplete = vi.mocked(forceComplete);

// --- Helpers ---

/** Render the page with the given job status pre-loaded. */
function renderWithStatus(status: string) {
	mockFetchJob.mockResolvedValue({ ...baseJob, status } as any);
	renderComponent(Page);
}

/** Render, wait for the skip button to appear, click it, then confirm the dialog. */
async function clickSkipButton(status = 'waiting_transcode') {
	renderWithStatus(status);
	const btn = await screen.findByText('Skip Transcode & Finalize');
	await fireEvent.click(btn);
	// The skip button now opens a confirmation dialog. Click the dialog's confirm
	// button to actually invoke the API.
	const confirmBtn = await screen.findByText(/yes.*skip.*finalize/i);
	await fireEvent.click(confirmBtn);
}

const SKIP_BTN = 'Skip Transcode & Finalize';

describe('Job detail page — skip transcode', () => {
	afterEach(() => {
		cleanup();
		vi.clearAllMocks();
	});

	it('shows Skip Transcode & Finalize button for waiting_transcode status', async () => {
		renderWithStatus('waiting_transcode');
		await waitFor(() => {
			expect(screen.getByText(SKIP_BTN)).toBeInTheDocument();
		});
	});

	it('does NOT show skip button for transcoding status (backend would 409)', async () => {
		renderWithStatus('transcoding');
		await waitFor(() => {
			expect(screen.getByText('Dashboard')).toBeInTheDocument();
		});
		expect(screen.queryByText(SKIP_BTN)).not.toBeInTheDocument();
	});

	it('does NOT show skip button for other statuses', async () => {
		renderWithStatus('success');
		await waitFor(() => {
			expect(screen.getByText('Dashboard')).toBeInTheDocument();
		});
		expect(screen.queryByText(SKIP_BTN)).not.toBeInTheDocument();
	});

	it('calls skipAndFinalize and shows success feedback', async () => {
		mockSkipAndFinalize.mockResolvedValue({ success: true, message: 'Finalized without transcoding' });
		await clickSkipButton();
		await waitFor(() => {
			expect(mockSkipAndFinalize).toHaveBeenCalledWith(42);
		});
		await waitFor(() => {
			expect(screen.getByText('Finalized without transcoding')).toBeInTheDocument();
		});
	});

	it('shows error feedback when skipAndFinalize returns success=false', async () => {
		mockSkipAndFinalize.mockResolvedValue({ success: false, error: 'Job not found' });
		await clickSkipButton();
		await waitFor(() => {
			expect(screen.getByText('Job not found')).toBeInTheDocument();
		});
	});

	it('shows error feedback when skipAndFinalize throws', async () => {
		mockSkipAndFinalize.mockRejectedValue(new Error('Network error'));
		await clickSkipButton();
		await waitFor(() => {
			expect(screen.getByText('Network error')).toBeInTheDocument();
		});
	});

	it('disables button while skipping is in progress', async () => {
		mockSkipAndFinalize.mockReturnValue(new Promise(() => {}));
		await clickSkipButton();
		await waitFor(() => {
			expect(screen.getByText('Finalizing...')).toBeInTheDocument();
		});
		expect(screen.getByText('Finalizing...').closest('button')).toBeDisabled();
	});
});

describe('Job detail page — skip transcode confirmation dialog', () => {
	afterEach(() => {
		cleanup();
		vi.clearAllMocks();
	});

	it('does not call the API until the user confirms', async () => {
		renderWithStatus('waiting_transcode');
		const skipBtn = await screen.findByText(SKIP_BTN);
		await fireEvent.click(skipBtn);

		// API must not be called yet - dialog must appear first.
		expect(mockSkipAndFinalize).not.toHaveBeenCalled();

		// Dialog is rendered with an explanatory title.
		expect(screen.getByText(/skip transcoding and finalize\?/i)).toBeInTheDocument();

		// Click the dialog's confirm button (distinct label so it does not collide
		// with the page's Skip Transcode & Finalize button).
		const confirmBtn = screen.getByText(/yes.*skip.*finalize/i);
		await fireEvent.click(confirmBtn);

		await waitFor(() => {
			expect(mockSkipAndFinalize).toHaveBeenCalledOnce();
		});
		expect(mockSkipAndFinalize).toHaveBeenCalledWith(42);
	});

	it('cancels without calling the API', async () => {
		renderWithStatus('waiting_transcode');
		const skipBtn = await screen.findByText(SKIP_BTN);
		await fireEvent.click(skipBtn);

		// Dialog appears.
		const dialogTitle = await screen.findByText(/skip transcoding and finalize\?/i);
		expect(dialogTitle).toBeInTheDocument();

		// Cancel the dialog. Use within() to scope to the dialog, in case any
		// other cancel buttons exist elsewhere on the page.
		const dialog = dialogTitle.closest('[data-dialog]') as HTMLElement;
		expect(dialog).not.toBeNull();
		const cancelBtn = within(dialog).getByText('Cancel');
		await fireEvent.click(cancelBtn);

		expect(mockSkipAndFinalize).not.toHaveBeenCalled();
		// Dialog is dismissed.
		await waitFor(() => {
			expect(screen.queryByText(/skip transcoding and finalize\?/i)).not.toBeInTheDocument();
		});
	});
});

const FORCE_BTN = 'Force Complete';

describe('Job detail page — force complete', () => {
	afterEach(() => {
		cleanup();
		vi.clearAllMocks();
	});

	it.each(['waiting_transcode', 'transcoding'])(
		'shows Force Complete button for %s status',
		async (status) => {
			renderWithStatus(status);
			await waitFor(() => {
				expect(screen.getByText(FORCE_BTN)).toBeInTheDocument();
			});
		}
	);

	it('does NOT show Force Complete button for other statuses', async () => {
		renderWithStatus('success');
		await waitFor(() => {
			expect(screen.getByText('Dashboard')).toBeInTheDocument();
		});
		expect(screen.queryByText(FORCE_BTN)).not.toBeInTheDocument();
	});

	it('calls forceComplete and shows success feedback', async () => {
		mockForceComplete.mockResolvedValue({ success: true, message: 'Marked as complete' });
		renderWithStatus('waiting_transcode');
		const btn = await screen.findByText(FORCE_BTN);
		await fireEvent.click(btn);
		await waitFor(() => {
			expect(mockForceComplete).toHaveBeenCalledWith(42);
		});
		await waitFor(() => {
			expect(screen.getByText('Marked as complete')).toBeInTheDocument();
		});
	});

	it('shows error feedback when forceComplete returns success=false', async () => {
		mockForceComplete.mockResolvedValue({ success: false, error: 'Job not found' });
		renderWithStatus('waiting_transcode');
		const btn = await screen.findByText(FORCE_BTN);
		await fireEvent.click(btn);
		await waitFor(() => {
			expect(screen.getByText('Job not found')).toBeInTheDocument();
		});
	});

	it('disables button while force completing is in progress', async () => {
		mockForceComplete.mockReturnValue(new Promise(() => {}));
		renderWithStatus('waiting_transcode');
		const btn = await screen.findByText(FORCE_BTN);
		await fireEvent.click(btn);
		await waitFor(() => {
			expect(screen.getByText('Completing...')).toBeInTheDocument();
		});
		expect(screen.getByText('Completing...').closest('button')).toBeDisabled();
	});
});
