<script lang="ts">
	import type { JobSchema as Job } from '$lib/types/api.gen';
	import StatusBadge from './StatusBadge.svelte';
	import ProgressBar from './ProgressBar.svelte';
	import { elapsedTime, etaTime, statusAccentVar } from '$lib/utils/format';
	import { getVideoTypeConfig, isJobActive, discTypeLabel } from '$lib/utils/job-type';
	import DiscTypeIcon from './DiscTypeIcon.svelte';
	import TimeAgo from './TimeAgo.svelte';
	import PosterImage from './PosterImage.svelte';
	import SkeletonCard from './SkeletonCard.svelte';
	import { abandonJob } from '$lib/api/jobs';
	import { slide } from 'svelte/transition';

	interface Props {
		job?: Job;
		driveNames?: Record<string, string> | null;
		progress?: number | null;
		progressStage?: string | null;
		tracksRipped?: number | null;
		tracksTotal?: number | null;
	}

	let { job, driveNames, progress = null, progressStage = null, tracksRipped = null, tracksTotal = null }: Props = $props();

	function formatStage(s: string): string {
		if (s === 'scratch-to-media') return 'Copying to shared storage';
		if (s === 'work-to-completed') return 'Moving to completed';
		return s;
	}

	// Use progress-polled counts when available (real-time), fall back to DB counts
	let displayRipped = $derived(tracksRipped ?? job?.track_counts?.ripped ?? 0);
	let displayTotal = $derived(tracksTotal ?? job?.track_counts?.total ?? 0);
	let expanded = $state(false);

	let driveName = $derived(job?.devpath ? (driveNames?.[job.devpath] ?? null) : null);
	let typeConfig = $derived(getVideoTypeConfig(job?.video_type ?? null, job?.disctype ?? null));
	let active = $derived(isJobActive(job?.status ?? null));
	let hasErrors = $derived(!!job?.errors && job.errors.trim().length > 0);
	let isFolderImport = $derived(job?.source_type === 'folder');
	let accentVar = $derived(
		statusAccentVar(isFolderImport && job?.status === 'ripping' ? 'importing' : job?.status)
	);
	let etaDisplay = $derived(
		active && job?.start_time ? etaTime(job.start_time, progress) : null
	);
	let discLabelDiffers = $derived(
		!!job?.label && !!job?.title && job.label.toLowerCase() !== job.title.toLowerCase()
	);

	function toggle(e: MouseEvent) {
		// Don't toggle when clicking links/buttons inside
		if ((e.target as HTMLElement).closest('a, button:not(.row-toggle)')) return;
		expanded = !expanded;
	}

	let abandoning = $state(false);
	let abandonError = $state<string | null>(null);

	async function handleAbandon() {
		if (!job) return;
		if (!confirm(`Abandon job "${job.title || job.label || job.job_id}"?`)) return;
		abandoning = true;
		abandonError = null;
		try {
			await abandonJob(job.job_id);
		} catch (e) {
			abandonError = e instanceof Error ? e.message : 'Failed to abandon';
		} finally {
			abandoning = false;
		}
	}
</script>

{#if !job}
	<SkeletonCard lines={3} />
{:else}
<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
<div
	class="rounded-lg border border-primary/20 border-l-4 {typeConfig.accentBorder} bg-surface shadow-xs transition dark:border-primary/20 dark:bg-surface-dark"
	onclick={toggle}
	role="button"
	tabindex="0"
>
	<!-- Collapsed row -->
	<div class="cursor-pointer px-4 pt-2.5" class:pb-2.5={!active}>
		<div class="flex items-center gap-3">
			<!-- Poster thumbnail -->
			<PosterImage url={job.poster_url} alt="" class="h-10 w-7 shrink-0 rounded-sm object-cover" />

			<!-- Title -->
			<h3 class="min-w-0 flex-shrink truncate font-semibold text-sm text-gray-900 dark:text-white">
				{job.title || job.label || 'Untitled'}
			</h3>

			<!-- Year -->
			{#if job.year}
				<span class="shrink-0 text-xs text-gray-500 dark:text-gray-400">{job.year}</span>
			{/if}

			<!-- Status badge: folder-import jobs in the rip phase render as
			     'importing' regardless of which JobState rip variant arm-neu
			     emits. Both v2.0.0 'video_ripping' and the legacy 'ripping'
			     are matched so in-flight jobs mid-deploy still show the
			     correct badge. -->
			<div class="shrink-0">
				<StatusBadge status={isFolderImport && (job.status === 'video_ripping' || job.status === 'ripping') ? 'importing' : job.status} />
			</div>

			<!-- Type + disc badges -->
			<div class="hidden sm:flex shrink-0 items-center gap-1.5">
				<span class="rounded-sm px-1.5 py-0.5 text-xs font-medium {typeConfig.badgeClasses}">{typeConfig.label}</span>
				{#if job.disctype}
					<span class="inline-flex items-center gap-0.5 rounded-sm bg-primary/10 px-1.5 py-0.5 text-xs dark:bg-primary/15">
						<DiscTypeIcon disctype={job.disctype} size="h-3 w-3" />
						{discTypeLabel(job.disctype)}
					</span>
				{/if}
			</div>

			<!-- Drive / source -->
			<span class="hidden md:inline shrink-0 text-xs text-gray-500 dark:text-gray-400">
				{#if job.devpath}
					{driveName ?? job.devpath}
				{:else if job.source_path}
					{job.source_path.split('/').slice(-1)[0]}
				{/if}
			</span>

			<!-- Spacer -->
			<span class="flex-1"></span>

			<!-- Track counts -->
			{#if active && displayTotal > 0 && !isFolderImport}
				<span class="shrink-0 text-xs text-gray-500 dark:text-gray-400">
					{displayRipped}/{displayTotal}
				</span>
			{/if}

			<!-- ETA (active) or Elapsed (inactive but recent) -->
			{#if active}
				<span class="shrink-0 text-xs text-gray-500 dark:text-gray-400" title="Estimated time remaining">
					{etaDisplay ? `~${etaDisplay}` : elapsedTime(job.start_time)}
				</span>
			{/if}

			<!-- Errors indicator -->
			{#if hasErrors}
				<span class="shrink-0 text-red-500 dark:text-red-400" title={job.errors ?? ''}>
					<svg class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
						<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
					</svg>
				</span>
			{/if}

			<!-- Expand chevron -->
			<button class="row-toggle shrink-0 p-0.5 text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 transition-transform" class:rotate-180={expanded} title={expanded ? 'Collapse' : 'Expand'}>
				<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
					<path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
				</svg>
			</button>
		</div>
	</div>

	<!-- Progress row: own line below a divider, indented under content -->
	{#if active}
		<div class="mt-2 border-t border-primary/10 dark:border-primary/15 px-4 pl-[64px] pr-4 py-2.5">
			{#if progress != null}
				<!-- Render the bar even at 0%. The MakeMKV prelude (libredrive
				     init, key ingest) can sit at 0 for several seconds and
				     "ripping 0%" is more honest than an indeterminate spinner. -->
				<ProgressBar value={progress} colorVar={accentVar} />
			{:else}
				<div class="flex items-center gap-2">
					<div class="h-2.5 flex-1 overflow-hidden rounded-full bg-primary/15">
						<div
							class="h-full w-1/3 animate-indeterminate rounded-full"
							style="background: {accentVar}; opacity: 0.6"
						></div>
					</div>
					<span class="min-w-[3ch] text-right text-xs text-gray-500 dark:text-gray-400">…</span>
				</div>
			{/if}
		</div>
	{/if}

	<!-- Expanded detail -->
	{#if expanded}
		<div transition:slide={{ duration: 200 }} class="border-t border-primary/10 px-4 py-3 dark:border-primary/15">
			<div class="flex gap-4">
				<!-- Poster (larger) -->
				<PosterImage url={job.poster_url} alt={job.title ?? 'Poster'} class="h-32 w-22 shrink-0 rounded-sm object-cover" />

				<div class="min-w-0 flex-1">
					<!-- Title + links + abandon -->
					<div class="mb-2 flex items-start justify-between gap-2">
						<a href="/jobs/{job.job_id}" class="text-sm font-semibold text-primary hover:underline">{job.title || job.label || 'Untitled'}</a>
						<div class="flex items-center gap-2">
							{#if job.imdb_id}
								<a href="https://www.imdb.com/title/{job.imdb_id}/" target="_blank" rel="noopener noreferrer" class="inline-flex items-center rounded-sm bg-yellow-400 px-1.5 py-0.5 text-xs font-bold text-black hover:bg-yellow-300">IMDb</a>
							{/if}
							{#if active}
								<button
									onclick={handleAbandon}
									disabled={abandoning}
									class="text-xs font-medium text-red-500 hover:underline disabled:opacity-50 dark:text-red-400"
								>{abandoning ? 'Abandoning…' : 'Abandon'}</button>
							{/if}
						</div>
					</div>
					{#if abandonError}
						<div class="mb-2 text-xs text-red-500 dark:text-red-400">{abandonError}</div>
					{/if}

					<!-- Data table -->
					<table class="w-full text-xs">
						<tbody class="divide-y divide-primary/5 dark:divide-primary/10">
							<tr>
								<td class="py-1 pr-4 text-gray-500 dark:text-gray-400 whitespace-nowrap">Job ID</td>
								<td class="py-1 text-gray-900 dark:text-white">{job.job_id}</td>
								<td class="py-1 pr-4 text-gray-500 dark:text-gray-400 whitespace-nowrap pl-6">Status</td>
								<td class="py-1"><StatusBadge status={isFolderImport && (job.status === 'video_ripping' || job.status === 'ripping') ? 'importing' : job.status} /></td>
							</tr>
							<tr>
								<td class="py-1 pr-4 text-gray-500 dark:text-gray-400 whitespace-nowrap">Type</td>
								<td class="py-1"><span class="rounded-sm px-1 py-0.5 font-medium {typeConfig.badgeClasses}">{typeConfig.label}</span></td>
								<td class="py-1 pr-4 text-gray-500 dark:text-gray-400 whitespace-nowrap pl-6">Disc</td>
								<td class="py-1 text-gray-900 dark:text-white">
									{#if job.disctype}
										<span class="inline-flex items-center gap-1"><DiscTypeIcon disctype={job.disctype} size="h-3.5 w-3.5" />{discTypeLabel(job.disctype)}</span>
									{:else}
										—
									{/if}
								</td>
							</tr>
							<tr>
								<td class="py-1 pr-4 text-gray-500 dark:text-gray-400 whitespace-nowrap">Year</td>
								<td class="py-1 text-gray-900 dark:text-white">{job.year || '—'}</td>
								<td class="py-1 pr-4 text-gray-500 dark:text-gray-400 whitespace-nowrap pl-6">
									{#if job.devpath}Drive{:else}Source{/if}
								</td>
								<td class="py-1 text-gray-900 dark:text-white">
									{#if job.devpath}
										{driveName ?? job.devpath}
									{:else if job.source_path}
										<span class="truncate" title={job.source_path}>{job.source_path}</span>
									{:else}
										—
									{/if}
								</td>
							</tr>
							{#if discLabelDiffers || job.disc_number || job.stage}
								<tr>
									<td class="py-1 pr-4 text-gray-500 dark:text-gray-400 whitespace-nowrap">Label</td>
									<td class="py-1 font-mono text-gray-600 dark:text-gray-400">{job.label || '—'}</td>
									{#if job.disc_number}
										<td class="py-1 pr-4 text-gray-500 dark:text-gray-400 whitespace-nowrap pl-6">Disc #</td>
										<td class="py-1 text-gray-900 dark:text-white">{job.disc_number}{#if job.disc_total} / {job.disc_total}{/if}</td>
									{:else if job.stage}
										<td class="py-1 pr-4 text-gray-500 dark:text-gray-400 whitespace-nowrap pl-6">Stage</td>
										<td class="py-1"><span class="rounded-sm bg-primary-light-bg px-1.5 py-0.5 font-medium text-primary-text dark:bg-primary-light-bg-dark/20 dark:text-primary-text-dark">{job.stage}</span></td>
									{:else}
										<td class="py-1"></td><td class="py-1"></td>
									{/if}
								</tr>
							{/if}
							<tr>
								<td class="py-1 pr-4 text-gray-500 dark:text-gray-400 whitespace-nowrap">Tracks</td>
								<td class="py-1 text-gray-900 dark:text-white">
									{#if !isFolderImport && displayTotal > 0}
										{displayRipped} / {displayTotal} ripped
									{:else if job.no_of_titles != null}
										{job.no_of_titles} title{job.no_of_titles === 1 ? '' : 's'}
									{:else}
										—
									{/if}
								</td>
								<td class="py-1 pr-4 text-gray-500 dark:text-gray-400 whitespace-nowrap pl-6">
									{#if !active && job.job_length}Total{:else}ETA{/if}
								</td>
								<td class="py-1 text-gray-900 dark:text-white">
									{#if active && job.start_time}
										{etaTime(job.start_time, progress) ?? '—'}
									{:else if !active && job.job_length}
										{job.job_length}
									{:else}
										—
									{/if}
								</td>
							</tr>
							<tr>
								<td class="py-1 pr-4 text-gray-500 dark:text-gray-400 whitespace-nowrap">Started</td>
								<td class="py-1 text-gray-900 dark:text-white">{#if job.start_time}<TimeAgo date={job.start_time} />{:else}—{/if}</td>
								<td class="py-1 pr-4 text-gray-500 dark:text-gray-400 whitespace-nowrap pl-6">
									{#if !active}Finished{:else}Progress{/if}
								</td>
								<td class="py-1 text-gray-900 dark:text-white">
									{#if !active && job.stop_time}
										<TimeAgo date={job.stop_time} />
									{:else if active && progressStage}
										{formatStage(progressStage)}
									{:else}
										—
									{/if}
								</td>
							</tr>
							{#if isFolderImport}
								<tr>
									<td class="py-1 pr-4 text-gray-500 dark:text-gray-400 whitespace-nowrap">Mode</td>
									<td class="py-1 inline-flex items-center gap-1 text-violet-600 dark:text-violet-400">
										<svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
										</svg>
										Folder Import
									</td>
									<td class="py-1"></td><td class="py-1"></td>
								</tr>
							{/if}
						</tbody>
					</table>

					<!-- Errors -->
					{#if hasErrors}
						<div class="mt-2 flex items-center gap-1 text-xs text-red-500 dark:text-red-400">
							<svg class="h-3.5 w-3.5 shrink-0" fill="currentColor" viewBox="0 0 20 20">
								<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
							</svg>
							{#if job.logfile}
								<a href="/logs/{job.logfile}" class="hover:underline">{job.errors}</a>
							{:else}
								<span>{job.errors}</span>
							{/if}
						</div>
					{/if}

					<!-- Actions -->
					<div class="mt-3 flex items-center gap-2">
						<a
							href="/jobs/{job.job_id}"
							class="rounded-md border border-primary/30 bg-primary/15 px-3 py-1 text-xs font-medium text-primary hover:bg-primary/25"
						>Open details</a>
						{#if job.logfile}
							<a
								href="/logs/{job.logfile}"
								class="rounded-md border border-primary/25 bg-transparent px-3 py-1 text-xs font-medium text-gray-600 hover:bg-primary/10 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white"
							>View log</a>
						{/if}
					</div>
				</div>
			</div>
		</div>
	{/if}
</div>
{/if}
