import { describe, it, expect, afterEach } from 'vitest';
import { renderComponent, screen, cleanup } from '$lib/test-utils';
import StatusBadge from './StatusBadge.svelte';

describe('StatusBadge', () => {
	afterEach(() => cleanup());

	it.each([
		['ripping', 'Ripping', 'status-active'],
		['SUCCESS', 'Success', 'status-success'],
		['copying', 'Copying', 'status-finishing'],
		['something_new', 'something_new', 'status-unknown']
	])('renders status=%s as "%s" with class %s', (status, expectedText, expectedClass) => {
		renderComponent(StatusBadge, { props: { status } });
		const badge = screen.getByText(expectedText);
		expect(badge).toBeInTheDocument();
		expect(badge).toHaveClass(expectedClass);
	});

	it('renders null status as Unknown', () => {
		renderComponent(StatusBadge, { props: { status: null } });
		const badge = screen.getByText('Unknown');
		expect(badge).toBeInTheDocument();
		expect(badge).toHaveClass('status-unknown');
	});
});
