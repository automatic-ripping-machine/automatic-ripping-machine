export function timeAgo(dateString: string | null | undefined): string {
	if (!dateString) return 'N/A';
	const date = new Date(dateString);
	const now = new Date();
	const seconds = Math.max(0, Math.floor((now.getTime() - date.getTime()) / 1000));

	if (seconds < 60) return `${seconds}s ago`;
	const minutes = Math.floor(seconds / 60);
	if (minutes < 60) return `${minutes}m ago`;
	const hours = Math.floor(minutes / 60);
	if (hours < 24) return `${hours}h ago`;
	const days = Math.floor(hours / 24);
	return `${days}d ago`;
}

export function formatBytes(bytes: number): string {
	if (bytes === 0) return '0 B';
	const k = 1024;
	const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
	const i = Math.floor(Math.log(bytes) / Math.log(k));
	return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

export function formatDateTime(dateString: string | null | undefined): string {
	if (!dateString) return 'N/A';
	return new Date(dateString).toLocaleString();
}

export function elapsedTime(startTime: string | null | undefined): string {
	if (!startTime) return 'N/A';
	const start = new Date(startTime);
	const now = new Date();
	const totalSeconds = Math.max(0, Math.floor((now.getTime() - start.getTime()) / 1000));

	const hours = Math.floor(totalSeconds / 3600);
	const minutes = Math.floor((totalSeconds % 3600) / 60);
	const seconds = totalSeconds % 60;

	if (hours > 0) return `${hours}h ${minutes}m`;
	if (minutes > 0) return `${minutes}m ${seconds}s`;
	return `${seconds}s`;
}

/**
 * Estimate time remaining for an in-flight job.
 * Returns null when an ETA can't be reasonably computed (just started,
 * already done, no progress signal); the caller renders an em-dash.
 *
 * The 30s elapsed threshold smooths the noisy first-percent jitter
 * that MakeMKV/abcde produce during drive-spin and warm-up.
 * Capped at 24h+ to avoid printing absurd estimates from sub-1%
 * progress values that haven't yet stabilised.
 */
export function etaTime(
	startTime: string | null | undefined,
	progressPct: number | null | undefined
): string | null {
	if (!startTime || progressPct == null) return null;
	if (progressPct <= 0 || progressPct >= 100) return null;
	const start = new Date(startTime);
	const elapsedSec = (Date.now() - start.getTime()) / 1000;
	if (elapsedSec < 30) return null;
	const remainingSec = (elapsedSec * (100 - progressPct)) / progressPct;
	if (remainingSec >= 24 * 3600) return '24h+';
	const h = Math.floor(remainingSec / 3600);
	const m = Math.floor((remainingSec % 3600) / 60);
	const s = Math.floor(remainingSec % 60);
	if (h > 0) return `${h}h ${m}m`;
	if (m > 0) return `${m}m ${s}s`;
	return `${s}s`;
}

/**
 * Map a job status to a themeable CSS variable reference suitable for
 * inline `style="background: ${statusAccentVar(status)}"` use. Falls back
 * to the primary brand color so unrecognized statuses still pick up
 * theme tinting.
 *
 * Accepts JobState (arm-neu Job.status), JobStatus (transcoder), or
 * TrackStatus values. v2.0.0 disambiguated 'ripping' into
 * 'video_ripping'/'audio_ripping' and 'waiting' into
 * 'manual_paused'/'makemkv_throttled'; both new and legacy strings are
 * mapped here so in-flight jobs observed mid-deploy still tint correctly.
 */
export function statusAccentVar(status: string | null | undefined): string {
	switch (status?.toLowerCase()) {
		case 'identifying':
			return 'var(--color-status-scanning)';
		case 'ready':
		case 'active':
		case 'ripping':         // legacy pre-v2.0.0
		case 'video_ripping':
		case 'audio_ripping':
		case 'importing':
			return 'var(--color-status-ripping)';
		case 'copying':
		case 'ejecting':
			return 'var(--color-status-finishing)';
		case 'transcoding':
		case 'processing':
			return 'var(--color-status-transcoding)';
		case 'success':
		case 'completed':
		case 'complete':
		case 'transcoded':
			return 'var(--color-status-success)';
		case 'fail':
		case 'failed':
		case 'error':
			return 'var(--color-status-error)';
		case 'waiting':         // legacy pre-v2.0.0
		case 'manual_paused':
		case 'makemkv_throttled':
		case 'waiting_transcode':
		case 'pending':
			return 'var(--color-status-waiting)';
		default:
			return 'var(--color-primary)';
	}
}

/**
 * Map a status string to a CSS class. Receives values from three different
 * enums depending on caller:
 *   - arm_contracts.JobState (arm-neu Job.status) - StatusBadge in JobRow,
 *     JobCard, ActiveJobRow, DriveCard, jobs/[id]. Disambiguated in v2.0.0:
 *     'ripping' -> 'video_ripping'/'audio_ripping', 'waiting' ->
 *     'manual_paused'/'makemkv_throttled'. Old strings kept as defensive
 *     fallbacks for in-flight jobs observed mid-deploy.
 *   - arm_contracts.JobStatus (transcoder TranscodeJob.status) - StatusBadge
 *     in TranscodeCard, transcoder/+page.svelte
 *   - arm_contracts.TrackStatus (Track.status) - StatusBadge at jobs/[id]:849.
 *     'failed' is a real TrackStatus member as of v2.0.0 (was previously
 *     only handled defensively for transcoder JobStatus).
 * Plus two locally-generated literals: 'importing' (folder-import override
 * for status='ripping') and 'skipped' (UI-only marker for filtered/disabled
 * tracks). Both are produced inline at the StatusBadge call site, not by any
 * backend.
 */
export function statusColor(status: string | null | undefined): string {
	switch (status?.toLowerCase()) {
		case 'identifying':
			return 'status-scanning';
		case 'ready':
		case 'ripping':         // legacy pre-v2.0.0; in-flight jobs mid-deploy
		case 'video_ripping':
		case 'audio_ripping':
		case 'importing': // locally generated when isFolderImport && status='ripping'
			return 'status-active';
		case 'copying':
		case 'ejecting':
			return 'status-finishing';
		case 'transcoding':
		case 'processing': // JobStatus (transcoder) - TranscodeCard / transcoder page
			return 'status-processing';
		case 'success':
		case 'completed': // JobStatus (transcoder) terminal
		case 'transcoded': // TrackStatus terminal (transcode-phase)
			return 'status-success';
		case 'fail':
		case 'failed': // JobStatus (transcoder) terminal AND TrackStatus.failed (v2.0.0+)
			return 'status-error';
		case 'waiting':         // legacy pre-v2.0.0; in-flight jobs mid-deploy
		case 'manual_paused':
		case 'makemkv_throttled':
		case 'waiting_transcode':
		case 'pending': // JobStatus (transcoder) + TrackStatus member
			return 'status-warning';
		case 'skipped': // locally generated for !track.enabled || filtered (jobs/[id]:849)
			return 'status-unknown';
		default:
			return 'status-unknown';
	}
}

const STATUS_LABELS: Record<string, string> = {
	identifying: 'Scanning',
	ready: 'Ready',
	active: 'Active',
	ripping: 'Ripping',           // legacy pre-v2.0.0; in-flight jobs mid-deploy
	video_ripping: 'Ripping',
	audio_ripping: 'Ripping',
	importing: 'Processing',
	copying: 'Copying',
	ejecting: 'Ejecting',
	processing: 'Transcoding',
	transcoding: 'Transcoding',
	success: 'Success',
	completed: 'Completed',
	complete: 'Complete',
	fail: 'Failed',
	failed: 'Failed',
	error: 'Error',
	waiting: 'Waiting',           // legacy pre-v2.0.0; in-flight jobs mid-deploy
	manual_paused: 'Paused',
	makemkv_throttled: 'Throttled',
	waiting_transcode: 'Waiting to Transcode',
	pending: 'Pending',
	skipped: 'Skipped',
	transcoded: 'Transcoded',
	info: 'Scanning',
	cancelled: 'Cancelled',
};

export function statusLabel(status: string | null | undefined): string {
	if (!status) return 'Unknown';
	return STATUS_LABELS[status.toLowerCase()] ?? status;
}
