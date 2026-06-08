<script lang="ts">
	import { onMount } from 'svelte';
	import { fetchJobStats, type JobStats } from '$lib/api/system';
	import SectionFrame from './SectionFrame.svelte';

	let stats = $state<JobStats | null>(null);
	let error = $state<string | null>(null);

	onMount(async () => {
		try {
			stats = await fetchJobStats();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load stats';
		}
	});
</script>

<SectionFrame label="Ripping Statistics" accent="#10b981">
	<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
		<div class="text-center">
			<div class="text-2xl font-bold text-gray-900 dark:text-white">{stats ? stats.total : '—'}</div>
			<div class="text-xs text-gray-500 dark:text-gray-400">Total Rips</div>
		</div>
		<div class="text-center">
			<div class="text-2xl font-bold text-green-600 dark:text-green-400">{stats ? (stats.by_status.success ?? 0) : '—'}</div>
			<div class="text-xs text-gray-500 dark:text-gray-400">Success</div>
		</div>
		<div class="text-center">
			<div class="text-2xl font-bold text-red-600 dark:text-red-400">{stats ? (stats.by_status.fail ?? 0) : '—'}</div>
			<div class="text-xs text-gray-500 dark:text-gray-400">Failed</div>
		</div>
		<div class="text-center">
			<div class="text-2xl font-bold text-blue-600 dark:text-blue-400">
				{stats ? (stats.by_status.ripping ?? 0) + (stats.by_status.transcoding ?? 0) : '—'}
			</div>
			<div class="text-xs text-gray-500 dark:text-gray-400">Active</div>
		</div>
	</div>
	{#if stats && Object.keys(stats.by_type).length > 0}
		<div class="mt-3 flex flex-wrap gap-3 border-t border-primary/15 pt-3 dark:border-primary/20">
			{#each Object.entries(stats.by_type) as [type, count]}
				<div class="flex items-center gap-1.5 text-sm text-gray-600 dark:text-gray-400">
					<span class="font-medium capitalize">{type}</span>
					<span class="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary-text dark:bg-primary/15 dark:text-primary-text-dark">{count}</span>
				</div>
			{/each}
		</div>
	{/if}
</SectionFrame>
