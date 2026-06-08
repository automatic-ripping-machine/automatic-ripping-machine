import { describe, it, expect, afterEach } from 'vitest';
import { renderComponent, screen, fireEvent, cleanup } from '$lib/test-utils';
import ToastHost from '../ToastHost.svelte';
import { addToast, toasts, dismissToast } from '$lib/stores/toast.svelte';

describe('ToastHost', () => {
	afterEach(() => {
		for (const t of toasts.value) dismissToast(t.id);
		cleanup();
	});

	it('renders an active toast', async () => {
		addToast({ tone: 'success', title: 'Saved', body: 'All good' });
		renderComponent(ToastHost);
		expect(await screen.findByText('Saved')).toBeInTheDocument();
		expect(screen.getByText('All good')).toBeInTheDocument();
	});

	it('dismisses a toast when its close button is clicked', async () => {
		addToast({ tone: 'info', title: 'Closable' });
		renderComponent(ToastHost);
		await fireEvent.click(screen.getByRole('button', { name: /dismiss/i }));
		expect(screen.queryByText('Closable')).toBeNull();
	});
});
