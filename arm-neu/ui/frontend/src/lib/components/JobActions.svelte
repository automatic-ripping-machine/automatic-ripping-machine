<script lang="ts">
	import type { JobSchema as Job } from '$lib/types/api.gen';
	import { abandonJob, deleteJob, fixJobPermissions, bulkPurgeJobs } from '$lib/api/jobs';
	import { isJobActive } from '$lib/utils/job-type';

	interface Props {
		job: Job;
		onaction?: () => void;
		ondelete?: () => void;
		compact?: boolean;
	}

	let { job, onaction, ondelete, compact = false }: Props = $props();

	let loading = $state<string | null>(null);
	let feedback = $state<{ type: 'success' | 'error'; message: string } | null>(null);

	let active = $derived(isJobActive(job.status));
	let statusLower = $derived(job.status?.toLowerCase() ?? '');
	let canAbandon = $derived(active);
	let canDelete = $derived(statusLower === 'success' || statusLower === 'fail' || statusLower === 'waiting_transcode');
	let canFixPerms = $derived(statusLower === 'success');
	let canPurge = $derived(statusLower === 'fail' || statusLower === 'success');

	function clearFeedback() {
		setTimeout(() => (feedback = null), 3000);
	}

	async function handleAbandon() {
		if (!confirm(`Abandon job "${job.title || job.label || job.job_id}"?`)) return;
		loading = 'abandon';
		feedback = null;
		try {
			await abandonJob(job.job_id);
			feedback = { type: 'success', message: 'Job abandoned' };
			onaction?.();
		} catch (e) {
			feedback = { type: 'error', message: e instanceof Error ? e.message : 'Failed to abandon' };
		} finally {
			loading = null;
			clearFeedback();
		}
	}

	async function handleDelete() {
		if (!confirm(`Delete job "${job.title || job.label || job.job_id}"? This cannot be undone.`)) return;
		loading = 'delete';
		feedback = null;
		try {
			await deleteJob(job.job_id);
			if (ondelete) {
				ondelete();
				return;
			}
			feedback = { type: 'success', message: 'Job deleted' };
			onaction?.();
		} catch (e) {
			feedback = { type: 'error', message: e instanceof Error ? e.message : 'Failed to delete' };
		} finally {
			loading = null;
			clearFeedback();
		}
	}

	async function handleFixPerms() {
		if (!confirm(`Fix permissions for job "${job.title || job.label || job.job_id}"?`)) return;
		loading = 'fixperms';
		feedback = null;
		try {
			await fixJobPermissions(job.job_id);
			feedback = { type: 'success', message: 'Permissions fixed' };
			onaction?.();
		} catch (e) {
			feedback = { type: 'error', message: e instanceof Error ? e.message : 'Failed to fix permissions' };
		} finally {
			loading = null;
			clearFeedback();
		}
	}

	async function handlePurge() {
		if (!confirm(`Purge job "${job.title || job.label || job.job_id}"? This will delete the job record, log files, and raw files.`)) return;
		loading = 'purge';
		feedback = null;
		try {
			await bulkPurgeJobs({ job_ids: [job.job_id] });
			if (ondelete) {
				ondelete();
				return;
			}
			feedback = { type: 'success', message: 'Job purged' };
			onaction?.();
		} catch (e) {
			feedback = { type: 'error', message: e instanceof Error ? e.message : 'Failed to purge' };
		} finally {
			loading = null;
			clearFeedback();
		}
	}

	let btnBase = $derived(
		compact
			? 'rounded px-2 py-0.5 text-xs font-medium disabled:opacity-50 transition-colors'
			: 'rounded-full px-3 py-1.5 text-xs font-medium disabled:opacity-50 transition-colors'
	);
</script>

{#if canAbandon || canDelete || canFixPerms || canPurge}
	<div class="flex flex-wrap items-center gap-1.5">
		{#if canAbandon}
			<button
				onclick={handleAbandon}
				disabled={loading !== null}
				class="{btnBase} bg-yellow-100 text-yellow-700 hover:bg-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-400 dark:hover:bg-yellow-900/50"
			>
				{loading === 'abandon' ? 'Abandoning...' : 'Abandon'}
			</button>
		{/if}
		{#if canFixPerms}
			<button
				onclick={handleFixPerms}
				disabled={loading !== null}
				class="{btnBase} bg-blue-100 text-blue-700 ring-1 ring-blue-200 hover:bg-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:ring-blue-800 dark:hover:bg-blue-900/50"
			>
				{loading === 'fixperms' ? 'Fixing...' : 'Fix Permissions'}
			</button>
		{/if}
		{#if canDelete}
			<button
				onclick={handleDelete}
				disabled={loading !== null}
				class="{btnBase} bg-red-100 text-red-700 ring-1 ring-red-200 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400 dark:ring-red-800 dark:hover:bg-red-900/50"
			>
				{loading === 'delete' ? 'Deleting...' : 'Delete'}
			</button>
		{/if}
		{#if canPurge}
			<button
				onclick={handlePurge}
				disabled={loading !== null}
				class="{btnBase} bg-orange-100 text-orange-700 ring-1 ring-orange-200 hover:bg-orange-200 dark:bg-orange-900/30 dark:text-orange-400 dark:ring-orange-800 dark:hover:bg-orange-900/50"
			>
				{loading === 'purge' ? 'Purging...' : 'Purge'}
			</button>
		{/if}
		{#if feedback}
			<span class="text-xs {feedback.type === 'success' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}">
				{feedback.message}
			</span>
		{/if}
	</div>
{/if}
