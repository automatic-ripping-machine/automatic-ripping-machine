export interface VideoTypeConfig {
	label: string;
	icon: string;
	badgeClasses: string;
	placeholderClasses: string;
	accentBorder: string;
	iconColor: string;
}

const MOVIE_CONFIG: VideoTypeConfig = {
	label: 'Movie',
	icon: 'clapperboard',
	badgeClasses: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
	placeholderClasses: 'bg-blue-100 text-blue-400 dark:bg-blue-900/30 dark:text-blue-500',
	accentBorder: 'border-l-blue-500',
	iconColor: 'text-blue-500 dark:text-blue-400',
};

const SERIES_CONFIG: VideoTypeConfig = {
	label: 'Series',
	icon: 'tv',
	badgeClasses: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
	placeholderClasses: 'bg-purple-100 text-purple-400 dark:bg-purple-900/30 dark:text-purple-500',
	accentBorder: 'border-l-purple-500',
	iconColor: 'text-purple-500 dark:text-purple-400',
};

const MUSIC_CONFIG: VideoTypeConfig = {
	label: 'Music',
	icon: 'music',
	badgeClasses: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
	placeholderClasses: 'bg-green-100 text-green-400 dark:bg-green-900/30 dark:text-green-500',
	accentBorder: 'border-l-green-500',
	iconColor: 'text-green-500 dark:text-green-400',
};

const DATA_CONFIG: VideoTypeConfig = {
	label: 'Data',
	icon: 'database',
	badgeClasses: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
	placeholderClasses: 'bg-amber-100 text-amber-400 dark:bg-amber-900/30 dark:text-amber-500',
	accentBorder: 'border-l-amber-500',
	iconColor: 'text-amber-500 dark:text-amber-400',
};

// Unidentified video disc: ARM knows it's a DVD/Blu-ray/UHD but
// hasn't classified it as movie/series yet. Cyan reads "informational"
// without colliding with Movie (blue), Series (purple), or Data (amber).
const VIDEO_FALLBACK_CONFIG: VideoTypeConfig = {
	label: 'Video',
	icon: 'disc',
	badgeClasses: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400',
	placeholderClasses: 'bg-cyan-100 text-cyan-400 dark:bg-cyan-900/30 dark:text-cyan-500',
	accentBorder: 'border-l-cyan-500',
	iconColor: 'text-cyan-500 dark:text-cyan-400',
};

const FALLBACK_CONFIG: VideoTypeConfig = {
	label: 'Disc',
	icon: 'disc',
	badgeClasses: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
	placeholderClasses: 'bg-primary/10 text-gray-400 dark:bg-primary/15 dark:text-gray-500',
	accentBorder: 'border-l-gray-400',
	iconColor: 'text-gray-500 dark:text-gray-400',
};

const TYPE_MAP: Record<string, VideoTypeConfig> = {
	movie: MOVIE_CONFIG,
	series: SERIES_CONFIG,
	music: MUSIC_CONFIG,
	data: DATA_CONFIG,
};

const VIDEO_DISCTYPES = new Set(['dvd', 'bluray', 'bluray4k', 'uhd']);

export function getVideoTypeConfig(
	videoType: string | null | undefined,
	disctype?: string | null,
): VideoTypeConfig {
	const known = videoType ? TYPE_MAP[videoType.toLowerCase()] : undefined;
	if (known) return known;
	if (disctype && VIDEO_DISCTYPES.has(disctype.toLowerCase())) {
		return VIDEO_FALLBACK_CONFIG;
	}
	return FALLBACK_CONFIG;
}

// Source of truth: arm_contracts.JobState (see components/contracts).
// isJobActive() is only ever called with arm-neu Job.status values
// (ActiveJobRow / JobCard / JobRow / JobActions / job-fields / jobs/[id]),
// so this set deliberately tracks JobState's non-terminal members and
// nothing else. Transcoder-side JobStatus ('processing', 'pending') and
// TrackStatus ('pending') are intentionally absent - they never reach
// isJobActive in current code paths.
//
// v2.0.0 disambiguation: 'ripping' split into 'video_ripping'/'audio_ripping',
// 'waiting' split into 'manual_paused'/'makemkv_throttled'. Old strings kept
// as defensive fallbacks for in-flight jobs observed mid-deploy.
const ACTIVE_STATUSES = new Set([
	'identifying',
	'ready',
	'ripping',                  // legacy pre-v2.0.0
	'video_ripping',
	'audio_ripping',
	'copying',
	'ejecting',
	'transcoding',
	'waiting',                  // legacy pre-v2.0.0
	'manual_paused',
	'makemkv_throttled',
	'waiting_transcode',
]);

const DISC_TYPE_LABELS: Record<string, string> = {
	dvd: 'DVD',
	bluray: 'Blu-ray',
	bluray4k: '4K UHD',
	music: 'Music CD',
	data: 'Data',
};

export function discTypeLabel(disctype: string | null | undefined): string {
	if (!disctype) return 'Unknown';
	return DISC_TYPE_LABELS[disctype.toLowerCase()] ?? disctype;
}

export function isJobActive(status: string | null | undefined): boolean {
	if (!status) return false;
	return ACTIVE_STATUSES.has(status.toLowerCase());
}
