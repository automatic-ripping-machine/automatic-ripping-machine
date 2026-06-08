<script lang="ts">
	import { onMount } from 'svelte';
	import { fade } from 'svelte/transition';
	import { fetchTranscoderJobs, retryTranscoderJob, deleteTranscoderJob, retranscodeTranscoderJob } from '$lib/api/transcoder';
	import { fetchStructuredTranscoderLogContent } from '$lib/api/logs';
	import { posterSrc, posterFallback } from '$lib/utils/poster';
	import type { TranscoderJobListResponse } from '$lib/types/api.gen';
	import { getVideoTypeConfig, discTypeLabel } from '$lib/utils/job-type';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import DiscTypeIcon from '$lib/components/DiscTypeIcon.svelte';
	import ProgressBar from '$lib/components/ProgressBar.svelte';
	import TimeAgo from '$lib/components/TimeAgo.svelte';
	import InlineLogFeed from '$lib/components/InlineLogFeed.svelte';
	import LoadState from '$lib/components/LoadState.svelte';
	import SkeletonCard from '$lib/components/SkeletonCard.svelte';
	import { fadeIn, fadeOut } from '$lib/transitions';
	import { dashboard } from '$lib/stores/dashboard';
	import { transcoderStats, transcoderWorkers, getJobsCache, setJobsCache } from '$lib/stores/transcoder';

	const emptyJobs: TranscoderJobListResponse = { jobs: [], total: 0 };

	// Singleton stores (see $lib/stores/transcoder) so stats/workers survive
	// navigation and don't flash the offline/empty state on every visit.
	const stats = transcoderStats;
	const statsError = stats.error;
	const statsInitialized = stats.initialized;
	const workers = transcoderWorkers;
	let activeTab = $state('all');
	// Seed jobs from the per-tab cache so a revisit paints the last cards
	// immediately instead of dropping to a skeleton.
	let jobs = $state<TranscoderJobListResponse>(getJobsCache('all') ?? emptyJobs);
	let loadingJobs = $state(getJobsCache('all') == null);
	let jobsError = $state<Error | null>(null);

	function formatDuration(startISO: string | null, endISO?: string | null): string | null {
		if (!startISO) return null;
		const start = new Date(startISO).getTime();
		if (isNaN(start)) return null;
		const end = endISO ? new Date(endISO).getTime() : Date.now();
		if (isNaN(end)) return null;
		const diffSec = Math.max(0, Math.floor((end - start) / 1000));
		const h = Math.floor(diffSec / 3600);
		const m = Math.floor((diffSec % 3600) / 60);
		const s = diffSec % 60;
		if (h > 0) return `${h}h ${m}m ${s}s`;
		if (m > 0) return `${m}m ${s}s`;
		return `${s}s`;
	}

	function sourceBasename(path: string | null | undefined): string {
		if (!path) return '';
		const parts = path.replace(/\/+$/, '').split('/');
		return parts[parts.length - 1] ?? '';
	}

	async function loadJobs(showLoading = true) {
		if (showLoading) loadingJobs = true;
		jobsError = null;
		try {
			const statusParam = activeTab === 'all' ? undefined : activeTab;
			jobs = await fetchTranscoderJobs({ status: statusParam });
			setJobsCache(activeTab, jobs);
		} catch (e) {
			jobsError = e instanceof Error ? e : new Error('Failed to load jobs');
			jobs = emptyJobs;
		} finally {
			loadingJobs = false;
		}
	}

	function switchTab(tab: string) {
		activeTab = tab;
		// Show cached cards instantly for a previously-viewed tab; only the
		// first view of a tab shows the loading skeleton.
		loadJobs(getJobsCache(tab) == null);
	}

	async function handleRetry(id: number) {
		await retryTranscoderJob(id);
		loadJobs();
	}

	let actionFeedback = $state<{ type: 'success' | 'error'; message: string } | null>(null);

	async function handleRetranscode(id: number) {
		actionFeedback = null;
		try {
			await retranscodeTranscoderJob(id);
			actionFeedback = { type: 'success', message: 'Job re-queued for transcoding' };
		} catch (e) {
			actionFeedback = { type: 'error', message: e instanceof Error ? e.message : 'Re-transcode failed' };
		}
		loadJobs();
	}

	async function handleDelete(id: number) {
		if (confirm('Delete this transcode job?')) {
			await deleteTranscoderJob(id);
			loadJobs();
		}
	}

	let jobsTimer: ReturnType<typeof setInterval> | null = null;

	function startJobsPolling() {
		stopJobsPolling();
		jobsTimer = setInterval(() => loadJobs(false), 5000);
	}

	function stopJobsPolling() {
		if (jobsTimer) { clearInterval(jobsTimer); jobsTimer = null; }
	}

	// Auto-refresh jobs when any are processing or pending
	$effect(() => {
		const s = $stats.stats;
		if (s && ((s.processing ?? 0) > 0 || (s.pending ?? 0) > 0)) {
			startJobsPolling();
		} else {
			stopJobsPolling();
		}
	});

	onMount(() => {
		stats.start();
		workers.start();
		// Skeleton only when we have nothing cached for the current tab.
		loadJobs(getJobsCache(activeTab) == null);
		return () => { stats.stop(); workers.stop(); stopJobsPolling(); };
	});

	const tabs = ['all', 'pending', 'processing', 'completed', 'failed'];

	function vendorPillClasses(vendor: string): string {
		switch (vendor.toLowerCase()) {
			case 'nvidia': return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
			case 'amd': return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
			case 'intel': return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400';
			default: return 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400';
		}
	}
</script>

<svelte:head>
	<title>ARM - Transcoder</title>
</svelte:head>

<div class="space-y-6">
	<h1 class="text-2xl font-bold text-gray-900 dark:text-white">Transcoder</h1>

	<!-- API error -->
	{#if $statsError}
		<div in:fade={fadeIn} out:fade={fadeOut} class="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
			Failed to reach transcoder: {$statsError}
		</div>
	{/if}

	<!-- Stats / worker pool. On the very first load (nothing cached yet) show a
	     skeleton sized to match the real cards so it fills in place without a
	     layout shift; only show the "offline" banner once a poll has actually
	     confirmed the service is down, never while still loading. -->
	{#if !$statsInitialized && !$statsError}
		<div class="space-y-4">
			<div class="rounded-lg border border-primary/20 bg-surface p-4 shadow-xs dark:border-primary/20 dark:bg-surface-dark">
				<div class="h-5 w-56 animate-pulse rounded bg-gray-200 dark:bg-gray-700"></div>
			</div>
			<div class="grid grid-cols-2 gap-4 lg:grid-cols-5">
				{#each Array(5) as _unused}
					<div class="rounded-lg border border-primary/20 bg-surface p-4 shadow-xs dark:border-primary/20 dark:bg-surface-dark">
						<div class="h-4 w-16 animate-pulse rounded bg-gray-200 dark:bg-gray-700"></div>
						<div class="mt-2 h-8 w-12 animate-pulse rounded bg-gray-200 dark:bg-gray-700"></div>
					</div>
				{/each}
			</div>
		</div>
	{:else if !$stats.online}
		<!-- Offline banner -->
		<div in:fade={fadeIn} out:fade={fadeOut} class="flex items-center gap-3 rounded-lg border border-primary/25 bg-page p-4 dark:border-primary/25 dark:bg-page-dark">
			<div class="h-3 w-3 shrink-0 rounded-full bg-gray-400"></div>
			<div>
				<p class="font-medium text-gray-700 dark:text-gray-300">Transcoder Offline</p>
				<p class="text-sm text-gray-500 dark:text-gray-400">The transcoder service is not responding. Transcoding features are unavailable.</p>
			</div>
		</div>
	{:else if $stats.online && $stats.stats}
		<!-- Worker pool + Stats cards -->
		{@const s = $stats.stats}
		{@const w = $workers}
		<div in:fade={fadeIn} out:fade={fadeOut} class="space-y-4">
		<!-- Worker pool status -->
		<div class="rounded-lg border border-primary/20 bg-surface p-4 shadow-xs dark:border-primary/20 dark:bg-surface-dark">
			<div class="mb-3 flex items-center justify-between">
				<div class="flex items-center gap-2">
					<div class="h-2.5 w-2.5 rounded-full {s.worker_running ? 'bg-green-500' : 'bg-yellow-500'}"></div>
					<span class="text-sm font-semibold text-gray-700 dark:text-gray-300">
						Workers {w.active_count}/{w.max_concurrent} active
					</span>
				</div>
				<span class="text-xs text-gray-400 dark:text-gray-500">Queue: {s.pending} pending</span>
			</div>
			{#if (w.workers ?? []).length > 0}
				<div class="grid gap-2 {(w.max_concurrent ?? 0) > 1 ? 'sm:grid-cols-2 lg:grid-cols-3' : ''}">
					{#each (w.workers ?? []) as worker}
						<div class="flex items-center gap-3 rounded-md border px-3 py-2
							{worker.status === 'processing'
								? 'border-indigo-200 bg-indigo-50/50 dark:border-indigo-800 dark:bg-indigo-900/20'
								: 'border-gray-200 bg-gray-50/50 dark:border-gray-700 dark:bg-gray-800/30'}">
							<div class="h-2 w-2 rounded-full {worker.status === 'processing' ? 'bg-indigo-500 animate-pulse' : 'bg-gray-400'}"></div>
							<div class="min-w-0 flex-1">
								<p class="text-sm font-medium text-gray-700 dark:text-gray-300">
									Worker {worker.worker_id}
									{#if worker.status === 'processing' && worker.current_job}
										<span class="font-normal text-gray-500 dark:text-gray-400"> &mdash; {worker.current_job}</span>
									{/if}
								</p>
								{#if worker.status === 'processing' && worker.started_at}
									{@const dur = formatDuration(worker.started_at)}
									{#if dur}
										<p class="text-xs text-indigo-600 dark:text-indigo-400">Running for {dur}</p>
									{/if}
								{:else}
									<p class="text-xs text-gray-400 dark:text-gray-500">Idle</p>
								{/if}
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</div>
		<div class="grid grid-cols-2 gap-4 lg:grid-cols-5">
			<div class="rounded-lg border border-primary/20 bg-surface p-4 shadow-xs dark:border-primary/20 dark:bg-surface-dark">
				<p class="text-sm text-gray-500 dark:text-gray-400">Pending</p>
				<p class="mt-1 text-3xl font-bold text-primary-text dark:text-primary-text-dark">{s.pending}</p>
			</div>
			<div class="rounded-lg border border-primary/20 bg-surface p-4 shadow-xs dark:border-primary/20 dark:bg-surface-dark">
				<p class="text-sm text-gray-500 dark:text-gray-400">Processing</p>
				<p class="mt-1 text-3xl font-bold text-indigo-600 dark:text-indigo-400">{s.processing}</p>
			</div>
			<div class="rounded-lg border border-primary/20 bg-surface p-4 shadow-xs dark:border-primary/20 dark:bg-surface-dark">
				<p class="text-sm text-gray-500 dark:text-gray-400">Completed</p>
				<p class="mt-1 text-3xl font-bold text-green-600 dark:text-green-400">{s.completed}</p>
			</div>
			<div class="rounded-lg border border-primary/20 bg-surface p-4 shadow-xs dark:border-primary/20 dark:bg-surface-dark">
				<p class="text-sm text-gray-500 dark:text-gray-400">Failed</p>
				<p class="mt-1 text-3xl font-bold text-red-600 dark:text-red-400">{s.failed}</p>
			</div>
			<div class="rounded-lg border border-primary/20 bg-surface p-4 shadow-xs dark:border-primary/20 dark:bg-surface-dark">
				<p class="text-sm text-gray-500 dark:text-gray-400">Cancelled</p>
				<p class="mt-1 text-3xl font-bold text-gray-500 dark:text-gray-400">{s.cancelled}</p>
			</div>
		</div>
		</div>
	{/if}

	<!-- GPU stats -->
	{#if $dashboard.transcoder_online && $dashboard.transcoder_system_stats?.gpu}
		{@const gpu = $dashboard.transcoder_system_stats.gpu}
		<div in:fade={fadeIn} out:fade={fadeOut} class="rounded-lg border border-primary/20 bg-surface p-4 shadow-xs dark:border-primary/20 dark:bg-surface-dark">
			<div class="mb-3 flex items-center gap-2">
				<p class="text-sm font-semibold text-gray-700 dark:text-gray-300">GPU</p>
				<span class="rounded-full px-2.5 py-0.5 text-[10px] font-semibold capitalize {vendorPillClasses(gpu.vendor)}">{gpu.vendor}</span>
			</div>
			<div class="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
				{#if gpu.utilization_percent != null}
					<div>
						<p class="text-xs text-gray-500 dark:text-gray-400">Load</p>
						<p class="mt-1 text-2xl font-bold text-amber-600 dark:text-amber-400">{gpu.utilization_percent.toFixed(0)}%</p>
					</div>
				{/if}
				{#if gpu.encoder_percent != null}
					<div>
						<p class="text-xs text-gray-500 dark:text-gray-400">Encoder</p>
						<p class="mt-1 text-2xl font-bold text-amber-600 dark:text-amber-400">{gpu.encoder_percent.toFixed(0)}%</p>
					</div>
				{/if}
				{#if gpu.memory_used_mb != null && gpu.memory_total_mb != null}
					<div>
						<p class="text-xs text-gray-500 dark:text-gray-400">VRAM</p>
						<p class="mt-1 text-2xl font-bold text-amber-600 dark:text-amber-400">{(gpu.memory_used_mb / 1024).toFixed(1)}<span class="text-base font-normal text-gray-400"> / {(gpu.memory_total_mb / 1024).toFixed(1)} GB</span></p>
					</div>
				{/if}
				{#if gpu.temperature_c != null}
					<div>
						<p class="text-xs text-gray-500 dark:text-gray-400">Temperature</p>
						<p class="mt-1 text-2xl font-bold text-orange-500">{gpu.temperature_c.toFixed(0)}&deg;C</p>
					</div>
				{/if}
				{#if gpu.power_draw_w != null}
					<div>
						<p class="text-xs text-gray-500 dark:text-gray-400">Power</p>
						<p class="mt-1 text-2xl font-bold text-amber-600 dark:text-amber-400">{gpu.power_draw_w.toFixed(0)}<span class="text-base font-normal text-gray-400">{#if gpu.power_limit_w != null} / {gpu.power_limit_w.toFixed(0)}{/if} W</span></p>
					</div>
				{/if}
				{#if gpu.clock_core_mhz != null}
					<div>
						<p class="text-xs text-gray-500 dark:text-gray-400">Core Clock</p>
						<p class="mt-1 text-2xl font-bold text-amber-600 dark:text-amber-400">{gpu.clock_core_mhz.toFixed(0)}<span class="text-base font-normal text-gray-400"> MHz</span></p>
					</div>
				{/if}
				{#if gpu.clock_memory_mhz != null}
					<div>
						<p class="text-xs text-gray-500 dark:text-gray-400">Memory Clock</p>
						<p class="mt-1 text-2xl font-bold text-amber-600 dark:text-amber-400">{gpu.clock_memory_mhz.toFixed(0)}<span class="text-base font-normal text-gray-400"> MHz</span></p>
					</div>
				{/if}
			</div>
		</div>
	{/if}

	<!-- Jobs section -->
	<section class="space-y-4">
		<h2 class="text-lg font-semibold text-gray-900 dark:text-white">Transcode Jobs</h2>

		{#if actionFeedback}
			<div class="rounded-lg border px-4 py-3 text-sm {actionFeedback.type === 'success' ? 'border-green-200 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-900/20 dark:text-green-400' : 'border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400'}">
				{actionFeedback.message}
				<button onclick={() => (actionFeedback = null)} class="ml-2 font-medium hover:opacity-75">Dismiss</button>
			</div>
		{/if}

		<!-- Tabs -->
		<div class="flex gap-1 border-b border-primary/20 dark:border-primary/20">
			{#each tabs as tab}
				<button
					onclick={() => switchTab(tab)}
					class="border-b-2 px-4 py-2 text-sm font-medium capitalize transition-colors
						{activeTab === tab
							? 'border-primary text-primary-text dark:border-primary-text-dark dark:text-primary-text-dark'
							: 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'}"
				>
					{tab}
				</button>
			{/each}
		</div>

		<!-- Jobs list -->
		<LoadState
			data={jobs}
			loading={loadingJobs}
			error={jobsError}
			isEmpty={(d) => (d.jobs ?? []).length === 0}
			transitionKey="transcoder-jobs"
		>
			{#snippet loadingSlot()}
				<div class="space-y-3">
					<SkeletonCard lines={4} />
					<SkeletonCard lines={4} />
					<SkeletonCard lines={4} />
				</div>
			{/snippet}
			{#snippet empty()}
				<p class="py-8 text-center text-gray-400">No transcode jobs found.</p>
			{/snippet}
			{#snippet ready(jobsData)}
				{@const jobList = jobsData.jobs ?? []}
			<div class="space-y-3">
				{#each jobList as job (job.id)}
					{@const typeConfig = getVideoTypeConfig(job.video_type ?? null, job.disctype ?? null)}
					<div in:fade={fadeIn} out:fade={fadeOut} class="rounded-lg border border-primary/20 border-l-4 {typeConfig.accentBorder} bg-surface p-4 shadow-xs dark:border-primary/20 dark:bg-surface-dark">
						<div class="flex gap-4">
							<!-- Poster -->
							{#if job.poster_url}
								<img
									src={posterSrc(job.poster_url)}
									alt={job.title ?? 'Poster'}
									class="h-24 w-16 shrink-0 rounded-sm object-cover"
									onerror={posterFallback}
								/>
							{:else}
								<div class="flex h-24 w-16 shrink-0 items-center justify-center rounded-sm {typeConfig.placeholderClasses}">
									<svg class="h-10 w-10" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
										<circle cx="12" cy="12" r="10" />
										<circle cx="12" cy="12" r="3" />
										<circle cx="12" cy="12" r="6.5" stroke-width="0.75" opacity="0.4" />
									</svg>
								</div>
							{/if}

							<div class="min-w-0 flex-1">
								<!-- Row 1: Title + Status + Actions -->
								<div class="flex items-start justify-between gap-2">
									<div class="flex min-w-0 items-center gap-3">
										<h3 class="truncate font-semibold text-gray-900 dark:text-white" title={job.title}>
											{job.title || 'Untitled'}
										</h3>
										<StatusBadge status={job.status} />
									</div>
									<div class="flex shrink-0 gap-2">
										{#if job.status === 'completed' || job.status === 'failed'}
										{@const sourceDeleted = job.status === 'completed' && (job.config_overrides?.delete_source !== false)}
											<button
												onclick={() => handleRetranscode(job.id)}
												disabled={sourceDeleted}
												title={sourceDeleted ? 'Source files were deleted after transcoding' : 'Re-queue this job for transcoding'}
												class="rounded-sm px-2.5 py-1 text-xs font-medium {sourceDeleted ? 'bg-gray-400 text-gray-200 cursor-not-allowed dark:bg-gray-600' : 'bg-indigo-600 text-white hover:bg-indigo-700'}"
											>Re-transcode</button>
										{/if}
										{#if job.status === 'failed'}
											<button
												onclick={() => handleRetry(job.id)}
												class="rounded-sm bg-primary px-2.5 py-1 text-xs font-medium text-on-primary hover:bg-primary-hover"
											>Retry</button>
										{/if}
										<button
											onclick={() => handleDelete(job.id)}
											class="rounded-sm bg-red-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-red-700"
										>Delete</button>
									</div>
								</div>

								<!-- Row 2: Year, ARM link, source basename -->
								<div class="mt-0.5 flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
									{#if job.year}
										<span>{job.year}</span>
									{/if}
									<a
										href="/jobs/{job.id}"
										class="inline-flex items-center rounded-sm bg-primary/10 px-1.5 py-0.5 text-xs font-medium text-primary-text hover:bg-primary/20 dark:bg-primary/15 dark:text-primary-text-dark dark:hover:bg-primary/25"
									>Job #{job.id}</a>
									{#if job.source_path}
										<span class="truncate font-mono text-xs text-gray-400 dark:text-gray-500" title={job.source_path}>{sourceBasename(job.source_path)}</span>
									{/if}
								</div>

								<!-- Row 3: Type badge, disc type, tracks -->
								<div class="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 text-xs text-gray-500 dark:text-gray-400">
									<span class="rounded-sm px-1.5 py-0.5 font-medium {typeConfig.badgeClasses}">{typeConfig.label}</span>
									{#if job.disctype}
										<span class="inline-flex items-center gap-1 rounded-sm bg-primary/10 px-1.5 py-0.5 dark:bg-primary/15">
											<DiscTypeIcon disctype={job.disctype} size="h-3.5 w-3.5" />
											{discTypeLabel(job.disctype)}
										</span>
									{/if}
									{#if job.total_tracks != null && job.total_tracks > 0}
										<span>{job.total_tracks} track{job.total_tracks === 1 ? '' : 's'}</span>
									{/if}
								</div>

								<!-- Error message for failed jobs -->
								{#if job.status === 'failed' && job.error}
									<p class="mt-2 rounded-sm bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400">
										{job.error}
									</p>
								{/if}

								<!-- Progress bar for pending/processing -->
								{#if (job.status === 'pending' || job.status === 'processing') && typeof job.progress === 'number'}
									<div class="mt-3">
										<ProgressBar value={job.progress} color="bg-indigo-500" />
									</div>
								{/if}

								<!-- Timestamps + duration -->
								<div class="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500 dark:text-gray-400">
									{#if job.created_at}
										<span>Queued <TimeAgo date={job.created_at} /></span>
									{/if}
									{#if job.started_at}
										<span>Started <TimeAgo date={job.started_at} /></span>
									{/if}
									{#if job.status === 'completed' && job.started_at}
										{@const dur = formatDuration(job.started_at, job.completed_at)}
										{#if dur}
											<span class="text-green-600 dark:text-green-400">Took {dur}</span>
										{/if}
									{:else if job.status === 'processing' && job.started_at}
										{@const dur = formatDuration(job.started_at)}
										{#if dur}
											<span class="text-indigo-600 dark:text-indigo-400">Running for {dur}</span>
										{/if}
									{/if}
								</div>

								<!-- Per-job log preview -->
								{#if job.logfile}
									<InlineLogFeed
										logfile={job.logfile}
										maxEntries={8}
										fetchFn={fetchStructuredTranscoderLogContent}
										logLinkBase="/logs/transcoder"
										autoRefresh={job.status === 'processing'}
										containerClass="mt-3"
									/>
								{/if}

								<!-- Output path for completed jobs -->
								{#if job.status === 'completed' && job.output_path}
									<p class="mt-2 flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
										<span class="text-gray-400 dark:text-gray-500">&rarr;</span>
										<span class="truncate font-mono" title={job.output_path}>{sourceBasename(job.output_path)}</span>
									</p>
								{/if}
							</div>
						</div>
					</div>
				{/each}
			</div>
			{/snippet}
		</LoadState>
	</section>
</div>
