<script lang="ts">
	import type { JobDetailSchema as JobDetail } from '$lib/types/api.gen';
	import {
		tvdbMatch,
		fetchTvdbEpisodes,
		type TvdbMatch,
		type TvdbMatchResponse,
		type TvdbAlternative,
		type TvdbEpisode,
		type TvdbEpisodesResponse
	} from '$lib/api/jobs';

	interface Props {
		job: JobDetail;
		onapply?: () => void;
	}

	let { job, onapply }: Props = $props();

	// --- Tabs ---
	let activeTab = $state<'match' | 'browse'>('match');

	// --- Match state ---
	let seasonInput = $state(job.season || job.season_auto || '');
	let toleranceInput = $state('300');
	let autoDetect = $state(!seasonInput);
	let loading = $state(false);
	let error = $state<string | null>(null);
	let result = $state<TvdbMatchResponse | null>(null);
	let applying = $state(false);
	let applyFeedback = $state<{ type: 'success' | 'error'; message: string } | null>(null);

	// Per-match selection (checked = will be applied)
	let selectedMatches = $state<Set<string>>(new Set());

	let selectedCount = $derived(selectedMatches.size);

	// --- Browse state ---
	let browseSeason = $state(Number(job.season || job.season_auto) || 1);
	let browseLoading = $state(false);
	let browseError = $state<string | null>(null);
	let browseResult = $state<TvdbEpisodesResponse | null>(null);

	// Build a map of track lengths for display
	let trackLengthMap = $derived(
		Object.fromEntries((job.tracks || []).map((t) => [t.track_number, t.length]))
	);

	// Build a map of track episode assignments for browse view
	let trackEpisodeMap = $derived(
		Object.fromEntries(
			(job.tracks || [])
				.filter((t) => t.episode_number)
				.map((t) => [t.episode_number, t.track_number])
		)
	);

	async function handlePreview() {
		loading = true;
		error = null;
		result = null;
		applyFeedback = null;
		try {
			result = await tvdbMatch(job.job_id, {
				season: autoDetect ? null : Number(seasonInput) || null,
				tolerance: Number(toleranceInput) || 300,
				apply: false
			});
			// Select all matches by default
			selectedMatches = new Set(result.matches.map((m) => m.track_number));
		} catch (e) {
			error = e instanceof Error ? e.message : 'TVDB match failed';
		} finally {
			loading = false;
		}
	}

	async function handleApply() {
		if (!result || selectedCount === 0) return;
		applying = true;
		applyFeedback = null;
		try {
			await tvdbMatch(job.job_id, {
				season: result.season ?? null,
				tolerance: Number(toleranceInput) || 300,
				apply: true
			});
			applyFeedback = {
				type: 'success',
				message: `Applied ${result.matches.length} episode matches (S${String(result.season).padStart(2, '0')})`
			};
			onapply?.();
		} catch (e) {
			applyFeedback = {
				type: 'error',
				message: e instanceof Error ? e.message : 'Apply failed'
			};
		} finally {
			applying = false;
		}
	}

	function toggleMatch(trackNumber: string) {
		const next = new Set(selectedMatches);
		if (next.has(trackNumber)) {
			next.delete(trackNumber);
		} else {
			next.add(trackNumber);
		}
		selectedMatches = next;
	}

	function toggleAllMatches() {
		if (!result) return;
		if (selectedCount === result.matches.length) {
			selectedMatches = new Set();
		} else {
			selectedMatches = new Set(result.matches.map((m) => m.track_number));
		}
	}

	function switchToSeason(season: number) {
		autoDetect = false;
		seasonInput = String(season);
		handlePreview();
	}

	async function handleBrowse() {
		browseLoading = true;
		browseError = null;
		browseResult = null;
		try {
			browseResult = await fetchTvdbEpisodes(job.job_id, browseSeason);
		} catch (e) {
			browseError = e instanceof Error ? e.message : 'Failed to fetch episodes';
		} finally {
			browseLoading = false;
		}
	}

	function formatRuntime(seconds: number | null | undefined): string {
		if (!seconds) return '--';
		const m = Math.floor(seconds / 60);
		const s = seconds % 60;
		return `${m}:${String(s).padStart(2, '0')}`;
	}

	function formatDelta(trackLen: number | null, epRuntime: number): string {
		if (!trackLen) return '--';
		const delta = trackLen - epRuntime;
		const sign = delta >= 0 ? '+' : '';
		return `${sign}${delta}s`;
	}

	const btnBase =
		'rounded-lg px-3 py-1.5 text-sm font-medium disabled:opacity-50 transition-colors';
	const inputBase =
		'rounded-lg border border-primary/25 bg-primary/5 px-3 py-1.5 text-sm text-gray-900 focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary dark:border-primary/30 dark:bg-primary/10 dark:text-white';
	const tabBase =
		'px-3 py-1.5 text-sm font-medium rounded-t-lg border-b-2 transition-colors';
</script>

<div class="space-y-4">
	<!-- TVDB ID status -->
	<div class="flex items-center gap-2 text-sm">
		{#if job.tvdb_id}
			<span class="font-mono text-xs text-gray-500 dark:text-gray-400">TVDB {job.tvdb_id}</span>
		{:else}
			<span class="text-gray-400 dark:text-gray-500 italic">TVDB ID resolves on first match</span>
		{/if}
		{#if job.season_auto}
			<span
				class="rounded-sm bg-blue-100 px-1.5 py-0.5 text-[10px] font-semibold text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
			>
				Season {job.season_auto}
			</span>
		{/if}
	</div>

	<!-- Tab bar -->
	<div class="flex border-b border-gray-200 dark:border-gray-700">
		<button
			onclick={() => (activeTab = 'match')}
			class="{tabBase} {activeTab === 'match'
				? 'border-primary text-primary dark:text-primary'
				: 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'}"
		>
			Match Tracks
		</button>
		<button
			onclick={() => (activeTab = 'browse')}
			class="{tabBase} {activeTab === 'browse'
				? 'border-primary text-primary dark:text-primary'
				: 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'}"
		>
			Browse Episodes
		</button>
	</div>

	<!-- ===== MATCH TAB ===== -->
	{#if activeTab === 'match'}
		<!-- Controls -->
		<div class="flex flex-wrap items-end gap-3">
			<label class="flex items-center gap-2">
				<input
					type="checkbox"
					bind:checked={autoDetect}
					class="h-4 w-4 rounded-sm border-primary/25 text-primary focus:ring-primary dark:border-primary/30 dark:bg-primary/10"
				/>
				<span class="text-sm text-gray-700 dark:text-gray-300">Auto-detect season</span>
			</label>
			{#if !autoDetect}
				<label>
					<span class="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400"
						>Season</span
					>
					<input
						type="number"
						bind:value={seasonInput}
						min="1"
						class="w-20 {inputBase}"
					/>
				</label>
			{/if}
			<label>
				<span class="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400"
					>Tolerance (sec)</span
				>
				<input
					type="number"
					bind:value={toleranceInput}
					min="60"
					step="30"
					class="w-24 {inputBase}"
				/>
			</label>
			<button
				onclick={handlePreview}
				disabled={loading}
				class="{btnBase} bg-primary text-on-primary hover:bg-primary-hover dark:bg-primary dark:hover:bg-primary-hover"
			>
				{loading ? 'Matching...' : 'Preview Match'}
			</button>
		</div>

		{#if error}
			<p class="text-sm text-red-600 dark:text-red-400">{error}</p>
		{/if}

		<!-- Results -->
		{#if result}
			<div class="space-y-3">
				<!-- Summary -->
				<div class="flex flex-wrap items-center gap-3 text-sm">
					<span class="font-medium text-gray-900 dark:text-white">
						Season {result.season}: {result.match_count} match{result.match_count !== 1
							? 'es'
							: ''}
					</span>
					{#if result.score > 0}
						<span class="text-gray-500 dark:text-gray-400"
							>avg delta {result.score}s</span
						>
					{/if}
				</div>

				<!-- Alternative seasons (clickable to re-match) -->
				{#if result.alternatives.length > 0}
					<div class="flex flex-wrap items-center gap-1.5">
						<span
							class="text-xs font-medium text-gray-400 dark:text-gray-500"
							>Also try:</span
						>
						{#each result.alternatives as alt}
							{#if alt.match_count > 0}
								<button
									onclick={() => switchToSeason(alt.season)}
									class="rounded-md px-2 py-0.5 text-xs font-medium text-blue-700 ring-1 ring-blue-200 hover:bg-blue-50 dark:text-blue-400 dark:ring-blue-800 dark:hover:bg-blue-900/30 transition-colors"
								>
									S{String(alt.season).padStart(2, '0')} ({alt.match_count} match{alt.match_count !== 1 ? 'es' : ''})
								</button>
							{/if}
						{/each}
					</div>
				{/if}

				<!-- Match table -->
				{#if result.matches.length > 0}
					<div
						class="overflow-x-auto rounded-lg border border-primary/20 dark:border-primary/20"
					>
						<table class="w-full text-left text-sm">
							<thead
								class="bg-page text-gray-600 dark:bg-primary/5 dark:text-gray-400"
							>
								<tr>
									<th class="w-8 px-3 py-2">
										<input
											type="checkbox"
											checked={selectedCount === result.matches.length}
											onchange={toggleAllMatches}
											class="h-4 w-4 rounded-sm border-primary/25 text-primary focus:ring-primary dark:border-primary/30 dark:bg-primary/10"
										/>
									</th>
									<th class="px-3 py-2 font-medium">Track</th>
									<th class="px-3 py-2 font-medium">Track Length</th>
									<th class="px-3 py-2 font-medium">Episode</th>
									<th class="px-3 py-2 font-medium">Name</th>
									<th class="px-3 py-2 font-medium">TVDB Runtime</th>
									<th class="px-3 py-2 font-medium">Delta</th>
								</tr>
							</thead>
							<tbody class="divide-y divide-gray-200 dark:divide-gray-700">
								{#each result.matches as match}
									{@const trackLen =
										trackLengthMap[match.track_number] ?? null}
									{@const delta =
										trackLen != null
											? Math.abs(trackLen - match.episode_runtime)
											: null}
									{@const selected = selectedMatches.has(
										match.track_number
									)}
									<tr
										class="hover:bg-page dark:hover:bg-gray-800/50 {!selected
											? 'opacity-40'
											: ''}"
									>
										<td class="px-3 py-2">
											<input
												type="checkbox"
												checked={selected}
												onchange={() =>
													toggleMatch(match.track_number)}
												class="h-4 w-4 rounded-sm border-primary/25 text-primary focus:ring-primary dark:border-primary/30 dark:bg-primary/10"
											/>
										</td>
										<td class="px-3 py-2 font-mono"
											>{match.track_number}</td
										>
										<td class="px-3 py-2"
											>{formatRuntime(trackLen)}</td
										>
										<td class="px-3 py-2 font-medium"
											>S{String(result.season).padStart(
												2,
												'0'
											)}E{String(
												match.episode_number
											).padStart(2, '0')}</td
										>
										<td
											class="px-3 py-2 text-gray-900 dark:text-white"
											>{match.episode_name}</td
										>
										<td class="px-3 py-2"
											>{formatRuntime(
												match.episode_runtime
											)}</td
										>
										<td
											class="px-3 py-2 font-mono text-xs {delta !=
												null && delta < 60
												? 'text-green-600 dark:text-green-400'
												: delta != null && delta < 120
													? 'text-amber-600 dark:text-amber-400'
													: 'text-gray-500 dark:text-gray-400'}"
										>
											{formatDelta(trackLen, match.episode_runtime)}
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>

					<!-- Unmatched tracks -->
					{@const matchedTracks = new Set(
						result.matches.map((m) => m.track_number)
					)}
					{@const unmatchedTracks = (job.tracks || []).filter(
						(t) =>
							t.track_number &&
							!matchedTracks.has(t.track_number) &&
							(t.length ?? 0) >= 120
					)}
					{#if unmatchedTracks.length > 0}
						<p class="text-xs text-gray-400 dark:text-gray-500">
							Unmatched tracks: {unmatchedTracks
								.map(
									(t) =>
										`#${t.track_number} (${formatRuntime(t.length)})`
								)
								.join(', ')}
						</p>
					{/if}

					<!-- Apply button -->
					<div class="flex items-center gap-3">
						<button
							onclick={handleApply}
							disabled={applying || selectedCount === 0}
							class="{btnBase} bg-green-600 text-white hover:bg-green-700 dark:bg-green-500 dark:hover:bg-green-600"
						>
							{applying
								? 'Applying...'
								: `Apply ${selectedCount} Match${selectedCount !== 1 ? 'es' : ''}`}
						</button>
						{#if applyFeedback}
							<span
								class="text-xs {applyFeedback.type === 'success'
									? 'text-green-600 dark:text-green-400'
									: 'text-red-600 dark:text-red-400'}"
							>
								{applyFeedback.message}
							</span>
						{/if}
					</div>
				{:else}
					<p class="text-sm text-gray-400 dark:text-gray-500">
						No matches found. Try adjusting the tolerance or season.
					</p>
				{/if}
			</div>
		{/if}

	<!-- ===== BROWSE TAB ===== -->
	{:else if activeTab === 'browse'}
		<div class="flex flex-wrap items-end gap-3">
			<label>
				<span class="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400"
					>Season</span
				>
				<input
					type="number"
					bind:value={browseSeason}
					min="1"
					class="w-20 {inputBase}"
				/>
			</label>
			<button
				onclick={handleBrowse}
				disabled={browseLoading}
				class="{btnBase} bg-primary text-on-primary hover:bg-primary-hover dark:bg-primary dark:hover:bg-primary-hover"
			>
				{browseLoading ? 'Loading...' : 'Load Episodes'}
			</button>
		</div>

		{#if browseError}
			<p class="text-sm text-red-600 dark:text-red-400">{browseError}</p>
		{/if}

		{#if browseResult}
			<div class="space-y-2">
				<p class="text-xs text-gray-500 dark:text-gray-400">
					{browseResult.episodes.length} episode{browseResult.episodes.length !== 1 ? 's' : ''} in Season {browseResult.season}
					{#if browseResult.tvdb_id}
						<span class="font-mono">(TVDB {browseResult.tvdb_id})</span>
					{/if}
				</p>

				{#if browseResult.episodes.length > 0}
					<div
						class="overflow-x-auto rounded-lg border border-primary/20 dark:border-primary/20"
					>
						<table class="w-full text-left text-sm">
							<thead
								class="bg-page text-gray-600 dark:bg-primary/5 dark:text-gray-400"
							>
								<tr>
									<th class="px-3 py-2 font-medium w-16">#</th>
									<th class="px-3 py-2 font-medium">Episode Name</th>
									<th class="px-3 py-2 font-medium w-24">Runtime</th>
									<th class="px-3 py-2 font-medium w-24">Aired</th>
									<th class="px-3 py-2 font-medium w-24">Matched</th>
								</tr>
							</thead>
							<tbody
								class="divide-y divide-gray-200 dark:divide-gray-700"
							>
								{#each browseResult.episodes as ep}
									{@const matchedTrack = trackEpisodeMap[String(ep.number)]}
									<tr
										class="hover:bg-page dark:hover:bg-gray-800/50"
									>
										<td class="px-3 py-2 font-mono text-gray-500 dark:text-gray-400"
											>E{String(ep.number).padStart(2, '0')}</td
										>
										<td
											class="px-3 py-2 text-gray-900 dark:text-white"
											>{ep.name}</td
										>
										<td class="px-3 py-2"
											>{formatRuntime(ep.runtime)}</td
										>
										<td
											class="px-3 py-2 text-xs text-gray-500 dark:text-gray-400"
											>{ep.aired || '--'}</td
										>
										<td class="px-3 py-2">
											{#if matchedTrack}
												<span
													class="rounded-sm bg-green-100 px-1.5 py-0.5 text-[10px] font-semibold text-green-700 dark:bg-green-900/30 dark:text-green-400"
												>
													Track {matchedTrack}
												</span>
											{:else}
												<span class="text-xs text-gray-400">--</span>
											{/if}
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{:else}
					<p class="text-sm text-gray-400 dark:text-gray-500">
						No episodes found for this season.
					</p>
				{/if}
			</div>
		{/if}
	{/if}
</div>
