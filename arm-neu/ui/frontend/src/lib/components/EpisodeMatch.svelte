<script lang="ts">
	import type { JobDetailSchema as JobDetail, Track } from '$lib/types/api.gen';
	import type { TvdbEpisode, NamingPreviewTrack } from '$lib/api/jobs';
	import { tvdbMatch, fetchTvdbEpisodes, updateTrack, fetchNamingPreview } from '$lib/api/jobs';

	interface Props {
		job: JobDetail;
		onapply?: () => void;
	}

	let { job, onapply }: Props = $props();

	// Controls - initialized empty, synced from job props via $effect
	let seasonInput = $state('');
	let discInput = $state('');
	let discTotalInput = $state('');
	let toleranceInput = $state('600');
	let controlsSynced = $state(false);

	// Sync controls from job props when they become available
	$effect(() => {
		if (!controlsSynced) {
			const s = job.season || job.season_auto || '';
			const d = job.disc_number?.toString() || '';
			const dt = job.disc_total?.toString() || '';
			if (s || d || dt) {
				seasonInput = s;
				discInput = d;
				discTotalInput = dt;
				controlsSynced = true;
			}
		}
	});

	// State
	let loading = $state(false);
	let error = $state<string | null>(null);
	let matches = $state<Array<{ track_number: string; episode_number: number; episode_name: string; episode_runtime: number }>>([]);
	let episodes = $state<TvdbEpisode[]>([]);
	let namingPreviews = $state<Record<string, NamingPreviewTrack>>({});
	let matchedSeason = $state<number | null>(null);
	let applying = $state(false);

	// Editable assignments: track_number -> episode_number (null = unassigned)
	let assignments = $state<Record<string, number | null>>({});

	// Derived
	let mainTracks = $derived(
		(job.tracks || []).filter((t) => (t.length ?? 0) >= 120).sort((a, b) => {
			const an = parseInt(a.track_number ?? '0');
			const bn = parseInt(b.track_number ?? '0');
			return an - bn;
		})
	);
	let shortTracks = $derived(
		(job.tracks || []).filter((t) => (t.length ?? 0) < 120)
	);
	let matchCount = $derived(
		Object.values(assignments).filter((v) => v !== null && v !== undefined).length
	);
	let unmatched = $derived(mainTracks.length - matchCount);

	function formatDuration(seconds: number | null | undefined): string {
		if (!seconds) return '-';
		const m = Math.floor(seconds / 60);
		const s = seconds % 60;
		return `${m}:${s.toString().padStart(2, '0')}`;
	}

	function deltaClass(trackLen: number | null | undefined, epRuntime: number | null): string {
		if (!trackLen || !epRuntime) return '';
		const delta = Math.abs(trackLen - epRuntime * 60);
		if (delta < 60) return 'text-green-400';
		if (delta < 180) return 'text-yellow-400';
		return 'text-red-400';
	}

	function deltaText(trackLen: number | null | undefined, epRuntime: number | null): string {
		if (!trackLen || !epRuntime) return '-';
		const delta = trackLen - epRuntime * 60;
		const abs = Math.abs(delta);
		const sign = delta >= 0 ? '+' : '-';
		if (abs < 60) return `${sign}${abs}s`;
		return `${sign}${Math.floor(abs / 60)}m${(abs % 60).toString().padStart(2, '0')}s`;
	}

	async function loadEpisodeList(season: number, fallbackMatches?: typeof matches) {
		try {
			const epResult = await fetchTvdbEpisodes(job.job_id, season);
			// API returns runtime in seconds - always convert to minutes
			episodes = epResult.episodes.map(ep => ({
				...ep,
				runtime: Math.round(ep.runtime / 60),
			}));
		} catch {
			if (fallbackMatches?.length) {
				const seen = new Set<number>();
				const fallback: TvdbEpisode[] = [];
				for (const m of fallbackMatches) {
					if (!seen.has(m.episode_number)) {
						seen.add(m.episode_number);
						fallback.push({
							number: m.episode_number,
							name: m.episode_name,
							runtime: m.episode_runtime ? Math.round(m.episode_runtime / 60) : 0,
							aired: '',
						});
					}
				}
				episodes = fallback;
			}
		}
	}

	async function runMatch() {
		loading = true;
		error = null;
		try {
			const season = seasonInput ? Number(seasonInput) : null;
			const result = await tvdbMatch(job.job_id, {
				season,
				tolerance: Number(toleranceInput) || 300,
				apply: false,
				disc_number: discInput ? Number(discInput) : null,
				disc_total: discTotalInput ? Number(discTotalInput) : null,
			});

			if (!result.success) {
				error = result.error || 'Match failed';
				return;
			}

			matches = result.matches;
			matchedSeason = result.season;

			// Update season input if auto-detected
			if (!seasonInput && result.season) {
				seasonInput = result.season.toString();
			}

			// Populate assignments from matches
			assignments = {};
			for (const m of result.matches) {
				assignments[m.track_number] = m.episode_number;
			}

			// Fetch ALL season episodes for dropdowns
			if (result.season) {
				await loadEpisodeList(result.season, result.matches);
			}
			} catch (e) {
			error = e instanceof Error ? e.message : 'Match failed';
		} finally {
			loading = false;
		}
	}

	async function applyMatches() {
		applying = true;
		error = null;
		try {
			// Apply via tvdb-match with apply=true for auto-matched tracks
			const season = seasonInput ? Number(seasonInput) : null;
			await tvdbMatch(job.job_id, {
				season,
				tolerance: Number(toleranceInput) || 300,
				apply: true,
				disc_number: discInput ? Number(discInput) : null,
				disc_total: discTotalInput ? Number(discTotalInput) : null,
			});

			// Apply manual overrides for tracks that differ from auto-match
			for (const track of mainTracks) {
				const tn = track.track_number ?? '';
				const assigned = assignments[tn];
				const autoMatch = matches.find((m) => m.track_number === tn);

				if (assigned !== undefined && assigned !== (autoMatch?.episode_number ?? null)) {
					const ep = episodes.find((e) => e.number === assigned);
					await updateTrack(job.job_id, track.track_id, {
						episode_number: assigned?.toString() ?? '',
						episode_name: ep?.name ?? '',
					});
				}
			}

			// Fetch rendered filenames after apply
			await loadNamingPreviews();
			onapply?.();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Apply failed';
		} finally {
			applying = false;
		}
	}

	async function loadNamingPreviews() {
		try {
			const result = await fetchNamingPreview(job.job_id);
			if (result.success) {
				const map: Record<string, NamingPreviewTrack> = {};
				for (const t of result.tracks) {
					map[t.track_number] = t;
				}
				namingPreviews = map;
			}
		} catch {
			// Non-critical - silently skip
		}
	}

	function clearAll() {
		assignments = {};
		matches = [];
		episodes = [];
	}

	function getEpisodeForTrack(trackNumber: string): TvdbEpisode | undefined {
		const epNum = assignments[trackNumber];
		if (epNum == null) return undefined;
		return episodes.find((e) => e.number === epNum);
	}

	// Tracks with existing episode assignments (from previous Apply)
	let existingMatches = $derived(
		mainTracks.filter(t => t.episode_number)
	);

	// On mount: if tracks have existing episodes, restore into assignments
	// and load full episode list for dropdowns. Otherwise auto-run match.
	$effect(() => {
		if (mainTracks.length > 0 && matches.length === 0) {
			if (existingMatches.length > 0) {
				// Populate assignments from DB track data
				for (const t of existingMatches) {
					assignments[t.track_number ?? ''] = Number(t.episode_number);
				}
				// Set matches so the interactive table renders
				matches = existingMatches.map(t => ({
					track_number: t.track_number ?? '',
					episode_number: Number(t.episode_number),
					episode_name: t.episode_name || '',
					episode_runtime: 0,
				}));
				// Load full episode list for dropdowns
				if (job.tvdb_id) {
					const s = Number(seasonInput || job.season || job.season_auto || 1);
					loadEpisodeList(s);
				}
			} else if (job.tvdb_id || job.imdb_id) {
				runMatch();
			}
		}
	});
</script>

<div class="space-y-3">
	<!-- Controls bar (always visible) -->
	<div class="flex flex-wrap items-center gap-3 rounded-lg bg-surface/50 p-3 ring-1 ring-primary/10 dark:bg-surface-dark/50 dark:ring-primary/10">
		<div class="flex items-center gap-1.5">
			<span class="text-[10px] font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Season</span>
			<input
				type="number"
				bind:value={seasonInput}
				min="1"
				class="w-12 rounded border border-primary/20 bg-surface px-1.5 py-0.5 text-center text-xs text-gray-900 dark:border-primary/20 dark:bg-surface-dark dark:text-white"
			/>
		</div>
		<div class="flex items-center gap-1.5">
			<span class="text-[10px] font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Disc</span>
			<input
				type="number"
				bind:value={discInput}
				min="1"
				class="w-12 rounded border border-primary/20 bg-surface px-1.5 py-0.5 text-center text-xs text-gray-900 dark:border-primary/20 dark:bg-surface-dark dark:text-white"
			/>
			<span class="text-xs text-gray-400">of</span>
			<input
				type="number"
				bind:value={discTotalInput}
				min="1"
				class="w-12 rounded border border-primary/20 bg-surface px-1.5 py-0.5 text-center text-xs text-gray-900 dark:border-primary/20 dark:bg-surface-dark dark:text-white"
			/>
		</div>
		<div class="flex items-center gap-1.5">
			<span class="text-[10px] font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Tolerance</span>
			<input
				type="number"
				bind:value={toleranceInput}
				min="60"
				step="60"
				class="w-16 rounded border border-primary/20 bg-surface px-1.5 py-0.5 text-center text-xs text-gray-900 dark:border-primary/20 dark:bg-surface-dark dark:text-white"
			/>
			<span class="text-[10px] text-gray-400">sec</span>
		</div>
		<button
			onclick={runMatch}
			disabled={loading}
			class="rounded-md bg-blue-600 px-3 py-1 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-50 dark:bg-blue-700 dark:hover:bg-blue-600"
		>
			{loading ? 'Matching...' : 'Match'}
		</button>
		{#if matches.length > 0}
			<div class="ml-auto flex items-center gap-2 text-xs">
				<span class="text-green-500">{matchCount} matched</span>
				<span class="text-gray-500">&middot;</span>
				{#if unmatched > 0}
					<span class="text-amber-500">{unmatched} unmatched</span>
				{:else}
					<span class="text-gray-500">0 unmatched</span>
				{/if}
				<span class="text-gray-500">&middot;</span>
				<span class="text-gray-500">{shortTracks.length} skipped</span>
			</div>
		{/if}
	</div>

	<!-- Error -->
	{#if error}
		<div class="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400">
			{error}
		</div>
	{/if}

	<!-- Match table -->
	{#if matches.length > 0 || Object.keys(assignments).length > 0}
		<div class="overflow-x-auto">
			<table class="w-full table-fixed text-sm">
				<colgroup>
					<col class="w-[25%]" />
					<col class="w-[8%]" />
					<col class="w-[28%]" />
					<col class="w-[23%]" />
					<col class="w-[8%]" />
					<col class="w-[8%]" />
				</colgroup>
				<thead>
					<tr class="border-b border-primary/10 dark:border-primary/10">
						<th class="px-2 py-1.5 text-left text-[10px] font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Track</th>
						<th class="px-2 py-1.5 text-left text-[10px] font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Duration</th>
						<th class="px-2 py-1.5 text-left text-[10px] font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Episode</th>
						<th class="px-2 py-1.5 text-left text-[10px] font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Title</th>
						<th class="px-2 py-1.5 text-right text-[10px] font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">TVDB</th>
						<th class="px-2 py-1.5 text-right text-[10px] font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Delta</th>
					</tr>
				</thead>
				<tbody>
					{#each mainTracks as track}
						{@const tn = track.track_number ?? ''}
						{@const ep = getEpisodeForTrack(tn)}
						<tr class="border-b border-primary/5 dark:border-primary/5">
							<td class="px-2 py-2">
								<span class="text-xs text-gray-500">T{tn}</span>
								<span class="ml-1 text-xs text-gray-400 dark:text-gray-500">{(track.filename ?? '').slice(0, 30)}</span>
							</td>
							<td class="px-2 py-2 text-gray-300 dark:text-gray-300">{formatDuration(track.length)}</td>
							<td class="px-2 py-2">
								<select
									class="w-full rounded border border-primary/20 bg-surface px-1.5 py-0.5 text-xs truncate dark:border-primary/20 dark:bg-surface-dark {assignments[tn] != null ? 'text-green-400' : 'text-gray-400'}"
									value={assignments[tn] ?? ''}
									onchange={(e) => {
										const val = (e.target as HTMLSelectElement).value;
										assignments[tn] = val ? Number(val) : null;
									}}
								>
									<option value="">- None -</option>
									{#each [...episodes].sort((a, b) => a.number - b.number) as episode}
										<option value={episode.number}>
											E{episode.number} - {episode.name} ({episode.runtime}m)
										</option>
									{/each}
								</select>
							</td>
							<td class="px-2 py-2 text-xs text-gray-300 dark:text-gray-400">
								{namingPreviews[tn]?.rendered_title || ep?.name || '-'}
							</td>
							<td class="px-2 py-2 text-right text-gray-400">{ep ? `${ep.runtime}m` : '-'}</td>
							<td class="px-2 py-2 text-right {deltaClass(track.length, ep?.runtime ?? null)}">
								{deltaText(track.length, ep?.runtime ?? null)}
							</td>
						</tr>
					{/each}
					{#if shortTracks.length > 0}
						<tr class="opacity-40">
							<td class="px-2 py-2 text-xs text-gray-500" colspan="6">
								{shortTracks.length} short track{shortTracks.length > 1 ? 's' : ''} skipped (menus, intros)
							</td>
						</tr>
					{/if}
				</tbody>
			</table>
		</div>

		<!-- Actions -->
		<div class="flex items-center gap-2">
			<button
				onclick={applyMatches}
				disabled={applying || matchCount === 0}
				class="rounded-md bg-green-600 px-4 py-1.5 text-sm font-medium text-white transition-colors hover:bg-green-700 disabled:opacity-50 dark:bg-green-700 dark:hover:bg-green-600"
			>
				{applying ? 'Applying...' : 'Apply Matches'}
			</button>
			<button
				onclick={clearAll}
				class="rounded-md px-4 py-1.5 text-sm text-gray-500 ring-1 ring-gray-300 transition-colors hover:bg-gray-50 dark:text-gray-400 dark:ring-gray-600 dark:hover:bg-gray-800"
			>
				Clear All
			</button>
			<span class="ml-auto text-[11px] text-gray-400 dark:text-gray-500">
				Change season/disc and re-match to try different assignments.
			</span>
		</div>
	{:else if loading}
		<div class="flex items-center justify-center py-8">
			<div class="flex items-center gap-2 text-sm text-gray-400 dark:text-gray-500">
				<svg class="h-5 w-5 animate-spin" fill="none" viewBox="0 0 24 24">
					<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
					<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
				</svg>
				Matching episodes...
			</div>
		</div>
	{:else if !error && !applying}
		<div class="py-6 text-center text-sm text-gray-400 dark:text-gray-500">
			{#if !job.tvdb_id && !job.imdb_id}
				No IMDB or TVDB ID set. Use <strong>Search</strong> to identify the show first.
			{:else if mainTracks.length === 0}
				No tracks found. The prescan may still be running.
			{:else}
				Click <strong>Match</strong> to auto-assign episodes to tracks.
			{/if}
		</div>
	{/if}
</div>
