import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get } from 'svelte/store';

// Mock fetchDashboard before the store imports it. We control its return
// value per-test to drive the sticky-merge behavior.
const fetchDashboardMock = vi.fn();
vi.mock('$lib/api/dashboard', () => ({
	fetchDashboard: fetchDashboardMock
}));

describe('dashboard store sticky merge', () => {
	beforeEach(() => {
		fetchDashboardMock.mockReset();
		// Re-import the store fresh each test so the lastGood module-level
		// cache resets. vitest resets module cache via vi.resetModules.
		vi.resetModules();
	});

	function fullPayload(overrides: Record<string, unknown> = {}) {
		return {
			db_available: true,
			arm_online: true,
			active_jobs: [{ id: 1 } as unknown],
			system_info: null,
			drives_online: 2,
			drive_names: { '/dev/sr0': 'Drive 1' },
			notification_count: 7,
			ripping_enabled: true,
			makemkv_key_valid: null,
			makemkv_key_checked_at: null,
			transcoder_online: false,
			transcoder_stats: null,
			transcoder_system_stats: null,
			active_transcodes: [],
			system_stats: null,
			transcoder_info: null,
			...overrides
		};
	}

	it('keeps prior notification_count when BFF sends null on next poll', async () => {
		fetchDashboardMock
			.mockResolvedValueOnce(fullPayload({ notification_count: 7 }))
			.mockResolvedValueOnce(fullPayload({ notification_count: null }));

		const { dashboard } = await import('../dashboard');
		await dashboard.refresh();
		expect(get(dashboard).notification_count).toBe(7);
		await dashboard.refresh();
		// Sticky: still 7, not 0, even though BFF sent null.
		expect(get(dashboard).notification_count).toBe(7);
	});

	it('keeps prior drives_online + drive_names when BFF sends null', async () => {
		fetchDashboardMock
			.mockResolvedValueOnce(fullPayload({ drives_online: 3, drive_names: { '/dev/sr0': 'A' } }))
			.mockResolvedValueOnce(fullPayload({ drives_online: null, drive_names: null }));

		const { dashboard } = await import('../dashboard');
		await dashboard.refresh();
		await dashboard.refresh();
		expect(get(dashboard).drives_online).toBe(3);
		expect(get(dashboard).drive_names).toEqual({ '/dev/sr0': 'A' });
	});

	it('uses fresh value when BFF sends a non-null value', async () => {
		fetchDashboardMock
			.mockResolvedValueOnce(fullPayload({ notification_count: 7 }))
			.mockResolvedValueOnce(fullPayload({ notification_count: 12 }));

		const { dashboard } = await import('../dashboard');
		await dashboard.refresh();
		await dashboard.refresh();
		expect(get(dashboard).notification_count).toBe(12);
	});

	it('uses fresh zero when BFF sends 0 (not null) - 0 is a real count', async () => {
		fetchDashboardMock
			.mockResolvedValueOnce(fullPayload({ notification_count: 7 }))
			.mockResolvedValueOnce(fullPayload({ notification_count: 0 }));

		const { dashboard } = await import('../dashboard');
		await dashboard.refresh();
		await dashboard.refresh();
		// 0 is a real value (user cleared all notifications), not a sentinel.
		expect(get(dashboard).notification_count).toBe(0);
	});

	it('debounces a single transcoder_online=false blip (two-strike)', async () => {
		// First poll online; second blips to false (transient backend timeout);
		// store masks it as still true to absorb the blip. Third poll still
		// false → store flips to false (real outage).
		fetchDashboardMock
			.mockResolvedValueOnce(fullPayload({ transcoder_online: true }))
			.mockResolvedValueOnce(fullPayload({ transcoder_online: false }))
			.mockResolvedValueOnce(fullPayload({ transcoder_online: false }));

		const { dashboard } = await import('../dashboard');
		await dashboard.refresh();
		await dashboard.refresh();
		expect(get(dashboard).transcoder_online).toBe(true);  // blip absorbed
		await dashboard.refresh();
		expect(get(dashboard).transcoder_online).toBe(false); // real outage
	});

	it('debounces a single arm_online=false blip (two-strike)', async () => {
		fetchDashboardMock
			.mockResolvedValueOnce(fullPayload({ arm_online: true }))
			.mockResolvedValueOnce(fullPayload({ arm_online: false }))
			.mockResolvedValueOnce(fullPayload({ arm_online: false }));

		const { dashboard } = await import('../dashboard');
		await dashboard.refresh();
		await dashboard.refresh();
		expect(get(dashboard).arm_online).toBe(true);
		await dashboard.refresh();
		expect(get(dashboard).arm_online).toBe(false);
	});

	it('two-strike counter resets when a true poll lands between false polls', async () => {
		fetchDashboardMock
			.mockResolvedValueOnce(fullPayload({ arm_online: true }))
			.mockResolvedValueOnce(fullPayload({ arm_online: false }))
			.mockResolvedValueOnce(fullPayload({ arm_online: true }))
			.mockResolvedValueOnce(fullPayload({ arm_online: false }))
			.mockResolvedValueOnce(fullPayload({ arm_online: false }));

		const { dashboard } = await import('../dashboard');
		await dashboard.refresh();
		await dashboard.refresh();
		expect(get(dashboard).arm_online).toBe(true);
		await dashboard.refresh();
		expect(get(dashboard).arm_online).toBe(true);
		await dashboard.refresh();
		expect(get(dashboard).arm_online).toBe(true);
		await dashboard.refresh();
		expect(get(dashboard).arm_online).toBe(false);
	});
});
