<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { fetchJob, fetchJobProgress, retranscodeJob, skipAndFinalize, forceComplete, fetchMusicDetail, toggleMultiTitle, updateTrack, fetchNamingPreview } from '$lib/api/jobs';
	import type { NamingPreviewTrack, RipProgress } from '$lib/api/jobs';
	import ProgressBar from '$lib/components/ProgressBar.svelte';
	import { posterSrc, posterFallback } from '$lib/utils/poster';
	import PosterImage from '$lib/components/PosterImage.svelte';
	import { fetchStructuredTranscoderLogContent, fetchTranscoderLogForArmJob } from '$lib/api/logs';
	import type { JobDetailSchema as JobDetail, MusicDetailSchema as MusicDetail } from '$lib/types/api.gen';
	import JobActions from '$lib/components/JobActions.svelte';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';
	import TitleSearch from '$lib/components/TitleSearch.svelte';
	import MusicSearch from '$lib/components/MusicSearch.svelte';
	import RipSettings from '$lib/components/RipSettings.svelte';
	import TranscodeOverrides from '$lib/components/TranscodeOverrides.svelte';
	import CrcLookup from '$lib/components/CrcLookup.svelte';
	import InlineLogFeed from '$lib/components/InlineLogFeed.svelte';
	import TrackTitleSearch from '$lib/components/TrackTitleSearch.svelte';
	import JobLifecycle from '$lib/components/JobLifecycle.svelte';
	import EpisodeMatch from '$lib/components/EpisodeMatch.svelte';
	import { formatDateTime, timeAgo, statusLabel } from '$lib/utils/format';
	import { discTypeLabel, isJobActive } from '$lib/utils/job-type';
	import { buildMetadataFields } from '$lib/utils/job-fields';
	import { transcoderEnabled } from '$lib/stores/config';
	import { get } from 'svelte/store';
	import LoadState from '$lib/components/LoadState.svelte';
	import SkeletonCard from '$lib/components/SkeletonCard.svelte';
	import { Disc } from 'lucide-svelte';

	let job = $state<JobDetail | null>(null);
	let jobLoading = $state(true);
	let jobError = $state<Error | null>(null);
	let error = $state<string | null>(null);
	let activePanel = $state<string | null>(null);
	let showDebug = $state(false);
	let retranscoding = $state(false);
	let retranscodeFeedback = $state<{ type: 'success' | 'error'; message: string } | null>(null);
	let transcoderLogfile = $state<string | null>(null);
	let transcoderProgress = $state<number | null>(null);
	let transcoderFps = $state<number | null>(null);
	let transcoderJobStatus = $state<string | null>(null);
	let transcoderPhase = $state<string | null>(null);
	let ripProgress = $state<RipProgress | null>(null);

	let isFolderImport = $derived(job?.source_type === 'folder');

	// MusicBrainz track listing (fetched when DB tracks are empty for music discs)
	let musicDetail = $state<MusicDetail | null>(null);
	let musicDetailLoading = $state(false);
	let togglingMultiTitle = $state(false);
	let editingTrackId = $state<number | null>(null);
	let savingTrackField = $state<string | null>(null);
	let togglingAllEnabled = $state(false);
	let editingFilenameTrackId = $state<number | null>(null);
	let editingFilenameValue = $state('');
	let namingPreviews = $state<Record<string, NamingPreviewTrack>>({});

	let minlength = $derived(Number(job?.config?.MINLENGTH) || 120);
	let maxlength = $derived(Number(job?.config?.MAXLENGTH) || 99999);

	function isFiltered(track: { process?: boolean }): boolean {
		return track.process === false;
	}

	function skipTooltip(track: { skip_reason?: string | null }): string {
		switch (track.skip_reason) {
			case 'too_short':       return `Skipped: shorter than minimum length (${minlength}s)`;
			case 'too_long':        return `Skipped: longer than maximum length (${maxlength}s)`;
			case 'makemkv_skipped': return `Skipped by MakeMKV (likely below ${minlength}s)`;
			case 'user_disabled':   return 'Skipped: deselected';
			case 'below_main_feature': return 'Skipped: below the main feature';
			default:                return 'Skipped';
		}
	}

	let rippableTracks = $derived(
		job?.tracks?.filter((t) => !isFiltered(t)) ?? []
	);
	let allEnabled = $derived(
		!!rippableTracks.length && rippableTracks.every((t) => t.enabled)
	);

	async function handleToggleAllEnabled() {
		if (!rippableTracks.length) return;
		togglingAllEnabled = true;
		const newVal = !allEnabled;
		try {
			await Promise.all(
				rippableTracks.map((t) => updateTrack(job!.job_id, t.track_id, { enabled: newVal }))
			);
			await loadJob();
		} catch {
			// next refresh will reconcile
		} finally {
			togglingAllEnabled = false;
		}
	}

	async function handleTrackFieldUpdate(trackId: number, field: string, value: boolean | string) {
		if (!job) return;
		savingTrackField = `${trackId}-${field}`;
		try {
			await updateTrack(job!.job_id, trackId, { [field]: value });
			await loadJob();
		} catch {
			// next refresh will reconcile
		} finally {
			savingTrackField = null;
		}
	}

	async function handleRetranscode() {
		if (!job) return;
		retranscoding = true;
		retranscodeFeedback = null;
		try {
			const result = await retranscodeJob(job.job_id);
			retranscodeFeedback = { type: 'success', message: result.message || 'Queued for transcoding' };
		} catch (e) {
			retranscodeFeedback = { type: 'error', message: e instanceof Error ? e.message : 'Failed to queue' };
		} finally {
			retranscoding = false;
		}
	}

	let skippingTranscode = $state(false);
	let skipTranscodeFeedback = $state<{ type: 'success' | 'error'; message: string } | null>(null);
	let showSkipConfirm = $state(false);
	let forcingComplete = $state(false);
	let forceCompleteFeedback = $state<{ type: 'success' | 'error'; message: string } | null>(null);

	async function confirmSkipAndFinalize() {
		showSkipConfirm = false;
		await handleSkipAndFinalize();
	}

	async function handleSkipAndFinalize() {
		if (!job) return;
		skippingTranscode = true;
		skipTranscodeFeedback = null;
		try {
			const result = await skipAndFinalize(job.job_id);
			if (result.success) {
				skipTranscodeFeedback = { type: 'success', message: result.message || 'Finalized without transcoding' };
				await loadJob();
			} else {
				skipTranscodeFeedback = { type: 'error', message: result.error || 'Failed to skip transcode' };
			}
		} catch (e) {
			skipTranscodeFeedback = { type: 'error', message: e instanceof Error ? e.message : 'Failed to skip transcode' };
		} finally {
			skippingTranscode = false;
		}
	}

	async function handleForceComplete() {
		if (!job) return;
		forcingComplete = true;
		forceCompleteFeedback = null;
		try {
			const result = await forceComplete(job.job_id);
			if (result.success) {
				forceCompleteFeedback = { type: 'success', message: result.message || 'Marked as complete' };
				await loadJob();
			} else {
				forceCompleteFeedback = { type: 'error', message: result.error || 'Failed to force complete' };
			}
		} catch (e) {
			forceCompleteFeedback = { type: 'error', message: e instanceof Error ? e.message : 'Failed to force complete' };
		} finally {
			forcingComplete = false;
		}
	}

	async function handleToggleMultiTitle() {
		if (!job) return;
		togglingMultiTitle = true;
		try {
			await toggleMultiTitle(job.job_id, !job.multi_title);
			await loadJob();
		} catch {
			// next refresh will reconcile
		} finally {
			togglingMultiTitle = false;
		}
	}

	function handleTrackTitleApply() {
		editingTrackId = null;
		loadJob();
	}

	let isVideoDisc = $derived(
		job?.disctype === 'dvd' || job?.disctype === 'bluray' || job?.disctype === 'bluray4k'
	);

	let isMusicDisc = $derived(
		job?.disctype === 'music' || job?.video_type === 'music'
	);

	let hasCrcData = $derived(
		!isMusicDisc && (job?.disctype === 'dvd' || !!job?.crc_id)
	);

	let metadataFields = $derived(job ? buildMetadataFields(job) : []);

	const panelTabBase = 'flex-1 border-r border-primary/15 px-4 py-2.5 text-center text-sm font-medium transition-colors dark:border-primary/15';
	const panelTabActive = 'text-primary border-b-2 border-b-primary bg-primary/5 dark:bg-primary/10';
	const panelTabInactive = 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300';
	function panelTabClass(id: string, last = false): string {
		const base = last ? panelTabBase.replace(' border-r border-primary/15', '') : panelTabBase;
		return `${base} ${activePanel === id ? panelTabActive : panelTabInactive}`;
	}

	function formatTvEpisodeName(track: { episode_number?: string | null; episode_name?: string | null }): string {
		if (!job || !track.episode_number) return '--';
		const cfgStr = (job.config ?? {}) as unknown as Record<string, string | null | undefined>;
		const pattern = cfgStr.TV_TITLE_PATTERN ?? '{title} S{season}E{episode}';
		const season = String(job.season || job.season_auto || '0').padStart(2, '0');
		const episode = track.episode_number.padStart(2, '0');
		const title = job.title || job.label || '';
		const year = job.year || '';
		return pattern
			.replace(/\{title\}/gi, title)
			.replace(/\{year\}/gi, year)
			.replace(/\{season\}/gi, season)
			.replace(/\{episode\}/gi, episode)
			.replace(/\{episode_name\}/gi, track.episode_name || '')
			.replace(/\{label\}/gi, job.label || '');
	}

	let hasAutoManualDiff = $derived(
		job != null &&
			job.title_auto != null &&
			job.title != null &&
			job.title_auto !== job.title
	);

	function extractReleaseId(posterUrl: string | null | undefined): string | null {
		if (!posterUrl) return null;
		const match = posterUrl.match(/coverartarchive\.org\/release\/([a-f0-9-]+)\//);
		return match?.[1] ?? null;
	}

	async function loadMusicTracks() {
		if (!job || !isMusicDisc || job.tracks.length > 0) return;
		const releaseId = extractReleaseId(job.poster_url);
		if (!releaseId) return;
		musicDetailLoading = true;
		try {
			musicDetail = await fetchMusicDetail(releaseId);
		} catch {
			musicDetail = null;
		} finally {
			musicDetailLoading = false;
		}
	}

	async function loadJob() {
		const id = Number($page.params.id);
		// Only flip into the loading state on the FIRST load. The 5s poll
		// re-calls loadJob() and on a slow network that would unmount the
		// rendered detail in favour of a skeleton, then remount when the
		// fetch settles - the height change scrolls the page (and the user
		// loses their scroll position). On refreshes we already have a
		// previous `job` to render; just swap it in place when the new
		// payload arrives.
		const isInitialLoad = job == null;
		if (isInitialLoad) {
			jobLoading = true;
		}
		jobError = null;
		try {
			job = await fetchJob(id);
			// Fetch naming previews for rendered filenames
			fetchNamingPreview(id).then((preview) => {
				const map: Record<string, NamingPreviewTrack> = {};
				for (const t of preview.tracks || []) {
					map[t.track_number] = t;
				}
				namingPreviews = map;
			}).catch(() => {
				namingPreviews = {};
			});
			// Look up transcoder job info for this ARM job (logfile + progress)
			if (get(transcoderEnabled)) {
				fetchTranscoderLogForArmJob(id).then((info) => {
					if (info.found) {
						transcoderLogfile = info.logfile ?? null;
						transcoderProgress = info.progress ?? null;
						transcoderFps = info.current_fps ?? null;
						transcoderJobStatus = info.status ?? null;
						transcoderPhase = info.phase ?? null;
					} else {
						transcoderLogfile = null;
						transcoderProgress = null;
						transcoderFps = null;
						transcoderJobStatus = null;
						transcoderPhase = null;
					}
				}).catch(() => {
					transcoderLogfile = null;
					transcoderProgress = null;
					transcoderFps = null;
					transcoderJobStatus = null;
					transcoderPhase = null;
				});
			}
		} catch (e) {
			if (e instanceof Error && e.message.includes('404')) {
				goto('/');
				return;
			}
			error = e instanceof Error ? e.message : 'Failed to load job';
			jobError = e instanceof Error ? e : new Error('Failed to load job');
		} finally {
			jobLoading = false;
		}
	}

	function formatDurationMs(ms: number | null | undefined): string {
		if (!ms) return '--';
		const totalSec = Math.round(ms / 1000);
		const m = Math.floor(totalSec / 60);
		const s = totalSec % 60;
		return `${m}:${s.toString().padStart(2, '0')}`;
	}

	function handleTitleApply() {
		activePanel = null;
		loadJob();
	}

	function handleConfigSaved() {
		activePanel = null;
		loadJob();
	}

	async function refreshProgress() {
		if (!job) return;
		const s = job.status?.toLowerCase();
		// 'ripping' kept as legacy fallback for in-flight jobs mid-deploy (pre-v2.0.0).
		const isRipping = s === 'video_ripping' || s === 'audio_ripping' || s === 'ripping';
		if (isRipping) {
			try {
				ripProgress = await fetchJobProgress(job.job_id);
			} catch {
				ripProgress = null;
			}
		} else if (ripProgress) {
			// Clear stale rip progress once the phase changes so 100% doesn't linger
			ripProgress = null;
		}
		if ((s === 'waiting_transcode' || s === 'transcoding' || s === 'copying') && get(transcoderEnabled)) {
			try {
				const info = await fetchTranscoderLogForArmJob(job.job_id);
				if (info.found) {
					transcoderLogfile = info.logfile ?? null;
					transcoderProgress = info.progress ?? null;
					transcoderFps = info.current_fps ?? null;
					transcoderJobStatus = info.status ?? null;
					transcoderPhase = info.phase ?? null;
				} else {
					transcoderProgress = null;
					transcoderFps = null;
					transcoderJobStatus = null;
					transcoderPhase = null;
				}
			} catch {
				transcoderProgress = null;
				transcoderFps = null;
				transcoderPhase = null;
			}
		}
	}

	onMount(() => {
		let stopped = false;
		async function poll() {
			while (!stopped) {
				await new Promise((r) => setTimeout(r, 5000));
				if (job && isJobActive(job.status)) {
					await loadJob();
					await refreshProgress();
				} else {
					break;
				}
			}
		}
		loadJob().then(() => { loadMusicTracks(); refreshProgress(); return poll(); });
		return () => {
			stopped = true;
		};
	});
</script>

<svelte:head>
	<title>ARM - {job?.title || 'Job Detail'}</title>
</svelte:head>

<LoadState
	data={job}
	loading={jobLoading}
	error={jobError}
	transitionKey="job-detail-main"
>
	{#snippet loadingSlot()}
		<SkeletonCard lines={6} />
	{/snippet}
	{#snippet ready(j)}
	{@const job = j}
	<div class="space-y-6">
		<!-- Breadcrumb -->
		<nav class="text-sm">
			<a href="/" class="text-primary-text hover:underline dark:text-primary-text-dark">Dashboard</a>
			<span class="mx-1.5 text-gray-400 dark:text-gray-500">&rsaquo;</span>
			<span class="text-gray-500 dark:text-gray-400">{job.title || job.label || 'Untitled'}</span>
		</nav>

		<!-- Main header container -->
		<div class="rounded-lg border border-primary/20 bg-surface shadow-xs overflow-hidden dark:border-primary/20 dark:bg-surface-dark">

			<!-- Title bar -->
			<div class="flex flex-wrap items-center gap-2 border-b border-primary/15 px-5 py-3 dark:border-primary/15">
				<h1 class="text-xl font-bold text-gray-900 dark:text-white">
					{job.title || job.label || 'Untitled'}
				</h1>
				{#if job.year && job.year !== '0000'}
					<span class="text-base text-gray-400 dark:text-gray-500">({job.year})</span>
				{/if}
				<StatusBadge status={isFolderImport && (job.status === 'video_ripping' || job.status === 'ripping') ? 'importing' : job.status} />
				{#if job.source_type === 'folder'}
					<span class="inline-flex items-center gap-1 rounded-sm bg-violet-100 px-1.5 py-0.5 text-[10px] font-medium text-violet-700 dark:bg-violet-900/30 dark:text-violet-400">
						<svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
						</svg>
						Folder Import
					</span>
				{:else if job.source_type === 'iso'}
					<span class="inline-flex items-center gap-1 rounded-sm bg-violet-100 px-1.5 py-0.5 text-[10px] font-medium text-violet-700 dark:bg-violet-900/30 dark:text-violet-400">
						<Disc class="h-3 w-3" />
						ISO
					</span>
				{/if}
				{#if job.multi_title}
					<span class="rounded-full bg-purple-100 px-2.5 py-0.5 text-[10px] font-semibold uppercase text-purple-700 dark:bg-purple-900/30 dark:text-purple-400">Multi-Title</span>
				{/if}
				{#if job.imdb_id && !isMusicDisc}
					<a href="https://www.imdb.com/title/{job.imdb_id}" target="_blank" rel="noopener noreferrer" class="rounded-full bg-yellow-400 px-2.5 py-0.5 text-[10px] font-bold text-black">IMDb</a>
				{/if}

				<!-- Action buttons pushed right -->
				<div class="flex flex-wrap items-center gap-2 ml-auto">
					{#if $transcoderEnabled && isVideoDisc && (job.status === 'success' || job.status === 'fail')}
						<button
							onclick={handleRetranscode}
							disabled={retranscoding}
							class="rounded-full px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-50 bg-indigo-100 text-indigo-700 hover:bg-indigo-200 dark:bg-indigo-900/30 dark:text-indigo-400 dark:hover:bg-indigo-900/50"
						>
							{retranscoding ? 'Queuing...' : 'Re-transcode'}
						</button>
					{/if}
					{#if $transcoderEnabled && job.status === 'waiting_transcode'}
						<button
							onclick={() => (showSkipConfirm = true)}
							disabled={skippingTranscode}
							class="rounded-full px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-50 bg-amber-100 text-amber-700 hover:bg-amber-200 dark:bg-amber-900/30 dark:text-amber-400 dark:hover:bg-amber-900/50"
						>
							{skippingTranscode ? 'Finalizing...' : 'Skip Transcode & Finalize'}
						</button>
					{/if}
					{#if job.status === 'waiting_transcode' || job.status === 'transcoding'}
						<button
							onclick={handleForceComplete}
							disabled={forcingComplete}
							class="rounded-md border border-amber-600 px-3 py-1.5 text-sm font-medium text-amber-600 hover:bg-amber-50 disabled:opacity-50 dark:text-amber-400 dark:hover:bg-amber-900/20"
						>
							{forcingComplete ? 'Completing...' : 'Force Complete'}
						</button>
					{/if}
					<JobActions {job} onaction={loadJob} ondelete={() => goto('/')} />
					{#if retranscodeFeedback}
						<span class="text-xs {retranscodeFeedback.type === 'success' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}">
							{retranscodeFeedback.message}
						</span>
					{/if}
					{#if skipTranscodeFeedback}
						<span class="text-xs {skipTranscodeFeedback.type === 'success' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}">
							{skipTranscodeFeedback.message}
						</span>
					{/if}
					{#if forceCompleteFeedback}
						<span class="text-xs {forceCompleteFeedback.type === 'success' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}">
							{forceCompleteFeedback.message}
						</span>
					{/if}
				</div>
			</div>

			<!-- Poster + Metadata grid -->
			<div class="flex flex-col sm:flex-row items-start">
				<!-- Poster -->
				<div class="shrink-0 border-b sm:border-b-0 sm:border-r border-primary/15 p-4 dark:border-primary/15">
					<PosterImage
						url={job.poster_url}
						alt={job.title ?? 'Poster'}
						class="rounded-md object-cover shadow-sm {isMusicDisc ? 'h-[120px] w-[120px]' : 'w-[120px]'}"
						style={isMusicDisc ? '' : 'aspect-ratio: 2/3'}
					/>
				</div>

				<!-- Metadata grid -->
				<div class="metadata-grid w-full sm:w-auto flex-1 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4">
					{#each metadataFields as field, i}
						<div class="metadata-cell px-4 py-3 border-b border-r border-primary/15 dark:border-primary/15">
							{#if !field.empty}
								<div class="text-[11px] uppercase tracking-wider text-gray-500 dark:text-gray-400">{field.label}</div>
								{#if field.isSelect}
									<div class="mt-1">
										<select
											value={job.multi_title ? 'multi' : 'single'}
											onchange={(e) => { const v = e.currentTarget.value; if ((v === 'multi') !== !!job?.multi_title) handleToggleMultiTitle(); }}
											disabled={togglingMultiTitle}
											class="rounded-md border border-primary/25 bg-primary/5 px-3 py-2 text-sm text-gray-900 focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary dark:border-primary/30 dark:bg-primary/10 dark:text-white"
										>
											<option value="single">Single Title</option>
											<option value="multi">Multi-Title</option>
										</select>
									</div>
								{:else if field.link}
									<a href={field.link} target="_blank" rel="noopener noreferrer" class="mt-1 block text-sm font-medium text-primary hover:underline dark:text-primary {field.mono ? 'font-mono text-xs' : ''}">{field.value}</a>
								{:else}
									<div class="mt-1 text-sm font-medium text-gray-900 dark:text-white {field.mono ? 'font-mono text-xs truncate' : ''}" title={field.mono ? field.value : undefined}>{field.value}</div>
								{/if}
							{/if}
						</div>
					{/each}
				</div>
			</div>

			<!-- Panel toggle bar -->
			<div class="flex border-t border-primary/15 bg-surface/50 dark:border-primary/15 dark:bg-surface-dark/50">
				{#if isVideoDisc}
					<button onclick={() => (activePanel = activePanel === 'title' ? null : 'title')} class={panelTabClass('title')}>Identify</button>
				{/if}
				{#if isMusicDisc}
					<button onclick={() => (activePanel = activePanel === 'music' ? null : 'music')} class={panelTabClass('music')}>Search Music</button>
				{/if}
				{#if job.config}
					<button onclick={() => (activePanel = activePanel === 'rip' ? null : 'rip')} class={panelTabClass('rip')}>Rip Settings</button>
				{/if}
				{#if isVideoDisc && job.video_type === 'series' && job.imdb_id}
					<button onclick={() => (activePanel = activePanel === 'tvdb' ? null : 'tvdb')} class={panelTabClass('tvdb')}>Episodes</button>
				{/if}
				{#if $transcoderEnabled && isVideoDisc}
					<button onclick={() => (activePanel = activePanel === 'transcode' ? null : 'transcode')} class={panelTabClass('transcode')}>Transcode Settings</button>
				{/if}
				{#if hasCrcData}
					<button onclick={() => (activePanel = activePanel === 'crc' ? null : 'crc')} class={panelTabClass('crc', true)}>CRC Lookup</button>
				{/if}
			</div>

			<!-- Active panel content -->
			{#if activePanel === 'title'}
				<div class="border-t border-primary/15 p-5 dark:border-primary/15">
					<TitleSearch {job} onapply={handleTitleApply} />
				</div>
			{:else if activePanel === 'music'}
				<div class="border-t border-primary/15 p-5 dark:border-primary/15">
					<MusicSearch {job} onapply={handleTitleApply} />
				</div>
			{:else if activePanel === 'crc'}
				<div class="border-t border-primary/15 p-5 dark:border-primary/15">
					<CrcLookup {job} onapply={loadJob} />
				</div>
			{:else if activePanel === 'rip'}
				<div class="border-t border-primary/15 p-5 dark:border-primary/15">
					<RipSettings {job} config={job.config!} isMusic={isMusicDisc} multiTitle={!!job.multi_title} onsaved={handleConfigSaved} />
				</div>
			{:else if activePanel === 'tvdb'}
				<div class="border-t border-primary/15 p-5 dark:border-primary/15">
					<EpisodeMatch {job} onapply={loadJob} />
				</div>
			{:else if $transcoderEnabled && activePanel === 'transcode'}
				<div class="border-t border-primary/15 p-5 dark:border-primary/15">
					<TranscodeOverrides {job} onsaved={loadJob} />
				</div>
			{/if}
		</div>

		<!-- Lifecycle widget: visual stage progression below header, above status bars -->
		<div class="rounded-lg border border-primary/20 bg-surface px-4 py-3 shadow-xs dark:border-primary/20 dark:bg-surface-dark">
			<JobLifecycle status={job.status} sourceType={job.source_type} size="md" />
		</div>

		<!-- Progress widget: ripping, copying, waiting_transcode, transcoding -->
		<!-- 'ripping' kept as legacy fallback for in-flight jobs mid-deploy (pre-v2.0.0). -->
		{#if job.status === 'video_ripping' || job.status === 'audio_ripping' || job.status === 'ripping'}
			<div class="rounded-lg border border-primary/20 bg-surface p-4 shadow-xs dark:border-primary/20 dark:bg-surface-dark">
				<div class="mb-2 flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300">
					<span>Ripping</span>
					{#if ripProgress?.stage}
						<span class="text-xs text-gray-500 dark:text-gray-400">{ripProgress.stage}</span>
					{/if}
				</div>
				{#if ripProgress?.progress != null}
					<ProgressBar value={ripProgress.progress} color="bg-primary" />
				{:else}
					<div class="h-2.5 overflow-hidden rounded-full bg-primary/15">
						<div class="h-full w-1/3 animate-indeterminate rounded-full bg-primary/60"></div>
					</div>
				{/if}
			</div>
		{:else if job.status === 'copying'}
			<div class="rounded-lg border border-amber-200 bg-amber-50 p-4 shadow-xs dark:border-amber-800 dark:bg-amber-900/20">
				<div class="mb-2 flex items-center gap-2 text-sm font-medium text-amber-800 dark:text-amber-300">
					<span>Copying to shared storage</span>
					<span class="text-xs text-amber-700/80 dark:text-amber-400/80">ARM is moving raw files to the transcoder's working directory.</span>
				</div>
				<div class="h-2.5 overflow-hidden rounded-full bg-amber-200/60 dark:bg-amber-900/40">
					<div class="h-full w-1/3 animate-indeterminate rounded-full bg-amber-500/70"></div>
				</div>
			</div>
		{:else if job.status === 'waiting_transcode'}
			<div class="rounded-lg border border-primary/20 bg-surface p-4 shadow-xs dark:border-primary/20 dark:bg-surface-dark">
				<div class="mb-2 flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300">
					<span>Waiting to transcode</span>
					<span class="text-xs text-gray-500 dark:text-gray-400">Queued on the transcoder.</span>
				</div>
				<div class="h-2.5 overflow-hidden rounded-full bg-primary/15">
					<div class="h-full w-1/3 animate-indeterminate rounded-full bg-primary/60"></div>
				</div>
			</div>
		{:else if job.status === 'transcoding'}
			<div class="rounded-lg border border-primary/20 bg-surface p-4 shadow-xs dark:border-primary/20 dark:bg-surface-dark">
				<div class="mb-2 flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300">
					<span>
						{#if transcoderPhase === 'copying_source'}
							Copying source files
						{:else if transcoderPhase === 'finalizing'}
							Finalizing
						{:else}
							Transcoding
						{/if}
					</span>
					{#if transcoderPhase === 'copying_source'}
						<span class="text-xs text-gray-500 dark:text-gray-400">Moving source files to local scratch.</span>
					{:else if transcoderPhase === 'finalizing'}
						<span class="text-xs text-gray-500 dark:text-gray-400">Moving output to completed and running cleanup.</span>
					{:else if transcoderJobStatus}
						<span class="text-xs text-gray-500 dark:text-gray-400">({transcoderJobStatus})</span>
					{/if}
					{#if transcoderPhase === 'encoding' && typeof transcoderFps === 'number' && transcoderFps > 0}
						<span class="ml-auto font-mono text-xs text-gray-500 dark:text-gray-400" title="Encoder frames per second">{transcoderFps.toFixed(1)} fps</span>
					{/if}
				</div>
				{#if transcoderPhase === 'copying_source' || transcoderPhase === 'finalizing'}
					<div class="h-2.5 overflow-hidden rounded-full bg-primary/15">
						<div class="h-full w-1/3 animate-indeterminate rounded-full bg-primary/60"></div>
					</div>
				{:else if transcoderProgress != null}
					<ProgressBar value={transcoderProgress} color="bg-primary" />
				{:else}
					<div class="h-2.5 overflow-hidden rounded-full bg-primary/15">
						<div class="h-full w-1/3 animate-indeterminate rounded-full bg-primary/60"></div>
					</div>
				{/if}
			</div>
		{/if}

		<!-- Auto vs Manual title info (outside container) -->
		{#if hasAutoManualDiff}
			<div class="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2.5 text-sm dark:border-amber-800 dark:bg-amber-900/20">
				<svg class="h-4 w-4 shrink-0 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
				</svg>
				<span class="text-amber-800 dark:text-amber-300">
					Auto-detected: <span class="font-medium">{job.title_auto}{#if job.year_auto} ({job.year_auto}){/if}</span>
				</span>
			</div>
		{/if}

		{#if job.errors}
			<div class="rounded-lg border p-3 text-sm {job.status === 'success'
				? 'border-yellow-200 bg-yellow-50 text-yellow-700 dark:border-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400'
				: 'border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400'}">
				<strong>{job.status === 'success' ? 'Warnings:' : 'Errors:'}</strong> {job.errors}
			</div>
		{/if}

		{#if job.logfile}
			<InlineLogFeed logfile={job.logfile} maxEntries={15} title="ARM Ripper Log" />
		{/if}
		{#if $transcoderEnabled && transcoderLogfile && transcoderJobStatus && !isMusicDisc && job?.disctype !== 'data'}
			<InlineLogFeed
				logfile={transcoderLogfile}
				maxEntries={15}
				title="Transcoder Log"
				fetchFn={fetchStructuredTranscoderLogContent}
				logLinkBase="/logs/transcoder"
			/>
		{/if}

		<!-- Tracks -->
		{#if job.tracks.length > 0}
			<section>
				<div class="mb-3 flex items-center justify-between">
					<h2 class="text-lg font-semibold text-gray-900 dark:text-white">
						Tracks ({job.tracks.length})
						{#if job.disc_number && job.disc_total}
							<span class="text-sm font-normal text-gray-500 dark:text-gray-400">— Disc {job.disc_number} of {job.disc_total}</span>
						{/if}
					</h2>
				</div>
				<div class="overflow-x-auto rounded-lg border border-primary/20 dark:border-primary/20">
					<table class="responsive-table w-full text-left text-sm">
						<thead class="bg-page text-gray-600 dark:bg-primary/5 dark:text-gray-400">
							<tr>
								<th class="px-4 py-3 font-medium">#</th>
								<th class="px-4 py-3 font-medium">{isMusicDisc ? 'Name' : 'Filename'}</th>
								{#if !isMusicDisc}
									<th class="px-4 py-3 font-medium">Title</th>
								{/if}
								{#if !isMusicDisc && job.video_type === 'series'}
									<th class="px-4 py-3 font-medium">Episode</th>
								{/if}
								<th class="px-4 py-3 font-medium">{isMusicDisc ? 'Duration' : 'Length'}</th>
								{#if !isMusicDisc}
									<th class="px-4 py-3 font-medium">Aspect</th>
									<th class="px-4 py-3 font-medium">FPS</th>
									<th class="pl-1 pr-4 py-3 font-medium">
										<label class="flex items-center gap-1.5 cursor-pointer">
											<span>Rip</span>
											<input
												type="checkbox"
												checked={allEnabled}
												onchange={handleToggleAllEnabled}
												disabled={togglingAllEnabled}
												class="h-4 w-4 rounded-sm border-primary/25 text-primary focus:ring-primary dark:border-primary/30 dark:bg-primary/10"
											/>
										</label>
									</th>
								{/if}
								<th class="px-4 py-3 font-medium">Ripped</th>
								<th class="px-4 py-3 font-medium">Status</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-gray-200 dark:divide-gray-700">
							{#each job.tracks as track}
								{@const filtered = !isMusicDisc && isFiltered(track)}
								<tr class="{filtered ? 'opacity-40' : ''} hover:bg-page dark:hover:bg-gray-800/50">
									<td class="px-4 py-3" data-label="#">{track.track_number ?? ''}</td>
									{#if isMusicDisc}
										<td class="max-w-[300px] truncate px-4 py-3" data-label="Name">{track.title || track.filename || '--'}</td>
									{:else}
										<td class="max-w-[250px] px-4 py-3" data-label="Filename">
											{#if !track.enabled}
												<span class="text-xs text-gray-400"></span>
											{:else if editingFilenameTrackId === track.track_id}
												<div class="flex items-center gap-1">
													<input
														type="text"
														bind:value={editingFilenameValue}
														onkeydown={(e) => { if (e.key === 'Enter') { updateTrack(job!.job_id, track.track_id, { custom_filename: editingFilenameValue }); editingFilenameTrackId = null; loadJob(); } if (e.key === 'Escape') editingFilenameTrackId = null; }}
														class="w-full min-w-[120px] rounded-sm border border-amber-400 bg-transparent px-1 py-0.5 font-mono text-xs text-amber-600 focus:outline-hidden focus:ring-1 focus:ring-amber-400 dark:border-amber-600 dark:text-amber-400"
													/>
													<button
														onclick={async () => { await updateTrack(job!.job_id, track.track_id, { custom_filename: editingFilenameValue }); editingFilenameTrackId = null; loadJob(); }}
														class="rounded bg-green-600 px-1.5 py-0.5 text-[10px] text-white hover:bg-green-700"
													>Save</button>
													<button
														onclick={() => { editingFilenameTrackId = null; }}
														class="rounded border border-gray-400 px-1 py-0.5 text-[10px] text-gray-400 hover:bg-gray-800"
													>x</button>
												</div>
											{:else}
												{@const customFn = track.custom_filename}
												{@const renderedFn = namingPreviews[track.track_number ?? '']?.rendered_title}
												{@const defaultFn = renderedFn || track.filename || track.basename || '--'}
												<button
													onclick={() => { editingFilenameTrackId = track.track_id; editingFilenameValue = customFn || defaultFn; }}
													class="w-full text-left font-mono text-xs {customFn ? 'text-amber-500 dark:text-amber-400' : 'text-gray-700 dark:text-gray-300'} hover:underline truncate"
												>
													{customFn || defaultFn}
												</button>
												{#if customFn}
													<div class="flex items-center gap-1">
														<span class="text-[9px] text-gray-500">was: {defaultFn}</span>
														<button
															onclick={async () => { await updateTrack(job!.job_id, track.track_id, { custom_filename: '' }); loadJob(); }}
															class="text-[9px] text-red-400 hover:text-red-300"
														>clear</button>
													</div>
												{/if}
											{/if}
										</td>
									{/if}
									{#if !isMusicDisc}
										<td
											class="px-4 py-3 cursor-pointer hover:bg-primary/5 dark:hover:bg-primary/10"
											data-label="Title"
											onclick={() => { editingTrackId = editingTrackId === track.track_id ? null : track.track_id; }}
										>
											{#if track.title}
												<div class="flex items-center gap-1.5">
													{#if track.poster_url}
														<img src={posterSrc(track.poster_url)} alt="" class="h-8 w-5 rounded-sm object-cover" onerror={posterFallback} />
													{/if}
													<div>
														<span class="font-medium text-gray-900 dark:text-white">{track.title}</span>
														{#if track.year}
															<span class="text-gray-400"> ({track.year})</span>
														{/if}
													</div>
												</div>
											{:else}
												<span class="text-xs text-gray-400">{job.title || job.label || 'Untitled'}{#if job.year} ({job.year}){/if}</span>
											{/if}
										</td>
									{/if}
									{#if !isMusicDisc && job.video_type === 'series'}
									<td class="px-4 py-3" data-label="Episode">
										<div class="flex items-center gap-1.5">
											<input
												type="text"
												value={track.episode_number ?? ''}
												onchange={async (e) => {
													const val = e.currentTarget.value.trim();
													await updateTrack(job!.job_id, track.track_id, { episode_number: val });
													loadJob();
												}}
												placeholder="--"
												disabled={filtered || !track.enabled}
												class="w-12 rounded-sm border border-primary/25 bg-primary/5 px-1.5 py-0.5 text-center text-sm text-gray-900 focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary disabled:opacity-30 dark:border-primary/30 dark:bg-primary/10 dark:text-white"
											/>
											{#if track.episode_name}
												<span class="text-xs text-gray-500 dark:text-gray-400">{track.episode_name}</span>
											{/if}
										</div>
									</td>
								{/if}
								<td class="px-4 py-3" data-label={isMusicDisc ? 'Duration' : 'Length'}>{track.length != null ? `${Math.floor(track.length / 60)}:${String(track.length % 60).padStart(2, '0')}` : ''}</td>
									{#if !isMusicDisc}
										<td class="px-4 py-3" data-label="Aspect">{track.aspect_ratio ?? ''}</td>
										<td class="px-4 py-3" data-label="FPS">{track.fps ?? ''}</td>
										<td class="pl-1 pr-4 py-3" data-label="Rip">
											{#if filtered}
												<span class="ml-4 text-[10px] text-gray-400 dark:text-gray-500" title={skipTooltip(track)}>skip</span>
											{:else}
												<input
													type="checkbox"
													checked={track.enabled}
													onchange={() => handleTrackFieldUpdate(track.track_id, 'enabled', !track.enabled)}
													disabled={savingTrackField === `${track.track_id}-enabled`}
													class="ml-[26px] h-4 w-4 rounded-sm border-primary/25 text-primary focus:ring-primary disabled:opacity-50 dark:border-primary/30 dark:bg-primary/10"
												/>
											{/if}
										</td>
									{/if}
									<td class="px-4 py-3" data-label="Ripped">
										{#if track.enabled && !filtered}
											<span class="rounded-sm px-1.5 py-0.5 text-[10px] font-semibold {track.ripped
												? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
												: 'bg-gray-100 text-gray-400 dark:bg-gray-700/50 dark:text-gray-500'}"
											>
												{track.ripped ? 'Yes' : 'No'}
											</span>
										{/if}
									</td>
									<td class="px-4 py-3" data-label="Status"><StatusBadge status={!track.enabled || filtered ? 'skipped' : track.status} /></td>
									</tr>
								{#if editingTrackId === track.track_id}
									<tr>
										<td colspan="99" class="px-4 py-3" data-label="">
											<TrackTitleSearch jobId={job.job_id} {track} onapply={handleTrackTitleApply} onclose={() => { editingTrackId = null; }} />
										</td>
									</tr>
								{/if}
							{/each}
						</tbody>
					</table>
				</div>
			</section>
		{:else if isMusicDisc && musicDetailLoading}
			<section>
				<h2 class="mb-3 text-lg font-semibold text-gray-900 dark:text-white">Track Listing</h2>
				<p class="text-sm text-gray-400">Loading track listing from MusicBrainz...</p>
			</section>
		{:else if isMusicDisc && musicDetail && musicDetail.tracks.length > 0}
			<section>
				<h2 class="mb-3 text-lg font-semibold text-gray-900 dark:text-white">
					Track Listing
					<span class="text-sm font-normal text-gray-500 dark:text-gray-400">({musicDetail.tracks.length} tracks via MusicBrainz)</span>
				</h2>
				<div class="overflow-x-auto rounded-lg border border-primary/20 dark:border-primary/20">
					<table class="w-full text-left text-sm">
						<thead class="bg-page text-gray-600 dark:bg-primary/5 dark:text-gray-400">
							<tr>
								<th class="w-12 px-4 py-3 font-medium">#</th>
								<th class="px-4 py-3 font-medium">Title</th>
								<th class="w-20 px-4 py-3 font-medium text-right">Duration</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-gray-200 dark:divide-gray-700">
							{#each musicDetail.tracks as track}
								<tr class="hover:bg-page dark:hover:bg-gray-800/50">
									<td class="px-4 py-3 font-mono text-gray-500 dark:text-gray-400">{track.number}</td>
									<td class="px-4 py-3 text-gray-900 dark:text-white">{track.title}</td>
									<td class="px-4 py-3 text-right font-mono text-gray-500 dark:text-gray-400">{formatDurationMs(track.length_ms)}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			</section>
		{/if}

		<!-- Debug -->
		{#if job.config}
			<section>
				<button
					onclick={() => { showDebug = !showDebug; }}
					class="flex w-full items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white"
				>
					<svg class="h-4 w-4 transition-transform {showDebug ? 'rotate-90' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
					</svg>
					Debug
				</button>
				{#if showDebug}
					<div class="mt-3 overflow-x-auto rounded-lg border border-primary/20 dark:border-primary/20">
						<table class="w-full text-left text-sm">
							<tbody class="divide-y divide-gray-200 dark:divide-gray-700">
								{#each Object.entries(job.config) as [key, value]}
									<tr class="hover:bg-page dark:hover:bg-gray-800/50">
										<td class="px-4 py-2 font-mono text-xs font-medium text-gray-500 dark:text-gray-400">{key}</td>
										<td class="px-4 py-2 text-gray-900 dark:text-white">{value ?? ''}</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{/if}
			</section>
		{/if}
	</div>
	{/snippet}
</LoadState>

<ConfirmDialog
	open={showSkipConfirm}
	title="Skip transcoding and finalize?"
	message="The raw ripped files will be moved from the raw directory to the completed directory as-is. No transcoding will be applied. This cannot be undone."
	confirmLabel="Yes, Skip & Finalize"
	variant="danger"
	onconfirm={confirmSkipAndFinalize}
	oncancel={() => (showSkipConfirm = false)}
/>
