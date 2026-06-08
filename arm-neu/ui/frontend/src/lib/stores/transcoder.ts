import { createPollingStore } from './polling';
import { fetchTranscoderStats, fetchTranscoderWorkers } from '$lib/api/transcoder';
import type { TranscoderStatsResponse as TranscoderStats, TranscoderJobListResponse, WorkersResponse } from '$lib/types/api.gen';

export const emptyStats: TranscoderStats = { online: false, stats: null };
export const emptyWorkers: WorkersResponse = { max_concurrent: 0, active_count: 0, workers: [] };

/**
 * Singleton transcoder stores — they survive page navigations and retain their
 * last-known data, so returning to the Transcoder page renders the previous
 * stats/workers immediately instead of flashing the "offline" state and popping
 * in once the next poll resolves. Polling is still gated by the page via
 * start()/stop(); only the cached value persists between visits.
 */
export const transcoderStats = createPollingStore(fetchTranscoderStats, emptyStats, 5000);
export const transcoderWorkers = createPollingStore(fetchTranscoderWorkers, emptyWorkers, 5000);

// Last successful jobs response per tab, so navigating back (or to a
// previously-viewed tab) shows the cards immediately while we refresh in the
// background, rather than dropping to a skeleton each time.
let jobsCache: { tab: string; data: TranscoderJobListResponse } | null = null;

export function getJobsCache(tab: string): TranscoderJobListResponse | null {
	return jobsCache && jobsCache.tab === tab ? jobsCache.data : null;
}

export function setJobsCache(tab: string, data: TranscoderJobListResponse): void {
	jobsCache = { tab, data };
}
