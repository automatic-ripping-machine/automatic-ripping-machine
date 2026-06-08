import { describe, it, expect, vi, afterEach } from 'vitest';
import { toasts, addToast, dismissToast } from '$lib/stores/toast.svelte';

describe('toast store', () => {
	afterEach(() => {
		vi.useRealTimers();
		// clear any toasts left between tests
		for (const t of toasts.value) dismissToast(t.id);
	});

	it('adds a toast and returns its id', () => {
		const id = addToast({ tone: 'success', title: 'Done' });
		expect(toasts.value.find((t) => t.id === id)?.title).toBe('Done');
	});

	it('dismissToast removes by id', () => {
		const id = addToast({ tone: 'info', title: 'Hi' });
		dismissToast(id);
		expect(toasts.value.find((t) => t.id === id)).toBeUndefined();
	});

	it('auto-dismisses after the timeout', () => {
		vi.useFakeTimers();
		const id = addToast({ tone: 'error', title: 'Boom' });
		expect(toasts.value.find((t) => t.id === id)).toBeTruthy();
		vi.advanceTimersByTime(4200);
		expect(toasts.value.find((t) => t.id === id)).toBeUndefined();
	});
});
