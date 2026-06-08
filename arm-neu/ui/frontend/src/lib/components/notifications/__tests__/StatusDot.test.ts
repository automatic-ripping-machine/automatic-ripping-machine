import { describe, it, expect, afterEach } from 'vitest';
import { renderComponent, screen, cleanup } from '$lib/test-utils';
import StatusDot from '../StatusDot.svelte';

describe('StatusDot', () => {
	afterEach(() => cleanup());

	it('exposes the status via title/aria for accessibility', () => {
		renderComponent(StatusDot, { props: { status: 'error' } });
		expect(screen.getByTitle('error')).toBeInTheDocument();
	});
});
