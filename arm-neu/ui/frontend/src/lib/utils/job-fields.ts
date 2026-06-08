import type { JobDetailSchema as JobDetail } from '$lib/types/api.gen';
import { formatDateTime, timeAgo } from '$lib/utils/format';
import { discTypeLabel, isJobActive } from '$lib/utils/job-type';

export interface MetadataField {
	label: string;
	value: string;
	mono?: boolean;
	link?: string;
	isSelect?: boolean;
	empty?: boolean;
}

function videoTypeLabel(vt: string | null | undefined): string {
	if (!vt) return 'Unknown';
	const labels: Record<string, string> = {
		movie: 'Movie',
		series: 'Series',
		music: 'Music',
		data: 'Data',
	};
	return labels[vt.toLowerCase()] ?? vt;
}

export function buildMetadataFields(job: JobDetail): MetadataField[] {
	const isMusic = job.video_type?.toLowerCase() === 'music';
	const isSeries = job.video_type?.toLowerCase() === 'series';
	const isDvd = job.disctype?.toLowerCase() === 'dvd';
	const isFolderImport = job.source_type === 'folder';
	const active = isJobActive(job.status);

	const fields: MetadataField[] = [];

	// --- Always-present base fields ---
	fields.push({ label: 'Type', value: videoTypeLabel(job.video_type) });
	fields.push({ label: 'Disc Type', value: discTypeLabel(job.disctype) });
	fields.push({ label: 'Titles', value: job.no_of_titles != null ? String(job.no_of_titles) : '-' });
	fields.push({ label: 'Label', value: job.label ?? '-', mono: true });
	fields.push({ label: 'Device', value: job.devpath ?? '-' });
	fields.push({ label: 'Source', value: isFolderImport ? 'Folder' : 'Disc' });
	fields.push({ label: 'Started', value: formatDateTime(job.start_time) });

	// --- Video discs only: Title Mode ---
	if (!isMusic) {
		fields.push({
			label: 'Title Mode',
			value: job.multi_title ? 'multi' : 'single',
			isSelect: true,
		});
	}

	// --- DVD only + when present: CRC ---
	if (isDvd && job.crc_id) {
		fields.push({ label: 'CRC', value: job.crc_id, mono: true });
	}

	// --- When present + not music: IMDb ---
	if (job.imdb_id && !isMusic) {
		fields.push({
			label: 'IMDb',
			value: job.imdb_id,
			link: `https://www.imdb.com/title/${job.imdb_id}`,
		});
	}

	// --- Series + when present: Season, TVDB ---
	if (isSeries && job.season) {
		fields.push({ label: 'Season', value: job.season });
	}
	if (isSeries && job.tvdb_id) {
		fields.push({
			label: 'TVDB',
			value: String(job.tvdb_id),
			link: `https://www.thetvdb.com/dereferrer/series/${job.tvdb_id}`,
		});
	}

	// --- Music only: Artist, Album ---
	if (isMusic) {
		fields.push({ label: 'Artist', value: job.artist ?? '-' });
		fields.push({ label: 'Album', value: job.album ?? '-' });
	}

	// --- Disc number when present ---
	if (job.disc_number != null) {
		const discValue =
			job.disc_total != null ? `${job.disc_number} of ${job.disc_total}` : String(job.disc_number);
		fields.push({ label: 'Disc #', value: discValue });
	}

	// --- Folder imports: Source Path ---
	if (isFolderImport && job.source_path) {
		fields.push({ label: 'Source Path', value: job.source_path, mono: true });
	}

	// --- Time fields based on job state ---
	if (active) {
		fields.push({ label: 'Elapsed', value: timeAgo(job.start_time) });
	} else {
		fields.push({ label: 'Finished', value: formatDateTime(job.stop_time) });
		fields.push({ label: 'Duration', value: job.job_length ?? '-' });
	}

	// --- Path fields when present ---
	if (job.path) {
		fields.push({ label: 'Output', value: job.path, mono: true });
	}
	if (job.raw_path) {
		fields.push({ label: 'Raw', value: job.raw_path, mono: true });
	}
	if (job.transcode_path) {
		fields.push({ label: 'Transcode', value: job.transcode_path, mono: true });
	}

	// --- Pad to multiple of 4 ---
	const remainder = fields.length % 4;
	if (remainder !== 0) {
		const padding = 4 - remainder;
		for (let i = 0; i < padding; i++) {
			fields.push({ label: '', value: '', empty: true });
		}
	}

	return fields;
}
