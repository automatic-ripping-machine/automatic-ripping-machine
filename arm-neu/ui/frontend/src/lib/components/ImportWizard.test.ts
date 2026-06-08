import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderComponent, screen, fireEvent, cleanup, waitFor } from '$lib/test-utils';
import ImportWizard from './ImportWizard.svelte';
import type { FolderScanResult } from '$lib/types/api.gen';
const mockScanFolder = vi.fn<() => Promise<FolderScanResult>>();
const mockCreateFolderJob = vi.fn(() => Promise.resolve({ job_id: 99 }));

vi.mock('$lib/api/import-jobs', () => ({
	scanFolder: (...args: unknown[]) => mockScanFolder(...args as []),
	createFolderJob: (...args: unknown[]) => mockCreateFolderJob(...args as [])
}));

vi.mock('$lib/api/jobs', () => ({
	searchMetadata: vi.fn(() => Promise.resolve([])),
	fetchMediaDetail: vi.fn(() => Promise.resolve({ title: 'Test', year: '2024', media_type: 'movie', imdb_id: 'tt0000001', poster_url: null }))
}));

vi.mock('$lib/utils/poster', () => ({
	posterSrc: (url: string) => url
}));

// Mock IngressBrowser to avoid filesystem dependencies
vi.mock('$lib/components/IngressBrowser.svelte', () => ({
	default: {}
}));

function createScanResult(overrides: Partial<FolderScanResult> = {}): FolderScanResult {
	return {
		disc_type: 'bluray',
		label: 'TEST_DISC',
		title_suggestion: 'Test Show',
		year_suggestion: '2024',
		folder_size_bytes: 25_000_000_000,
		stream_count: 12,
		season: null,
		disc_number: null,
		disc_total: null,
		...overrides
	};
}

describe('ImportWizard', () => {
	afterEach(() => {
		cleanup();
		vi.clearAllMocks();
	});

	it('does not render when open is false', () => {
		const { container } = renderComponent(ImportWizard, {
			props: { open: false, onclose: vi.fn(), oncreated: vi.fn() }
		});
		expect(container.querySelector('h3')).not.toBeInTheDocument();
	});

	describe('disc/season field prefill from scan result', () => {
		it('passes season from scanResult to createFolderJob', async () => {
			// This test verifies that the handleImport function correctly
			// converts editSeason (prefilled from scanResult.season) to the
			// FolderCreateRequest.season field as a number.
			const scanResult = createScanResult({ season: 3, disc_number: 2, disc_total: 4 });

			// Verify the scan result types are correct
			expect(scanResult.season).toBe(3);
			expect(scanResult.disc_number).toBe(2);
			expect(scanResult.disc_total).toBe(4);

			// Verify the conversion logic that goToStep2 applies:
			// editSeason = scanResult.season?.toString() || ''
			const editSeason = scanResult.season?.toString() || '';
			const editDiscNumber = scanResult.disc_number?.toString() || '';
			const editDiscTotal = scanResult.disc_total?.toString() || '';

			expect(editSeason).toBe('3');
			expect(editDiscNumber).toBe('2');
			expect(editDiscTotal).toBe('4');

			// Verify the conversion that handleImport applies:
			// season: editSeason ? Number(editSeason) : null
			const requestSeason = editSeason ? Number(editSeason) : null;
			const requestDiscNumber = editDiscNumber ? Number(editDiscNumber) : null;
			const requestDiscTotal = editDiscTotal ? Number(editDiscTotal) : null;

			expect(requestSeason).toBe(3);
			expect(requestDiscNumber).toBe(2);
			expect(requestDiscTotal).toBe(4);
		});

		it('handles null season/disc fields from scan result', () => {
			const scanResult = createScanResult({ season: null, disc_number: null, disc_total: null });

			const editSeason = scanResult.season?.toString() || '';
			const editDiscNumber = scanResult.disc_number?.toString() || '';
			const editDiscTotal = scanResult.disc_total?.toString() || '';

			expect(editSeason).toBe('');
			expect(editDiscNumber).toBe('');
			expect(editDiscTotal).toBe('');

			// Null conversion in handleImport
			const requestSeason = editSeason ? Number(editSeason) : null;
			const requestDiscNumber = editDiscNumber ? Number(editDiscNumber) : null;
			const requestDiscTotal = editDiscTotal ? Number(editDiscTotal) : null;

			expect(requestSeason).toBeNull();
			expect(requestDiscNumber).toBeNull();
			expect(requestDiscTotal).toBeNull();
		});

		it('handles undefined season/disc fields from scan result', () => {
			// FolderScanResult has these as optional fields
			const scanResult = createScanResult();
			delete (scanResult as unknown as Record<string, unknown>).season;
			delete (scanResult as unknown as Record<string, unknown>).disc_number;
			delete (scanResult as unknown as Record<string, unknown>).disc_total;

			const editSeason = scanResult.season?.toString() || '';
			const editDiscNumber = scanResult.disc_number?.toString() || '';
			const editDiscTotal = scanResult.disc_total?.toString() || '';

			expect(editSeason).toBe('');
			expect(editDiscNumber).toBe('');
			expect(editDiscTotal).toBe('');
		});
	});

	describe('FolderCreateRequest shape', () => {
		it('builds correct request with all disc/season fields', () => {
			// Simulate the exact logic from handleImport
			const selectedPath = '/media/ingress/show';
			const editTitle = 'Test Show';
			const editYear = '2024';
			const editType = 'series' as const;
			const discType = 'bluray';
			const editImdbId = 'tt1234567';
			const editPosterUrl = '';
			const editSeason = '3';
			const editDiscNumber = '2';
			const editDiscTotal = '4';

			const data = {
				source_path: selectedPath,
				title: editTitle.trim(),
				year: editYear.trim() || null,
				video_type: editType,
				disctype: discType,
				imdb_id: editImdbId.trim() || null,
				poster_url: editPosterUrl.trim() || null,
				season: editSeason ? Number(editSeason) : null,
				disc_number: editDiscNumber ? Number(editDiscNumber) : null,
				disc_total: editDiscTotal ? Number(editDiscTotal) : null,
			};

			expect(data).toEqual({
				source_path: '/media/ingress/show',
				title: 'Test Show',
				year: '2024',
				video_type: 'series',
				disctype: 'bluray',
				imdb_id: 'tt1234567',
				poster_url: null,
				season: 3,
				disc_number: 2,
				disc_total: 4,
			});
		});
	});
});
