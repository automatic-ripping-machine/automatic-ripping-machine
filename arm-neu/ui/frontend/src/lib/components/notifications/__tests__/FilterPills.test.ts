import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderComponent, screen, fireEvent, cleanup } from '$lib/test-utils';
import FilterPills from '../FilterPills.svelte';

const counts = { all: 4, enabled: 3, paused: 1, issues: 1 };

describe('FilterPills', () => {
	afterEach(() => cleanup());

	it('renders each pill with its count', () => {
		renderComponent(FilterPills, { props: { active: 'all', counts } });
		expect(screen.getByRole('button', { name: /All.*4/ })).toBeInTheDocument();
		expect(screen.getByRole('button', { name: /Enabled.*3/ })).toBeInTheDocument();
		expect(screen.getByRole('button', { name: /Paused.*1/ })).toBeInTheDocument();
		expect(screen.getByRole('button', { name: /Issues.*1/ })).toBeInTheDocument();
	});

	it('calls onselect with the chosen filter', async () => {
		const onselect = vi.fn();
		renderComponent(FilterPills, { props: { active: 'all', counts, onselect } });
		await fireEvent.click(screen.getByRole('button', { name: /Issues.*1/ }));
		expect(onselect).toHaveBeenCalledWith('issues');
	});
});
