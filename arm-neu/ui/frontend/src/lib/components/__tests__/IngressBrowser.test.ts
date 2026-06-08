import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderComponent, screen, fireEvent, cleanup, waitFor } from '$lib/test-utils';
import IngressBrowser from '../IngressBrowser.svelte';
import { createFolderEntry } from '../__fixtures__/files';

import { fetchIngressRoot, fetchIngressDirectory } from '$lib/api/import-jobs';

const movieFolder = createFolderEntry('Movie_Folder');
const tvShowFolder = createFolderEntry('TV_Show', '2025-06-14T10:00:00Z');
const subFolder = createFolderEntry('Subfolder');

vi.mock('$lib/api/import-jobs', () => ({
	fetchIngressRoot: vi.fn(() => Promise.resolve([
		{ key: 'ingress', label: 'Ingress', path: '/home/arm/ingress' }
	])),
	fetchIngressDirectory: vi.fn(() => Promise.resolve({
		path: '/home/arm/ingress',
		entries: [movieFolder, tvShowFolder]
	}))
}));

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

vi.mock('$lib/stores/importWizard', async () => {
	const { writable } = await import('svelte/store');
	return { showImportWizard: writable(false) };
});

const mockFetchIngressDirectory = vi.mocked(fetchIngressDirectory);

// jsdom does not implement scrollTo
HTMLElement.prototype.scrollTo = vi.fn();

function renderBrowser(onselect: (sel: { path: string; kind: 'dir' | 'iso' }) => void = vi.fn()) {
	return renderComponent(IngressBrowser, { onselect });
}

async function waitForEntries() {
	await waitFor(() => {
		expect(screen.getByText('Movie_Folder')).toBeInTheDocument();
	});
}

/** Navigate into Movie_Folder and wait for the ".." back-row to appear. */
async function navigateIntoSubfolder() {
	mockFetchIngressDirectory.mockResolvedValueOnce({
		path: '/home/arm/ingress',
		entries: [{ ...movieFolder, size: 4294967296 }]
	} as any).mockResolvedValueOnce({
		path: '/home/arm/ingress/Movie_Folder',
		entries: [{ ...subFolder, size: 1024 }]
	} as any);

	renderBrowser();
	await waitForEntries();

	await fireEvent.dblClick(screen.getByText('Movie_Folder'));
	await waitFor(() => {
		expect(screen.getByText('..')).toBeInTheDocument();
	});
}

describe('IngressBrowser', () => {
	afterEach(() => {
		cleanup();
		vi.clearAllMocks();
	});

	it('renders path bar with current path', async () => {
		renderBrowser();
		await waitFor(() => {
			expect(screen.getByText('/home/arm/ingress')).toBeInTheDocument();
		});
	});

	it('renders directory entries in table', async () => {
		renderBrowser();
		await waitFor(() => {
			expect(screen.getByText('Movie_Folder')).toBeInTheDocument();
			expect(screen.getByText('TV_Show')).toBeInTheDocument();
		});
	});

	it('shows .. row when navigated past root', async () => {
		await navigateIntoSubfolder();
		// ".." is already asserted inside navigateIntoSubfolder
	});

	it('clicking .. navigates up', async () => {
		await navigateIntoSubfolder();

		await fireEvent.click(screen.getByText('..'));
		await waitFor(() => {
			expect(mockFetchIngressDirectory).toHaveBeenCalledWith('/home/arm/ingress');
		});
	});

	it('filter input is disabled when 5 or fewer directories', async () => {
		renderBrowser();
		await waitForEntries();
		const filterInput = screen.getByPlaceholderText('Filter entries...');
		expect(filterInput).toBeDisabled();
	});

	it('sort buttons render in table header', async () => {
		renderBrowser();
		await waitForEntries();
		expect(screen.getByText(/^Name/)).toBeInTheDocument();
		expect(screen.getByText(/^Size/)).toBeInTheDocument();
		expect(screen.getByText(/^Modified/)).toBeInTheDocument();
	});

	it('shows empty state in table when no directories', async () => {
		mockFetchIngressDirectory.mockResolvedValueOnce({
			path: '/home/arm/ingress',
			entries: []
		} as any);

		renderBrowser();
		await waitFor(() => {
			expect(screen.getByText('No entries found.')).toBeInTheDocument();
		});
	});

	it('shows loading text before directory loads', async () => {
		mockFetchIngressDirectory.mockImplementationOnce(() => new Promise(() => {}));

		renderBrowser();

		await waitFor(() => {
			expect(screen.getByText('Loading...')).toBeInTheDocument();
		});
	});

	describe('ISO support', () => {
		it('renders ISO files alongside folders', async () => {
			mockFetchIngressDirectory.mockResolvedValueOnce({
				path: '/home/arm/ingress',
				entries: [
					movieFolder,
					{ name: 'Movie.iso', type: 'file', size: 8_000_000_000, modified: '2025-06-15T12:00:00Z', extension: 'iso', category: 'archive', permissions: 'rw-r--r--', owner: 'arm', group: 'arm' }
				]
			} as any);

			renderBrowser();

			await waitFor(() => {
				expect(screen.getByText('Movie.iso')).toBeInTheDocument();
				expect(screen.getByText('Movie_Folder')).toBeInTheDocument();
			});
		});

		it('greys out non-importable other files', async () => {
			mockFetchIngressDirectory.mockResolvedValueOnce({
				path: '/home/arm/ingress',
				entries: [
					{ name: 'notes.txt', type: 'file', size: 100, modified: '2025-06-15T12:00:00Z', extension: 'txt', category: 'text', permissions: 'rw-r--r--', owner: 'arm', group: 'arm' }
				]
			} as any);

			const { container } = renderBrowser();

			await waitFor(() => {
				expect(screen.getByText('notes.txt')).toBeInTheDocument();
			});

			const otherRow = container.querySelector('tr[data-kind="other"]');
			expect(otherRow).toBeTruthy();
			expect(otherRow?.getAttribute('data-disabled')).toBe('');
			expect(otherRow?.getAttribute('aria-disabled')).toBe('true');
		});

		it('selecting an ISO emits kind=iso', async () => {
			mockFetchIngressDirectory.mockResolvedValueOnce({
				path: '/home/arm/ingress',
				entries: [
					{ name: 'Movie.iso', type: 'file', size: 8_000_000_000, modified: '2025-06-15T12:00:00Z', extension: 'iso', category: 'archive', permissions: 'rw-r--r--', owner: 'arm', group: 'arm' }
				]
			} as any);

			const onselect = vi.fn();
			renderBrowser(onselect);

			await waitFor(() => {
				expect(screen.getByText('Movie.iso')).toBeInTheDocument();
			});

			await fireEvent.click(screen.getByText('Movie.iso'));
			expect(onselect).toHaveBeenCalledWith({
				path: '/home/arm/ingress/Movie.iso',
				kind: 'iso'
			});
		});

		it('selecting a folder emits kind=dir', async () => {
			const onselect = vi.fn();
			renderBrowser(onselect);

			await waitFor(() => {
				expect(screen.getByText('Movie_Folder')).toBeInTheDocument();
			});

			await fireEvent.click(screen.getByText('Movie_Folder'));
			expect(onselect).toHaveBeenCalledWith({
				path: '/home/arm/ingress/Movie_Folder',
				kind: 'dir'
			});
		});

		it('clicking on a non-importable other entry does not select', async () => {
			mockFetchIngressDirectory.mockResolvedValueOnce({
				path: '/home/arm/ingress',
				entries: [
					{ name: 'notes.txt', type: 'file', size: 100, modified: '2025-06-15T12:00:00Z', extension: 'txt', category: 'text', permissions: 'rw-r--r--', owner: 'arm', group: 'arm' }
				]
			} as any);

			const onselect = vi.fn();
			renderBrowser(onselect);

			await waitFor(() => {
				expect(screen.getByText('notes.txt')).toBeInTheDocument();
			});

			await fireEvent.click(screen.getByText('notes.txt'));
			expect(onselect).not.toHaveBeenCalled();
		});
	});
});
