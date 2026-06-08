import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderComponent, screen, fireEvent, cleanup, waitFor } from '$lib/test-utils';
import FilesPage from '../+page.svelte';
import { createFileEntry, createFolderEntry } from '$lib/components/__fixtures__/files';

import { fetchRoots, fetchDirectory } from '$lib/api/files';
import { fetchOrphanFolders, cleanupTranscoder } from '$lib/api/maintenance';

const defaultEntries = [
	createFileEntry('movie.mkv', 4294967296),
	createFolderEntry('subfolder', '2025-06-14T10:00:00Z'),
	createFileEntry('show.mkv', 2147483648, 'mkv')
];

vi.mock('$app/stores', async () => {
	const { readable } = await import('svelte/store');
	return {
		page: readable({ url: new URL('http://localhost/files') })
	};
});

vi.mock('$lib/api/files', () => ({
	fetchRoots: vi.fn(() => Promise.resolve([
		{ key: 'raw', label: 'Raw', path: '/media/raw' },
		{ key: 'completed', label: 'Completed', path: '/media/completed' }
	])),
	fetchDirectory: vi.fn(() => Promise.resolve({
		path: '/media/raw',
		parent: null,
		entries: [
			createFileEntry('movie.mkv', 4294967296),
			createFolderEntry('subfolder', '2025-06-14T10:00:00Z'),
			createFileEntry('show.mkv', 2147483648, 'mkv')
		]
	})),
	renameFile: vi.fn(() => Promise.resolve()),
	moveFile: vi.fn(() => Promise.resolve()),
	deleteFile: vi.fn(() => Promise.resolve()),
	createDirectory: vi.fn(() => Promise.resolve()),
	fixPermissions: vi.fn(() => Promise.resolve({ fixed: 3 }))
}));

vi.mock('$lib/api/maintenance', () => ({
	fetchOrphanFolders: vi.fn(() => Promise.resolve({ total_size_bytes: 0, folders: [] })),
	deleteFolder: vi.fn(() => Promise.resolve({ success: true })),
	bulkDeleteFolders: vi.fn(() => Promise.resolve({ removed: [], errors: [] })),
	cleanupTranscoder: vi.fn(() => Promise.resolve({ success: true, deleted: 0, errors: [] }))
}));

vi.stubGlobal('confirm', vi.fn(() => true));

const mockFetchDirectory = vi.mocked(fetchDirectory);

describe('Files Page', () => {
	afterEach(() => {
		cleanup();
		vi.clearAllMocks();
		vi.mocked(confirm).mockReturnValue(true);
	});

	describe('rendering', () => {
		it('renders page title', () => {
			renderComponent(FilesPage);
			expect(screen.getByText('Files')).toBeInTheDocument();
		});

		it('renders root tabs after loading', async () => {
			renderComponent(FilesPage);
			await waitFor(() => {
				const matches = screen.getAllByText('Completed');
				expect(matches.length).toBeGreaterThanOrEqual(1);
			});
		});

		it('renders tabs in rootOrder: Raw before Completed', async () => {
			renderComponent(FilesPage);
			await waitFor(() => {
				const rawTab = screen.getAllByText('Raw')[0];
				const completedTab = screen.getAllByText('Completed')[0];
				// Raw should appear before Completed in DOM order
				expect(rawTab.compareDocumentPosition(completedTab) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
			});
		});

		it('renders file listing after auto-navigation', async () => {
			renderComponent(FilesPage);
			await waitFor(() => {
				expect(screen.getByText('movie.mkv')).toBeInTheDocument();
				expect(screen.getByText('subfolder')).toBeInTheDocument();
				expect(screen.getByText('show.mkv')).toBeInTheDocument();
			});
		});

		it('renders file sizes', async () => {
			renderComponent(FilesPage);
			await waitFor(() => {
				expect(screen.getByText('4 GB')).toBeInTheDocument();
				expect(screen.getByText('2 GB')).toBeInTheDocument();
			});
		});

		it('renders checkboxes for file selection', async () => {
			renderComponent(FilesPage);
			await waitFor(() => {
				expect(screen.getByText('movie.mkv')).toBeInTheDocument();
			});
			const checkboxes = screen.getAllByRole('checkbox');
			expect(checkboxes.length).toBeGreaterThanOrEqual(3); // 3 entries
		});
	});

	describe('navigation', () => {
		it('navigates to subdirectory on click', async () => {
			renderComponent(FilesPage);
			await waitFor(() => {
				expect(screen.getByText('subfolder')).toBeInTheDocument();
			});
			// subfolder is a directory — clicking it triggers navigation
			await fireEvent.click(screen.getByText('subfolder'));
			await waitFor(() => {
				expect(mockFetchDirectory).toHaveBeenCalledWith('/media/raw/subfolder');
			});
		});

		it('switches root on tab click', async () => {
			renderComponent(FilesPage);
			await waitFor(() => {
				const matches = screen.getAllByText('Raw');
				expect(matches.length).toBeGreaterThanOrEqual(1);
			});
			await fireEvent.click(screen.getByText('Completed'));
			await waitFor(() => {
				expect(mockFetchDirectory).toHaveBeenCalledWith('/media/completed');
			});
		});
	});

	describe('error handling', () => {
		it('shows error when fetchRoots fails', async () => {
			vi.mocked(fetchRoots).mockRejectedValueOnce(new Error('Connection failed'));
			renderComponent(FilesPage);
			await waitFor(() => {
				expect(screen.getByText('Connection failed')).toBeInTheDocument();
			});
		});

		it('shows error when fetchDirectory fails', async () => {
			mockFetchDirectory.mockRejectedValueOnce(new Error('Permission denied'));
			renderComponent(FilesPage);
			await waitFor(() => {
				expect(screen.getByText('Permission denied')).toBeInTheDocument();
			});
		});
	});

	describe('orphan folders', () => {
		it('shows orphan folders button in toolbar', async () => {
			renderComponent(FilesPage);
			await waitFor(() => {
				expect(screen.getByTitle('Orphan folders')).toBeInTheDocument();
			});
		});

		it('opens orphan folders modal when clicked', async () => {
			renderComponent(FilesPage);
			await waitFor(() => {
				expect(screen.getByTitle('Orphan folders')).toBeInTheDocument();
			});
			await fireEvent.click(screen.getByTitle('Orphan folders'));
			await waitFor(() => {
				expect(screen.getByText('Orphan Folders')).toBeInTheDocument();
				expect(screen.getByText('Folders not associated with any job')).toBeInTheDocument();
			});
		});

		it('displays folder list in modal', async () => {
			vi.mocked(fetchOrphanFolders).mockResolvedValueOnce({
				roots: ['/media/raw', '/media/completed'],
				total_size_bytes: 5000000,
				folders: [
					{ path: '/media/raw/orphan1', name: 'orphan1', size_bytes: 3000000, category: 'raw' },
					{ path: '/media/completed/orphan2', name: 'orphan2', size_bytes: 2000000, category: 'completed' }
				]
			});
			renderComponent(FilesPage);
			await waitFor(() => {
				expect(screen.getByTitle('Orphan folders')).toBeInTheDocument();
			});
			await fireEvent.click(screen.getByTitle('Orphan folders'));
			await waitFor(() => {
				expect(screen.getByText('orphan1')).toBeInTheDocument();
				expect(screen.getByText('orphan2')).toBeInTheDocument();
			});
		});
	});

	describe('transcoder cleanup', () => {
		it('shows transcoder cleanup button in toolbar', async () => {
			renderComponent(FilesPage);
			await waitFor(() => {
				expect(screen.getByTitle('Clean up transcoder jobs')).toBeInTheDocument();
			});
		});

		it('opens confirm dialog when clicked', async () => {
			renderComponent(FilesPage);
			await waitFor(() => {
				expect(screen.getByTitle('Clean up transcoder jobs')).toBeInTheDocument();
			});
			await fireEvent.click(screen.getByTitle('Clean up transcoder jobs'));
			await waitFor(() => {
				expect(screen.getByText('Clean Up Transcoder')).toBeInTheDocument();
				expect(screen.getByText('Delete all completed and failed transcoder jobs from the transcoder database?')).toBeInTheDocument();
			});
		});
	});
});
