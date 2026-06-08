import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

function jsonResponse(data: unknown, ok = true) {
	return { ok, status: ok ? 200 : 500, statusText: ok ? 'OK' : 'Error', json: () => Promise.resolve(data) };
}

import { toggleMultiTitle, updateTrackTitle, clearTrackTitle, tvdbMatch, fetchTvdbEpisodes, updateTrack, fetchNamingPreview, updateJobNaming, validatePattern, fetchNamingVariables } from '../api/jobs';

beforeEach(() => mockFetch.mockReset());

describe('toggleMultiTitle', () => {
	it('POSTs to /api/jobs/:id/multi-title', async () => {
		mockFetch.mockResolvedValue(jsonResponse({ success: true }));
		await toggleMultiTitle(1, true);
		expect(mockFetch).toHaveBeenCalledWith('/api/jobs/1/multi-title', expect.objectContaining({
			method: 'POST',
			body: JSON.stringify({ enabled: true })
		}));
	});
});

describe('updateTrackTitle', () => {
	it('PUTs to /api/jobs/:jobId/tracks/:trackId/title', async () => {
		mockFetch.mockResolvedValue(jsonResponse({ success: true }));
		await updateTrackTitle(1, 2, { title: 'New Title' });
		expect(mockFetch).toHaveBeenCalledWith('/api/jobs/1/tracks/2/title', expect.objectContaining({
			method: 'PUT',
			body: expect.stringContaining('New Title')
		}));
	});
});

describe('clearTrackTitle', () => {
	it('DELETEs /api/jobs/:jobId/tracks/:trackId/title', async () => {
		mockFetch.mockResolvedValue(jsonResponse({ success: true }));
		await clearTrackTitle(1, 3);
		expect(mockFetch).toHaveBeenCalledWith('/api/jobs/1/tracks/3/title', expect.objectContaining({ method: 'DELETE' }));
	});
});

describe('tvdbMatch', () => {
	it('POSTs to /api/jobs/:id/tvdb-match', async () => {
		mockFetch.mockResolvedValue(jsonResponse({ success: true, matches: [], match_count: 0 }));
		await tvdbMatch(1, { season: 2, apply: true });
		expect(mockFetch).toHaveBeenCalledWith('/api/jobs/1/tvdb-match', expect.objectContaining({
			method: 'POST',
			body: JSON.stringify({ season: 2, tolerance: null, apply: true, disc_number: null, disc_total: null })
		}));
	});

	it('uses null defaults when no options', async () => {
		mockFetch.mockResolvedValue(jsonResponse({ success: true, matches: [] }));
		await tvdbMatch(1);
		expect(mockFetch).toHaveBeenCalledWith('/api/jobs/1/tvdb-match', expect.objectContaining({
			body: JSON.stringify({ season: null, tolerance: null, apply: false, disc_number: null, disc_total: null })
		}));
	});
});

describe('fetchTvdbEpisodes', () => {
	it('GETs /api/jobs/:id/tvdb-episodes?season=N', async () => {
		mockFetch.mockResolvedValue(jsonResponse({ episodes: [], tvdb_id: 123, season: 1 }));
		const result = await fetchTvdbEpisodes(1, 1);
		expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining('/api/jobs/1/tvdb-episodes?season=1'), expect.any(Object));
		expect(result.tvdb_id).toBe(123);
	});
});

describe('updateTrack', () => {
	it('PATCHes /api/jobs/:jobId/tracks/:trackId', async () => {
		mockFetch.mockResolvedValue(jsonResponse({ success: true, updated: { enabled: false } }));
		const result = await updateTrack(1, 2, { enabled: false });
		expect(mockFetch).toHaveBeenCalledWith('/api/jobs/1/tracks/2', expect.objectContaining({
			method: 'PATCH',
			body: JSON.stringify({ enabled: false })
		}));
		expect(result.success).toBe(true);
	});
});

describe('fetchNamingPreview', () => {
	it('GETs /api/jobs/:id/naming-preview', async () => {
		const preview = {
			success: true,
			job_title: 'Test Show S01E01',
			job_folder: 'Test Show/Season 01',
			tracks: [
				{ track_number: '0', rendered_title: 'Pilot S01E01', rendered_folder: 'Test Show/Season 01' },
				{ track_number: '1', rendered_title: 'Episode 2 S01E02', rendered_folder: 'Test Show/Season 01' }
			]
		};
		mockFetch.mockResolvedValue(jsonResponse(preview));
		const result = await fetchNamingPreview(42);
		expect(mockFetch).toHaveBeenCalledWith('/api/jobs/42/naming-preview', expect.objectContaining({
			headers: expect.objectContaining({ 'Content-Type': 'application/json' })
		}));
		expect(result.success).toBe(true);
		expect(result.tracks).toHaveLength(2);
		expect(result.tracks[0].rendered_title).toBe('Pilot S01E01');
	});
});

describe('updateJobNaming', () => {
	it('PATCHes /api/jobs/:id/naming with pattern overrides', async () => {
		mockFetch.mockResolvedValue(jsonResponse({ success: true, title_pattern_override: '{title} - E{episode}', folder_pattern_override: null }));
		const result = await updateJobNaming(1, { title_pattern_override: '{title} - E{episode}' });
		expect(mockFetch).toHaveBeenCalledWith('/api/jobs/1/naming', expect.objectContaining({
			method: 'PATCH',
			body: JSON.stringify({ title_pattern_override: '{title} - E{episode}' })
		}));
		expect(result.success).toBe(true);
		expect(result.title_pattern_override).toBe('{title} - E{episode}');
	});

	it('clears override with null', async () => {
		mockFetch.mockResolvedValue(jsonResponse({ success: true, title_pattern_override: null, folder_pattern_override: null }));
		const result = await updateJobNaming(1, { title_pattern_override: null });
		expect(result.title_pattern_override).toBeNull();
	});
});

describe('validatePattern', () => {
	it('POSTs to /api/naming/validate', async () => {
		mockFetch.mockResolvedValue(jsonResponse({ valid: false, invalid_vars: ['episde'], suggestions: { episde: 'episode' } }));
		const result = await validatePattern('{title} {episde}');
		expect(mockFetch).toHaveBeenCalledWith('/api/naming/validate', expect.objectContaining({
			method: 'POST',
			body: JSON.stringify({ pattern: '{title} {episde}' })
		}));
		expect(result.valid).toBe(false);
		expect(result.invalid_vars).toContain('episde');
		expect(result.suggestions.episde).toBe('episode');
	});

	it('returns valid for correct pattern', async () => {
		mockFetch.mockResolvedValue(jsonResponse({ valid: true, invalid_vars: [], suggestions: {} }));
		const result = await validatePattern('{title} S{season}E{episode}');
		expect(result.valid).toBe(true);
	});
});

describe('fetchNamingVariables', () => {
	it('GETs /api/naming/variables', async () => {
		mockFetch.mockResolvedValue(jsonResponse({ variables: ['album', 'artist', 'episode', 'label', 'season', 'title', 'video_type', 'year'], descriptions: {} }));
		const result = await fetchNamingVariables();
		expect(result.variables).toHaveLength(8);
		expect(result.variables).toContain('title');
		expect(result.variables).toContain('episode');
	});
});
