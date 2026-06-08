import { describe, it, expect, afterEach } from 'vitest';
import { renderComponent, screen, cleanup } from '$lib/test-utils';
import StatStrip from '../StatStrip.svelte';

describe('StatStrip', () => {
	afterEach(() => cleanup());

	it('shows the three counts', () => {
		renderComponent(StatStrip, { props: { total: 4, issues: 1, subscribedEvents: 5 } });
		expect(screen.getByText('Channels')).toBeInTheDocument();
		expect(screen.getByText('4')).toBeInTheDocument();
		expect(screen.getByText('Issues')).toBeInTheDocument();
		expect(screen.getByText('Subscribed events')).toBeInTheDocument();
		expect(screen.getByText('5')).toBeInTheDocument();
	});
});
