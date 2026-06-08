import { describe, it, expect, vi } from 'vitest';

vi.mock('$app/environment', () => ({ browser: false }));
vi.mock('$lib/api/dashboard', () => ({
	fetchDashboard: vi.fn(() => Promise.resolve({ db_available: true, arm_online: true }))
}));

import { dashboard } from '../stores/dashboard';

describe('dashboard store', () => {
	it('exports a polling store with subscribe', () => {
		expect(dashboard).toBeDefined();
		expect(typeof dashboard.subscribe).toBe('function');
	});

	it('has initial empty dashboard data', () => {
		let value: any;
		const unsub = dashboard.subscribe((v) => (value = v));
		expect(value.db_available).toBe(true);
		expect(value.active_jobs).toEqual([]);
		unsub();
	});
});
