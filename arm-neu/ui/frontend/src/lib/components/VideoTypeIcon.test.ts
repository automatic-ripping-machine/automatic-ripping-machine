import { describe, it, expect, afterEach } from 'vitest';
import { renderComponent, cleanup } from '$lib/test-utils';
import VideoTypeIcon from './VideoTypeIcon.svelte';

describe('VideoTypeIcon', () => {
	afterEach(() => cleanup());

	describe('rendering', () => {
		it('renders an SVG element for a known icon', () => {
			const { container } = renderComponent(VideoTypeIcon, { props: { icon: 'tv' } });
			const svg = container.querySelector('svg');
			expect(svg).toBeInTheDocument();
		});

		it('renders fallback icon for unknown icon name', () => {
			const { container } = renderComponent(VideoTypeIcon, { props: { icon: 'nonexistent' } });
			const svg = container.querySelector('svg');
			expect(svg).toBeInTheDocument();
		});

		it('applies default class', () => {
			const { container } = renderComponent(VideoTypeIcon, { props: { icon: 'tv' } });
			const svg = container.querySelector('svg');
			expect(svg).toHaveClass('h-4', 'w-4');
		});

		it('applies custom class', () => {
			const { container } = renderComponent(VideoTypeIcon, { props: { icon: 'tv', class: 'h-8 w-8 text-red-500' } });
			const svg = container.querySelector('svg');
			expect(svg).toHaveClass('h-8', 'w-8', 'text-red-500');
		});
	});
});
