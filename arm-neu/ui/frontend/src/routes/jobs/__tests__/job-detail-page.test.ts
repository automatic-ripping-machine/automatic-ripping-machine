import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderComponent, screen, cleanup, waitFor } from '$lib/test-utils';
import JobDetailPage from '../[id]/+page.svelte';

vi.mock('$app/stores', async () => {
	const { readable } = await import('svelte/store');
	return { page: readable({ params: { id: '1' } }) };
});

vi.mock('$app/navigation', () => ({
	goto: vi.fn()
}));

const { buildJob } = vi.hoisted(() => {
	const baseMovieJob = {
		job_id: 1, title: 'Test Movie', status: 'success', video_type: 'movie',
		year: '2024', disctype: 'bluray', label: 'TEST_MOVIE', start_time: '2025-06-15T10:00:00Z',
		stop_time: '2025-06-15T11:00:00Z', job_length: '1h 0m', devpath: '/dev/sr0',
		imdb_id: 'tt1234567', poster_url: null, errors: null, stage: null,
		no_of_titles: 3, logfile: 'job_1.log', crc_id: 'abc123', multi_title: false,
		source_type: 'disc', source_path: null, path: null, raw_path: null, transcode_path: null,
		disc_number: null, disc_total: null, season: null, season_auto: null, tvdb_id: null,
		artist: null, artist_auto: null, album: null, album_auto: null,
		tracks: [
			{ track_id: 1, job_id: 1, track_number: '1', length: 7200, aspect_ratio: '16:9', fps: 24, enabled: true, basename: 'title_01', filename: 'title_01.mkv', orig_filename: 'title_01.mkv', new_filename: null, ripped: true, status: 'success', error: null, source: null, title: null, year: null, imdb_id: null, poster_url: null, video_type: null, episode_number: null, episode_name: null }
		],
		config: {}
	};
	return { buildJob: (overrides: Record<string, unknown> = {}) => ({ ...baseMovieJob, ...overrides }) };
});

vi.mock('$lib/api/jobs', () => ({
	fetchJob: vi.fn(() => Promise.resolve(buildJob())),
	retranscodeJob: vi.fn(() => Promise.resolve({ status: 'ok', message: 'Queued' })),
	fetchMusicDetail: vi.fn(),
	toggleMultiTitle: vi.fn(() => Promise.resolve()),
	updateTrack: vi.fn(() => Promise.resolve()),
	abandonJob: vi.fn(),
	deleteJob: vi.fn(),
	fixJobPermissions: vi.fn(),
	searchMetadata: vi.fn(),
	fetchMediaDetail: vi.fn(),
	searchMusicMetadata: vi.fn(),
	setJobTracks: vi.fn(),
	fetchCrcLookup: vi.fn(() => Promise.resolve({ no_crc: true })),
	submitToCrcDb: vi.fn(),
	updateJobTitle: vi.fn(() => Promise.resolve()),
	updateJobConfig: vi.fn(() => Promise.resolve()),
	updateJobTranscodeConfig: vi.fn(() => Promise.resolve()),
	updateTrackTitle: vi.fn(() => Promise.resolve()),
	clearTrackTitle: vi.fn(() => Promise.resolve()),
	tvdbMatch: vi.fn(() => Promise.resolve({ success: true, matches: [] })),
	fetchTvdbEpisodes: vi.fn(() => Promise.resolve({ episodes: [] })),
	fetchNamingPreview: vi.fn(() => Promise.resolve({ previews: [] }))
}));

vi.mock('$lib/api/logs', () => ({
	fetchStructuredLogContent: vi.fn(() => Promise.resolve({ entries: [] })),
	fetchStructuredTranscoderLogContent: vi.fn(() => Promise.resolve({ entries: [] })),
	fetchTranscoderLogForArmJob: vi.fn(() => Promise.resolve(null))
}));

vi.mock('$lib/api/settings', () => ({
	fetchSettings: vi.fn(() => Promise.resolve({ transcoder_config: { config: {} } }))
}));

describe('Job Detail Page', () => {
	afterEach(() => cleanup());

	describe('rendering', () => {
		it('renders job title after loading', async () => {
			renderComponent(JobDetailPage);
			await waitFor(() => {
				expect(screen.getByRole('heading', { name: 'Test Movie' })).toBeInTheDocument();
			});
		});

		it('renders breadcrumb navigation', async () => {
			renderComponent(JobDetailPage);
			await waitFor(() => {
				expect(screen.getByText('Dashboard')).toBeInTheDocument();
			});
		});

		it('renders status badge', async () => {
			renderComponent(JobDetailPage);
			await waitFor(() => {
				const matches = screen.getAllByText('Success');
				expect(matches.length).toBeGreaterThanOrEqual(1);
			});
		});

		it('renders disc type', async () => {
			renderComponent(JobDetailPage);
			await waitFor(() => {
				expect(screen.getByText('Blu-ray')).toBeInTheDocument();
			});
		});

		it('renders tracks table', async () => {
			renderComponent(JobDetailPage);
			await waitFor(() => {
				expect(screen.getByText('title_01.mkv')).toBeInTheDocument();
			});
		});

		it('renders without crashing', () => {
			const { container } = renderComponent(JobDetailPage);
			expect(container).toBeInTheDocument();
		});

		it('hides Episodes tab for movie jobs even when imdb_id is set', async () => {
			// Repro: hifi job 222 (Annihilation, video_type=movie, imdb_id=tt2798920)
			// rendered the Episodes tab + an empty matcher message because the
			// tab gate was `series || imdb_id`. The correct gate is series AND imdb_id.
			renderComponent(JobDetailPage);
			await waitFor(() => {
				expect(screen.getByRole('heading', { name: 'Test Movie' })).toBeInTheDocument();
			});
			expect(screen.queryByRole('button', { name: 'Episodes' })).not.toBeInTheDocument();
		});
	});

	describe('series jobs', () => {
		it('shows Episodes tab for series jobs with imdb_id', async () => {
			const { fetchJob } = await import('$lib/api/jobs');
			vi.mocked(fetchJob).mockResolvedValueOnce(buildJob({
				job_id: 2, title: 'Test Series', video_type: 'series', imdb_id: 'tt9999999', tracks: []
			}) as never);

			renderComponent(JobDetailPage);
			await waitFor(() => {
				expect(screen.getByRole('button', { name: 'Episodes' })).toBeInTheDocument();
			});
		});

		it('hides Episodes tab for series jobs without imdb_id', async () => {
			const { fetchJob } = await import('$lib/api/jobs');
			vi.mocked(fetchJob).mockResolvedValueOnce(buildJob({
				job_id: 3, title: 'Unidentified Series', video_type: 'series', imdb_id: null, tracks: []
			}) as never);

			renderComponent(JobDetailPage);
			await waitFor(() => {
				expect(screen.getByRole('heading', { name: 'Unidentified Series' })).toBeInTheDocument();
			});
			expect(screen.queryByRole('button', { name: 'Episodes' })).not.toBeInTheDocument();
		});
	});

	describe('error handling', () => {
		it('redirects to home on 404', async () => {
			const { fetchJob } = await import('$lib/api/jobs');
			const { goto } = await import('$app/navigation');
			vi.mocked(fetchJob).mockRejectedValueOnce(new Error('404 Not Found'));

			renderComponent(JobDetailPage);
			await waitFor(() => {
				expect(goto).toHaveBeenCalledWith('/');
			});
		});
	});
});
