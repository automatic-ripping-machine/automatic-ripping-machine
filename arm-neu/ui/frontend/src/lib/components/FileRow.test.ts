import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderComponent, screen, fireEvent, cleanup } from '$lib/test-utils';
import FileRow from './FileRow.svelte';
import type { FileEntry } from '$lib/types/api.gen';
function createEntry(overrides: Partial<FileEntry> = {}): FileEntry {
	return {
		name: 'movie.mkv',
		type: 'file',
		size: 4294967296,
		modified: '2025-06-15T12:00:00Z',
		extension: 'mkv',
		category: 'video',
		permissions: 'rwxr-xr-x',
		owner: 'arm',
		group: 'arm',
		...overrides
	};
}

const defaultCallbacks = {
	onnavigate: vi.fn(),
	onrename: vi.fn(),
	ondelete: vi.fn(),
	ontoggle: vi.fn(),
	onfixpermissions: vi.fn()
};

describe('FileRow', () => {
	beforeEach(() => {
		vi.useFakeTimers();
		vi.setSystemTime(new Date('2025-06-15T12:00:00Z'));
	});

	afterEach(() => {
		cleanup();
		vi.useRealTimers();
	});

	describe('rendering', () => {
		it('renders file name', () => {
			renderComponent(FileRow, {
				props: { entry: createEntry(), currentPath: '/media', selected: false, ...defaultCallbacks }
			});
			expect(screen.getByText('movie.mkv')).toBeInTheDocument();
		});

		it('renders formatted file size', () => {
			renderComponent(FileRow, {
				props: { entry: createEntry(), currentPath: '/media', selected: false, ...defaultCallbacks }
			});
			expect(screen.getByText('4 GB')).toBeInTheDocument();
		});

		it('renders permissions info', () => {
			renderComponent(FileRow, {
				props: { entry: createEntry(), currentPath: '/media', selected: false, ...defaultCallbacks }
			});
			expect(screen.getByText('arm:arm rwxr-xr-x')).toBeInTheDocument();
		});

		it('renders -- for zero-size files', () => {
			renderComponent(FileRow, {
				props: { entry: createEntry({ size: 0 }), currentPath: '/media', selected: false, ...defaultCallbacks }
			});
			expect(screen.getByText('--')).toBeInTheDocument();
		});
	});

	describe('interactions', () => {
		it('calls ontoggle when checkbox is changed', async () => {
			const ontoggle = vi.fn();
			renderComponent(FileRow, {
				props: { entry: createEntry(), currentPath: '/media', selected: false, ...defaultCallbacks, ontoggle }
			});
			const checkbox = screen.getByRole('checkbox');
			await fireEvent.change(checkbox);
			expect(ontoggle).toHaveBeenCalledWith('/media/movie.mkv');
		});

		it('calls onnavigate for directory clicks', async () => {
			const onnavigate = vi.fn();
			renderComponent(FileRow, {
				props: {
					entry: createEntry({ name: 'subdir', type: 'directory', category: 'directory' }),
					currentPath: '/media',
					selected: false,
					...defaultCallbacks,
					onnavigate
				}
			});
			await fireEvent.click(screen.getByText('subdir'));
			expect(onnavigate).toHaveBeenCalledWith('/media/subdir');
		});

		it('calls ondelete when delete button is clicked', async () => {
			const ondelete = vi.fn();
			renderComponent(FileRow, {
				props: { entry: createEntry(), currentPath: '/media', selected: false, ...defaultCallbacks, ondelete }
			});
			await fireEvent.click(screen.getByTitle('Delete'));
			expect(ondelete).toHaveBeenCalledWith('/media/movie.mkv', 'movie.mkv');
		});

		it('calls onfixpermissions when fix permissions button is clicked', async () => {
			const onfixpermissions = vi.fn();
			renderComponent(FileRow, {
				props: { entry: createEntry(), currentPath: '/media', selected: false, ...defaultCallbacks, onfixpermissions }
			});
			await fireEvent.click(screen.getByTitle('Fix permissions'));
			expect(onfixpermissions).toHaveBeenCalledWith('/media/movie.mkv', 'movie.mkv');
		});

		it('enters rename mode when rename button is clicked', async () => {
			renderComponent(FileRow, {
				props: { entry: createEntry(), currentPath: '/media', selected: false, ...defaultCallbacks }
			});
			await fireEvent.click(screen.getByTitle('Rename'));
			expect(screen.getByDisplayValue('movie.mkv')).toBeInTheDocument();
		});
	});

	describe('skeleton', () => {
		it('renders skeleton cells when entry prop is omitted', () => {
			const { container } = renderComponent(FileRow, { props: {} });
			expect(container.querySelectorAll('[data-variant="line"]').length).toBeGreaterThan(0);
		});
	});
});
