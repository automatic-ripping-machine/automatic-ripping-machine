import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { get } from 'svelte/store';

vi.mock('$app/environment', () => ({ browser: true }));

import { createPollingStore } from '../stores/polling';

beforeEach(() => {
	vi.useFakeTimers();
});

afterEach(() => {
	vi.useRealTimers();
});

describe('createPollingStore', () => {
	it('has correct initial state', () => {
		const store = createPollingStore(() => Promise.resolve('data'), 'initial');
		expect(get(store)).toBe('initial');
		expect(get(store.loading)).toBe(false);
		expect(get(store.error)).toBe(null);
		expect(get(store.initialized)).toBe(false);
	});

	it('refresh() updates data on success', async () => {
		const fetcher = vi.fn().mockResolvedValue('fetched');
		const store = createPollingStore(fetcher, 'initial');

		await store.refresh();

		expect(get(store)).toBe('fetched');
		expect(get(store.error)).toBe(null);
		expect(get(store.initialized)).toBe(true);
		expect(get(store.loading)).toBe(false);
	});

	it('refresh() sets error on failure', async () => {
		const fetcher = vi.fn().mockRejectedValue(new Error('Network error'));
		const store = createPollingStore(fetcher, 'initial');

		await store.refresh();

		expect(get(store)).toBe('initial');
		expect(get(store.error)).toBe('Network error');
		expect(get(store.loading)).toBe(false);
	});

	it('refresh() sets "Unknown error" for non-Error throws', async () => {
		const fetcher = vi.fn().mockRejectedValue('string error');
		const store = createPollingStore(fetcher, 'initial');

		await store.refresh();

		expect(get(store.error)).toBe('Unknown error');
	});

	it('refresh() debounces concurrent calls', async () => {
		let resolve: (v: string) => void;
		const fetcher = vi
			.fn()
			.mockImplementation(() => new Promise<string>((r) => { resolve = r; }));
		const store = createPollingStore(fetcher, 'initial');

		const p1 = store.refresh();
		const p2 = store.refresh(); // should be skipped

		resolve!('result');
		await p1;
		await p2;

		expect(fetcher).toHaveBeenCalledTimes(1);
	});

	it('start() calls refresh and begins polling', async () => {
		const fetcher = vi.fn().mockResolvedValue('data');
		const store = createPollingStore(fetcher, 'initial', 1000);

		store.start();
		await vi.advanceTimersByTimeAsync(0);
		expect(fetcher).toHaveBeenCalledTimes(1);

		await vi.advanceTimersByTimeAsync(1000);
		expect(fetcher).toHaveBeenCalledTimes(2);

		await vi.advanceTimersByTimeAsync(1000);
		expect(fetcher).toHaveBeenCalledTimes(3);

		store.stop();
	});

	it('stop() clears the timer', async () => {
		const fetcher = vi.fn().mockResolvedValue('data');
		const store = createPollingStore(fetcher, 'initial', 1000);

		store.start();
		await vi.advanceTimersByTimeAsync(0);
		expect(fetcher).toHaveBeenCalledTimes(1);

		store.stop();

		await vi.advanceTimersByTimeAsync(5000);
		expect(fetcher).toHaveBeenCalledTimes(1);
	});

	it('update() modifies the store data', () => {
		const store = createPollingStore(() => Promise.resolve(0), 5);
		store.update((n) => n + 1);
		expect(get(store)).toBe(6);
	});

	it('pauses on visibility hidden and resumes on visible', async () => {
		const fetcher = vi.fn().mockResolvedValue('data');
		const store = createPollingStore(fetcher, 'initial', 1000);

		store.start();
		await vi.advanceTimersByTimeAsync(0);
		expect(fetcher).toHaveBeenCalledTimes(1);

		// Simulate tab hidden
		Object.defineProperty(document, 'hidden', { value: true, writable: true });
		document.dispatchEvent(new Event('visibilitychange'));

		await vi.advanceTimersByTimeAsync(5000);
		expect(fetcher).toHaveBeenCalledTimes(1); // timer stopped

		// Simulate tab visible
		Object.defineProperty(document, 'hidden', { value: false, writable: true });
		document.dispatchEvent(new Event('visibilitychange'));

		await vi.advanceTimersByTimeAsync(0);
		expect(fetcher).toHaveBeenCalledTimes(2); // refresh on visible

		store.stop();
	});

	it('clears error on successful refresh after failure', async () => {
		const fetcher = vi.fn()
			.mockRejectedValueOnce(new Error('fail'))
			.mockResolvedValueOnce('ok');
		const store = createPollingStore(fetcher, 'initial');

		await store.refresh();
		expect(get(store.error)).toBe('fail');

		await store.refresh();
		expect(get(store.error)).toBe(null);
		expect(get(store)).toBe('ok');
	});
});
