import { describe, it, expect, afterEach } from 'vitest';
import { renderComponent, cleanup } from '$lib/test-utils';
import SkeletonCard from '../SkeletonCard.svelte';

describe('SkeletonCard', () => {
	afterEach(() => cleanup());

	it('renders a card shell with 3 skeleton lines by default', () => {
		const { container } = renderComponent(SkeletonCard, { props: {} });
		const lines = container.querySelectorAll('[data-variant="line"]');
		expect(lines.length).toBe(3);
	});

	it('respects the lines prop', () => {
		const { container } = renderComponent(SkeletonCard, { props: { lines: 5 } });
		const lines = container.querySelectorAll('[data-variant="line"]');
		expect(lines.length).toBe(5);
	});

	it('merges the class prop onto the card shell', () => {
		const { container } = renderComponent(SkeletonCard, { props: { class: 'my-custom' } });
		const shell = container.querySelector('.my-custom');
		expect(shell).not.toBeNull();
	});
});
