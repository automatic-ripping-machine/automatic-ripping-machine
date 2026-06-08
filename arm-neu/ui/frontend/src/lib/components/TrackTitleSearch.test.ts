import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderComponent, screen, fireEvent, cleanup, waitFor } from '$lib/test-utils';
import TrackTitleSearch from './TrackTitleSearch.svelte';
import type { Track } from '$lib/types/api.gen';
vi.mock('$lib/api/jobs', () => ({
	searchMetadata: vi.fn(),
	fetchMediaDetail: vi.fn(),
	updateTrackTitle: vi.fn(() => Promise.resolve()),
	clearTrackTitle: vi.fn(() => Promise.resolve())
}));

import { searchMetadata, fetchMediaDetail, updateTrackTitle, clearTrackTitle } from '$lib/api/jobs';
const mockSearchMetadata = vi.mocked(searchMetadata);
const mockFetchDetail = vi.mocked(fetchMediaDetail);
const mockUpdateTrackTitle = vi.mocked(updateTrackTitle);
const mockClearTrackTitle = vi.mocked(clearTrackTitle);

function createSearchResult(overrides: Record<string, unknown> = {}) {
	return {
		title: 'Result', year: '2024', imdb_id: 'tt1111',
		poster_url: null, media_type: 'movie',
		...overrides
	};
}

function createTrack(overrides: Partial<Track> = {}): Track {
	return {
		track_id: 1,
		job_id: 1,
		track_number: '1',
		length: 7200,
		aspect_ratio: '16:9',
		fps: 24,
		enabled: true,
		basename: 'title_01',
		filename: 'title_01.mkv',
		orig_filename: 'title_01.mkv',
		new_filename: null,
		ripped: false,
		status: null,
		error: null,
		source: null,
		title: 'Track Title',
		year: '2024',
		imdb_id: null,
		poster_url: null,
		video_type: null,
		episode_number: null,
		episode_name: null,
		custom_filename: null,
		...overrides
	};
}

describe('TrackTitleSearch', () => {
	afterEach(() => {
		cleanup();
		vi.clearAllMocks();
	});

	describe('rendering', () => {
		it('renders search form with pre-filled track title', () => {
			renderComponent(TrackTitleSearch, {
				props: { jobId: 1, track: createTrack() }
			});
			expect(screen.getByDisplayValue('Track Title')).toBeInTheDocument();
		});

		it('renders search button', () => {
			renderComponent(TrackTitleSearch, {
				props: { jobId: 1, track: createTrack() }
			});
			expect(screen.getByText('Search')).toBeInTheDocument();
		});

		it('falls back to basename when no title', () => {
			renderComponent(TrackTitleSearch, {
				props: { jobId: 1, track: createTrack({ title: null, basename: 'title_02' }) }
			});
			expect(screen.getByDisplayValue('title_02')).toBeInTheDocument();
		});
	});

	describe('interactions', () => {
		it('calls searchMetadata on search', async () => {
			mockSearchMetadata.mockResolvedValue([
				createSearchResult({ title: 'Found Title', imdb_id: 'tt2222' })
			]);
			renderComponent(TrackTitleSearch, {
				props: { jobId: 1, track: createTrack() }
			});
			await fireEvent.click(screen.getByText('Search'));
			await waitFor(() => {
				expect(screen.getByText('Found Title')).toBeInTheDocument();
			});
		});

		it('shows no results message', async () => {
			mockSearchMetadata.mockResolvedValue([]);
			renderComponent(TrackTitleSearch, {
				props: { jobId: 1, track: createTrack() }
			});
			await fireEvent.click(screen.getByText('Search'));
			await waitFor(() => {
				expect(screen.getByText(/No results found/)).toBeInTheDocument();
			});
		});

		it('shows error on search failure', async () => {
			mockSearchMetadata.mockRejectedValue(new Error('Search failed'));
			renderComponent(TrackTitleSearch, {
				props: { jobId: 1, track: createTrack() }
			});
			await fireEvent.click(screen.getByText('Search'));
			await waitFor(() => {
				expect(screen.getByText('Search failed')).toBeInTheDocument();
			});
		});

		it('fetches detail when result is selected', async () => {
			mockSearchMetadata.mockResolvedValue([
				createSearchResult({ imdb_id: 'tt3333' })
			]);
			mockFetchDetail.mockResolvedValue({
				title: 'Result', year: '2024', imdb_id: 'tt3333', poster_url: null,
				media_type: 'movie', plot: 'A plot', background_url: null
			});
			renderComponent(TrackTitleSearch, {
				props: { jobId: 1, track: createTrack() }
			});
			await fireEvent.click(screen.getByText('Search'));
			await waitFor(() => expect(screen.getByText('Result')).toBeInTheDocument());
			await fireEvent.click(screen.getByText('Result'));
			await waitFor(() => {
				expect(mockFetchDetail).toHaveBeenCalledWith('tt3333');
			});
		});

		it('renders close button when onclose provided', () => {
			const onclose = vi.fn();
			renderComponent(TrackTitleSearch, {
				props: { jobId: 1, track: createTrack(), onclose }
			});
			const closeBtn = screen.getByTitle('Close');
			expect(closeBtn).toBeInTheDocument();
		});

		it('renders Clear Override button when track has title', () => {
			renderComponent(TrackTitleSearch, {
				props: { jobId: 1, track: createTrack({ title: 'Override Title' }) }
			});
			expect(screen.getByText('Clear Override')).toBeInTheDocument();
		});

		it('calls clearTrackTitle on Clear Override click', async () => {
			const onclear = vi.fn();
			renderComponent(TrackTitleSearch, {
				props: { jobId: 1, track: createTrack({ title: 'Override' }), onclear }
			});
			await fireEvent.click(screen.getByText('Clear Override'));
			await waitFor(() => {
				expect(mockClearTrackTitle).toHaveBeenCalledWith(1, 1);
				expect(onclear).toHaveBeenCalled();
			});
		});

		it('renders year input with pre-filled value', () => {
			renderComponent(TrackTitleSearch, {
				props: { jobId: 1, track: createTrack({ year: '2023' }) }
			});
			expect(screen.getByDisplayValue('2023')).toBeInTheDocument();
		});
	});
});
