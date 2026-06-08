import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderComponent, screen, cleanup, fireEvent, waitFor } from '$lib/test-utils';
import ImportWizard from '../ImportWizard.svelte';
import IngressBrowserMock from './IngressBrowserMock.svelte';

vi.mock('$lib/components/IngressBrowser.svelte', async () => ({
	default: (await import('./IngressBrowserMock.svelte')).default
}));

const searchMetadataMock = vi.fn(() => Promise.resolve([]));
const scanIsoMock = vi.fn<(path: string) => Promise<unknown>>(() => Promise.resolve({
	disc_type: 'bluray', iso_size: 12345678, stream_count: 7,
	label: 'MOVIE_ISO', title_suggestion: 'ISO Movie', year_suggestion: '2025',
	volume_id: 'VOL_LABEL_HERE'
}));
const createIsoJobMock = vi.fn<(data: Record<string, unknown>) => Promise<unknown>>(() => Promise.resolve({ success: true, job_id: 2 }));
const scanFolderMock = vi.fn<(path: string) => Promise<unknown>>(() => Promise.resolve({
	disc_type: 'bluray', folder_size_bytes: 25000000000, stream_count: 5,
	label: 'TEST_DISC', title_suggestion: 'Test Movie', year_suggestion: '2025',
	season: null, disc_number: null, disc_total: null
}));
const createFolderJobMock = vi.fn<(data: Record<string, unknown>) => Promise<unknown>>(() => Promise.resolve({ job_id: 1 }));

vi.mock('$lib/api/import-jobs', () => ({
	scanFolder: (path: string) => scanFolderMock(path),
	createFolderJob: (data: Record<string, unknown>) => createFolderJobMock(data),
	scanIso: (path: string) => scanIsoMock(path),
	createIsoJob: (data: Record<string, unknown>) => createIsoJobMock(data),
	fetchIngressRoot: vi.fn(() => Promise.resolve([
		{ key: 'ingress', label: 'Ingress', path: '/home/arm/ingress' }
	])),
	fetchIngressDirectory: vi.fn(() => Promise.resolve({
		path: '/home/arm/ingress',
		entries: [
			{ name: 'Movie_Folder', type: 'directory', size: 4294967296, modified: '2025-06-15T12:00:00Z', extension: '', category: 'directory', permissions: 'rwxr-xr-x', owner: 'arm', group: 'arm' }
		]
	}))
}));

vi.mock('$lib/api/jobs', () => ({
	searchMetadata: (...args: unknown[]) => searchMetadataMock(...(args as [])),
	fetchMediaDetail: vi.fn(() => Promise.resolve({}))
}));

void IngressBrowserMock; // ensure import isn't tree-shaken

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

vi.mock('$lib/stores/importWizard', async () => {
	const { writable } = await import('svelte/store');
	return { showImportWizard: writable(false) };
});

describe('ImportWizard', () => {
	afterEach(() => {
		cleanup();
		vi.clearAllMocks();
	});

	it('renders dialog when open', () => {
		renderComponent(ImportWizard, {
			props: { open: true, onclose: vi.fn(), oncreated: vi.fn() }
		});
		// h3 is the wizard title (and the only h3 in the dialog).
		expect(screen.getByRole('heading', { level: 3, name: 'Import' })).toBeInTheDocument();
	});

	it('shows X close button in header', () => {
		renderComponent(ImportWizard, {
			props: { open: true, onclose: vi.fn(), oncreated: vi.fn() }
		});
		expect(screen.getByLabelText('Close', { selector: 'button' })).toBeInTheDocument();
	});

	it('shows progress dots in footer', () => {
		const { container } = renderComponent(ImportWizard, {
			props: { open: true, onclose: vi.fn(), oncreated: vi.fn() }
		});
		const dots = container.querySelectorAll('.h-2.w-2.rounded-full');
		// 4-step wizard: Pick -> Verify metadata -> OMDB Match -> Confirm
		expect(dots.length).toBe(4);
	});

	it('renders source browser on step 1', () => {
		renderComponent(ImportWizard, {
			props: { open: true, onclose: vi.fn(), oncreated: vi.fn() }
		});
		// The Next button is present on step 1
		expect(screen.getByText('Next')).toBeInTheDocument();
	});

	it('does not render when closed', () => {
		renderComponent(ImportWizard, {
			props: { open: false, onclose: vi.fn(), oncreated: vi.fn() }
		});
		expect(screen.queryByRole('heading', { level: 3, name: 'Import' })).not.toBeInTheDocument();
	});

	describe('4-step flow (Pick -> Verify -> OMDB -> Confirm)', () => {
		async function advanceToStep2() {
			renderComponent(ImportWizard, {
				props: { open: true, onclose: vi.fn(), oncreated: vi.fn() }
			});
			// Step 1: pick a folder via the mocked IngressBrowser, then click Next.
			await fireEvent.click(screen.getByTestId('folder-browser-mock-select'));
			await fireEvent.click(screen.getByText('Next'));
			// scanFolder resolves, wizard auto-advances to step 2.
			await waitFor(() => expect(screen.getByText('Looks good')).toBeInTheDocument());
		}

		it('step 2 shows both "Looks good" (skip OMDB) and "Search OMDB" buttons', async () => {
			await advanceToStep2();
			expect(screen.getByText('Looks good')).toBeInTheDocument();
			expect(screen.getByText('Search OMDB')).toBeInTheDocument();
		});

		it('"Looks good" on step 2 jumps directly to step 4 (Confirm), skipping OMDB', async () => {
			await advanceToStep2();
			await fireEvent.click(screen.getByText('Looks good'));
			// Step 4 has the Import button (look for button specifically; "Import" is also the wizard title)
			await waitFor(() => expect(screen.getByRole('button', { name: 'Import' })).toBeInTheDocument());
		});

		it('"Search OMDB" on step 2 advances to step 3 and auto-fires the search', async () => {
			searchMetadataMock.mockClear();
			await advanceToStep2();
			await fireEvent.click(screen.getByText('Search OMDB'));
			// Step 3 has a "Next" button (advances to Confirm) and a search input.
			await waitFor(() => {
				expect(screen.getByPlaceholderText('Search title...')).toBeInTheDocument();
			});
			// Auto-search fires with the seeded title.
			await waitFor(() => expect(searchMetadataMock).toHaveBeenCalled());
		});
	});

	describe('ISO branch', () => {
		it('selecting ISO calls scanIso (not scanFolder) and shows volume id', async () => {
			scanFolderMock.mockClear();
			scanIsoMock.mockClear();
			renderComponent(ImportWizard, {
				props: { open: true, onclose: vi.fn(), oncreated: vi.fn() }
			});
			// Step 1: pick the ISO via the mocked IngressBrowser, then click Next.
			await fireEvent.click(screen.getByTestId('folder-browser-mock-select-iso'));
			await fireEvent.click(screen.getByText('Next'));

			await waitFor(() => expect(scanIsoMock).toHaveBeenCalledWith('/home/arm/ingress/Movie.iso'));
			expect(scanFolderMock).not.toHaveBeenCalled();

			// Step 2 shows the ISO Volume ID surfaced from the scan result.
			await waitFor(() => {
				expect(screen.getByText('VOL_LABEL_HERE')).toBeInTheDocument();
			});
		});

		it('Import on ISO flow calls createIsoJob (not createFolderJob)', async () => {
			scanFolderMock.mockClear();
			createIsoJobMock.mockClear();
			createFolderJobMock.mockClear();
			renderComponent(ImportWizard, {
				props: { open: true, onclose: vi.fn(), oncreated: vi.fn() }
			});
			await fireEvent.click(screen.getByTestId('folder-browser-mock-select-iso'));
			await fireEvent.click(screen.getByText('Next'));
			await waitFor(() => expect(screen.getByText('Looks good')).toBeInTheDocument());
			await fireEvent.click(screen.getByText('Looks good'));
			await waitFor(() => expect(screen.getByRole('button', { name: 'Import' })).toBeInTheDocument());
			await fireEvent.click(screen.getByRole('button', { name: 'Import' }));

			await waitFor(() => expect(createIsoJobMock).toHaveBeenCalled());
			expect(createFolderJobMock).not.toHaveBeenCalled();
			const payload = createIsoJobMock.mock.calls[0][0];
			expect(payload).toMatchObject({
				source_path: '/home/arm/ingress/Movie.iso',
				title: 'ISO Movie',
				year: '2025',
				disctype: 'bluray',
			});
		});
	});
});
