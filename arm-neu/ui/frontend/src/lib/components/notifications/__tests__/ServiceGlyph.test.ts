import { describe, it, expect, afterEach } from 'vitest';
import { renderComponent, screen, cleanup } from '$lib/test-utils';
import ServiceGlyph from '../ServiceGlyph.svelte';

describe('ServiceGlyph', () => {
	afterEach(() => cleanup());

	it('renders the first letter of the name, uppercased', () => {
		renderComponent(ServiceGlyph, { props: { id: 'discord', name: 'Discord' } });
		expect(screen.getByText('D')).toBeInTheDocument();
	});

	it('is deterministic: same id yields the same background color', () => {
		const { container: a } = renderComponent(ServiceGlyph, { props: { id: 'slack', name: 'Slack' } });
		const colorA = (a.querySelector('[data-glyph]') as HTMLElement).style.background;
		cleanup();
		const { container: b } = renderComponent(ServiceGlyph, { props: { id: 'slack', name: 'Slack' } });
		const colorB = (b.querySelector('[data-glyph]') as HTMLElement).style.background;
		expect(colorA).toBe(colorB);
		expect(colorA).not.toBe('');
	});
});
