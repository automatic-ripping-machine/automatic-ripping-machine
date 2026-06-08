/**
 * Coarse 5-step lifecycle for visual progress display:
 * Waiting -> Identifying -> Ripping -> Transcoding -> Complete
 *
 * Folder imports use the same 5 stages: folder_ripper still drives a
 * MakeMKV remux pass (job.status = VIDEO_RIPPING) before handing off to
 * the transcoder. An earlier 4-stage variant that omitted "Ripping"
 * left video_ripping/audio_ripping unmapped, painting all nodes pending.
 *
 * Maps the disambiguated v2.0.0 JobState wire strings (and legacy pre-v2
 * strings, defensive) to lifecycle stages. Failures paint the active
 * stage with the failure color; subsequent stages stay pending. Paused
 * jobs surface a pause icon overlay on the active stage.
 */

export type LifecycleStageId =
	| 'waiting'
	| 'identifying'
	| 'ripping'
	| 'transcoding'
	| 'complete';

export type LifecycleNodeState =
	| 'completed'
	| 'active'
	| 'paused'
	| 'failed'
	| 'pending';

export interface LifecycleNode {
	id: LifecycleStageId;
	label: string;
	state: LifecycleNodeState;
}

const ALL_STAGES: { id: LifecycleStageId; label: string }[] = [
	{ id: 'waiting',      label: 'Waiting' },
	{ id: 'identifying',  label: 'Identifying' },
	{ id: 'ripping',      label: 'Ripping' },
	{ id: 'transcoding',  label: 'Transcoding' },
	{ id: 'complete',     label: 'Complete' }
];


const STATUS_TO_STAGE: Record<string, LifecycleStageId> = {
	// Waiting
	'waiting':            'waiting',          // legacy pre-v2.0.0
	'manual_paused':      'waiting',
	'makemkv_throttled':  'waiting',
	'waiting_transcode':  'waiting',
	'pending':            'waiting',
	'ready':              'waiting',
	// Identifying
	'info':               'identifying',
	'identifying':        'identifying',
	// Ripping (disc rip)
	'ripping':            'ripping',          // legacy pre-v2.0.0
	'video_ripping':      'ripping',
	'audio_ripping':      'ripping',
	'copying':            'ripping',
	'ejecting':           'ripping',
	'importing':          'ripping',
	// Transcoding
	'transcoding':        'transcoding',
	'finishing':          'transcoding',
	'processing':         'transcoding',
	// Complete
	'success':            'complete',
	'completed':          'complete',
	'complete':           'complete',
	'transcoded':         'complete'
};

const FAILURE_STATUSES = new Set(['fail', 'failed', 'failure', 'error']);
const PAUSED_STATUSES = new Set(['manual_paused']);

export function isFolderImport(sourceType: string | null | undefined): boolean {
	return sourceType === 'folder';
}

/**
 * Compute the lifecycle node list for a job. Caller passes the snapshot
 * status + source_type; we derive the active stage and paint earlier
 * stages as completed, later stages as pending.
 *
 * Failure heuristic: when the snapshot is a failure status we don't have
 * which stage failed in (no history), so we paint the *last reachable*
 * non-complete stage as failed. The complete node stays pending.
 */
export function deriveLifecycle(
	status: string | null | undefined,
	_sourceType?: string | null
): LifecycleNode[] {
	const stages = ALL_STAGES;
	const lower = (status ?? '').toLowerCase();

	if (FAILURE_STATUSES.has(lower)) {
		// Failure snapshot: paint the last non-complete stage red.
		const failIndex = stages.length - 2; // index of stage before 'complete'
		return stages.map((s, i) => {
			let state: LifecycleNodeState;
			if (i < failIndex) state = 'completed';
			else if (i === failIndex) state = 'failed';
			else state = 'pending';
			return { ...s, state };
		});
	}

	const stageId = STATUS_TO_STAGE[lower];
	if (!stageId) {
		// Unknown status: render fully pending.
		return stages.map((s) => ({ ...s, state: 'pending' as const }));
	}

	const activeIndex = stages.findIndex((s) => s.id === stageId);
	if (activeIndex < 0) {
		// Stage maps to one not in this lifecycle (e.g. ripping on a folder import).
		// Fall back to pending.
		return stages.map((s) => ({ ...s, state: 'pending' as const }));
	}

	const isPaused = PAUSED_STATUSES.has(lower);
	const isComplete = stageId === 'complete';

	return stages.map((s, i) => {
		if (isComplete) {
			return { ...s, state: 'completed' as const };
		}
		if (i < activeIndex) return { ...s, state: 'completed' as const };
		if (i === activeIndex) return { ...s, state: isPaused ? 'paused' as const : 'active' as const };
		return { ...s, state: 'pending' as const };
	});
}

/**
 * CSS variable reference for a node state; reuses the existing
 * --color-status-* tokens that StatusBadge / JobCard / DriveCard use.
 */
export function lifecycleColorVar(state: LifecycleNodeState): string {
	switch (state) {
		case 'completed': return 'var(--color-status-success)';
		case 'active':    return 'var(--color-status-ripping)';
		case 'paused':    return 'var(--color-status-waiting)';
		case 'failed':    return 'var(--color-status-error)';
		case 'pending':   return 'var(--color-status-pending, #9ca3af)';
	}
}
