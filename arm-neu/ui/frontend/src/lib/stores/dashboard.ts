import { createPollingStore } from './polling';
import { fetchDashboard } from '$lib/api/dashboard';
import type { DashboardResponse as DashboardData } from '$lib/types/api.gen';
const emptyDashboard: DashboardData = {
	db_available: true,
	arm_online: false,
	active_jobs: [],
	system_info: null,
	drives_online: 0,
	drive_names: {},
	notification_count: 0,
	ripping_enabled: true,
	makemkv_key_valid: null,
	makemkv_key_checked_at: null,
	transcoder_online: false,
	transcoder_stats: null,
	transcoder_system_stats: null,
	active_transcodes: [],
	system_stats: null,
	transcoder_info: null
};

// Fields the BFF marks `null` when their underlying ARM endpoint blipped on
// this poll. We hold the previous value for these so a transient timeout
// doesn't flicker badges/counts to zero.
const STICKY_FIELDS = [
	'active_jobs',
	'drives_online',
	'drive_names',
	'notification_count',
	'ripping_enabled'
] as const satisfies readonly (keyof DashboardData)[];

// Booleans that flip to `false` on a single backend blip (RemoteProtocolError,
// timeout, etc). Don't pop the sidebar to "Cannot reach …" until we've seen
// two consecutive `false` polls — one stale reading absorbs transient blips
// while real outages still surface within ~10s.
const TWO_STRIKE_FIELDS = ['arm_online', 'transcoder_online'] as const satisfies readonly (keyof DashboardData)[];

let lastGood: DashboardData = emptyDashboard;
const consecutiveFalse: Record<(typeof TWO_STRIKE_FIELDS)[number], number> = {
	arm_online: 0,
	transcoder_online: 0
};

async function fetchDashboardSticky(): Promise<DashboardData> {
	const fresh = (await fetchDashboard()) as DashboardData & Partial<Record<(typeof STICKY_FIELDS)[number], unknown>>;
	const merged = { ...fresh } as DashboardData;
	for (const key of STICKY_FIELDS) {
		if (fresh[key] === null || fresh[key] === undefined) {
			(merged[key] as unknown) = lastGood[key];
		}
	}
	for (const key of TWO_STRIKE_FIELDS) {
		if (fresh[key] === false) {
			consecutiveFalse[key]++;
			// First `false` after a `true` — keep showing online (debounce
			// a single-poll blip). A second consecutive `false` surfaces
			// the real outage on the next poll, ~5s later.
			if (consecutiveFalse[key] < 2) {
				(merged[key] as unknown) = true;
			}
		} else {
			consecutiveFalse[key] = 0;
		}
	}
	lastGood = merged;
	return merged;
}

/** Singleton dashboard store — survives page navigations, retains last-known data. */
export const dashboard = createPollingStore(fetchDashboardSticky, emptyDashboard, 5000);
