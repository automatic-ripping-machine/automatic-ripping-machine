import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { JobDetailSchema as JobDetail } from '../types/api.gen';
import { buildMetadataFields, type MetadataField } from '../utils/job-fields';

// Mock format utilities so tests don't depend on locale/time
vi.mock('../utils/format', () => ({
	formatDateTime: (s: string | null) => (s ? `formatted:${s}` : 'N/A'),
	timeAgo: (s: string | null) => (s ? `ago:${s}` : 'N/A'),
}));

function createJob(overrides: Partial<JobDetail> = {}): JobDetail {
	return {
		job_id: 1,
		arm_version: '2.0',
		crc_id: null,
		guid: null,
		logfile: null,
		start_time: '2026-01-01T10:00:00',
		stop_time: null,
		job_length: null,
		status: 'ripping',
		stage: null,
		no_of_titles: 5,
		errors: null,
		updated: null,
		ejected: null,
		pid: null,
		pid_hash: null,
		title: 'Test Movie',
		title_auto: null,
		title_manual: null,
		year: '2025',
		year_auto: null,
		year_manual: null,
		video_type: 'movie',
		video_type_auto: null,
		video_type_manual: null,
		imdb_id: null,
		imdb_id_auto: null,
		imdb_id_manual: null,
		poster_url: null,
		poster_url_auto: null,
		poster_url_manual: null,
		devpath: '/dev/sr0',
		mountpoint: null,
		hasnicetitle: null,
		disctype: 'dvd',
		label: 'DISC_LABEL',
		path: null,
		raw_path: null,
		transcode_path: null,
		source_type: null,
		source_path: null,
		is_iso: null,
		artist: null,
		artist_auto: null,
		artist_manual: null,
		album: null,
		album_auto: null,
		album_manual: null,
		season: null,
		season_auto: null,
		season_manual: null,
		episode: null,
		episode_auto: null,
		episode_manual: null,
		multi_title: false,
		disc_number: null,
		disc_total: null,
		tvdb_id: null,
		manual_start: null,
		manual_pause: null,
		manual_mode: null,
		wait_start_time: null,
		title_pattern_override: null,
		folder_pattern_override: null,
		transcode_overrides: null,
		track_counts: null,
		tracks: [],
		config: null,
		...overrides,
	};
}

function fieldLabels(fields: MetadataField[]): string[] {
	return fields.filter((f) => !f.empty).map((f) => f.label);
}

function findField(fields: MetadataField[], label: string): MetadataField | undefined {
	return fields.find((f) => f.label === label);
}

describe('buildMetadataFields', () => {
	beforeEach(() => {
		vi.useFakeTimers();
		vi.setSystemTime(new Date('2026-01-01T12:00:00'));
	});

	describe('always-present fields', () => {
		it('includes base fields for any job', () => {
			const fields = buildMetadataFields(createJob());
			const labels = fieldLabels(fields);
			expect(labels).toContain('Type');
			expect(labels).toContain('Disc Type');
			expect(labels).toContain('Titles');
			expect(labels).toContain('Label');
			expect(labels).toContain('Device');
			expect(labels).toContain('Source');
			expect(labels).toContain('Started');
		});

		it('Label is mono', () => {
			const fields = buildMetadataFields(createJob());
			expect(findField(fields, 'Label')?.mono).toBe(true);
		});

		it('Type shows video_type', () => {
			const fields = buildMetadataFields(createJob({ video_type: 'series' }));
			expect(findField(fields, 'Type')?.value).toBe('Series');
		});

		it('Disc Type uses discTypeLabel', () => {
			const fields = buildMetadataFields(createJob({ disctype: 'bluray' }));
			expect(findField(fields, 'Disc Type')?.value).toBe('Blu-ray');
		});

		it('Titles shows no_of_titles', () => {
			const fields = buildMetadataFields(createJob({ no_of_titles: 12 }));
			expect(findField(fields, 'Titles')?.value).toBe('12');
		});

		it('Device shows devpath', () => {
			const fields = buildMetadataFields(createJob({ devpath: '/dev/sr1' }));
			expect(findField(fields, 'Device')?.value).toBe('/dev/sr1');
		});

		it('Source shows disc or folder', () => {
			expect(findField(buildMetadataFields(createJob()), 'Source')?.value).toBe('Disc');
			expect(
				findField(buildMetadataFields(createJob({ source_type: 'folder' })), 'Source')?.value
			).toBe('Folder');
		});

		it('Started uses formatDateTime', () => {
			const fields = buildMetadataFields(createJob({ start_time: '2026-01-01T10:00:00' }));
			expect(findField(fields, 'Started')?.value).toBe('formatted:2026-01-01T10:00:00');
		});
	});

	describe('video disc fields', () => {
		it('includes Title Mode for movie disc', () => {
			const fields = buildMetadataFields(createJob({ video_type: 'movie', disctype: 'dvd' }));
			const f = findField(fields, 'Title Mode');
			expect(f).toBeDefined();
			expect(f?.isSelect).toBe(true);
		});

		it('includes Title Mode for series disc', () => {
			const fields = buildMetadataFields(createJob({ video_type: 'series', disctype: 'bluray' }));
			expect(findField(fields, 'Title Mode')).toBeDefined();
		});

		it('Title Mode value reflects multi_title', () => {
			expect(
				findField(buildMetadataFields(createJob({ multi_title: true })), 'Title Mode')?.value
			).toBe('multi');
			expect(
				findField(buildMetadataFields(createJob({ multi_title: false })), 'Title Mode')?.value
			).toBe('single');
		});

		it('excludes Title Mode for music disc', () => {
			const fields = buildMetadataFields(createJob({ video_type: 'music', disctype: 'music' }));
			expect(findField(fields, 'Title Mode')).toBeUndefined();
		});
	});

	describe('DVD CRC field', () => {
		it('includes CRC for DVD when present', () => {
			const fields = buildMetadataFields(createJob({ disctype: 'dvd', crc_id: 'ABC123' }));
			const f = findField(fields, 'CRC');
			expect(f).toBeDefined();
			expect(f?.value).toBe('ABC123');
			expect(f?.mono).toBe(true);
		});

		it('excludes CRC when not present', () => {
			const fields = buildMetadataFields(createJob({ disctype: 'dvd', crc_id: null }));
			expect(findField(fields, 'CRC')).toBeUndefined();
		});

		it('excludes CRC for non-DVD disc types', () => {
			const fields = buildMetadataFields(createJob({ disctype: 'bluray', crc_id: 'ABC123' }));
			expect(findField(fields, 'CRC')).toBeUndefined();
		});
	});

	describe('IMDb field', () => {
		it('includes IMDb when present and not music', () => {
			const fields = buildMetadataFields(createJob({ imdb_id: 'tt1234567', video_type: 'movie' }));
			const f = findField(fields, 'IMDb');
			expect(f).toBeDefined();
			expect(f?.value).toBe('tt1234567');
			expect(f?.link).toBe('https://www.imdb.com/title/tt1234567');
		});

		it('excludes IMDb when not present', () => {
			const fields = buildMetadataFields(createJob({ imdb_id: null }));
			expect(findField(fields, 'IMDb')).toBeUndefined();
		});

		it('excludes IMDb for music', () => {
			const fields = buildMetadataFields(
				createJob({ imdb_id: 'tt1234567', video_type: 'music', disctype: 'music' })
			);
			expect(findField(fields, 'IMDb')).toBeUndefined();
		});
	});

	describe('series-specific fields', () => {
		it('includes Season and TVDB for series when present', () => {
			const fields = buildMetadataFields(
				createJob({ video_type: 'series', season: '2', tvdb_id: 12345 })
			);
			const seasonField = findField(fields, 'Season');
			expect(seasonField).toBeDefined();
			expect(seasonField?.value).toBe('2');

			const tvdbField = findField(fields, 'TVDB');
			expect(tvdbField).toBeDefined();
			expect(tvdbField?.value).toBe('12345');
			expect(tvdbField?.link).toBe('https://www.thetvdb.com/dereferrer/series/12345');
		});

		it('excludes Season and TVDB for movie', () => {
			const fields = buildMetadataFields(
				createJob({ video_type: 'movie', season: '1', tvdb_id: 999 })
			);
			expect(findField(fields, 'Season')).toBeUndefined();
			expect(findField(fields, 'TVDB')).toBeUndefined();
		});

		it('excludes TVDB when not present even for series', () => {
			const fields = buildMetadataFields(
				createJob({ video_type: 'series', tvdb_id: null })
			);
			expect(findField(fields, 'TVDB')).toBeUndefined();
		});

		it('excludes Season when not present for series', () => {
			const fields = buildMetadataFields(
				createJob({ video_type: 'series', season: null })
			);
			expect(findField(fields, 'Season')).toBeUndefined();
		});
	});

	describe('music-specific fields', () => {
		it('includes Artist and Album for music', () => {
			const fields = buildMetadataFields(
				createJob({ video_type: 'music', disctype: 'music', artist: 'Tool', album: 'Lateralus' })
			);
			expect(findField(fields, 'Artist')?.value).toBe('Tool');
			expect(findField(fields, 'Album')?.value).toBe('Lateralus');
		});

		it('excludes Title Mode, IMDb, TVDB, Season, CRC for music', () => {
			const fields = buildMetadataFields(
				createJob({
					video_type: 'music',
					disctype: 'music',
					imdb_id: 'tt000',
					tvdb_id: 123,
					season: '1',
					crc_id: 'ABC',
					artist: 'Tool',
					album: 'Lateralus',
				})
			);
			const labels = fieldLabels(fields);
			expect(labels).not.toContain('Title Mode');
			expect(labels).not.toContain('IMDb');
			expect(labels).not.toContain('TVDB');
			expect(labels).not.toContain('Season');
			expect(labels).not.toContain('CRC');
		});

		it('excludes Artist and Album for non-music', () => {
			const fields = buildMetadataFields(createJob({ video_type: 'movie' }));
			expect(findField(fields, 'Artist')).toBeUndefined();
			expect(findField(fields, 'Album')).toBeUndefined();
		});
	});

	describe('disc number', () => {
		it('shows disc number when present', () => {
			const fields = buildMetadataFields(createJob({ disc_number: 2, disc_total: 4 }));
			const f = findField(fields, 'Disc #');
			expect(f).toBeDefined();
			expect(f?.value).toBe('2 of 4');
		});

		it('shows just disc number without total', () => {
			const fields = buildMetadataFields(createJob({ disc_number: 1, disc_total: null }));
			const f = findField(fields, 'Disc #');
			expect(f).toBeDefined();
			expect(f?.value).toBe('1');
		});

		it('excludes disc number when not present', () => {
			const fields = buildMetadataFields(createJob({ disc_number: null }));
			expect(findField(fields, 'Disc #')).toBeUndefined();
		});
	});

	describe('folder import fields', () => {
		it('includes Source Path for folder imports', () => {
			const fields = buildMetadataFields(
				createJob({ source_type: 'folder', source_path: '/media/imports/MOVIE' })
			);
			const f = findField(fields, 'Source Path');
			expect(f).toBeDefined();
			expect(f?.value).toBe('/media/imports/MOVIE');
			expect(f?.mono).toBe(true);
		});

		it('excludes Source Path for disc jobs', () => {
			const fields = buildMetadataFields(createJob());
			expect(findField(fields, 'Source Path')).toBeUndefined();
		});
	});

	describe('time fields based on job state', () => {
		it('shows Elapsed for active jobs', () => {
			const fields = buildMetadataFields(createJob({ status: 'ripping' }));
			const labels = fieldLabels(fields);
			expect(labels).toContain('Elapsed');
			expect(labels).not.toContain('Finished');
			expect(labels).not.toContain('Duration');
		});

		it('shows Finished and Duration for completed jobs', () => {
			const fields = buildMetadataFields(
				createJob({
					status: 'success',
					stop_time: '2026-01-01T11:30:00',
					job_length: '01:30:00',
				})
			);
			const labels = fieldLabels(fields);
			expect(labels).toContain('Finished');
			expect(labels).toContain('Duration');
			expect(labels).not.toContain('Elapsed');
		});

		it('Finished uses formatDateTime', () => {
			const fields = buildMetadataFields(
				createJob({ status: 'success', stop_time: '2026-01-01T11:30:00', job_length: '01:30:00' })
			);
			expect(findField(fields, 'Finished')?.value).toBe('formatted:2026-01-01T11:30:00');
		});

		it('Duration shows job_length', () => {
			const fields = buildMetadataFields(
				createJob({ status: 'success', stop_time: '2026-01-01T11:30:00', job_length: '01:30:00' })
			);
			expect(findField(fields, 'Duration')?.value).toBe('01:30:00');
		});

		it('Elapsed uses timeAgo on start_time', () => {
			const fields = buildMetadataFields(
				createJob({ status: 'ripping', start_time: '2026-01-01T10:00:00' })
			);
			expect(findField(fields, 'Elapsed')?.value).toBe('ago:2026-01-01T10:00:00');
		});
	});

	describe('path fields', () => {
		it('includes Output path when present', () => {
			const fields = buildMetadataFields(createJob({ path: '/output/movie' }));
			const f = findField(fields, 'Output');
			expect(f).toBeDefined();
			expect(f?.value).toBe('/output/movie');
			expect(f?.mono).toBe(true);
		});

		it('includes Raw path when present', () => {
			const fields = buildMetadataFields(createJob({ raw_path: '/raw/movie' }));
			const f = findField(fields, 'Raw');
			expect(f).toBeDefined();
			expect(f?.value).toBe('/raw/movie');
			expect(f?.mono).toBe(true);
		});

		it('includes Transcode path when present', () => {
			const fields = buildMetadataFields(createJob({ transcode_path: '/transcode/movie' }));
			const f = findField(fields, 'Transcode');
			expect(f).toBeDefined();
			expect(f?.value).toBe('/transcode/movie');
			expect(f?.mono).toBe(true);
		});

		it('excludes paths when not present', () => {
			const fields = buildMetadataFields(createJob());
			expect(findField(fields, 'Output')).toBeUndefined();
			expect(findField(fields, 'Raw')).toBeUndefined();
			expect(findField(fields, 'Transcode')).toBeUndefined();
		});
	});

	describe('padding to multiple of 4', () => {
		it('total length is a multiple of 4', () => {
			const fields = buildMetadataFields(createJob());
			expect(fields.length % 4).toBe(0);
		});

		it('padded fields have empty=true', () => {
			const fields = buildMetadataFields(createJob());
			const empties = fields.filter((f) => f.empty);
			// Each empty field should have label='' and value=''
			for (const e of empties) {
				expect(e.label).toBe('');
				expect(e.value).toBe('');
			}
		});

		it('content fields do not have empty=true', () => {
			const fields = buildMetadataFields(createJob());
			const content = fields.filter((f) => !f.empty);
			expect(content.length).toBeGreaterThan(0);
			for (const f of content) {
				expect(f.label).not.toBe('');
			}
		});

		it('pads correctly for different field counts', () => {
			// Movie disc with paths - many fields
			const manyFields = buildMetadataFields(
				createJob({
					status: 'success',
					stop_time: '2026-01-01T11:30:00',
					job_length: '01:30:00',
					path: '/output',
					raw_path: '/raw',
					transcode_path: '/transcode',
					imdb_id: 'tt1234567',
					crc_id: 'CRC1',
					disc_number: 1,
					disc_total: 3,
				})
			);
			expect(manyFields.length % 4).toBe(0);

			// Music disc - fewer fields
			const musicFields = buildMetadataFields(
				createJob({
					video_type: 'music',
					disctype: 'music',
					artist: 'Artist',
					album: 'Album',
				})
			);
			expect(musicFields.length % 4).toBe(0);

			// Series with all optional fields
			const seriesFields = buildMetadataFields(
				createJob({
					video_type: 'series',
					disctype: 'bluray',
					season: '3',
					tvdb_id: 54321,
					imdb_id: 'tt9999999',
					disc_number: 2,
					disc_total: 5,
					status: 'success',
					stop_time: '2026-01-01T11:30:00',
					job_length: '02:00:00',
					path: '/output',
				})
			);
			expect(seriesFields.length % 4).toBe(0);
		});
	});

	describe('field ordering', () => {
		it('starts with base fields in correct order', () => {
			const fields = buildMetadataFields(createJob());
			const labels = fieldLabels(fields);
			const baseOrder = ['Type', 'Disc Type', 'Titles', 'Label', 'Device', 'Source', 'Started'];
			for (let i = 0; i < baseOrder.length; i++) {
				expect(labels[i]).toBe(baseOrder[i]);
			}
		});
	});

	describe('null/missing field values', () => {
		it('handles null video_type', () => {
			const fields = buildMetadataFields(createJob({ video_type: null }));
			expect(findField(fields, 'Type')?.value).toBe('Unknown');
		});

		it('handles null disctype', () => {
			const fields = buildMetadataFields(createJob({ disctype: null }));
			expect(findField(fields, 'Disc Type')?.value).toBe('Unknown');
		});

		it('handles null no_of_titles', () => {
			const fields = buildMetadataFields(createJob({ no_of_titles: null }));
			expect(findField(fields, 'Titles')?.value).toBe('-');
		});

		it('handles null devpath', () => {
			const fields = buildMetadataFields(createJob({ devpath: null }));
			expect(findField(fields, 'Device')?.value).toBe('-');
		});

		it('handles null label', () => {
			const fields = buildMetadataFields(createJob({ label: null }));
			expect(findField(fields, 'Label')?.value).toBe('-');
		});
	});
});
