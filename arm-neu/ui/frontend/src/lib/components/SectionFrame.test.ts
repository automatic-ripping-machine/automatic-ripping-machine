import { describe, it, expect, afterEach } from 'vitest';
import { renderComponent, screen, cleanup } from '$lib/test-utils';
import SectionFrame from './SectionFrame.svelte';
import { createRawSnippet } from 'svelte';

function textSnippet(text: string) {
	return createRawSnippet(() => ({
		render: () => `<p>${text}</p>`
	}));
}

describe('SectionFrame', () => {
	afterEach(() => cleanup());

	describe('rendering', () => {
		it('renders children content', () => {
			renderComponent(SectionFrame, {
				props: { children: textSnippet('Hello World') }
			});
			expect(screen.getByText('Hello World')).toBeInTheDocument();
		});

		it('renders label when provided', () => {
			renderComponent(SectionFrame, {
				props: { label: 'Test Section', children: textSnippet('content') }
			});
			expect(screen.getByText('Test Section')).toBeInTheDocument();
		});

		it('does not render label when empty', () => {
			const { container } = renderComponent(SectionFrame, {
				props: { children: textSnippet('content') }
			});
			const topBar = container.querySelector('.section-frame-bar-top');
			expect(topBar?.querySelector('span')).toBeNull();
		});
	});

	describe('props', () => {
		it('sets data-frame-variant attribute', () => {
			const { container } = renderComponent(SectionFrame, {
				props: { variant: 'compact', children: textSnippet('content') }
			});
			const frame = container.querySelector('[data-frame-variant]');
			expect(frame).toHaveAttribute('data-frame-variant', 'compact');
		});

		it('renders sidebar blocks only in full variant', () => {
			const { container } = renderComponent(SectionFrame, {
				props: { variant: 'full', children: textSnippet('content') }
			});
			expect(container.querySelector('.section-frame-sidebar')).toBeInTheDocument();
		});

		it('does not render sidebar in compact variant', () => {
			const { container } = renderComponent(SectionFrame, {
				props: { variant: 'compact', children: textSnippet('content') }
			});
			expect(container.querySelector('.section-frame-sidebar')).toBeNull();
		});
	});
});
