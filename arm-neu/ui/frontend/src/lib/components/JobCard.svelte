<script lang="ts">
	import type { JobSchema as Job } from '$lib/types/api.gen';
	import PosterImage from './PosterImage.svelte';
	import StatusBadge from './StatusBadge.svelte';
	import TimeAgo from './TimeAgo.svelte';
	import ProgressBar from './ProgressBar.svelte';
	import { elapsedTime } from '$lib/utils/format';
	import { getVideoTypeConfig, isJobActive, discTypeLabel } from '$lib/utils/job-type';
	import DiscTypeIcon from './DiscTypeIcon.svelte';
	import SkeletonCard from './SkeletonCard.svelte';
	import JobLifecycle from './JobLifecycle.svelte';
	import { Disc } from 'lucide-svelte';

	interface Props {
		job?: Job;
		driveNames?: Record<string, string> | null;
		progress?: number | null;
		progressStage?: string | null;
	}

	let { job, driveNames, progress = null, progressStage = null }: Props = $props();
	let driveName = $derived(job?.devpath ? (driveNames?.[job.devpath] ?? null) : null);

	let typeConfig = $derived(getVideoTypeConfig(job?.video_type ?? null, job?.disctype ?? null));
	let active = $derived(isJobActive(job?.status ?? null));
	let hasErrors = $derived(!!job?.errors && job.errors.trim().length > 0);
	let isFolderImport = $derived(job?.source_type === 'folder');
	let discLabelDiffers = $derived(
		!!job?.label && !!job?.title && job.label.toLowerCase() !== job.title.toLowerCase()
	);
</script>

{#if !job}
	<SkeletonCard />
{:else}
<a
	href="/jobs/{job.job_id}"
	class="block rounded-lg border border-primary/20 border-l-4 {typeConfig.accentBorder} bg-surface p-4 shadow-xs transition hover:shadow-md dark:border-primary/20 dark:bg-surface-dark"
>
	<div class="flex gap-4">
		<PosterImage url={job.poster_url} alt={job.title ?? 'Poster'} class="h-24 w-16 rounded-sm object-cover" />
		<div class="min-w-0 flex-1">
			<!-- Row 1: Title + Status -->
			<div class="flex items-start justify-between gap-2">
				<h3 class="truncate font-semibold text-gray-900 dark:text-white">
					{job.title || job.label || 'Untitled'}
				</h3>
				<StatusBadge status={isFolderImport && (job.status === 'video_ripping' || job.status === 'ripping') ? 'importing' : job.status} />
			</div>

			<!-- Row 2: Year, IMDB, disc label -->
			<div class="mt-0.5 flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
				{#if job.year}
					<span>{job.year}</span>
				{/if}
				{#if job.imdb_id}
					<button
						onclick={(e) => { e.preventDefault(); e.stopPropagation(); window.open(`https://www.imdb.com/title/${job.imdb_id}/`, '_blank', 'noopener,noreferrer'); }}
						class="inline-flex items-center rounded-sm bg-yellow-400 px-1.5 py-0.5 text-xs font-bold text-black hover:bg-yellow-300"
					>IMDb</button>
				{/if}
				{#if discLabelDiffers}
					<span class="truncate font-mono text-xs text-gray-400 dark:text-gray-500">{job.label}</span>
				{/if}
			</div>

			<!-- Row 3: Active → stage/titles/elapsed; Completed → duration/finish -->
			<div class="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-500 dark:text-gray-400">
				{#if active}
					<JobLifecycle status={job.status} sourceType={job.source_type} size="sm" />
					{#if job.stage}
						<span class="rounded-sm bg-primary-light-bg px-1.5 py-0.5 font-medium text-primary-text dark:bg-primary-light-bg-dark/20 dark:text-primary-text-dark">{job.stage}</span>
					{/if}
					{#if isFolderImport}
						<!-- Folder imports use "all" mode — don't show per-track counts -->
					{:else if job.status === 'info'}
						<span>Scanning{job.no_of_titles ? `... ${job.no_of_titles} titles` : '...'}</span>
					{:else if job.track_counts && (job.track_counts.total ?? 0) > 0}
						<span>{job.track_counts.ripped ?? 0} / {job.track_counts.total ?? 0} titles</span>
					{:else if job.no_of_titles != null}
						<span>{job.no_of_titles} title{job.no_of_titles === 1 ? '' : 's'}</span>
					{/if}
					{#if job.start_time}
						<span>{elapsedTime(job.start_time)}</span>
					{/if}
				{:else}
					{#if job.job_length}
						<span>{job.job_length}</span>
					{/if}
					{#if job.stop_time}
						<TimeAgo date={job.stop_time} />
					{/if}
				{/if}
				{#if hasErrors}
					{#if job.logfile}
						<button type="button" onclick={(e) => { e.preventDefault(); e.stopPropagation(); window.location.href = `/logs/${job.logfile}`; }} class="inline-flex items-center gap-0.5 text-red-500 hover:text-red-600 dark:text-red-400 dark:hover:text-red-300" title={job.errors ?? ''}>
							<svg class="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 20 20">
								<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
							</svg>
							errors
						</button>
					{:else}
						<span class="inline-flex items-center gap-0.5 text-red-500 dark:text-red-400" title={job.errors ?? ''}>
							<svg class="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 20 20">
								<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
							</svg>
							errors
						</span>
					{/if}
				{/if}
			</div>

			<!-- Row 4: Type badge, disctype, device/source, start time -->
			<div class="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 text-xs text-gray-500 dark:text-gray-400">
				<span class="rounded-sm px-1.5 py-0.5 font-medium {typeConfig.badgeClasses}">{typeConfig.label}</span>
				{#if job.disctype}
					<span class="inline-flex items-center gap-1 rounded-sm bg-primary/10 px-1.5 py-0.5 dark:bg-primary/15">
						<DiscTypeIcon disctype={job.disctype} size="h-3.5 w-3.5" />
						{discTypeLabel(job.disctype)}
					</span>
				{/if}
				{#if job.source_type === 'folder'}
					<span class="inline-flex items-center gap-1 rounded-sm bg-violet-100 px-1.5 py-0.5 font-medium text-violet-700 dark:bg-violet-900/30 dark:text-violet-400">
						<svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
						</svg>
						Folder Import
					</span>
				{:else if job.source_type === 'iso'}
					<span class="inline-flex items-center gap-1 rounded-sm bg-violet-100 px-1.5 py-0.5 font-medium text-violet-700 dark:bg-violet-900/30 dark:text-violet-400">
						<Disc class="h-3 w-3" />
						ISO
					</span>
				{/if}
				{#if job.disc_number}
					<span class="rounded-sm bg-primary/10 px-1.5 py-0.5 dark:bg-primary/15">Disc {job.disc_number}{#if job.disc_total}/{job.disc_total}{/if}</span>
				{/if}
				{#if job.devpath}
					<span>{driveName ?? job.devpath}</span>
				{:else if job.source_path}
					<span class="truncate max-w-48" title={job.source_path}>{job.source_path.split('/').slice(-2).join('/')}</span>
				{/if}
				{#if !active && job.start_time}
					<TimeAgo date={job.start_time} />
				{/if}
			</div>
		</div>
	</div>
	{#if active}
		<div class="mt-3">
			{#if progress != null && progress > 0}
				<ProgressBar value={progress} color="bg-primary" />
				{#if progressStage}
					<p class="mt-0.5 text-xs text-gray-400 dark:text-gray-500">{progressStage}</p>
				{/if}
			{:else}
				<div class="h-2.5 overflow-hidden rounded-full bg-primary/15 dark:bg-primary/15">
					<div class="h-full w-1/3 animate-indeterminate rounded-full bg-primary/60"></div>
				</div>
			{/if}
		</div>
	{/if}
</a>
{/if}
