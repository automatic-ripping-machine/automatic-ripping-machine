import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderComponent, screen, fireEvent, cleanup } from '$lib/test-utils';
import BreadcrumbNav from './BreadcrumbNav.svelte';

const roots = [
	{ path: '/media/completed', label: 'Completed', writable: true },
	{ path: '/media/raw', label: 'Raw', writable: true }
];

describe('BreadcrumbNav', () => {
	afterEach(() => cleanup());

	describe('rendering', () => {
		it('renders root label for root path', () => {
			renderComponent(BreadcrumbNav, {
				props: { path: '/media/completed', roots, onnavigate: vi.fn() }
			});
			expect(screen.getByText('Completed')).toBeInTheDocument();
		});

		it('renders breadcrumb segments for nested path', () => {
			renderComponent(BreadcrumbNav, {
				props: { path: '/media/completed/movies/action', roots, onnavigate: vi.fn() }
			});
			expect(screen.getByText('Completed')).toBeInTheDocument();
			expect(screen.getByText('movies')).toBeInTheDocument();
			expect(screen.getByText('action')).toBeInTheDocument();
		});

		it('renders last segment as plain text (not a button)', () => {
			renderComponent(BreadcrumbNav, {
				props: { path: '/media/completed/movies', roots, onnavigate: vi.fn() }
			});
			const lastSegment = screen.getByText('movies');
			expect(lastSegment.tagName).toBe('SPAN');
		});

		it('renders intermediate segments as buttons', () => {
			renderComponent(BreadcrumbNav, {
				props: { path: '/media/completed/movies/action', roots, onnavigate: vi.fn() }
			});
			const rootBtn = screen.getByText('Completed');
			expect(rootBtn.tagName).toBe('BUTTON');
			const moviesBtn = screen.getByText('movies');
			expect(moviesBtn.tagName).toBe('BUTTON');
		});

		it('renders nothing for unrecognized root path', () => {
			const { container } = renderComponent(BreadcrumbNav, {
				props: { path: '/unknown/path', roots, onnavigate: vi.fn() }
			});
			const nav = container.querySelector('nav');
			expect(nav?.children.length).toBe(0);
		});
	});

	describe('interactions', () => {
		it('calls onnavigate with segment path when clicked', async () => {
			const onnavigate = vi.fn();
			renderComponent(BreadcrumbNav, {
				props: { path: '/media/completed/movies/action', roots, onnavigate }
			});
			await fireEvent.click(screen.getByText('Completed'));
			expect(onnavigate).toHaveBeenCalledWith('/media/completed');
		});

		it('calls onnavigate with intermediate path', async () => {
			const onnavigate = vi.fn();
			renderComponent(BreadcrumbNav, {
				props: { path: '/media/completed/movies/action', roots, onnavigate }
			});
			await fireEvent.click(screen.getByText('movies'));
			expect(onnavigate).toHaveBeenCalledWith('/media/completed/movies');
		});
	});
});
