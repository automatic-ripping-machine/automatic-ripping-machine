import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderComponent, screen, fireEvent, cleanup } from '$lib/test-utils';
import Toggle from '../Toggle.svelte';

describe('Toggle', () => {
	afterEach(() => cleanup());

	it('reflects checked state via aria-checked', () => {
		renderComponent(Toggle, { props: { checked: true, label: 'Enabled' } });
		expect(screen.getByRole('switch').getAttribute('aria-checked')).toBe('true');
	});

	it('calls onchange with the toggled value', async () => {
		const onchange = vi.fn();
		renderComponent(Toggle, { props: { checked: false, label: 'Enabled', onchange } });
		await fireEvent.click(screen.getByRole('switch'));
		expect(onchange).toHaveBeenCalledWith(true);
	});
});
