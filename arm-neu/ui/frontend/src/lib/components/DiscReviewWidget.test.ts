import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderComponent, screen, fireEvent, cleanup, waitFor } from '$lib/test-utils';
import DiscReviewWidget from './DiscReviewWidget.svelte';
import { createJob } from './__fixtures__/job';

vi.mock('$lib/api/jobs', () => ({
	fetchJob: vi.fn(() => Promise.resolve({
		job: { job_id: 1, title: 'Test Movie', status: 'waiting', video_type: 'movie', disctype: 'bluray', label: 'TEST', year: '2024', no_of_titles: 5, crc_id: 'abc123', logfile: 'job_1.log', start_time: '2025-06-15T10:00:00Z', wait_start_time: '2025-06-15T11:55:00Z', devpath: '/dev/sr0', imdb_id: null, poster_url: null, errors: null, multi_title: false },
		tracks: [],
		config: {}
	})),
	cancelWaitingJob: vi.fn(() => Promise.resolve()),
	startWaitingJob: vi.fn(() => Promise.resolve()),
	pauseWaitingJob: vi.fn(() => Promise.resolve()),
	updateJobTitle: vi.fn(() => Promise.resolve()),
	toggleMultiTitle: vi.fn(() => Promise.resolve()),
	updateTrack: vi.fn(() => Promise.resolve()),
	searchMetadata: vi.fn(),
	fetchMediaDetail: vi.fn(),
	searchMusicMetadata: vi.fn(),
	fetchMusicDetail: vi.fn(),
	setJobTracks: vi.fn(),
	fetchCrcLookup: vi.fn(() => Promise.resolve({ no_crc: true })),
	submitToCrcDb: vi.fn(),
	updateJobConfig: vi.fn(() => Promise.resolve()),
	updateJobTranscodeConfig: vi.fn(() => Promise.resolve()),
	fetchNamingPreview: vi.fn(() => Promise.resolve({ success: true, job_title: 'Test Movie', job_folder: 'Test Movie (2024)', tracks: [] }))
}));

vi.mock('$lib/api/settings', () => ({
	fetchSettings: vi.fn(() => Promise.resolve({ transcoder_config: { config: {} } })),
	fetchTranscoderScheme: vi.fn(() => Promise.resolve(null)),
	fetchTranscoderPresets: vi.fn(() => Promise.resolve([])),
	createCustomPreset: vi.fn(() => Promise.resolve(null))
}));

vi.mock('$lib/api/logs', () => ({
	fetchStructuredLogContent: vi.fn(() => Promise.resolve({ entries: [] })),
	fetchLogContent: vi.fn(() => Promise.resolve({ content: '' }))
}));

import { startWaitingJob, cancelWaitingJob, fetchJob, fetchNamingPreview, updateJobTitle, updateJobConfig } from '$lib/api/jobs';
const mockStart = vi.mocked(startWaitingJob);
const mockCancel = vi.mocked(cancelWaitingJob);
const mockFetchJob = vi.mocked(fetchJob);
const mockFetchNamingPreview = vi.mocked(fetchNamingPreview);
const mockUpdateJobTitle = vi.mocked(updateJobTitle);
const mockUpdateJobConfig = vi.mocked(updateJobConfig);

vi.stubGlobal('confirm', vi.fn(() => true));

/** Create a waiting job with common defaults. Merges overrides on top. */
function waitingJob(overrides: Partial<Parameters<typeof createJob>[0]> = {}) {
	return createJob({ status: 'waiting', wait_start_time: '2025-06-15T11:55:00Z', ...overrides });
}

/** Render the widget with a waiting job. Extra props (e.g. ondismiss) can be passed. */
function renderWidget(jobOverrides: Partial<Parameters<typeof createJob>[0]> = {}, extraProps: Record<string, unknown> = {}) {
	return renderComponent(DiscReviewWidget, {
		props: { job: waitingJob(jobOverrides), ...extraProps }
	});
}

describe('DiscReviewWidget', () => {
	afterEach(() => {
		cleanup();
		vi.clearAllMocks();
		vi.mocked(confirm).mockReturnValue(true);
	});

	describe('rendering', () => {
		it('renders job title after loading', async () => {
			renderWidget();
			await waitFor(() => {
				expect(screen.getByText('Test Movie')).toBeInTheDocument();
			});
		});

		it('renders Start and Cancel buttons', async () => {
			renderWidget();
			await waitFor(() => {
				expect(screen.getByText('Start')).toBeInTheDocument();
				expect(screen.getByText('Cancel')).toBeInTheDocument();
			});
		});

		it('renders disc type info', async () => {
			renderWidget({ disctype: 'bluray' });
			await waitFor(() => {
				expect(screen.getByText('Blu-ray')).toBeInTheDocument();
			});
		});

		it('renders drive name from driveNames prop', async () => {
			renderWidget({ devpath: '/dev/sr0' }, { driveNames: { '/dev/sr0': 'Main Drive' } });
			await waitFor(() => {
				expect(screen.getByText('Main Drive')).toBeInTheDocument();
			});
		});

		it('renders disc label', async () => {
			renderWidget({ label: 'MOVIE_DISC' });
			await waitFor(() => {
				expect(screen.getByText('MOVIE_DISC')).toBeInTheDocument();
			});
		});
	});

	describe('Episodes button visibility', () => {
		it('shows Episodes button when video_type is series and imdb_id is set', async () => {
			renderWidget({ video_type: 'series', disctype: 'bluray', imdb_id: 'tt1234567' });
			await waitFor(() => {
				expect(screen.getByText('Episodes')).toBeInTheDocument();
			});
		});

		it.each([
			{ desc: 'movie type even with imdb_id', overrides: { video_type: 'movie', disctype: 'bluray', imdb_id: 'tt1234567' } },
			{ desc: 'series without imdb_id', overrides: { video_type: 'series', disctype: 'bluray', imdb_id: null } },
			{ desc: 'music discs', overrides: { disctype: 'music', video_type: 'music' } },
			{ desc: 'movie disc with no imdb_id', overrides: { video_type: 'movie', disctype: 'bluray', imdb_id: null } }
		])('does NOT show Episodes button for $desc', async ({ overrides }) => {
			renderWidget(overrides);
			await waitFor(() => {
				expect(screen.getByText('Start')).toBeInTheDocument();
			});
			expect(screen.queryByText('Episodes')).not.toBeInTheDocument();
		});
	});

	describe('interactions', () => {
		it('calls startWaitingJob when Start is clicked', async () => {
			renderWidget();
			await waitFor(() => expect(screen.getByText('Start')).toBeInTheDocument());
			await fireEvent.click(screen.getByText('Start'));
			await waitFor(() => {
				expect(mockStart).toHaveBeenCalledWith(1);
			});
		});

		it('calls cancelWaitingJob when Cancel is clicked', async () => {
			renderWidget();
			await waitFor(() => expect(screen.getByText('Cancel')).toBeInTheDocument());
			await fireEvent.click(screen.getByText('Cancel'));
			await waitFor(() => {
				expect(mockCancel).toHaveBeenCalledWith(1);
			});
		});

		it('calls ondismiss after cancel', async () => {
			const ondismiss = vi.fn();
			renderWidget({}, { ondismiss });
			await waitFor(() => expect(screen.getByText('Cancel')).toBeInTheDocument());
			await fireEvent.click(screen.getByText('Cancel'));
			await waitFor(() => {
				expect(ondismiss).toHaveBeenCalled();
			});
		});

		it('calls onrefresh after start', async () => {
			const onrefresh = vi.fn();
			renderWidget({}, { onrefresh });
			await waitFor(() => expect(screen.getByText('Start')).toBeInTheDocument());
			await fireEvent.click(screen.getByText('Start'));
			await waitFor(() => {
				expect(onrefresh).toHaveBeenCalled();
			});
		});
	});

	describe('rendered filenames', () => {
		it('fetches naming preview on load and displays rendered titles in track table', async () => {
			mockFetchJob.mockResolvedValue({
				job_id: 1, title: 'Kolchak', status: 'waiting', video_type: 'series',
				disctype: 'bluray', label: 'TEST', year: '1974', no_of_titles: 2,
				crc_id: null, logfile: null, start_time: '2025-06-15T10:00:00Z',
				wait_start_time: '2025-06-15T11:55:00Z', devpath: '/dev/sr0',
				imdb_id: 'tt0071003', poster_url: null, errors: null, multi_title: false,
				tracks: [
					{ track_id: 1, track_number: '0', length: 3012, filename: 'Kolchak_t00.mkv', enabled: true, aspect_ratio: '16:9', fps: '23.976', ripped: false, basename: null, title: 'Demon in Lace', year: null, video_type: null, poster_url: null, episode_number: '16', episode_name: 'Demon in Lace' }
				],
				config: { MANUAL_WAIT_TIME: 60 }
			} as any);
			mockFetchNamingPreview.mockResolvedValue({
				success: true,
				job_title: 'Kolchak: The Night Stalker S01E16',
				job_folder: 'Kolchak: The Night Stalker/Season 01',
				tracks: [
					{ track_number: '0', rendered_title: 'Demon in Lace S01E16', rendered_folder: 'Kolchak/Season 01' }
				]
			} as any);

			renderWidget({ video_type: 'series', disctype: 'bluray', imdb_id: 'tt0071003' });

			await waitFor(() => expect(screen.getByText('Info')).toBeInTheDocument());
			await fireEvent.click(screen.getByText('Info'));

			await waitFor(() => {
				expect(mockFetchNamingPreview).toHaveBeenCalledWith(1);
			});

			await waitFor(() => {
				expect(screen.getByText('Demon in Lace S01E16')).toBeInTheDocument();
			});
			expect(screen.queryByText('Kolchak_t00.mkv')).not.toBeInTheDocument();
		});

		it('falls back to raw filename when naming preview fails', async () => {
			mockFetchJob.mockResolvedValue({
				job_id: 1, title: 'Test Movie', status: 'waiting', video_type: 'movie',
				disctype: 'bluray', label: 'TEST', year: '2024', no_of_titles: 1,
				crc_id: null, logfile: null, start_time: '2025-06-15T10:00:00Z',
				wait_start_time: '2025-06-15T11:55:00Z', devpath: '/dev/sr0',
				imdb_id: null, poster_url: null, errors: null, multi_title: false,
				tracks: [
					{ track_id: 1, track_number: '0', length: 7200, filename: 'title_t00.mkv', enabled: true, aspect_ratio: '16:9', fps: '23.976', ripped: false, basename: null, title: null, year: null, video_type: null, poster_url: null, episode_number: null, episode_name: null }
				],
				config: { MANUAL_WAIT_TIME: 60 }
			} as any);
			mockFetchNamingPreview.mockRejectedValue(new Error('API down'));

			renderWidget();

			await waitFor(() => expect(screen.getByText('Info')).toBeInTheDocument());
			await fireEvent.click(screen.getByText('Info'));

			await waitFor(() => {
				expect(screen.getByText('title_t00.mkv')).toBeInTheDocument();
			});
		});
	});

	describe('multi-title toggle', () => {
		it('renders Movie/Series buttons when multi_title=true', async () => {
			renderWidget({ multi_title: true, video_type: 'movie', disctype: 'dvd' });
			await waitFor(() => {
				expect(screen.getByText('Movie')).toBeInTheDocument();
				expect(screen.getByText('Series')).toBeInTheDocument();
			});
		});

		it('does NOT render Movie/Series toggle when multi_title=false', async () => {
			renderWidget({ multi_title: false, video_type: 'movie', disctype: 'dvd' });
			await waitFor(() => {
				expect(screen.getByText('Test Movie')).toBeInTheDocument();
			});
			expect(screen.queryByRole('button', { name: 'Movie' })).not.toBeInTheDocument();
		});

		it('calls updateJobTitle on toggle click', async () => {
			mockUpdateJobTitle.mockResolvedValue(undefined as any);
			renderWidget({ multi_title: true, video_type: 'movie', disctype: 'dvd' });
			await waitFor(() => expect(screen.getByText('Series')).toBeInTheDocument());
			await fireEvent.click(screen.getByText('Series'));
			await waitFor(() => {
				expect(mockUpdateJobTitle).toHaveBeenCalledWith(1, { video_type: 'series' });
			});
		});
	});

	describe('auto-default video_type', () => {
		it('fires updateJobTitle({video_type:"movie"}) for unknown+multi_title+dvd', async () => {
			mockUpdateJobTitle.mockResolvedValue(undefined as any);
			renderWidget({ multi_title: true, video_type: 'unknown', disctype: 'dvd' });
			await waitFor(() => {
				expect(mockUpdateJobTitle).toHaveBeenCalledWith(1, { video_type: 'movie' });
			});
		});

		it.each([
			{ desc: 'series', overrides: { multi_title: true, video_type: 'series', disctype: 'dvd' } },
			{ desc: 'single-title', overrides: { multi_title: false, video_type: 'unknown', disctype: 'dvd' } },
			{ desc: 'null disctype', overrides: { multi_title: true, video_type: 'unknown', disctype: null } }
		])('does NOT auto-default for $desc', async ({ overrides }) => {
			mockUpdateJobTitle.mockClear();
			renderWidget(overrides);
			await waitFor(() => {
				expect(screen.getByText('Test Movie')).toBeInTheDocument();
			});
			expect(mockUpdateJobTitle).not.toHaveBeenCalledWith(1, { video_type: 'movie' });
		});
	});

	describe('skip transcode toggle', () => {
		it('renders skip transcode toggle after clicking Transcode button', async () => {
			renderWidget({ video_type: 'movie', disctype: 'bluray' });
			await waitFor(() => expect(screen.getByText('Transcode')).toBeInTheDocument());
			await fireEvent.click(screen.getByText('Transcode'));
			await waitFor(() => {
				expect(screen.getByText('Skip Transcoding')).toBeInTheDocument();
			});
		});

		it('calls updateJobConfig with SKIP_TRANSCODE when toggled', async () => {
			mockUpdateJobConfig.mockResolvedValue(undefined as any);
			renderWidget({ video_type: 'movie', disctype: 'bluray' });
			await waitFor(() => expect(screen.getByText('Transcode')).toBeInTheDocument());
			await fireEvent.click(screen.getByText('Transcode'));
			await waitFor(() => expect(screen.getByTitle('Files will be sent to transcoder')).toBeInTheDocument());
			await fireEvent.click(screen.getByTitle('Files will be sent to transcoder'));
			await waitFor(() => {
				expect(mockUpdateJobConfig).toHaveBeenCalledWith(1, { SKIP_TRANSCODE: true });
			});
		});

		it('reverts skipTranscode and shows error when updateJobConfig rejects', async () => {
			mockUpdateJobConfig.mockRejectedValue(new Error('Network failure'));
			renderWidget({ video_type: 'movie', disctype: 'bluray' });
			await waitFor(() => expect(screen.getByText('Transcode')).toBeInTheDocument());
			await fireEvent.click(screen.getByText('Transcode'));
			// Toggle starts as off ("Files will be sent to transcoder")
			await waitFor(() => expect(screen.getByTitle('Files will be sent to transcoder')).toBeInTheDocument());
			await fireEvent.click(screen.getByTitle('Files will be sent to transcoder'));
			// After rejection, toggle should revert back to off state
			await waitFor(() => {
				expect(screen.getByTitle('Files will be sent to transcoder')).toBeInTheDocument();
			});
			// Error message should be displayed
			await waitFor(() => {
				expect(screen.getByText(/Failed to update skip transcode.*Network failure/)).toBeInTheDocument();
			});
		});
	});

	describe('field visibility for multi-title', () => {
		it('hides Search button for multi-title movie', async () => {
			renderWidget({ multi_title: true, video_type: 'movie', disctype: 'dvd' });
			await waitFor(() => {
				expect(screen.getByText('Start')).toBeInTheDocument();
			});
			expect(screen.queryByText('Search')).not.toBeInTheDocument();
		});

		it.each([
			{ desc: 'multi-title series', overrides: { multi_title: true, video_type: 'series', disctype: 'dvd' } },
			{ desc: 'single-title movie', overrides: { multi_title: false, video_type: 'movie', disctype: 'dvd' } }
		])('shows Search button for $desc', async ({ overrides }) => {
			renderWidget(overrides);
			await waitFor(() => {
				expect(screen.getByText('Search')).toBeInTheDocument();
			});
		});
	});

	it('renders skeleton when primary data prop is omitted', () => {
		const { container } = renderComponent(DiscReviewWidget, { props: {} });
		expect(container.querySelector('[aria-busy="true"]')).not.toBeNull();
	});
});
