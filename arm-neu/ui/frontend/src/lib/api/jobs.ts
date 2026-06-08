import type { JobConfigUpdateRequest as JobConfigUpdate, JobDetailSchema as JobDetail, JobListResponse, MediaDetailSchema as MediaDetail, MusicDetailSchema as MusicDetail, MusicSearchResultSchema as MusicSearchResult, SearchResultSchema as SearchResult, TitleUpdateRequest as TitleUpdate } from '$lib/types/api.gen';
import type { TrackTitleUpdateRequest as TrackTitleUpdate } from '$lib/types/api.gen';
import { apiFetch } from './client';

export function fetchJobs(params?: {
	page?: number;
	per_page?: number;
	status?: string;
	search?: string;
	video_type?: string;
	disctype?: string;
	days?: number;
	sort_by?: string;
	sort_dir?: string;
}): Promise<JobListResponse> {
	const query = new URLSearchParams();
	if (params?.page) query.set('page', String(params.page));
	if (params?.per_page) query.set('per_page', String(params.per_page));
	if (params?.status) query.set('status', params.status);
	if (params?.search) query.set('search', params.search);
	if (params?.video_type) query.set('video_type', params.video_type);
	if (params?.disctype) query.set('disctype', params.disctype);
	if (params?.days) query.set('days', String(params.days));
	if (params?.sort_by) query.set('sort_by', params.sort_by);
	if (params?.sort_dir) query.set('sort_dir', params.sort_dir);
	const qs = query.toString();
	return apiFetch<JobListResponse>(`/api/jobs${qs ? `?${qs}` : ''}`);
}

export function fetchJob(id: number): Promise<JobDetail> {
	return apiFetch<JobDetail>(`/api/jobs/${id}`);
}

export function abandonJob(id: number): Promise<unknown> {
	return apiFetch(`/api/jobs/${id}/abandon`, { method: 'POST' });
}

export function cancelWaitingJob(id: number): Promise<unknown> {
	return apiFetch(`/api/jobs/${id}/cancel`, { method: 'POST' });
}

export function startWaitingJob(id: number): Promise<unknown> {
	return apiFetch(`/api/jobs/${id}/start`, { method: 'POST' });
}

export function pauseWaitingJob(id: number, paused?: boolean): Promise<unknown> {
	return apiFetch(`/api/jobs/${id}/pause`, {
		method: 'POST',
		body: paused !== undefined ? JSON.stringify({ paused }) : undefined,
	});
}

export function deleteJob(id: number): Promise<unknown> {
	return apiFetch(`/api/jobs/${id}`, { method: 'DELETE' });
}

export function fixJobPermissions(id: number): Promise<unknown> {
	return apiFetch(`/api/jobs/${id}/fix-permissions`, { method: 'POST' });
}

export function skipAndFinalize(jobId: number): Promise<{ success: boolean; message?: string; error?: string }> {
	return apiFetch<{ success: boolean; message?: string; error?: string }>(
		`/api/jobs/${jobId}/skip-and-finalize`,
		{ method: 'POST' }
	);
}

export function forceComplete(jobId: number): Promise<{ success: boolean; message?: string; error?: string }> {
	return apiFetch<{ success: boolean; message?: string; error?: string }>(
		`/api/jobs/${jobId}/force-complete`,
		{ method: 'POST' }
	);
}

export function searchMetadata(query: string, year?: string, page = 1): Promise<SearchResult[]> {
	const params = new URLSearchParams({ q: query });
	if (year) params.set('year', year);
	if (page > 1) params.set('page', String(page));
	return apiFetch<SearchResult[]>(`/api/metadata/search?${params}`);
}

export function fetchMediaDetail(imdbId: string): Promise<MediaDetail> {
	return apiFetch<MediaDetail>(`/api/metadata/${imdbId}`);
}

export interface MusicSearchResponse {
	results: MusicSearchResult[];
	total: number;
}

export function searchMusicMetadata(
	query: string,
	filters?: { artist?: string; release_type?: string; format?: string; country?: string; status?: string; tracks?: number },
	offset = 0
): Promise<MusicSearchResponse> {
	const params = new URLSearchParams({ q: query });
	if (filters?.artist) params.set('artist', filters.artist);
	if (filters?.release_type) params.set('release_type', filters.release_type);
	if (filters?.format) params.set('format', filters.format);
	if (filters?.country) params.set('country', filters.country);
	if (filters?.status) params.set('status', filters.status);
	if (filters?.tracks) params.set('tracks', String(filters.tracks));
	if (offset > 0) params.set('offset', String(offset));
	return apiFetch<MusicSearchResponse>(`/api/metadata/music/search?${params}`);
}

export function fetchMusicDetail(releaseId: string): Promise<MusicDetail> {
	return apiFetch<MusicDetail>(`/api/metadata/music/${releaseId}`);
}

export function setJobTracks(
	jobId: number,
	tracks: { track_number: string; title: string; length_ms: number | null }[]
): Promise<unknown> {
	return apiFetch(`/api/jobs/${jobId}/tracks`, {
		method: 'PUT',
		body: JSON.stringify(tracks)
	});
}

export function updateJobTitle(jobId: number, data: Partial<TitleUpdate>): Promise<unknown> {
	return apiFetch(`/api/jobs/${jobId}/title`, {
		method: 'PUT',
		body: JSON.stringify(data)
	});
}

export function updateJobConfig(jobId: number, data: Partial<JobConfigUpdate>): Promise<unknown> {
	return apiFetch(`/api/jobs/${jobId}/config`, {
		method: 'PATCH',
		body: JSON.stringify(data)
	});
}

export interface CrcLookupResult {
	title: string;
	year: string;
	imdb_id: string;
	tmdb_id: string;
	video_type: string;
	disctype: string;
	label: string;
	poster_url: string;
	hasnicetitle: string;
	validated: string;
	date_added: string;
}

export interface CrcLookupResponse {
	found: boolean;
	results: CrcLookupResult[];
	no_crc?: boolean;
	error?: string;
	has_api_key?: boolean;
}

export function fetchCrcLookup(jobId: number): Promise<CrcLookupResponse> {
	return apiFetch<CrcLookupResponse>(`/api/jobs/${jobId}/crc-lookup`);
}

export function submitToCrcDb(id: number): Promise<unknown> {
	return apiFetch(`/api/jobs/${id}/crc-submit`, { method: 'POST' });
}

export interface RipProgress {
	progress: number | null;
	stage: string | null;
	tracks_total: number;
	tracks_ripped: number;
	no_of_titles: number | null;
	copy_progress: number | null;
	copy_stage: string | null;
}

export function fetchJobProgress(id: number): Promise<RipProgress> {
	return apiFetch<RipProgress>(`/api/jobs/${id}/progress`);
}

export function updateJobTranscodeConfig(
	jobId: number,
	overrides: Record<string, unknown>
): Promise<{ success: boolean; overrides: Record<string, unknown> }> {
	return apiFetch(`/api/jobs/${jobId}/transcode-config`, {
		method: 'PATCH',
		body: JSON.stringify(overrides)
	});
}

export function retranscodeJob(id: number): Promise<{ status: string; message: string }> {
	return apiFetch(`/api/jobs/${id}/retranscode`, { method: 'POST' });
}

export function toggleMultiTitle(jobId: number, enabled: boolean): Promise<unknown> {
	return apiFetch(`/api/jobs/${jobId}/multi-title`, {
		method: 'POST',
		body: JSON.stringify({ enabled })
	});
}

export function updateTrackTitle(
	jobId: number,
	trackId: number,
	data: Partial<TrackTitleUpdate>
): Promise<unknown> {
	return apiFetch(`/api/jobs/${jobId}/tracks/${trackId}/title`, {
		method: 'PUT',
		body: JSON.stringify(data)
	});
}

export function clearTrackTitle(jobId: number, trackId: number): Promise<unknown> {
	return apiFetch(`/api/jobs/${jobId}/tracks/${trackId}/title`, { method: 'DELETE' });
}

// --- TVDB Episode Matching ---

export interface TvdbMatch {
	track_number: string;
	episode_number: number;
	episode_name: string;
	episode_runtime: number;
}

export interface TvdbAlternative {
	season: number;
	score: number;
	match_count: number;
}

export interface TvdbMatchResponse {
	success: boolean;
	matcher: string;
	season: number;
	matches: TvdbMatch[];
	match_count: number;
	score: number;
	alternatives: TvdbAlternative[];
	applied?: boolean;
	error?: string;
}

export interface TvdbEpisode {
	number: number;
	name: string;
	/** Runtime in minutes (API returns seconds, caller must convert) */
	runtime: number;
	aired: string;
}

export interface TvdbEpisodesResponse {
	episodes: TvdbEpisode[];
	tvdb_id: number;
	season: number;
}

export function tvdbMatch(
	jobId: number,
	opts?: {
		season?: number | null;
		tolerance?: number | null;
		apply?: boolean;
		disc_number?: number | null;
		disc_total?: number | null;
	}
): Promise<TvdbMatchResponse> {
	return apiFetch<TvdbMatchResponse>(`/api/jobs/${jobId}/tvdb-match`, {
		method: 'POST',
		body: JSON.stringify({
			season: opts?.season ?? null,
			tolerance: opts?.tolerance ?? null,
			apply: opts?.apply ?? false,
			disc_number: opts?.disc_number ?? null,
			disc_total: opts?.disc_total ?? null
		})
	});
}

export function fetchTvdbEpisodes(jobId: number, season: number): Promise<TvdbEpisodesResponse> {
	return apiFetch<TvdbEpisodesResponse>(`/api/jobs/${jobId}/tvdb-episodes?season=${season}`);
}

export interface TrackFieldUpdate {
	enabled?: boolean;
	filename?: string;
	ripped?: boolean;
	episode_number?: string;
	episode_name?: string;
	custom_filename?: string | null;
}

export function updateTrack(
	jobId: number,
	trackId: number,
	data: TrackFieldUpdate
): Promise<{ success: boolean; updated: TrackFieldUpdate }> {
	return apiFetch(`/api/jobs/${jobId}/tracks/${trackId}`, {
		method: 'PATCH',
		body: JSON.stringify(data)
	});
}

export function namingPreview(
	pattern: string,
	variables: Record<string, string>
): Promise<{ success: boolean; rendered: string }> {
	return apiFetch('/api/naming/preview', {
		method: 'POST',
		body: JSON.stringify({ pattern, variables })
	});
}

export interface NamingPreviewTrack {
	track_number: string;
	rendered_title: string;
	rendered_folder: string;
}

export interface NamingPreviewResponse {
	success: boolean;
	job_title: string;
	job_folder: string;
	tracks: NamingPreviewTrack[];
}

export function fetchNamingPreview(jobId: number): Promise<NamingPreviewResponse> {
	return apiFetch<NamingPreviewResponse>(`/api/jobs/${jobId}/naming-preview`, {
		signal: AbortSignal.timeout(5000)
	});
}

export interface NamingOverrideUpdate {
	title_pattern_override?: string | null;
	folder_pattern_override?: string | null;
}

export interface NamingOverrideResponse {
	success: boolean;
	title_pattern_override: string | null;
	folder_pattern_override: string | null;
}

export function updateJobNaming(jobId: number, data: NamingOverrideUpdate): Promise<NamingOverrideResponse> {
	return apiFetch(`/api/jobs/${jobId}/naming`, {
		method: 'PATCH',
		body: JSON.stringify(data)
	});
}

export interface PatternValidation {
	valid: boolean;
	invalid_vars: string[];
	suggestions: Record<string, string>;
}

export function validatePattern(pattern: string): Promise<PatternValidation> {
	return apiFetch('/api/naming/validate', {
		method: 'POST',
		body: JSON.stringify({ pattern })
	});
}

export interface NamingVariablesResponse {
	variables: string[];
	descriptions: Record<string, string>;
}

export function fetchNamingVariables(): Promise<NamingVariablesResponse> {
	return apiFetch<NamingVariablesResponse>('/api/naming/variables');
}

export interface JobStats {
	total: number;
	active: number;
	success: number;
	fail: number;
	waiting: number;
}

export function fetchJobStats(params?: {
	search?: string;
	video_type?: string;
	disctype?: string;
	days?: number;
}): Promise<JobStats> {
	const query = new URLSearchParams();
	if (params?.search) query.set('search', params.search);
	if (params?.video_type) query.set('video_type', params.video_type);
	if (params?.disctype) query.set('disctype', params.disctype);
	if (params?.days) query.set('days', String(params.days));
	const qs = query.toString();
	return apiFetch<JobStats>(`/api/jobs/stats${qs ? `?${qs}` : ''}`);
}

export function bulkDeleteJobs(params: { job_ids?: number[]; status?: string }): Promise<{ deleted: number; errors: string[] }> {
	return apiFetch('/api/jobs/bulk-delete', { method: 'POST', body: JSON.stringify(params) });
}

export function bulkPurgeJobs(params: { job_ids?: number[]; status?: string }): Promise<{ purged: number; errors: string[] }> {
	return apiFetch('/api/jobs/bulk-purge', { method: 'POST', body: JSON.stringify(params) });
}
