<script lang="ts">
	import { onMount } from 'svelte';
	import type { JobSchema as Job, JobDetailSchema as JobDetail } from '$lib/types/api.gen';
	import { cancelWaitingJob, startWaitingJob, pauseWaitingJob, fetchJob, updateJobTitle, updateJobConfig, toggleMultiTitle, updateTrack, fetchNamingPreview } from '$lib/api/jobs';
	import type { NamingPreviewTrack } from '$lib/api/jobs';
	import { getVideoTypeConfig, discTypeLabel } from '$lib/utils/job-type';
	import { posterSrc, posterFallback } from '$lib/utils/poster';
	import PosterImage from './PosterImage.svelte';
	import CountdownTimer from './CountdownTimer.svelte';
	import TitleSearch from './TitleSearch.svelte';
	import MusicSearch from './MusicSearch.svelte';
	import RipSettings from './RipSettings.svelte';
	import TranscodeOverrides from './TranscodeOverrides.svelte';
	import CrcLookup from './CrcLookup.svelte';
	import DiscTypeIcon from './DiscTypeIcon.svelte';
	import InlineLogFeed from './InlineLogFeed.svelte';
	import TrackTitleSearch from './TrackTitleSearch.svelte';
	import EpisodeMatch from './EpisodeMatch.svelte';
	import SkeletonCard from './SkeletonCard.svelte';

	interface Props {
		job?: Job;
		driveNames?: Record<string, string> | null;
		paused?: boolean;
		onrefresh?: () => void;
		ondismiss?: () => void;
	}

	let { job, driveNames, paused = false, onrefresh, ondismiss }: Props = $props();
	let effectivePaused = $derived(paused || !!job?.manual_pause);
	let driveName = $derived(job?.devpath ? (driveNames?.[job.devpath] ?? null) : null);

	let detail = $state<JobDetail | null>(null);
	let initialLoading = $state(true);
	let showInfo = $state(false);
	let showTitleSearch = $state(false);
	let showMusicSearch = $state(false);
	let showCrcLookup = $state(false);
	let showRipSettings = $state(false);
	let showTranscodeSettings = $state(false);
	let showTvdb = $state(false);
	let cancelling = $state(false);
	let starting = $state(false);
	let togglingMultiTitle = $state(false);
	let openSearchTrackIds = $state<Set<number>>(new Set());
	let savingTrackField = $state<string | null>(null);
	let togglingAllEnabled = $state(false);
	let namingPreviews = $state<Record<string, NamingPreviewTrack>>({});
	let editingFilenameTrackId = $state<number | null>(null);
	let editingFilenameValue = $state('');
	let errorMessage = $state<string | null>(null);
	let skipTranscode = $state(false);

	// Sync from job config when detail loads
	$effect(() => {
		if (detail?.config?.SKIP_TRANSCODE != null) {
			const val = String(detail.config.SKIP_TRANSCODE).toLowerCase();
			skipTranscode = val === 'true' || val === '1';
		}
	});

	async function handleSkipTranscodeToggle() {
		if (!job) return;
		skipTranscode = !skipTranscode;
		errorMessage = null;
		try {
			await updateJobConfig(job.job_id, {
				SKIP_TRANSCODE: skipTranscode,
			});
			loadDetail();
		} catch (e) {
			errorMessage = `Failed to update skip transcode: ${e instanceof Error ? e.message : 'Unknown error'}`;
			skipTranscode = !skipTranscode;
		}
	}

	// MakeMKV's minlength threshold - retained for tooltip text. The actual
	// filter decision is made by the backend (track.process / skip_reason).
	let minlength = $derived(Number(detail?.config?.MINLENGTH) || 120);
	let maxlength = $derived(Number(detail?.config?.MAXLENGTH) || 99999);

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

	// "All enabled" only considers tracks the backend will actually rip
	let rippableTracks = $derived(
		detail?.tracks?.filter((t) => !isFiltered(t)) ?? []
	);
	let allEnabled = $derived(
		!!rippableTracks.length && rippableTracks.every((t) => t.enabled)
	);

	async function handleToggleAllEnabled() {
		if (!job || !rippableTracks.length) return;
		togglingAllEnabled = true;
		errorMessage = null;
		const newVal = !allEnabled;
		try {
			await Promise.all(
				rippableTracks.map((t) => updateTrack(job.job_id, t.track_id, { enabled: newVal }))
			);
			loadDetail();
		} catch (e) {
			errorMessage = `Failed to update tracks: ${e instanceof Error ? e.message : 'Unknown error'}`;
		} finally {
			togglingAllEnabled = false;
		}
	}

	async function handleTrackFieldUpdate(trackId: number, field: string, value: boolean | string) {
		if (!job) return;
		savingTrackField = `${trackId}-${field}`;
		errorMessage = null;
		try {
			await updateTrack(job.job_id, trackId, { [field]: value });
			loadDetail();
		} catch (e) {
			errorMessage = `Failed to update track: ${e instanceof Error ? e.message : 'Unknown error'}`;
		} finally {
			savingTrackField = null;
		}
	}

	// Editable metadata in Disc Info panel
	let infoTitle = $state(job?.title || '');
	let infoYear = $state(job?.year || '');
	let infoType = $state(job?.video_type || '');
	let infoImdbId = $state(job?.imdb_id || '');
	let infoPosterUrl = $state(job?.poster_url || '');
	let infoPath = $state(job?.path || '');
	let infoDisctype = $state(job?.disctype || '');
	let infoLabel = $state(job?.label || '');
	let infoArtist = $state(job?.artist || '');
	let infoAlbum = $state(job?.album || '');
	let infoSeason = $state(job?.season || '');
	let infoEpisode = $state(job?.episode || '');
	let infoPlot = $state<string | null>(null);
	let infoSaving = $state(false);
	let infoFeedback = $state<{ type: 'success' | 'error'; message: string } | null>(null);

	// Track which fields the user has manually edited to avoid
	// overwriting their changes when the job prop updates from polling
	let touched = $state<Record<string, boolean>>({});

	let infoDirty = $derived(Object.values(touched).some(Boolean));

	// Keep editable fields in sync with the job prop as the backend
	// detects metadata (title, year, poster, etc.) during disc identification.
	// Only sync fields the user hasn't manually edited.
	$effect.pre(() => {
		if (!touched.title) infoTitle = job?.title || '';
		if (!touched.year) infoYear = job?.year || '';
		if (!touched.type) infoType = job?.video_type || '';
		if (!touched.imdbId) infoImdbId = job?.imdb_id || '';
		if (!touched.posterUrl) infoPosterUrl = job?.poster_url || '';
		if (!touched.path && job?.path) infoPath = job.path;
		if (!touched.disctype) infoDisctype = job?.disctype || '';
		if (!touched.label) infoLabel = job?.label || '';
		if (!touched.artist) infoArtist = job?.artist || '';
		if (!touched.album) infoAlbum = job?.album || '';
		if (!touched.season) infoSeason = job?.season || '';
		if (!touched.episode) infoEpisode = job?.episode || '';
	});

	async function saveInfo() {
		if (!job) return;
		infoSaving = true;
		infoFeedback = null;
		try {
			await updateJobTitle(job.job_id, {
				title: infoTitle.trim() || undefined,
				year: infoYear.trim() || undefined,
				video_type: infoType || undefined,
				imdb_id: infoImdbId.trim() || undefined,
				poster_url: infoPosterUrl.trim() || undefined,
				path: infoPath.trim() || undefined,
				disctype: infoDisctype || undefined,
				label: infoLabel.trim() || undefined,
				artist: infoArtist.trim() || undefined,
				album: infoAlbum.trim() || undefined,
				season: infoSeason.trim() || undefined,
				episode: infoEpisode.trim() || undefined,
			});
			infoFeedback = { type: 'success', message: 'Saved' };
			touched = {};
			onrefresh?.();
		} catch (e) {
			infoFeedback = { type: 'error', message: e instanceof Error ? e.message : 'Save failed' };
		} finally {
			infoSaving = false;
		}
	}

	function resetInfo() {
		infoTitle = job?.title || '';
		infoYear = job?.year || '';
		infoType = job?.video_type || '';
		infoImdbId = job?.imdb_id || '';
		infoPosterUrl = job?.poster_url || '';
		infoPath = job?.path || '';
		infoDisctype = job?.disctype || '';
		infoLabel = job?.label || '';
		infoArtist = job?.artist || '';
		infoAlbum = job?.album || '';
		infoSeason = job?.season || '';
		infoEpisode = job?.episode || '';
		touched = {};
		infoFeedback = null;
		loadNamingPreviews();
	}

	async function handleTypeToggle(newType: string) {
		if (!job) return;
		infoType = newType;
		touched.type = true;
		try {
			await updateJobTitle(job.job_id, { video_type: newType });
			onrefresh?.();
		} catch (e) {
			errorMessage = e instanceof Error ? e.message : 'Failed to update type';
		}
	}

	let waitTime = $derived(Number(detail?.config?.MANUAL_WAIT_TIME) || 60);
	let typeConfig = $derived(getVideoTypeConfig(job?.video_type ?? null, job?.disctype ?? null));
	let isVideo = $derived(
		job?.disctype === 'dvd' || job?.disctype === 'bluray' || job?.disctype === 'bluray4k' || job?.video_type === 'movie' || job?.video_type === 'series'
	);
	let isMusic = $derived(
		job?.disctype === 'music' || job?.video_type === 'music'
	);
	let hasCrcData = $derived(
		job?.disctype === 'dvd' || !!job?.crc_id
	);
	let discLabelDiffers = $derived(
		!!job?.label && !!job?.title && job.label.toLowerCase() !== job.title.toLowerCase()
	);

	let isMultiTitleMovie = $derived(
		job?.multi_title && (job?.video_type === 'movie' || infoType === 'movie')
	);

	let defaultApplied = false;
	$effect(() => {
		if (!defaultApplied && job?.multi_title &&
			(!job?.video_type || job.video_type === 'unknown') &&
			(job?.disctype === 'dvd' || job.disctype === 'bluray' || job.disctype === 'bluray4k')) {
			defaultApplied = true;
			infoType = 'movie';
			updateJobTitle(job.job_id, { video_type: 'movie' }).then(() => onrefresh?.());
		}
	});

	async function loadDetail() {
		if (!job) return;
		try {
			detail = await fetchJob(job.job_id);
			loadNamingPreviews();
			autoOpenUnmatchedTracks();
		} catch {
			detail = null;
		} finally {
			initialLoading = false;
		}
	}

	async function loadNamingPreviews() {
		if (!job) return;
		try {
			const result = await fetchNamingPreview(job.job_id);
			if (result.success) {
				const map: Record<string, NamingPreviewTrack> = {};
				for (const t of result.tracks) {
					map[t.track_number] = t;
				}
				namingPreviews = map;
				// Populate output path from rendered folder (unless user edited it)
				if (result.job_folder && !touched.path) {
					infoPath = result.job_folder;
				}
			}
		} catch {
			// Non-critical — show raw filename as fallback
		}
	}

	function handleTitleApply() {
		touched = {};
		onrefresh?.();
		loadDetail();
	}

	function handleConfigSaved() {
		onrefresh?.();
		loadDetail();
	}

	async function handleStart() {
		if (!job) return;
		errorMessage = null;
		// Prevent starting with zero rippable tracks enabled (video discs only)
		if (rippableTracks.length && rippableTracks.every((t) => !t.enabled)) {
			errorMessage = 'Cannot start rip - at least one track must be enabled.';
			return;
		}
		starting = true;
		try {
			await startWaitingJob(job.job_id);
		} catch (e) {
			errorMessage = `Failed to start job: ${e instanceof Error ? e.message : 'Unknown error'}`;
		} finally {
			starting = false;
			if (!errorMessage) {
				ondismiss?.();
				onrefresh?.();
			}
		}
	}

	async function handleCancel() {
		if (!job) return;
		cancelling = true;
		try {
			await cancelWaitingJob(job.job_id);
		} catch {
			// still dismiss — next refresh will reconcile
		} finally {
			cancelling = false;
			ondismiss?.();
			onrefresh?.();
		}
	}

	async function handleToggleMultiTitle() {
		if (!job) return;
		togglingMultiTitle = true;
		try {
			await toggleMultiTitle(job.job_id, !job.multi_title);
			onrefresh?.();
			loadDetail();
		} catch {
			// next refresh will reconcile
		} finally {
			togglingMultiTitle = false;
		}
	}

	function handleTrackTitleApply(trackId?: number) {
		if (trackId != null) {
			openSearchTrackIds = new Set([...openSearchTrackIds].filter(id => id !== trackId));
		} else {
			openSearchTrackIds = new Set();
		}
		onrefresh?.();
		loadDetail();
	}

	function toggleTrackSearch(trackId: number) {
		const next = new Set(openSearchTrackIds);
		if (next.has(trackId)) next.delete(trackId);
		else next.add(trackId);
		openSearchTrackIds = next;
	}

	function autoOpenUnmatchedTracks() {
		if (!job?.multi_title || !detail?.tracks?.length) return;
		const unmatched = detail.tracks
			.filter(t => t.enabled && !t.title)
			.map(t => t.track_id);
		if (unmatched.length > 0) {
			openSearchTrackIds = new Set(unmatched);
		}
	}

	function handleCrcApply() {
		touched = {};
		onrefresh?.();
		loadDetail();
	}

	function toggleSection(section: 'info' | 'title' | 'music' | 'crc' | 'settings' | 'transcode' | 'tvdb') {
		const closeAll = () => { showInfo = false; showTitleSearch = false; showMusicSearch = false; showCrcLookup = false; showRipSettings = false; showTranscodeSettings = false; showTvdb = false; };
		if (section === 'info') {
			showInfo = !showInfo;
			if (showInfo) { closeAll(); showInfo = true; }
		} else if (section === 'title') {
			showTitleSearch = !showTitleSearch;
			if (showTitleSearch) { closeAll(); showTitleSearch = true; }
		} else if (section === 'music') {
			showMusicSearch = !showMusicSearch;
			if (showMusicSearch) { closeAll(); showMusicSearch = true; }
		} else if (section === 'crc') {
			showCrcLookup = !showCrcLookup;
			if (showCrcLookup) { closeAll(); showCrcLookup = true; }
		} else if (section === 'transcode') {
			showTranscodeSettings = !showTranscodeSettings;
			if (showTranscodeSettings) { closeAll(); showTranscodeSettings = true; }
		} else if (section === 'tvdb') {
			showTvdb = !showTvdb;
			if (showTvdb) { closeAll(); showTvdb = true; }
		} else {
			showRipSettings = !showRipSettings;
			if (showRipSettings) { closeAll(); showRipSettings = true; }
		}
	}

	function formatLength(secs: number | null | undefined): string {
		if (!secs) return '--';
		const h = Math.floor(secs / 3600);
		const m = Math.floor((secs % 3600) / 60);
		const s = secs % 60;
		if (h > 0) return `${h}h ${m}m ${s}s`;
		return `${m}m ${s}s`;
	}

	onMount(() => {
		loadDetail();
	});

	const btnBase =
		'rounded-lg px-3 py-1.5 text-sm font-medium transition-colors';
</script>

{#if !job}
	<SkeletonCard lines={4} />
{:else}
<div class="overflow-hidden rounded-lg ring-2 ring-primary bg-surface shadow-md dark:bg-surface-dark">
	<!-- Status bar -->
	<div class="flex items-center justify-between bg-primary px-4 py-1.5">
		<div class="flex items-center gap-2">
			<div class="h-2 w-2 animate-pulse rounded-full bg-white/80"></div>
			<span class="text-sm font-semibold text-on-primary">Waiting for Review</span>
		</div>
		{#if job.source_type !== 'folder' && (job.wait_start_time || job.start_time)}
			<CountdownTimer
			startTime={job.wait_start_time ?? job.start_time ?? ''}
			waitSeconds={waitTime}
			paused={effectivePaused}
			inverted
			onpause={() => { pauseWaitingJob(job.job_id, true).then(() => onrefresh?.()); }}
			onresume={() => { pauseWaitingJob(job.job_id, false).then(() => onrefresh?.()); }}
		/>
		{/if}
	</div>

	<!-- Header -->
	<div class="flex gap-4 p-4">
		<!-- Poster -->
		<PosterImage url={job.poster_url} alt={job.title ?? 'Poster'} class="h-24 shrink-0 rounded-sm object-cover {isMusic ? 'w-24' : 'w-16'}" />

		<!-- Info -->
		<div class="min-w-0 flex-1">
			<div class="flex items-center gap-2">
				<h3 class="min-w-0 truncate text-lg font-semibold text-gray-900 dark:text-white">
					{job.title || job.label || 'Untitled'}
					{#if job.year}
						<span class="font-normal text-gray-500 dark:text-gray-400">({job.year})</span>
					{/if}
				</h3>
				{#if job.multi_title}
					<span class="shrink-0 rounded-sm bg-purple-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-purple-700 dark:bg-purple-900/30 dark:text-purple-400">Multi-Title</span>
					<div class="flex shrink-0 rounded-sm bg-primary/10 p-0.5 dark:bg-primary/10">
						<button
							onclick={() => handleTypeToggle('movie')}
							class="rounded-sm px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wider transition-colors
								{infoType === 'movie' || job.video_type === 'movie'
									? 'bg-primary/20 text-primary-text shadow-xs dark:bg-primary/25 dark:text-primary-text-dark'
									: 'text-primary-text/50 hover:text-primary-text dark:text-primary-text-dark/50 dark:hover:text-primary-text-dark'}"
						>Movie</button>
						<button
							onclick={() => handleTypeToggle('series')}
							class="rounded-sm px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wider transition-colors
								{infoType === 'series' || job.video_type === 'series'
									? 'bg-primary/20 text-primary-text shadow-xs dark:bg-primary/25 dark:text-primary-text-dark'
									: 'text-primary-text/50 hover:text-primary-text dark:text-primary-text-dark/50 dark:hover:text-primary-text-dark'}"
						>Series</button>
					</div>
				{/if}
				{#if job.imdb_id}
					<a
						href="https://www.imdb.com/title/{job.imdb_id}/"
						target="_blank"
						rel="noopener noreferrer"
						class="inline-flex items-center rounded-sm bg-yellow-400 px-1.5 py-0.5 text-xs font-bold text-black hover:bg-yellow-300"
					>IMDb</a>
				{/if}
			</div>
			{#if discLabelDiffers}
				<p class="mt-0.5 text-sm text-gray-500 dark:text-gray-400">
					Auto-detected: <span class="font-mono text-xs">{job.label}</span>
				</p>
			{/if}
			<div class="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-500 dark:text-gray-400">
				{#if job.devpath}
					<span class="rounded-sm bg-primary/10 px-1.5 py-0.5 dark:bg-primary/15">{driveName ?? job.devpath}</span>
				{/if}
				{#if job.disctype}
					<span class="inline-flex items-center gap-1 rounded-sm bg-primary/10 px-1.5 py-0.5 dark:bg-primary/15">
						<DiscTypeIcon disctype={job.disctype} size="h-3.5 w-3.5" />
						{discTypeLabel(job.disctype)}
					</span>
				{/if}
			</div>
		</div>
	</div>

	<!-- Error banner -->
	{#if errorMessage}
		<div class="flex items-center gap-2 border-t border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
			<span class="flex-1">{errorMessage}</span>
			<button onclick={() => (errorMessage = null)} class="shrink-0 text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300">&times;</button>
		</div>
	{/if}

	<!-- Action buttons -->
	<div class="flex items-center gap-1.5 border-t border-primary/20 bg-primary-light-bg/50 px-4 py-2 dark:border-primary/20 dark:bg-primary-light-bg-dark/10">
		<button
			onclick={() => toggleSection('info')}
			class="{btnBase} {showInfo
				? 'bg-primary text-on-primary'
				: 'bg-primary/5 text-gray-700 ring-1 ring-primary/25 hover:bg-primary/10 dark:bg-primary/10 dark:text-gray-200 dark:ring-primary/30 dark:hover:bg-primary/15'}"
		>
			Info
		</button>
		{#if isVideo && (!job.multi_title || job.video_type === 'series')}
			<button
				onclick={() => toggleSection('title')}
				class="{btnBase} {showTitleSearch
					? 'bg-primary text-on-primary'
					: 'bg-primary/5 text-gray-700 ring-1 ring-primary/25 hover:bg-primary/10 dark:bg-primary/10 dark:text-gray-200 dark:ring-primary/30 dark:hover:bg-primary/15'}"
			>
				Search
			</button>
		{/if}
		{#if isVideo && job.video_type === 'series' && job.imdb_id}
			<button
				onclick={() => toggleSection('tvdb')}
				class="{btnBase} {showTvdb
					? 'bg-primary text-on-primary'
					: 'bg-primary/5 text-gray-700 ring-1 ring-primary/25 hover:bg-primary/10 dark:bg-primary/10 dark:text-gray-200 dark:ring-primary/30 dark:hover:bg-primary/15'}"
			>
				Episodes
			</button>
		{/if}
		{#if isMusic}
			<button
				onclick={() => toggleSection('music')}
				class="{btnBase} {showMusicSearch
					? 'bg-primary text-on-primary'
					: 'bg-primary/5 text-gray-700 ring-1 ring-primary/25 hover:bg-primary/10 dark:bg-primary/10 dark:text-gray-200 dark:ring-primary/30 dark:hover:bg-primary/15'}"
			>
				Search
			</button>
		{/if}
		{#if hasCrcData}
			<button
				onclick={() => toggleSection('crc')}
				class="{btnBase} {showCrcLookup
					? 'bg-primary text-on-primary'
					: 'bg-primary/5 text-gray-700 ring-1 ring-primary/25 hover:bg-primary/10 dark:bg-primary/10 dark:text-gray-200 dark:ring-primary/30 dark:hover:bg-primary/15'}"
			>
				CRC
			</button>
		{/if}
		<button
			onclick={() => toggleSection('settings')}
			class="{btnBase} {showRipSettings
				? 'bg-primary text-on-primary'
				: 'bg-primary/5 text-gray-700 ring-1 ring-primary/25 hover:bg-primary/10 dark:bg-primary/10 dark:text-gray-200 dark:ring-primary/30 dark:hover:bg-primary/15'}"
		>
			Settings
		</button>
		{#if isVideo}
			<button
				onclick={() => toggleSection('transcode')}
				class="{btnBase} {showTranscodeSettings
					? 'bg-primary text-on-primary'
					: 'bg-primary/5 text-gray-700 ring-1 ring-primary/25 hover:bg-primary/10 dark:bg-primary/10 dark:text-gray-200 dark:ring-primary/30 dark:hover:bg-primary/15'}"
			>
				Transcode
			</button>
		{/if}
		<button
			onclick={handleCancel}
			disabled={cancelling}
			class="{btnBase} ml-auto text-red-600 ring-1 ring-red-300 hover:bg-red-50 disabled:opacity-50 dark:text-red-400 dark:ring-red-700 dark:hover:bg-red-900/20"
		>
			{cancelling ? 'Cancelling...' : 'Cancel'}
		</button>
		<button
			onclick={handleStart}
			disabled={starting}
			class="{btnBase} bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 dark:bg-emerald-700 dark:hover:bg-emerald-600"
		>
			{starting ? 'Starting...' : 'Start'}
		</button>
	</div>

	<!-- Expanded sections -->
	{#if showInfo}
		{#if infoDirty}
			<div class="flex items-center justify-between border-t border-amber-300 bg-amber-50 px-4 py-2 dark:border-amber-700 dark:bg-amber-900/20">
				<span class="text-xs font-medium text-amber-700 dark:text-amber-400">Unsaved changes</span>
				<div class="flex items-center gap-2">
					{#if infoFeedback}
						<span class="text-xs {infoFeedback.type === 'success' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}">
							{infoFeedback.message}
						</span>
					{/if}
					<button
						onclick={resetInfo}
						class="{btnBase} text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700"
					>
						Reset
					</button>
					<button
						onclick={saveInfo}
						disabled={infoSaving}
						class="{btnBase} bg-primary text-on-primary hover:bg-primary-hover disabled:opacity-50"
					>
						{infoSaving ? 'Saving...' : 'Save'}
					</button>
				</div>
			</div>
		{/if}
		<div class="border-t border-primary/20 p-4 dark:border-primary/20">
			{#if initialLoading}
				<p class="text-sm text-gray-400">Loading...</p>
			{:else}
				<div class="space-y-4">
					<!-- Auto-detection context -->
					{#if job.title_auto}
						<div class="flex items-center gap-2 rounded-md bg-primary/5 px-3 py-2 text-xs dark:bg-primary/10">
							<span class="text-gray-500 dark:text-gray-400">Auto-detected:</span>
							<span class="font-medium text-gray-700 dark:text-gray-300">{job.title_auto}{#if job.year_auto} ({job.year_auto}){/if}</span>
							{#if job.hasnicetitle}
								<span class="rounded-sm bg-green-100 px-1.5 py-0.5 font-medium text-green-700 dark:bg-green-900/30 dark:text-green-400">confident</span>
							{:else}
								<span class="rounded-sm bg-amber-100 px-1.5 py-0.5 font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">best guess</span>
							{/if}
						</div>
					{/if}

					{#if !isMultiTitleMovie}
					<!-- Identity -->
					<h4 class="text-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">Identity</h4>
					<div class="space-y-2">
						<label class="block">
							<span class="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">Title</span>
							<input type="text" bind:value={infoTitle} oninput={() => { touched.title = true; }} class="w-full rounded-sm border border-primary/25 bg-primary/5 px-2 py-1 text-sm text-gray-900 focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary dark:border-primary/30 dark:bg-primary/10 dark:text-white" />
						</label>
						{#if isMusic}
							<div class="grid grid-cols-2 gap-3">
								<label>
									<span class="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">Artist</span>
									<input type="text" bind:value={infoArtist} oninput={() => { touched.artist = true; }} class="w-full rounded-sm border border-primary/25 bg-primary/5 px-2 py-1 text-sm text-gray-900 focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary dark:border-primary/30 dark:bg-primary/10 dark:text-white" />
								</label>
								<label>
									<span class="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">Album</span>
									<input type="text" bind:value={infoAlbum} oninput={() => { touched.album = true; }} class="w-full rounded-sm border border-primary/25 bg-primary/5 px-2 py-1 text-sm text-gray-900 focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary dark:border-primary/30 dark:bg-primary/10 dark:text-white" />
								</label>
							</div>
						{/if}
						{#if infoType === 'series'}
							<div class="grid grid-cols-2 gap-3">
								<label>
									<span class="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">Season</span>
									<input type="text" bind:value={infoSeason} oninput={() => { touched.season = true; }} placeholder="1" class="w-full rounded-sm border border-primary/25 bg-primary/5 px-2 py-1 text-sm text-gray-900 focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary dark:border-primary/30 dark:bg-primary/10 dark:text-white" />
								</label>
								<label>
									<span class="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">Episode</span>
									<input type="text" bind:value={infoEpisode} oninput={() => { touched.episode = true; }} placeholder="1" class="w-full rounded-sm border border-primary/25 bg-primary/5 px-2 py-1 text-sm text-gray-900 focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary dark:border-primary/30 dark:bg-primary/10 dark:text-white" />
								</label>
							</div>
						{/if}
					</div>
					{/if}
					<hr class="border-primary/10 dark:border-primary/15" />
					<h4 class="text-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">Media Metadata</h4>
					<div class="space-y-2">
						<div class="grid gap-3 {isMusic ? 'grid-cols-2' : 'grid-cols-3'}">
							{#if !isMultiTitleMovie}
							<label>
								<span class="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">Year</span>
								<input type="text" bind:value={infoYear} oninput={() => { touched.year = true; }} class="w-full rounded-sm border border-primary/25 bg-primary/5 px-2 py-1 text-sm text-gray-900 focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary dark:border-primary/30 dark:bg-primary/10 dark:text-white" />
							</label>
							{/if}
							<label>
								<span class="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">Type</span>
								<select bind:value={infoType} onchange={() => { touched.type = true; }} class="w-full rounded-sm border border-primary/25 bg-primary/5 px-2 py-1 text-sm text-gray-900 focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary dark:border-primary/30 dark:bg-primary/10 dark:text-white">
									{#if !infoType || infoType === 'unknown'}
										<option value="" disabled selected>Select type...</option>
									{/if}
									<option value="movie">Movie</option>
									<option value="series">Series</option>
									<option value="music">Music</option>
								</select>
							</label>
							{#if !isMusic && !isMultiTitleMovie}
								<label>
									<span class="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">IMDb ID</span>
									<input type="text" bind:value={infoImdbId} oninput={() => { touched.imdbId = true; }} placeholder="tt..." class="w-full rounded-sm border border-primary/25 bg-primary/5 px-2 py-1 text-sm text-gray-900 focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary dark:border-primary/30 dark:bg-primary/10 dark:text-white" />
								</label>
							{/if}
						</div>
						{#if !isMultiTitleMovie}
						<label class="block">
							<span class="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">{isMusic ? 'Cover Art URL' : 'Poster URL'}</span>
							<input type="text" bind:value={infoPosterUrl} oninput={() => { touched.posterUrl = true; }} placeholder="https://..." class="w-full rounded-sm border border-primary/25 bg-primary/5 px-2 py-1 text-sm text-gray-900 focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary dark:border-primary/30 dark:bg-primary/10 dark:text-white" />
						</label>
						{/if}
						{#if infoPlot}
							<div class="rounded-md bg-primary/5 px-3 py-2 text-sm italic text-gray-600 dark:bg-primary/10 dark:text-gray-400">{infoPlot}</div>
						{/if}
					</div>

					{#if infoFeedback && !infoDirty}
						<span class="text-xs {infoFeedback.type === 'success' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}">
							{infoFeedback.message}
						</span>
					{/if}

					<!-- Disc details -->
					<hr class="border-primary/10 dark:border-primary/15" />
					<h4 class="text-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">Disc Details</h4>
					<div class="grid gap-3 text-sm {isMusic ? 'grid-cols-3' : 'grid-cols-5'}">
						<label>
							<span class="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">Disc Type</span>
							<select bind:value={infoDisctype} onchange={() => { touched.disctype = true; }} class="w-full rounded-sm border border-primary/25 bg-primary/5 px-2 py-1 text-sm text-gray-900 focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary dark:border-primary/30 dark:bg-primary/10 dark:text-white">
								<option value="dvd">DVD</option>
								<option value="bluray">Blu-ray</option>
								<option value="bluray4k">4K UHD</option>
								<option value="music">Music</option>
								<option value="data">Data</option>
							</select>
						</label>
						{#if !isMusic}
							<label>
								<span class="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">Title Mode</span>
								<select
									value={job.multi_title ? 'multi' : 'single'}
									onchange={(e) => { const v = e.currentTarget.value; if ((v === 'multi') !== !!job.multi_title) handleToggleMultiTitle(); }}
									disabled={togglingMultiTitle}
									class="w-full rounded-sm border border-primary/25 bg-primary/5 px-2 py-1 text-sm text-gray-900 focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary dark:border-primary/30 dark:bg-primary/10 dark:text-white"
								>
									<option value="single">Single Title</option>
									<option value="multi">Multi-Title</option>
								</select>
							</label>
						{/if}
						<label>
							<span class="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">Disc Label</span>
							<input type="text" bind:value={infoLabel} oninput={() => { touched.label = true; }} class="w-full rounded-sm border border-primary/25 bg-primary/5 px-2 py-1 font-mono text-xs text-gray-900 focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary dark:border-primary/30 dark:bg-primary/10 dark:text-white" />
						</label>
						<div>
							<span class="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">Drive</span>
							<p class="px-2 py-1 text-sm text-gray-900 dark:text-white">{driveName ?? job.devpath ?? '--'}</p>
						</div>
						{#if !isMusic}
							<div>
								<span class="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">CRC</span>
								<p class="px-2 py-1 font-mono text-xs text-gray-900 dark:text-white">{job.crc_id || '--'}</p>
							</div>
						{/if}
					</div>

					<!-- Output path -->
					<label class="block text-sm">
						<span class="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">Output Path</span>
						<input type="text" bind:value={infoPath} oninput={() => { touched.path = true; }} class="w-full rounded-sm border border-primary/25 bg-primary/5 px-2 py-1 font-mono text-xs text-gray-900 focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary dark:border-primary/30 dark:bg-primary/10 dark:text-white" />
					</label>

					<!-- Tracks table -->
					{#if detail?.tracks && detail.tracks.length > 0}
						<div>
							<h4 class="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
								Tracks ({detail.tracks.length})
								{#if job.disc_number && job.disc_total}
									<span class="font-normal text-gray-400 dark:text-gray-500">— Disc {job.disc_number} of {job.disc_total}</span>
								{/if}
							</h4>
							<div class="overflow-x-auto rounded-md border border-primary/15 dark:border-primary/20">
								<table class="w-full text-left text-xs">
									<thead class="bg-page text-gray-500 dark:bg-primary/5 dark:text-gray-400">
										<tr>
											<th class="px-3 py-1.5 font-medium">#</th>
											<th class="px-3 py-1.5 font-medium">{isMusic ? 'Name' : 'Title'}</th>
											{#if !isMusic}<th class="px-2 py-1.5 font-medium text-center">Episode</th>{/if}
											<th class="px-3 py-1.5 font-medium">Length</th>
											{#if !isMusic}
												<th class="px-3 py-1.5 font-medium">Aspect</th>
												<th class="px-3 py-1.5 font-medium">FPS</th>
												<th class="pl-1 pr-3 py-1.5 font-medium">
													<label class="flex items-center gap-1 cursor-pointer">
														<span>Rip</span>
														<input
															type="checkbox"
															checked={allEnabled}
															onchange={handleToggleAllEnabled}
															disabled={togglingAllEnabled}
															class="h-3.5 w-3.5 rounded-sm border-primary/25 text-primary focus:ring-primary dark:border-primary/30 dark:bg-primary/10"
														/>
													</label>
												</th>
												<th class="px-3 py-1.5 font-medium">Filename</th>
												{#if job.multi_title}<th class="w-8"></th>{/if}
											{/if}
										</tr>
									</thead>
									<tbody class="divide-y divide-gray-100 dark:divide-gray-700/50">
										{#each detail.tracks as track}
											{@const filtered = !isMusic && isFiltered(track)}
											<tr class="{filtered ? 'opacity-40' : track.enabled && !isMusic ? 'bg-primary-light-bg/50 dark:bg-primary-light-bg-dark/10' : ''}">
												<td class="px-3 py-1.5 font-mono text-gray-700 dark:text-gray-300">{track.track_number ?? '--'}</td>
												{#if isMusic}
													<td class="px-3 py-1.5 text-gray-700 dark:text-gray-300">{track.title || track.filename || '--'}</td>
												{:else}
													<td
														class="px-3 py-1.5 {job.multi_title ? 'cursor-pointer hover:bg-primary/5 dark:hover:bg-primary/10' : ''}"
														onclick={() => { if (job.multi_title) toggleTrackSearch(track.track_id); }}
													>
														{#if track.title}
															<div class="flex items-center gap-1.5">
																{#if track.poster_url}
																	<img src={posterSrc(track.poster_url)} alt="" class="h-6 w-4 rounded-sm object-cover" onerror={posterFallback} />
																{/if}
																<span class="font-medium text-gray-700 dark:text-gray-300">{track.title}</span>
																{#if track.year}
																	<span class="text-gray-400">({track.year})</span>
																{/if}
															</div>
														{:else}
															<span class="text-gray-400">{job.title || job.label || 'Untitled'}{#if job.year} ({job.year}){/if}</span>
														{/if}
													</td>
												{/if}
												{#if !isMusic}
													<td class="px-2 py-1.5 text-center">
														<input
															type="text"
															value={track.episode_number ?? ''}
															onchange={(e) => handleTrackFieldUpdate(track.track_id, 'episode_number', e.currentTarget.value.trim())}
															placeholder="--"
															disabled={filtered || !track.enabled}
															class="w-10 rounded-sm border border-primary/25 bg-primary/5 px-1 py-0.5 text-center text-xs text-gray-900 focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary disabled:opacity-30 dark:border-primary/30 dark:bg-primary/10 dark:text-white"
														/>
													</td>
												{/if}
												<td class="px-3 py-1.5 text-gray-700 dark:text-gray-300">{formatLength(track.length)}</td>
												{#if !isMusic}
													<td class="px-3 py-1.5 text-gray-500 dark:text-gray-400">{track.aspect_ratio ?? '--'}</td>
													<td class="px-3 py-1.5 text-gray-500 dark:text-gray-400">{track.fps ?? '--'}</td>
													<td class="pl-1 pr-3 py-1.5">
														{#if filtered}
															<span class="ml-3 text-[10px] text-gray-400 dark:text-gray-500" title={skipTooltip(track)}>skip</span>
														{:else}
															<input
																type="checkbox"
																checked={track.enabled}
																onchange={() => handleTrackFieldUpdate(track.track_id, 'enabled', !track.enabled)}
																disabled={savingTrackField === `${track.track_id}-enabled`}
																class="ml-[22px] h-3.5 w-3.5 rounded-sm border-primary/25 text-primary focus:ring-primary disabled:opacity-50 dark:border-primary/30 dark:bg-primary/10"
															/>
														{/if}
													</td>
													<td class="px-3 py-1.5">
														{#if editingFilenameTrackId === track.track_id}
															<div class="flex items-center gap-1">
																<input
																	type="text"
																	bind:value={editingFilenameValue}
																	onkeydown={(e) => { if (e.key === 'Enter') { handleTrackFieldUpdate(track.track_id, 'custom_filename', editingFilenameValue); editingFilenameTrackId = null; } if (e.key === 'Escape') editingFilenameTrackId = null; }}
																	class="w-full min-w-[120px] rounded-sm border border-amber-400 bg-transparent px-1 py-0.5 font-mono text-xs text-amber-600 focus:outline-hidden focus:ring-1 focus:ring-amber-400 dark:border-amber-600 dark:text-amber-400"
																/>
																<button
																	onclick={() => { handleTrackFieldUpdate(track.track_id, 'custom_filename', editingFilenameValue); editingFilenameTrackId = null; }}
																	disabled={savingTrackField === `${track.track_id}-custom_filename`}
																	class="rounded bg-green-600 px-1.5 py-0.5 text-[10px] text-white hover:bg-green-700"
																>Save</button>
																<button
																	onclick={() => { editingFilenameTrackId = null; }}
																	class="rounded border border-gray-400 px-1 py-0.5 text-[10px] text-gray-400 hover:bg-gray-800"
																>×</button>
															</div>
														{:else}
															{@const customFn = track.custom_filename}
															{@const renderedFn = namingPreviews[track.track_number ?? '']?.rendered_title || track.filename || track.basename || '--'}
															<button
																onclick={() => { editingFilenameTrackId = track.track_id; editingFilenameValue = customFn || renderedFn; }}
																class="w-full text-left font-mono text-xs {customFn ? 'text-amber-500 dark:text-amber-400' : 'text-gray-500 dark:text-gray-400'} hover:underline"
															>
																{customFn || renderedFn}
															</button>
															{#if customFn}
																<div class="flex items-center gap-1">
																	<span class="text-[9px] text-gray-500">was: {renderedFn}</span>
																	<button
																		onclick={() => handleTrackFieldUpdate(track.track_id, 'custom_filename', '')}
																		class="text-[9px] text-red-400 hover:text-red-300"
																	>clear</button>
																</div>
															{/if}
														{/if}
													</td>
												{/if}
												{#if job.multi_title && !isMusic && !filtered}
													<td class="px-1 py-1.5">
														<button
															onclick={() => toggleTrackSearch(track.track_id)}
															class="rounded p-1 transition-colors {openSearchTrackIds.has(track.track_id) ? 'text-primary' : 'text-gray-400 hover:text-primary dark:text-gray-500 dark:hover:text-primary'}"
															title={openSearchTrackIds.has(track.track_id) ? 'Close search' : 'Search title'}
														>
															<svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
																<circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
															</svg>
														</button>
													</td>
												{/if}
											</tr>
											{#if job.multi_title && !filtered && openSearchTrackIds.has(track.track_id)}
												<tr>
													<td colspan="99" class="px-3 py-2">
														<TrackTitleSearch jobId={job.job_id} {track} onapply={() => handleTrackTitleApply(track.track_id)} onclear={() => { onrefresh?.(); loadDetail(); }} onclose={() => toggleTrackSearch(track.track_id)} />
													</td>
												</tr>
											{/if}
										{/each}
									</tbody>
								</table>
							</div>
						</div>
					{/if}

					<!-- Footer: details link + action buttons -->
					<div class="flex items-center justify-between">
						<a
							href="/jobs/{job.job_id}"
							class="{btnBase} inline-flex items-center gap-1 bg-primary/5 text-gray-700 ring-1 ring-primary/25 hover:bg-primary/10 dark:bg-primary/10 dark:text-gray-200 dark:ring-primary/30 dark:hover:bg-primary/15"
						>
							View Full Details
							<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
							</svg>
						</a>
						<div class="flex gap-2">
							<button
								onclick={handleCancel}
								disabled={cancelling}
								class="{btnBase} text-red-600 ring-1 ring-red-300 hover:bg-red-50 disabled:opacity-50 dark:text-red-400 dark:ring-red-700 dark:hover:bg-red-900/20"
							>
								{cancelling ? 'Cancelling...' : 'Cancel'}
							</button>
							<button
								onclick={handleStart}
								disabled={starting}
								class="{btnBase} bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 dark:bg-emerald-700 dark:hover:bg-emerald-600"
							>
								{starting ? 'Starting...' : 'Start'}
							</button>
						</div>
					</div>
				</div>
			{/if}
		</div>
	{/if}

	<!-- Unsaved changes bar -->
	{#if infoDirty && showInfo}
		<div class="flex items-center justify-between border-t border-amber-300 bg-amber-50 px-4 py-2 dark:border-amber-700 dark:bg-amber-900/20">
			<span class="text-xs font-medium text-amber-700 dark:text-amber-400">Unsaved changes</span>
			<div class="flex items-center gap-2">
				{#if infoFeedback}
					<span class="text-xs {infoFeedback.type === 'success' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}">
						{infoFeedback.message}
					</span>
				{/if}
				<button
					onclick={resetInfo}
					class="{btnBase} text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700"
				>
					Reset
				</button>
				<button
					onclick={saveInfo}
					disabled={infoSaving}
					class="{btnBase} bg-primary text-on-primary hover:bg-primary-hover disabled:opacity-50"
				>
					{infoSaving ? 'Saving...' : 'Save'}
				</button>
			</div>
		</div>
	{/if}

	{#if showTitleSearch && isVideo}
		<div class="border-t border-primary/20 p-4 dark:border-primary/20">
			<TitleSearch {job} onapply={handleTitleApply} onapplydetail={(d) => { infoPlot = d.plot ?? null; }} onepisodes={() => toggleSection('tvdb')} />
		</div>
	{/if}

	{#if showMusicSearch && isMusic}
		<div class="border-t border-primary/20 p-4 dark:border-primary/20">
			<MusicSearch {job} discTracks={detail?.tracks ?? []} onapply={handleTitleApply} />
		</div>
	{/if}

	{#if showCrcLookup && hasCrcData}
		<div class="border-t border-primary/20 p-4 dark:border-primary/20">
			<CrcLookup {job} onapply={handleCrcApply} />
		</div>
	{/if}

	{#if showRipSettings && detail?.config}
		<div class="border-t border-primary/20 p-4 dark:border-primary/20">
			<RipSettings {job} config={detail.config} {isMusic} multiTitle={!!job.multi_title} onsaved={handleConfigSaved} />
		</div>
	{:else if showRipSettings && initialLoading}
		<div class="border-t border-primary/20 p-4 text-sm text-gray-400 dark:border-primary/20">
			Loading config...
		</div>
	{:else if showRipSettings}
		<div class="border-t border-primary/20 p-4 text-sm text-gray-400 dark:border-primary/20">
			Rip settings unavailable — ARM did not return config data.
		</div>
	{/if}

	{#if showTranscodeSettings && isVideo}
		<div class="border-t border-primary/20 p-4 space-y-3 dark:border-primary/20">
			<div class="flex items-center justify-between rounded-lg bg-amber-50 px-3 py-2 dark:bg-amber-900/20">
				<div class="flex items-center gap-2">
					<span class="text-sm font-medium text-amber-800 dark:text-amber-200">Skip Transcoding</span>
					<span class="text-xs text-amber-600 dark:text-amber-400">Finalize with raw MKV files</span>
				</div>
				<button
					onclick={handleSkipTranscodeToggle}
					class="relative inline-flex h-5 w-9 items-center rounded-full transition-colors {skipTranscode ? 'bg-amber-500' : 'bg-gray-300 dark:bg-gray-600'}"
					title={skipTranscode ? 'Transcoding will be skipped' : 'Files will be sent to transcoder'}
				>
					<span class="inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform {skipTranscode ? 'translate-x-4' : 'translate-x-0.5'}"></span>
				</button>
			</div>
			{#if !skipTranscode}
				<TranscodeOverrides {job} onsaved={handleConfigSaved} />
			{/if}
		</div>
	{/if}

	{#if showTvdb && isVideo && detail}
		<div class="border-t border-primary/20 p-4 dark:border-primary/20">
			<EpisodeMatch job={detail} onapply={loadDetail} />
		</div>
	{/if}

	{#if job.logfile}
		<InlineLogFeed logfile={job.logfile} maxEntries={5} levelFilter="error" containerClass="border-t border-primary/20 px-4 py-3 dark:border-primary/20" />
	{/if}
</div>
{/if}
