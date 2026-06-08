import { describe, it, expect, afterEach } from 'vitest';
import { renderComponent, screen, cleanup } from '$lib/test-utils';
import DispatchHistory from '../DispatchHistory.svelte';
import type { DispatchRow } from '$lib/types/notifications';

const rows: DispatchRow[] = [
	{ id: 1, channel_id: 2, event_key: 'job.rip_complete', status: 'success', attempts: 1, last_error: null, created_at: '2026-05-20T00:00:00Z', completed_at: '2026-05-20T00:00:01Z' },
	{ id: 2, channel_id: 2, event_key: 'job.failed', status: 'failed', attempts: 5, last_error: 'http 503', created_at: '2026-05-20T00:00:00Z', completed_at: null }
];

describe('DispatchHistory', () => {
	afterEach(() => cleanup());

	it('renders one row per dispatch with event key and status', () => {
		renderComponent(DispatchHistory, { props: { rows } });
		expect(screen.getByText('job.rip_complete')).toBeTruthy();
		expect(screen.getByText('job.failed')).toBeTruthy();
	});

	it('shows the error for a failed dispatch', () => {
		renderComponent(DispatchHistory, { props: { rows } });
		expect(screen.getByText(/http 503/)).toBeTruthy();
	});

	it('renders an empty state when there are no rows', () => {
		renderComponent(DispatchHistory, { props: { rows: [] } });
		expect(screen.getByText(/No sends yet/i)).toBeTruthy();
	});
});
