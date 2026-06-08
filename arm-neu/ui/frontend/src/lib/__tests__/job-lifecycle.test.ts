import { describe, it, expect } from 'vitest';
import {
	deriveLifecycle,
	isFolderImport,
	lifecycleColorVar
} from '$lib/utils/job-lifecycle';

describe('deriveLifecycle - disc rip 5-step', () => {
	it('waiting -> first stage active, rest pending', () => {
		const nodes = deriveLifecycle('waiting', 'disc');
		expect(nodes.map((n) => n.id)).toEqual([
			'waiting', 'identifying', 'ripping', 'transcoding', 'complete'
		]);
		expect(nodes[0].state).toBe('active');
		expect(nodes.slice(1).every((n) => n.state === 'pending')).toBe(true);
	});

	it('identifying / info -> first completed, second active', () => {
		const fromInfo = deriveLifecycle('info', 'disc');
		expect(fromInfo[0].state).toBe('completed');
		expect(fromInfo[1].state).toBe('active');
		expect(fromInfo.slice(2).every((n) => n.state === 'pending')).toBe(true);
	});

	it('video_ripping -> first two completed, ripping active', () => {
		const nodes = deriveLifecycle('video_ripping', 'disc');
		expect(nodes[0].state).toBe('completed');
		expect(nodes[1].state).toBe('completed');
		expect(nodes[2].state).toBe('active');
		expect(nodes.slice(3).every((n) => n.state === 'pending')).toBe(true);
	});

	it('legacy ripping wire string maps to ripping stage', () => {
		const nodes = deriveLifecycle('ripping', 'disc');
		expect(nodes[2].state).toBe('active');
	});

	it('audio_ripping maps to ripping stage', () => {
		const nodes = deriveLifecycle('audio_ripping', 'disc');
		expect(nodes[2].state).toBe('active');
	});

	it('makemkv_throttled maps to waiting stage (active)', () => {
		const nodes = deriveLifecycle('makemkv_throttled', 'disc');
		expect(nodes[0].state).toBe('active');
	});

	it('waiting_transcode maps to waiting stage (active)', () => {
		// waiting_transcode is the post-rip pre-transcode wait; we paint it on
		// the waiting node so the user sees "still waiting on something".
		const nodes = deriveLifecycle('waiting_transcode', 'disc');
		expect(nodes[0].state).toBe('active');
	});

	it('transcoding -> first three completed, transcoding active', () => {
		const nodes = deriveLifecycle('transcoding', 'disc');
		expect(nodes.slice(0, 3).every((n) => n.state === 'completed')).toBe(true);
		expect(nodes[3].state).toBe('active');
		expect(nodes[4].state).toBe('pending');
	});

	it('finishing maps to transcoding stage', () => {
		const nodes = deriveLifecycle('finishing', 'disc');
		expect(nodes[3].state).toBe('active');
	});

	it('success -> all five completed', () => {
		const nodes = deriveLifecycle('success', 'disc');
		expect(nodes.every((n) => n.state === 'completed')).toBe(true);
	});
});

describe('deriveLifecycle - failure', () => {
	it('fail snapshot paints last non-complete stage as failed', () => {
		const nodes = deriveLifecycle('fail', 'disc');
		// failed on the stage just before complete (transcoding for disc)
		expect(nodes[3].state).toBe('failed');
		expect(nodes[4].state).toBe('pending');
		// earlier stages marked completed (heuristic: we don't know where it
		// actually died, but the last reachable stage carries the failed marker)
		expect(nodes.slice(0, 3).every((n) => n.state === 'completed')).toBe(true);
	});

	it('failed / failure / error all treated as failure', () => {
		for (const s of ['failed', 'failure', 'error']) {
			const nodes = deriveLifecycle(s, 'disc');
			expect(nodes[3].state).toBe('failed');
		}
	});

	it('folder import failure paints last non-complete stage too', () => {
		const nodes = deriveLifecycle('fail', 'folder');
		// folder imports share the disc 5-stage lifecycle (folder_ripper still
		// runs a MakeMKV remux that drives VIDEO_RIPPING)
		expect(nodes.map((n) => n.id)).toEqual([
			'waiting', 'identifying', 'ripping', 'transcoding', 'complete'
		]);
		expect(nodes[3].state).toBe('failed'); // transcoding, the last reachable non-complete
	});
});

describe('deriveLifecycle - paused', () => {
	it('manual_paused paints active stage with paused state', () => {
		const nodes = deriveLifecycle('manual_paused', 'disc');
		expect(nodes[0].state).toBe('paused');
	});
});

describe('deriveLifecycle - folder imports', () => {
	it('folder source uses the same 5-stage lifecycle as disc', () => {
		const nodes = deriveLifecycle('transcoding', 'folder');
		expect(nodes.map((n) => n.id)).toEqual([
			'waiting', 'identifying', 'ripping', 'transcoding', 'complete'
		]);
		expect(nodes[3].state).toBe('active');
	});

	it('video_ripping on folder source paints ripping active', () => {
		// Repro: hifi job 224 (Annihilation folder import) reported
		// status=video_ripping but earlier 4-stage FOLDER_STAGES had no
		// ripping node, so deriveLifecycle returned all-pending.
		const nodes = deriveLifecycle('video_ripping', 'folder');
		expect(nodes[2].id).toBe('ripping');
		expect(nodes[2].state).toBe('active');
	});

	it('importing on folder source maps to ripping stage', () => {
		const nodes = deriveLifecycle('importing', 'folder');
		expect(nodes[2].id).toBe('ripping');
		expect(nodes[2].state).toBe('active');
	});
});

describe('deriveLifecycle - edge cases', () => {
	it('null status renders fully pending', () => {
		const nodes = deriveLifecycle(null, 'disc');
		expect(nodes.every((n) => n.state === 'pending')).toBe(true);
	});

	it('unknown status renders fully pending', () => {
		const nodes = deriveLifecycle('weird-state', 'disc');
		expect(nodes.every((n) => n.state === 'pending')).toBe(true);
	});

	it('case-insensitive status matching', () => {
		const upper = deriveLifecycle('TRANSCODING', 'disc');
		expect(upper[3].state).toBe('active');
	});
});

describe('isFolderImport', () => {
	it('identifies folder source_type', () => {
		expect(isFolderImport('folder')).toBe(true);
		expect(isFolderImport('disc')).toBe(false);
		expect(isFolderImport(null)).toBe(false);
		expect(isFolderImport(undefined)).toBe(false);
	});
});

describe('lifecycleColorVar', () => {
	it('maps each state to a distinct CSS var', () => {
		const colors = ['completed', 'active', 'paused', 'failed', 'pending'].map(
			(s) => lifecycleColorVar(s as never)
		);
		// All distinct
		expect(new Set(colors).size).toBe(colors.length);
	});

	it('uses theme tokens for known statuses', () => {
		expect(lifecycleColorVar('completed')).toContain('--color-status-success');
		expect(lifecycleColorVar('failed')).toContain('--color-status-error');
		expect(lifecycleColorVar('active')).toContain('--color-status-ripping');
	});
});
