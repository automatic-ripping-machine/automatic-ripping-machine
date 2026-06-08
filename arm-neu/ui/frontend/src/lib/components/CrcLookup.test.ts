import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderComponent, screen, cleanup, waitFor } from '$lib/test-utils';
import CrcLookup from './CrcLookup.svelte';
import { createJob } from './__fixtures__/job';

vi.mock('$lib/api/jobs', () => ({
	fetchCrcLookup: vi.fn(),
	submitToCrcDb: vi.fn(() => Promise.resolve()),
	updateJobTitle: vi.fn(() => Promise.resolve())
}));

import { fetchCrcLookup } from '$lib/api/jobs';
const mockFetchCrcLookup = vi.mocked(fetchCrcLookup);

describe('CrcLookup', () => {
	afterEach(() => {
		cleanup();
		vi.clearAllMocks();
	});

	describe('rendering', () => {
		it('shows loading state initially', () => {
			mockFetchCrcLookup.mockReturnValue(new Promise(() => {}));
			renderComponent(CrcLookup, {
				props: { job: createJob({ crc_id: 'abc123' }) }
			});
			expect(screen.getByText('Looking up CRC database...')).toBeInTheDocument();
		});

		it('shows CRC hash when present', () => {
			mockFetchCrcLookup.mockReturnValue(new Promise(() => {}));
			renderComponent(CrcLookup, {
				props: { job: createJob({ crc_id: 'abc123def456' }) }
			});
			expect(screen.getByText('abc123def456')).toBeInTheDocument();
		});

		it('shows no matches message', async () => {
			mockFetchCrcLookup.mockResolvedValue({ found: false, results: [], has_api_key: true });
			renderComponent(CrcLookup, {
				props: { job: createJob({ crc_id: 'abc123' }) }
			});
			await waitFor(() => {
				expect(screen.getByText('No matches found in the CRC database.')).toBeInTheDocument();
			});
		});

		it('shows no CRC message for non-applicable discs', async () => {
			mockFetchCrcLookup.mockResolvedValue({ found: false, results: [], no_crc: true });
			renderComponent(CrcLookup, {
				props: { job: createJob() }
			});
			await waitFor(() => {
				expect(screen.getByText('No CRC hash for this disc type.')).toBeInTheDocument();
			});
		});

		it('shows error from lookup response', async () => {
			mockFetchCrcLookup.mockResolvedValue({ found: false, results: [], error: 'Service unavailable' });
			renderComponent(CrcLookup, {
				props: { job: createJob({ crc_id: 'abc123' }) }
			});
			await waitFor(() => {
				expect(screen.getByText('Service unavailable')).toBeInTheDocument();
			});
		});

		it('shows lookup error on fetch failure', async () => {
			mockFetchCrcLookup.mockRejectedValue(new Error('Network error'));
			renderComponent(CrcLookup, {
				props: { job: createJob({ crc_id: 'abc123' }) }
			});
			await waitFor(() => {
				expect(screen.getByText('Network error')).toBeInTheDocument();
			});
		});

		it('renders results with Apply button', async () => {
			mockFetchCrcLookup.mockResolvedValue({
				found: true,
				has_api_key: true,
				results: [{
					title: 'Found Movie',
					year: '2024',
					video_type: 'movie',
					disctype: 'bluray',
					label: 'FOUND_MOVIE',
					imdb_id: 'tt9999999',
					tmdb_id: '',
					poster_url: '',
					hasnicetitle: 'True',
					validated: 'True',
					date_added: '2025-01-01T00:00:00.000'
				}]
			});
			renderComponent(CrcLookup, {
				props: { job: createJob({ crc_id: 'abc123' }) }
			});
			await waitFor(() => {
				expect(screen.getByText('Found Movie')).toBeInTheDocument();
				expect(screen.getByText('Apply to Job')).toBeInTheDocument();
			});
		});
	});

	describe('submit section', () => {
		it('shows submit form when has_api_key is true', async () => {
			mockFetchCrcLookup.mockResolvedValue({ found: false, results: [], has_api_key: true });
			renderComponent(CrcLookup, {
				props: { job: createJob({ crc_id: 'abc123' }) }
			});
			await waitFor(() => {
				expect(screen.getByText('Submit to CRC Database')).toBeInTheDocument();
			});
		});

		it('pre-fills form with job metadata', async () => {
			mockFetchCrcLookup.mockResolvedValue({ found: false, results: [], has_api_key: true });
			renderComponent(CrcLookup, {
				props: { job: createJob({ title: 'My Film', year: '2023' }) }
			});
			await waitFor(() => {
				expect(screen.getByDisplayValue('My Film')).toBeInTheDocument();
				expect(screen.getByDisplayValue('2023')).toBeInTheDocument();
			});
		});
	});
});
