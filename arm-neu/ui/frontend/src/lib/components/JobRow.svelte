<script lang="ts">
	import type { JobSchema as Job } from '$lib/types/api.gen';
	import JobActions from './JobActions.svelte';
	import StatusBadge from './StatusBadge.svelte';
	import TimeAgo from './TimeAgo.svelte';
	import Skeleton from './Skeleton.svelte';
	import { elapsedTime } from '$lib/utils/format';
	import { getVideoTypeConfig, isJobActive, discTypeLabel } from '$lib/utils/job-type';
	import DiscTypeIcon from './DiscTypeIcon.svelte';
	import VideoTypeIcon from './VideoTypeIcon.svelte';

	interface Props {
		job?: Job;
		driveNames?: Record<string, string>;
		onaction?: () => void;
		selected?: boolean;
		onselect?: (jobId: number, selected: boolean) => void;
	}

	let { job, driveNames = {}, onaction, selected = false, onselect }: Props = $props();
	let driveName = $derived(job?.devpath ? driveNames[job.devpath] : null);

	let typeConfig = $derived(getVideoTypeConfig(job?.video_type ?? null, job?.disctype ?? null));
	let active = $derived(isJobActive(job?.status ?? null));
	let hasErrors = $derived(!!job?.errors && job.errors.trim().length > 0);
	let discLabelDiffers = $derived(
		!!job?.label && !!job?.title && job.label.toLowerCase() !== job.title.toLowerCase()
	);
</script>

{#if !job}
	<tr aria-busy="true">
		{#each { length: 9 } as _}
			<td class="p-2" data-label=""><Skeleton variant="line" width="80%" height="1rem" /></td>
		{/each}
	</tr>
{:else}
<tr class="border-b border-primary/20 hover:bg-page dark:border-primary/20 dark:hover:bg-primary/5 {selected ? 'bg-primary/[0.03] dark:bg-primary/[0.06]' : ''}">
	<!-- Checkbox -->
	<td class="px-4 py-3 w-8" data-label="">
		<input
			type="checkbox"
			checked={selected}
			onchange={() => onselect?.(job.job_id, !selected)}
			class="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary dark:border-gray-600 dark:bg-gray-700"
		/>
	</td>

	<!-- Title -->
	<td class="px-4 py-3" data-label="Title">
		<div class="flex items-center gap-2">
			<VideoTypeIcon icon={typeConfig.icon} class="h-4 w-4 shrink-0 {typeConfig.iconColor}" />
			<div class="min-w-0">
				<a href="/jobs/{job.job_id}" class="font-medium text-primary-text hover:underline dark:text-primary-text-dark">
					{job.title || job.label || 'Untitled'}
				</a>
				{#if discLabelDiffers}
					<div class="truncate font-mono text-xs text-gray-400 dark:text-gray-500">{job.label}</div>
				{/if}
			</div>
		</div>
	</td>

	<!-- Year + IMDB -->
	<td class="px-4 py-3 text-sm" data-label="Year">
		<div class="flex items-center gap-1.5">
			{#if job.year}
				<span>{job.year}</span>
			{/if}
			{#if job.imdb_id}
				<a
					href="https://www.imdb.com/title/{job.imdb_id}/"
					target="_blank"
					rel="noopener noreferrer"
					class="inline-flex items-center rounded-sm bg-yellow-400 px-1 py-0.5 text-[10px] font-bold leading-none text-black hover:bg-yellow-300"
				>IMDb</a>
			{/if}
		</div>
	</td>

	<!-- Status + stage/error -->
	<td class="px-4 py-3" data-label="Status">
		<div>
			<StatusBadge status={job.status} />
			{#if active && job.stage}
				<div class="mt-0.5 text-xs text-gray-500 dark:text-gray-400">{job.stage}</div>
			{/if}
			{#if hasErrors}
				{@const isWarning = job.status === 'success'}
				{#if job.logfile}
					<a href="/logs/{job.logfile}" class="mt-0.5 flex items-center gap-0.5 text-xs {isWarning ? 'text-yellow-500 hover:text-yellow-600 dark:text-yellow-400 dark:hover:text-yellow-300' : 'text-red-500 hover:text-red-600 dark:text-red-400 dark:hover:text-red-300'}" title={job.errors ?? ''}>
						<svg class="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
							<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
						</svg>
						{isWarning ? 'warnings' : 'errors'}
					</a>
				{:else}
					<div class="mt-0.5 flex items-center gap-0.5 text-xs {isWarning ? 'text-yellow-500 dark:text-yellow-400' : 'text-red-500 dark:text-red-400'}" title={job.errors ?? ''}>
						<svg class="h-3 w-3" fill="currentColor" viewBox="0 0 20 20">
							<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
						</svg>
						{isWarning ? 'warnings' : 'errors'}
					</div>
				{/if}
			{/if}
		</div>
	</td>

	<!-- Type (colored badge) -->
	<td class="px-4 py-3 text-sm" data-label="Type">
		<span class="rounded-sm px-1.5 py-0.5 text-xs font-medium {typeConfig.badgeClasses}">{typeConfig.label}</span>
	</td>

	<!-- Disc -->
	<td class="px-4 py-3 text-sm" data-label="Disc">
		{#if job.disctype}
			<span class="inline-flex items-center gap-1">
				<DiscTypeIcon disctype={job.disctype} size="h-4 w-4" />
				{discTypeLabel(job.disctype)}
			</span>
		{/if}
		{#if job.disc_number}
			<div class="text-xs text-gray-400 dark:text-gray-500">Disc {job.disc_number}{#if job.disc_total} of {job.disc_total}{/if}</div>
		{/if}
	</td>

	<!-- Device / Source -->
	<td class="px-4 py-3 text-sm" data-label="Source">
		{#if job.source_type === 'folder'}
			<span class="inline-flex items-center gap-1 text-violet-600 dark:text-violet-400" title={job.source_path ?? ''}>
				<svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
				</svg>
				Folder
			</span>
		{:else}
			{driveName ?? job.devpath ?? ''}
		{/if}
	</td>

	<!-- Started + elapsed/duration sub-text -->
	<td class="px-4 py-3 text-sm" data-label="Started">
		{#if job.start_time}
			<TimeAgo date={job.start_time} />
			{#if active}
				<div class="text-xs text-gray-400 dark:text-gray-500">{elapsedTime(job.start_time)}</div>
			{:else if job.job_length}
				<div class="text-xs text-gray-400 dark:text-gray-500">{job.job_length}</div>
			{/if}
		{:else}
			N/A
		{/if}
	</td>

	<!-- Actions -->
	<td class="px-4 py-3" data-label="">
		<JobActions {job} compact {onaction} />
	</td>
</tr>
{/if}
