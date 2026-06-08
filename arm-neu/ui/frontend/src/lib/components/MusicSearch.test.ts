import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderComponent, screen, fireEvent, cleanup, waitFor } from '$lib/test-utils';
import MusicSearch from './MusicSearch.svelte';
import { createJob } from './__fixtures__/job';

vi.mock('$lib/api/jobs', () => ({
	searchMusicMetadata: vi.fn(),
	fetchMusicDetail: vi.fn(),
	updateJobTitle: vi.fn(() => Promise.resolve()),
	setJobTracks: vi.fn(() => Promise.resolve())
}));

import { searchMusicMetadata, fetchMusicDetail, updateJobTitle } from '$lib/api/jobs';
const mockSearchMusicMetadata = vi.mocked(searchMusicMetadata);
const mockFetchMusicDetail = vi.mocked(fetchMusicDetail);
const mockUpdateJobTitle = vi.mocked(updateJobTitle);

function createMusicResult(overrides: Record<string, unknown> = {}) {
	return {
		release_id: 'r1', title: 'Album', artist: 'Artist', year: '2024',
		country: 'US', format: 'CD', track_count: 10, release_type: 'Album',
		poster_url: null, media_type: 'release', label: null,
		...overrides
	};
}

describe('MusicSearch', () => {
	afterEach(() => {
		cleanup();
		vi.clearAllMocks();
	});

	describe('rendering', () => {
		it('renders search form with pre-filled album/title', () => {
			renderComponent(MusicSearch, {
				props: { job: createJob({ album: 'My Album', title: 'Fallback' }) }
			});
			expect(screen.getByDisplayValue('My Album')).toBeInTheDocument();
		});

		it('renders artist input pre-filled', () => {
			renderComponent(MusicSearch, {
				props: { job: createJob({ artist: 'The Band' }) }
			});
			expect(screen.getByDisplayValue('The Band')).toBeInTheDocument();
		});

		it('renders search button', () => {
			renderComponent(MusicSearch, {
				props: { job: createJob() }
			});
			expect(screen.getByText('Search')).toBeInTheDocument();
		});
	});

	describe('interactions', () => {
		it('calls searchMusicMetadata on search', async () => {
			mockSearchMusicMetadata.mockResolvedValue({
				results: [createMusicResult({ title: 'Found Album', track_count: 12 })],
				total: 1
			});
			renderComponent(MusicSearch, {
				props: { job: createJob({ album: 'Search Term' }) }
			});
			await fireEvent.click(screen.getByText('Search'));
			await waitFor(() => {
				expect(mockSearchMusicMetadata).toHaveBeenCalled();
				expect(screen.getByText('Found Album')).toBeInTheDocument();
			});
		});

		it('shows no results message', async () => {
			mockSearchMusicMetadata.mockResolvedValue({ results: [], total: 0 });
			renderComponent(MusicSearch, {
				props: { job: createJob({ album: 'Nothing' }) }
			});
			await fireEvent.click(screen.getByText('Search'));
			await waitFor(() => {
				expect(screen.getByText(/No results found/)).toBeInTheDocument();
			});
		});

		it('shows error on search failure', async () => {
			mockSearchMusicMetadata.mockRejectedValue(new Error('MusicBrainz error'));
			renderComponent(MusicSearch, {
				props: { job: createJob({ album: 'Test' }) }
			});
			await fireEvent.click(screen.getByText('Search'));
			await waitFor(() => {
				expect(screen.getByText('MusicBrainz error')).toBeInTheDocument();
			});
		});

		it('renders result cards with artist and year', async () => {
			mockSearchMusicMetadata.mockResolvedValue({
				results: [
					createMusicResult({ release_id: 'r1', title: 'Album One', artist: 'Band A' }),
					createMusicResult({ release_id: 'r2', title: 'Album Two', artist: 'Band B', year: '2023', country: 'UK', format: 'Vinyl', track_count: 8 })
				],
				total: 2
			});
			renderComponent(MusicSearch, {
				props: { job: createJob({ album: 'Test' }) }
			});
			await fireEvent.click(screen.getByText('Search'));
			await waitFor(() => {
				expect(screen.getByText('Album One')).toBeInTheDocument();
				expect(screen.getByText('Album Two')).toBeInTheDocument();
				expect(screen.getByText('Band A')).toBeInTheDocument();
				expect(screen.getByText('Band B')).toBeInTheDocument();
			});
		});

		it('renders result count', async () => {
			mockSearchMusicMetadata.mockResolvedValue({
				results: [createMusicResult()],
				total: 25
			});
			renderComponent(MusicSearch, {
				props: { job: createJob({ album: 'Test' }) }
			});
			await fireEvent.click(screen.getByText('Search'));
			await waitFor(() => {
				expect(screen.getByText(/25/)).toBeInTheDocument();
			});
		});

		it('falls back to title when no album', () => {
			renderComponent(MusicSearch, {
				props: { job: createJob({ album: null, title: 'Fallback Title' }) }
			});
			expect(screen.getByDisplayValue('Fallback Title')).toBeInTheDocument();
		});
	});
});
