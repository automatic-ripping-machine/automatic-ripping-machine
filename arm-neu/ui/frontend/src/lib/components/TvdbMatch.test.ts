import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderComponent, screen, fireEvent, cleanup, waitFor } from '$lib/test-utils';
import TvdbMatch from './TvdbMatch.svelte';

vi.mock('$lib/api/jobs', () => ({
	tvdbMatch: vi.fn(),
	fetchTvdbEpisodes: vi.fn()
}));

import { tvdbMatch, fetchTvdbEpisodes } from '$lib/api/jobs';
import { createJob } from './__fixtures__/job';
import type { JobDetailSchema as JobDetail } from '$lib/types/api.gen';
const mockTvdbMatch = vi.mocked(tvdbMatch);
const mockFetchEpisodes = vi.mocked(fetchTvdbEpisodes);

function createTrack(id: number, trackNum: string, length: number) {
	return {
		track_id: id, job_id: 1, track_number: trackNum, length, aspect_ratio: null, fps: null,
		enabled: true, basename: `t${id}`, filename: `t${id}.mkv`, orig_filename: `t${id}.mkv`,
		new_filename: null, ripped: true, status: null, error: null, source: null,
		title: null, year: null, imdb_id: null, poster_url: null, video_type: null,
		episode_number: null, episode_name: null
	};
}

function createJobDetail(overrides: Record<string, unknown> = {}): JobDetail {
	const base = createJob({
		title: 'Test Series', status: 'success', video_type: 'series',
		year: '2024', disctype: 'bluray', season: '2', season_auto: null,
		tvdb_id: 12345, ...overrides
	});
	return {
		...base,
		tracks: [createTrack(1, '1', 2400), createTrack(2, '2', 2500), createTrack(3, '3', 2300)],
		config: {}
	} as JobDetail;
}

describe('TvdbMatch', () => {
	afterEach(() => {
		cleanup();
		vi.clearAllMocks();
	});

	describe('rendering', () => {
		it('renders tab buttons', () => {
			renderComponent(TvdbMatch, { props: { job: createJobDetail() } });
			expect(screen.getByText('Match Tracks')).toBeInTheDocument();
			expect(screen.getByText('Browse Episodes')).toBeInTheDocument();
		});

		it('renders Preview Match button', () => {
			renderComponent(TvdbMatch, { props: { job: createJobDetail() } });
			expect(screen.getByText('Preview Match')).toBeInTheDocument();
		});

		it('pre-fills season from job', () => {
			renderComponent(TvdbMatch, { props: { job: createJobDetail({ season: '3' }) } });
			expect(screen.getByDisplayValue('3')).toBeInTheDocument();
		});

		it('shows TVDB ID when present', () => {
			renderComponent(TvdbMatch, { props: { job: createJobDetail() } });
			expect(screen.getByText('TVDB 12345')).toBeInTheDocument();
		});
	});

	describe('match flow', () => {
		it('calls tvdbMatch on Preview click', async () => {
			mockTvdbMatch.mockResolvedValue({
				success: true, matcher: 'runtime', season: 2,
				matches: [
					{ track_number: '1', episode_number: 1, episode_name: 'Pilot', episode_runtime: 2400 }
				],
				match_count: 1, score: 95, alternatives: []
			});
			renderComponent(TvdbMatch, { props: { job: createJobDetail() } });
			await fireEvent.click(screen.getByText('Preview Match'));
			await waitFor(() => {
				expect(mockTvdbMatch).toHaveBeenCalledWith(1, expect.objectContaining({ apply: false }));
				expect(screen.getByText('Pilot')).toBeInTheDocument();
			});
		});

		it('shows Apply button after preview', async () => {
			mockTvdbMatch.mockResolvedValue({
				success: true, matcher: 'runtime', season: 2,
				matches: [{ track_number: '1', episode_number: 1, episode_name: 'Pilot', episode_runtime: 2400 }],
				match_count: 1, score: 90, alternatives: []
			});
			renderComponent(TvdbMatch, { props: { job: createJobDetail() } });
			await fireEvent.click(screen.getByText('Preview Match'));
			await waitFor(() => {
				expect(screen.getByText(/Apply 1 Match/)).toBeInTheDocument();
			});
		});

		it('shows error on match failure', async () => {
			mockTvdbMatch.mockRejectedValue(new Error('TVDB unavailable'));
			renderComponent(TvdbMatch, { props: { job: createJobDetail() } });
			await fireEvent.click(screen.getByText('Preview Match'));
			await waitFor(() => {
				expect(screen.getByText('TVDB unavailable')).toBeInTheDocument();
			});
		});
	});

	describe('browse flow', () => {
		it('switches to Browse tab and loads episodes', async () => {
			mockFetchEpisodes.mockResolvedValue({
				episodes: [
					{ number: 1, name: 'Episode One', runtime: 40, aired: '2024-01-15' },
					{ number: 2, name: 'Episode Two', runtime: 42, aired: '2024-01-22' }
				],
				tvdb_id: 12345, season: 2
			});
			renderComponent(TvdbMatch, { props: { job: createJobDetail() } });
			await fireEvent.click(screen.getByText('Browse Episodes'));
			await fireEvent.click(screen.getByText('Load Episodes'));
			await waitFor(() => {
				expect(screen.getByText('Episode One')).toBeInTheDocument();
				expect(screen.getByText('Episode Two')).toBeInTheDocument();
			});
		});

		it('shows error on browse failure', async () => {
			mockFetchEpisodes.mockRejectedValue(new Error('Not found'));
			renderComponent(TvdbMatch, { props: { job: createJobDetail() } });
			await fireEvent.click(screen.getByText('Browse Episodes'));
			await fireEvent.click(screen.getByText('Load Episodes'));
			await waitFor(() => {
				expect(screen.getByText('Not found')).toBeInTheDocument();
			});
		});
	});
});
