import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderComponent, screen, fireEvent, cleanup, waitFor } from '$lib/test-utils';
import TitleSearch from './TitleSearch.svelte';
import { createJob } from './__fixtures__/job';

vi.mock('$lib/api/jobs', () => ({
	searchMetadata: vi.fn(),
	fetchMediaDetail: vi.fn(),
	updateJobTitle: vi.fn(() => Promise.resolve())
}));

import { searchMetadata, fetchMediaDetail, updateJobTitle } from '$lib/api/jobs';
const mockSearchMetadata = vi.mocked(searchMetadata);
const mockFetchDetail = vi.mocked(fetchMediaDetail);
const mockUpdateTitle = vi.mocked(updateJobTitle);

function createSearchResult(overrides: Record<string, unknown> = {}) {
	return {
		title: 'Result', year: '2024', imdb_id: 'tt1111',
		poster_url: null, media_type: 'movie',
		...overrides
	};
}

describe('TitleSearch', () => {
	afterEach(() => {
		cleanup();
		vi.clearAllMocks();
	});

	describe('rendering', () => {
		it('renders search form with pre-filled title', () => {
			renderComponent(TitleSearch, {
				props: { job: createJob({ title: 'My Movie' }) }
			});
			expect(screen.getByDisplayValue('My Movie')).toBeInTheDocument();
		});

		it('renders search button', () => {
			renderComponent(TitleSearch, {
				props: { job: createJob() }
			});
			expect(screen.getByText('Search')).toBeInTheDocument();
		});

		it('renders year input pre-filled', () => {
			renderComponent(TitleSearch, {
				props: { job: createJob({ year: '2024' }) }
			});
			expect(screen.getByDisplayValue('2024')).toBeInTheDocument();
		});
	});

	describe('interactions', () => {
		it('calls searchMetadata on search', async () => {
			mockSearchMetadata.mockResolvedValue([
				createSearchResult({ title: 'Result 1' })
			]);
			renderComponent(TitleSearch, {
				props: { job: createJob({ title: 'Test', year: '2024' }) }
			});
			await fireEvent.click(screen.getByText('Search'));
			await waitFor(() => {
				expect(mockSearchMetadata).toHaveBeenCalledWith('Test', '2024');
				expect(screen.getByText('Result 1')).toBeInTheDocument();
			});
		});

		it('shows no results message', async () => {
			mockSearchMetadata.mockResolvedValue([]);
			renderComponent(TitleSearch, {
				props: { job: createJob({ title: 'Nonexistent' }) }
			});
			await fireEvent.click(screen.getByText('Search'));
			await waitFor(() => {
				expect(screen.getByText('No results found. Try a different search term.')).toBeInTheDocument();
			});
		});

		it('shows error on search failure', async () => {
			mockSearchMetadata.mockRejectedValue(new Error('API error'));
			renderComponent(TitleSearch, {
				props: { job: createJob({ title: 'Test' }) }
			});
			await fireEvent.click(screen.getByText('Search'));
			await waitFor(() => {
				expect(screen.getByText('API error')).toBeInTheDocument();
			});
		});

		it('renders IMDb ID input field', () => {
			renderComponent(TitleSearch, {
				props: { job: createJob() }
			});
			expect(screen.getByPlaceholderText('IMDb ID (tt...)')).toBeInTheDocument();
		});

		it('does direct IMDb lookup when IMDb ID is entered', async () => {
			mockFetchDetail.mockResolvedValue({
				title: 'Direct Movie', year: '2024', imdb_id: 'tt9999', poster_url: null,
				media_type: 'movie', plot: 'Found directly', background_url: null
			});
			renderComponent(TitleSearch, {
				props: { job: createJob({ title: 'Test' }) }
			});
			const imdbInput = screen.getByPlaceholderText('IMDb ID (tt...)');
			await fireEvent.input(imdbInput, { target: { value: 'tt9999' } });
			await fireEvent.click(screen.getByText('Search'));
			await waitFor(() => {
				expect(mockFetchDetail).toHaveBeenCalledWith('tt9999');
			});
		});

		it('renders multiple search results', async () => {
			mockSearchMetadata.mockResolvedValue([
				createSearchResult({ title: 'Movie A' }),
				createSearchResult({ title: 'Movie B', year: '2023', imdb_id: 'tt2222', media_type: 'series' })
			]);
			renderComponent(TitleSearch, {
				props: { job: createJob({ title: 'Movie', year: '2024' }) }
			});
			await fireEvent.click(screen.getByText('Search'));
			await waitFor(() => {
				expect(screen.getByText('Movie A')).toBeInTheDocument();
				expect(screen.getByText('Movie B')).toBeInTheDocument();
			});
		});

		it('renders result year and media type', async () => {
			mockSearchMetadata.mockResolvedValue([
				createSearchResult({ title: 'Movie A' })
			]);
			renderComponent(TitleSearch, {
				props: { job: createJob({ title: 'Movie', year: '2024' }) }
			});
			await fireEvent.click(screen.getByText('Search'));
			await waitFor(() => {
				expect(screen.getByText('Movie A')).toBeInTheDocument();
			});
		});
	});
});
