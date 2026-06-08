<script lang="ts">
	import type { JobSchema as Job, Track, MusicSearchResultSchema as MusicSearchResult, MusicDetailSchema as MusicDetail, TitleUpdateRequest as TitleUpdate } from '$lib/types/api.gen';
	import { searchMusicMetadata, fetchMusicDetail, updateJobTitle, setJobTracks } from '$lib/api/jobs';
	import { posterSrc, posterFallback } from '$lib/utils/poster';

	interface Props {
		job: Job;
		discTracks?: Track[];
		onapply?: () => void;
	}

	let { job, discTracks = [], onapply }: Props = $props();

	let query = $state(job.album || job.title || job.label || '');
	let artistInput = $state(job.artist || '');
	let filterType = $state('');
	let filterFormat = $state('');
	let filterCountry = $state('');
	let filterStatus = $state('');
	let matchTrackCount = $state(discTracks.length > 0);
	let searching = $state(false);
	let loadingMore = $state(false);
	let results = $state<MusicSearchResult[]>([]);
	let totalResults = $state(0);
	let searchError = $state<string | null>(null);

	let selectedId = $state<string | null>(null);
	let detail = $state<MusicDetail | null>(null);
	let loadingDetail = $state(false);

	let applying = $state(false);
	let feedback = $state<{ type: 'success' | 'error'; message: string } | null>(null);

	// Track which poster URLs failed to load (Cover Art Archive may 404)
	let failedImages = $state(new Set<string>());

	// Track which cards are flipped to show tracklist on the back
	let flippedCards = $state(new Map<string, MusicDetail | 'loading'>());

	// Editable metadata fields (populated from detail)
	let editTitle = $state('');
	let editArtist = $state('');
	let editAlbum = $state('');
	let editYear = $state('');
	let editPosterUrl = $state('');

	$effect(() => {
		if (detail) {
			editTitle = detail.artist ? `${detail.artist} - ${detail.title}` : detail.title;
			editArtist = detail.artist || '';
			editAlbum = detail.title || '';
			editYear = detail.year;
			editPosterUrl = detail.poster_url ?? '';
		}
	});

	function currentFilters() {
		return {
			artist: artistInput.trim() || undefined,
			release_type: filterType || undefined,
			format: filterFormat || undefined,
			country: filterCountry.trim() || undefined,
			status: filterStatus || undefined,
			tracks: matchTrackCount && discTracks.length > 0 ? discTracks.length : undefined,
		};
	}

	async function handleSearch() {
		if (!query.trim()) return;
		searching = true;
		searchError = null;
		results = [];
		totalResults = 0;
		selectedId = null;
		detail = null;
		failedImages = new Set();
		flippedCards = new Map();
		try {
			const resp = await searchMusicMetadata(query.trim(), currentFilters());
			results = resp.results;
			totalResults = resp.total;
			if (results.length === 0) {
				searchError = 'No results found. Try a different search term.';
			}
		} catch (e) {
			searchError = e instanceof Error ? e.message : 'Search failed';
		} finally {
			searching = false;
		}
	}

	async function loadMore() {
		if (!query.trim() || loadingMore) return;
		loadingMore = true;
		try {
			const resp = await searchMusicMetadata(query.trim(), currentFilters(), results.length);
			results = [...results, ...resp.results];
			totalResults = resp.total;
		} catch (e) {
			searchError = e instanceof Error ? e.message : 'Failed to load more results';
		} finally {
			loadingMore = false;
		}
	}

	let hasMore = $derived(results.length < totalResults);

	async function handleSelect(result: MusicSearchResult) {
		if (selectedId === result.release_id) {
			selectedId = null;
			detail = null;
			return;
		}
		selectedId = result.release_id;
		loadingDetail = true;
		detail = null;
		try {
			detail = await fetchMusicDetail(result.release_id);
		} catch {
			// Fall back to search result data
			detail = { ...result, catalog_number: null, barcode: null, status: null, disc_count: null, tracks: [] };
		} finally {
			loadingDetail = false;
		}
	}

	async function applyTitle(data: Partial<TitleUpdate>) {
		applying = true;
		feedback = null;
		try {
			await updateJobTitle(job.job_id, data);
			// Save track listing if available (non-fatal — title is already saved)
			let tracksWarning = '';
			if (detail?.tracks?.length) {
				try {
					// For multi-disc releases, filter to the matching disc
					let tracksToApply = detail.tracks;
					if (job.disc_number && detail.disc_count && detail.disc_count > 1) {
						const discTracks_ = detail.tracks.filter(t => t.disc_number === job.disc_number);
						if (discTracks_.length > 0) {
							tracksToApply = discTracks_;
						}
					}
					await setJobTracks(
						job.job_id,
						tracksToApply.map((t, i) => ({
							track_number: t.number,
							title: t.title,
							length_ms: discTracks[i]?.length != null ? discTracks[i].length! * 1000 : (t.length_ms ?? null)
						}))
					);
				} catch {
					tracksWarning = ' (track names could not be saved)';
				}
			}
			feedback = { type: 'success', message: 'Title updated' + tracksWarning };
			onapply?.();
		} catch (e) {
			feedback = { type: 'error', message: e instanceof Error ? e.message : 'Update failed' };
		} finally {
			applying = false;
		}
	}

	function applyFromDetail() {
		if (!editTitle.trim()) return;
		applyTitle({
			title: editTitle.trim(),
			year: editYear.trim() || undefined,
			video_type: 'music',
			poster_url: editPosterUrl.trim() || undefined,
			artist: editArtist.trim() || undefined,
			album: editAlbum.trim() || undefined,
		});
	}

	function backToResults() {
		detail = null;
		selectedId = null;
	}

	function handleSearchKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') handleSearch();
	}

	async function toggleFlip(e: MouseEvent, result: MusicSearchResult) {
		e.stopPropagation();
		const id = result.release_id;
		if (flippedCards.has(id)) {
			const next = new Map(flippedCards);
			next.delete(id);
			flippedCards = next;
			return;
		}
		flippedCards = new Map(flippedCards).set(id, 'loading');
		try {
			const d = await fetchMusicDetail(id);
			flippedCards = new Map(flippedCards).set(id, d);
		} catch {
			flippedCards = new Map(flippedCards).set(id, {
				...result,
				catalog_number: null,
				barcode: null,
				status: null,
				disc_count: null,
				tracks: [],
			});
		}
	}

	function handleImgError(url: string) {
		failedImages = new Set(failedImages).add(url);
	}

	function hasValidPoster(url: string | null | undefined): boolean {
		return !!url && !failedImages.has(url);
	}

	function formatDuration(ms: number | null | undefined): string {
		if (!ms) return '--';
		const totalSec = Math.round(ms / 1000);
		const m = Math.floor(totalSec / 60);
		const s = totalSec % 60;
		return `${m}:${s.toString().padStart(2, '0')}`;
	}

	function formatDiscDuration(secs: number | null | undefined): string {
		if (!secs) return '--';
		const m = Math.floor(secs / 60);
		const s = secs % 60;
		return `${m}:${s.toString().padStart(2, '0')}`;
	}

	function compareDurations(discSecs: number | null | undefined, mbMs: number | null | undefined): 'match' | 'close' | 'mismatch' | 'unknown' {
		if (discSecs == null || mbMs == null) return 'unknown';
		const diff = Math.abs(discSecs - Math.round(mbMs / 1000));
		if (diff <= 3) return 'match';
		if (diff <= 10) return 'close';
		return 'mismatch';
	}

	let hasDiscTracks = $derived(discTracks.length > 0);

	// For multi-disc releases, filter detail tracks to the matching disc
	let filteredDetailTracks = $derived.by(() => {
		if (!detail?.tracks?.length) return [];
		if (job.disc_number && detail.disc_count && detail.disc_count > 1) {
			const filtered = detail.tracks.filter(t => t.disc_number === job.disc_number);
			if (filtered.length > 0) return filtered;
		}
		return detail.tracks;
	});

	let activeFilterCount = $derived(
		[filterType, filterFormat, filterCountry.trim(), filterStatus, matchTrackCount ? 'x' : ''].filter(Boolean).length
	);

	function clearFilters() {
		filterType = '';
		filterFormat = '';
		filterCountry = '';
		filterStatus = '';
		matchTrackCount = false;
	}

	const btnBase =
		'rounded-lg px-3 py-1.5 text-sm font-medium disabled:opacity-50 transition-colors';
	const inputBase =
		'rounded-lg border border-primary/25 bg-primary/5 px-3 py-1.5 text-sm text-gray-900 focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary dark:border-primary/30 dark:bg-primary/10 dark:text-white';
	const selectBase =
		'rounded-lg border border-primary/25 bg-primary/5 px-2 py-1.5 text-xs text-gray-900 focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary dark:border-primary/30 dark:bg-primary/10 dark:text-white';
</script>

<div class="space-y-4">
	<!-- Search panel -->
	<div class="rounded-lg border border-primary/20 bg-primary/[0.02] p-3 dark:border-primary/20 dark:bg-primary/[0.03]">
		<div class="flex flex-wrap items-end gap-2">
			<label class="min-w-[160px] flex-1">
				<span class="mb-0.5 block text-[10px] font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Album / Title</span>
				<input
					type="text"
					bind:value={query}
					onkeydown={handleSearchKeydown}
					onfocus={(e) => (e.target as HTMLInputElement).select()}
					placeholder="Album or title..."
					class="w-full {inputBase}"
				/>
			</label>
			<label>
				<span class="mb-0.5 block text-[10px] font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Artist</span>
				<input
					type="text"
					bind:value={artistInput}
					onkeydown={handleSearchKeydown}
					placeholder="Artist (optional)"
					class="w-36 {inputBase}"
				/>
			</label>
			<label>
				<span class="mb-0.5 block text-[10px] font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Type</span>
				<select bind:value={filterType} class="{selectBase}">
					<option value="">Any</option>
					<option value="album">Album</option>
					<option value="single">Single</option>
					<option value="ep">EP</option>
					<option value="compilation">Compilation</option>
					<option value="live">Live</option>
					<option value="soundtrack">Soundtrack</option>
				</select>
			</label>
			<label>
				<span class="mb-0.5 block text-[10px] font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Format</span>
				<select bind:value={filterFormat} class="{selectBase}">
					<option value="">Any</option>
					<option value="CD">CD</option>
					<option value="Vinyl">Vinyl</option>
					<option value="Digital Media">Digital</option>
					<option value="Cassette">Cassette</option>
					<option value="SACD">SACD</option>
				</select>
			</label>
			<label>
				<span class="mb-0.5 block text-[10px] font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Country</span>
				<input
					type="text"
					bind:value={filterCountry}
					onkeydown={handleSearchKeydown}
					placeholder="US, GB..."
					class="w-20 {selectBase}"
				/>
			</label>
			<label>
				<span class="mb-0.5 block text-[10px] font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Status</span>
				<select bind:value={filterStatus} class="{selectBase}">
					<option value="">Any</option>
					<option value="official">Official</option>
					<option value="promotional">Promotional</option>
					<option value="bootleg">Bootleg</option>
				</select>
			</label>
			{#if hasDiscTracks}
				<label class="flex items-center gap-1.5">
					<span class="mb-0.5 block text-[10px] font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">&nbsp;</span>
					<div class="flex items-center gap-1.5 py-[5px]">
						<input type="checkbox" bind:checked={matchTrackCount} class="h-3.5 w-3.5 rounded border-gray-300 text-primary focus:ring-primary" />
						<span class="text-xs text-gray-600 dark:text-gray-400">{discTracks.length} tracks</span>
					</div>
				</label>
			{/if}
			<div class="flex items-center gap-2">
				<span class="mb-0.5 block text-[10px]">&nbsp;</span>
				<button
					onclick={handleSearch}
					disabled={searching || !query.trim()}
					class="{btnBase} bg-primary text-on-primary hover:bg-primary-hover dark:bg-primary dark:hover:bg-primary-hover"
				>
					{searching ? 'Searching...' : 'Search'}
				</button>
				{#if activeFilterCount > 0}
					<button
						onclick={clearFilters}
						class="rounded-lg px-2 py-1.5 text-xs text-gray-500 hover:text-red-600 dark:text-gray-400 dark:hover:text-red-400"
					>
						Clear
					</button>
				{/if}
			</div>
		</div>
	</div>

	{#if searchError}
		<p class="text-sm text-gray-500 dark:text-gray-400">{searchError}</p>
	{/if}

	<!-- Results grid (hidden when detail is shown) -->
	{#if !detail && results.length > 0}
		<div class="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
			{#each results as result}
				{@const flipData = flippedCards.get(result.release_id)}
				{@const isFlipped = flippedCards.has(result.release_id)}
				<div style="perspective: 800px">
					<div
						class="relative" style="transform-style: preserve-3d; transition: transform 0.5s; {isFlipped ? 'transform: rotateY(180deg)' : ''}"
					>
						<!-- FRONT FACE -->
						<div class="relative" style="backface-visibility: hidden; transform: rotateY(0deg)">
							<button
								onclick={() => handleSelect(result)}
								class="group flex w-full flex-col overflow-hidden rounded-lg border text-left transition-all {selectedId === result.release_id
									? 'border-primary ring-2 ring-primary/30'
									: 'border-primary/20 hover:border-primary/40 dark:border-primary/20 dark:hover:border-primary/40'}"
							>
								<div class="relative aspect-square w-full">
									{#if hasValidPoster(result.poster_url)}
										<img
											src={posterSrc(result.poster_url)}
											alt={result.title}
											class="aspect-square w-full object-cover"
											loading="lazy"
											onerror={posterFallback}
										/>
									{:else}
										<div
											class="flex aspect-square w-full items-center justify-center bg-primary/10 text-gray-400 dark:bg-primary/15"
										>
											<svg class="h-10 w-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													stroke-width="1.5"
													d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"
												/>
											</svg>
										</div>
									{/if}
								</div>
								<div class="p-2">
									<p
										class="text-sm font-medium text-gray-900 group-hover:text-primary-text dark:text-white dark:group-hover:text-primary-text-dark line-clamp-2"
									>
										{result.title}
									</p>
									<p class="mt-0.5 text-xs text-gray-500 dark:text-gray-400 line-clamp-1">
										{result.artist}
									</p>
									<div class="mt-1 flex flex-wrap items-center gap-1">
										{#if result.year}
											<span class="text-xs text-gray-500 dark:text-gray-400">{result.year}</span>
										{/if}
										{#if result.release_type}
											<span class="rounded-sm bg-purple-100 px-1 py-0.5 text-[10px] font-medium text-purple-700 dark:bg-purple-900/30 dark:text-purple-400">
												{result.release_type}
											</span>
										{/if}
										{#if result.format}
											<span class="rounded-sm bg-green-100 px-1 py-0.5 text-[10px] font-medium text-green-700 dark:bg-green-900/30 dark:text-green-400">
												{result.format}
											</span>
										{/if}
										{#if result.country}
											<span class="rounded-sm bg-gray-100 px-1 py-0.5 text-[10px] font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-300">
												{result.country}
											</span>
										{/if}
										{#if result.track_count}
											<span class="rounded-sm bg-blue-100 px-1 py-0.5 text-[10px] font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
												{result.track_count} tracks
											</span>
										{/if}
									</div>
								</div>
							</button>
							{#if result.track_count}
								<button
									onclick={(e) => toggleFlip(e, result)}
									class="absolute top-2 right-2 z-10 flex items-center gap-1 rounded-md bg-black/60 px-1.5 py-0.5 text-[10px] font-medium text-white backdrop-blur-sm transition-colors hover:bg-black/80"
									title="Flip to see tracklist"
								>
									<svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
									</svg>
									{result.track_count} tracks
								</button>
							{/if}
						</div>

						<!-- BACK FACE -->
						<div
							class="absolute inset-0 flex flex-col overflow-hidden rounded-lg border border-primary/20 bg-white dark:border-primary/20 dark:bg-gray-900" style="backface-visibility: hidden; transform: rotateY(180deg)"
						>
							{#if flipData === 'loading'}
								<div class="flex h-full items-center justify-center text-sm text-gray-500 dark:text-gray-400">
									<svg class="mr-2 h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
										<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
										<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
									</svg>
									Loading tracks...
								</div>
							{:else if flipData && flipData.tracks && flipData.tracks.length > 0}
								<!-- Compact header -->
								<div class="flex items-center gap-2 border-b border-primary/15 p-2 dark:border-primary/20">
									{#if hasValidPoster(flipData.poster_url)}
										<img src={posterSrc(flipData.poster_url)} alt="" class="h-8 w-8 shrink-0 rounded object-cover" onerror={posterFallback} />
									{/if}
									<div class="min-w-0 flex-1">
										<p class="truncate text-xs font-semibold text-gray-900 dark:text-white">{flipData.title}</p>
										<p class="truncate text-[10px] text-gray-500 dark:text-gray-400">{flipData.artist}</p>
									</div>
								</div>
								<!-- Scrollable track list -->
								<div class="min-h-0 flex-1 overflow-y-auto">
									<table class="w-full text-[11px]">
										<tbody>
											{#each flipData.tracks as track, i}
												{@const discTrack = hasDiscTracks ? (discTracks[i] ?? null) : null}
												{@const match = hasDiscTracks ? compareDurations(discTrack?.length ?? null, track.length_ms) : null}
												<tr class="border-b border-gray-100 last:border-0 dark:border-gray-800">
													<td class="w-6 py-0.5 pl-2 pr-1 text-right font-mono text-gray-400 dark:text-gray-500">{track.number}</td>
													<td class="max-w-0 truncate py-0.5 pr-1 text-gray-700 dark:text-gray-300">{track.title}</td>
													<td class="w-10 whitespace-nowrap py-0.5 pr-1 text-right font-mono text-gray-400 dark:text-gray-500">{formatDuration(track.length_ms)}</td>
													{#if hasDiscTracks}
														<td class="w-4 py-0.5 pr-1 text-center">
															{#if match === 'match'}
																<span class="text-green-600 dark:text-green-400">&#10003;</span>
															{:else if match === 'close'}
																<span class="text-yellow-600 dark:text-yellow-400">~</span>
															{:else if match === 'mismatch'}
																<span class="text-red-600 dark:text-red-400">&#10007;</span>
															{/if}
														</td>
													{/if}
												</tr>
											{/each}
										</tbody>
									</table>
								</div>
							{:else}
								<div class="flex h-full items-center justify-center text-xs text-gray-400 dark:text-gray-500">
									No track data available
								</div>
							{/if}
							<!-- Flip-back button -->
							<button
								onclick={(e) => toggleFlip(e, result)}
								class="absolute top-2 right-2 z-10 flex items-center gap-1 rounded-md bg-black/60 px-1.5 py-0.5 text-[10px] font-medium text-white backdrop-blur-sm transition-colors hover:bg-black/80"
								title="Flip back"
							>
								<svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
								</svg>
								Back
							</button>
						</div>
					</div>
				</div>
			{/each}
		</div>
		{#if hasMore}
			<div class="flex items-center justify-center gap-3 pt-1">
				<button
					onclick={loadMore}
					disabled={loadingMore}
					class="{btnBase} border border-primary/25 text-primary hover:bg-primary/10 dark:border-primary/30 dark:text-primary dark:hover:bg-primary/15"
				>
					{loadingMore ? 'Loading...' : 'Load More'}
				</button>
				<span class="text-xs text-gray-500 dark:text-gray-400">
					Showing {results.length} of {totalResults}
				</span>
			</div>
		{/if}
	{/if}

	<!-- Detail panel with editable fields -->
	{#if loadingDetail}
		<div class="rounded-lg border border-primary/20 bg-page p-4 text-sm text-gray-500 dark:border-primary/20 dark:bg-page-dark dark:text-gray-400">
			Loading details...
		</div>
	{:else if detail}
		<div class="overflow-hidden rounded-lg border border-primary/20 dark:border-primary/20">
			<div class="space-y-3 p-4">
				{#if results.length > 0}
					<button
						onclick={backToResults}
						class="inline-flex items-center gap-1 text-sm text-primary hover:text-primary-hover dark:text-primary dark:hover:text-primary-hover"
					>
						<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
						</svg>
						Back to results
					</button>
				{/if}

				<!-- Album art + info summary -->
				<div class="flex gap-4">
					<div class="relative h-28 w-28 shrink-0 overflow-hidden rounded-md">
						{#if hasValidPoster(detail.poster_url)}
							<img
								src={posterSrc(detail.poster_url)}
								alt={detail.title}
								class="h-full w-full object-cover"
								onerror={posterFallback}
							/>
						{:else}
							<div
								class="flex h-full w-full items-center justify-center bg-primary/10 text-gray-400 dark:bg-primary/15"
							>
								<svg class="h-10 w-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="1.5"
										d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"
									/>
								</svg>
							</div>
						{/if}
					</div>
					<div class="min-w-0 flex-1">
						<p class="text-lg font-semibold text-gray-900 dark:text-white">{detail.title}</p>
						<p class="text-sm text-gray-600 dark:text-gray-300">{detail.artist}</p>
						<div class="mt-1.5 flex flex-wrap items-center gap-1.5">
							{#if detail.year}
								<span class="text-xs text-gray-500 dark:text-gray-400">{detail.year}</span>
							{/if}
							{#if detail.release_type}
								<span class="rounded-sm bg-purple-100 px-1 py-0.5 text-[10px] font-medium text-purple-700 dark:bg-purple-900/30 dark:text-purple-400">{detail.release_type}</span>
							{/if}
							{#if detail.format}
								<span class="rounded-sm bg-green-100 px-1 py-0.5 text-[10px] font-medium text-green-700 dark:bg-green-900/30 dark:text-green-400">{detail.format}</span>
							{/if}
							{#if detail.status}
								<span class="rounded-sm bg-blue-100 px-1 py-0.5 text-[10px] font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">{detail.status}</span>
							{/if}
							{#if detail.country}
								<span class="rounded-sm bg-gray-100 px-1 py-0.5 text-[10px] font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-300">{detail.country}</span>
							{/if}
						</div>
						<div class="mt-1.5 flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-gray-500 dark:text-gray-400">
							{#if detail.label}
								<span>Label: {detail.label}</span>
							{/if}
							{#if detail.catalog_number}
								<span>Cat#: <span class="font-mono">{detail.catalog_number}</span></span>
							{/if}
							{#if detail.barcode}
								<span>Barcode: <span class="font-mono">{detail.barcode}</span></span>
							{/if}
							{#if detail.track_count}
								<span>{filteredDetailTracks.length !== detail.track_count ? `${filteredDetailTracks.length} / ${detail.track_count}` : detail.track_count} tracks</span>
							{/if}
						</div>
					</div>
				</div>

				<!-- Track listing / comparison -->
				{#if filteredDetailTracks.length > 0}
					<div>
						<h4 class="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
							{hasDiscTracks ? 'Track Comparison' : 'Track Listing'}{detail.disc_count && detail.disc_count > 1 && job.disc_number ? ` (Disc ${job.disc_number} of ${detail.disc_count})` : ''}
						</h4>
						<div class="overflow-x-auto rounded-md border border-primary/15 dark:border-primary/20">
							<table class="w-full text-left text-xs">
								<thead class="bg-page text-gray-500 dark:bg-primary/5 dark:text-gray-400">
									<tr>
										<th class="w-10 px-3 py-1.5 font-medium">#</th>
										<th class="px-3 py-1.5 font-medium">Title</th>
										{#if hasDiscTracks}
											<th class="w-16 px-3 py-1.5 font-medium text-right">Disc Length</th>
										{/if}
										<th class="w-16 px-3 py-1.5 font-medium text-right">{hasDiscTracks ? 'Match Length' : 'Duration'}</th>
										{#if hasDiscTracks}
											<th class="w-12 px-3 py-1.5 font-medium text-center">Match</th>
										{/if}
									</tr>
								</thead>
								<tbody class="divide-y divide-gray-100 dark:divide-gray-700/50">
									{#each filteredDetailTracks as track, i}
										{@const discTrack = hasDiscTracks ? discTracks[i] ?? null : null}
										{@const match = hasDiscTracks ? compareDurations(discTrack?.length ?? null, track.length_ms) : null}
										<tr>
											<td class="px-3 py-1.5 font-mono text-gray-500 dark:text-gray-400">{track.number}</td>
											<td class="px-3 py-1.5 text-gray-700 dark:text-gray-300">{track.title}</td>
											{#if hasDiscTracks}
												<td class="px-3 py-1.5 text-right font-mono text-gray-500 dark:text-gray-400">
													{discTrack ? formatDiscDuration(discTrack.length) : '--'}
												</td>
											{/if}
											<td class="px-3 py-1.5 text-right font-mono text-gray-500 dark:text-gray-400">{formatDuration(track.length_ms)}</td>
											{#if hasDiscTracks}
												<td class="px-3 py-1.5 text-center">
													{#if match === 'match'}
														<span class="text-green-600 dark:text-green-400" title="Match (within 3s)">&#10003;</span>
													{:else if match === 'close'}
														<span class="text-yellow-600 dark:text-yellow-400" title="Close (within 10s)">~</span>
													{:else if match === 'mismatch'}
														<span class="text-red-600 dark:text-red-400" title="Mismatch (>10s)">&#10007;</span>
													{:else}
														<span class="text-gray-400 dark:text-gray-500">--</span>
													{/if}
												</td>
											{/if}
										</tr>
									{/each}
								</tbody>
								{#if hasDiscTracks}
									{@const discTotal = discTracks.reduce((sum, t) => sum + (t.length ?? 0), 0)}
									{@const mbTotal = filteredDetailTracks.reduce((sum, t) => sum + (t.length_ms ?? 0), 0)}
									{@const totalMatch = compareDurations(discTotal, mbTotal)}
									<tfoot class="border-t border-gray-200 bg-page font-medium dark:border-gray-600 dark:bg-primary/5">
										<tr>
											<td class="px-3 py-1.5 text-gray-700 dark:text-gray-300">Total</td>
											<td class="px-3 py-1.5"></td>
											<td class="px-3 py-1.5 text-right font-mono text-gray-700 dark:text-gray-300">{formatDiscDuration(discTotal)}</td>
											<td class="px-3 py-1.5 text-right font-mono text-gray-700 dark:text-gray-300">{formatDuration(mbTotal)}</td>
											<td class="px-3 py-1.5 text-center">
												{#if totalMatch === 'match'}
													<span class="text-green-600 dark:text-green-400">&#10003;</span>
												{:else if totalMatch === 'close'}
													<span class="text-yellow-600 dark:text-yellow-400">~</span>
												{:else if totalMatch === 'mismatch'}
													<span class="text-red-600 dark:text-red-400">&#10007;</span>
												{:else}
													<span class="text-gray-400 dark:text-gray-500">--</span>
												{/if}
											</td>
										</tr>
									</tfoot>
								{/if}
							</table>
						</div>
					</div>
				{/if}

				<!-- Editable fields -->
				<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
					<label>
						<span class="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">Artist</span>
						<input type="text" bind:value={editArtist} class="w-full {inputBase}" />
					</label>
					<label>
						<span class="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">Album</span>
						<input type="text" bind:value={editAlbum} class="w-full {inputBase}" />
					</label>
					<label class="sm:col-span-2">
						<span class="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">Title</span>
						<input type="text" bind:value={editTitle} class="w-full {inputBase}" />
					</label>
					<label>
						<span class="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">Year</span>
						<input type="text" bind:value={editYear} class="w-full {inputBase}" />
					</label>
					<label>
						<span class="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">Poster URL</span>
						<input type="text" bind:value={editPosterUrl} placeholder="https://..." class="w-full {inputBase}" />
					</label>
				</div>
				<div class="flex items-center gap-2">
					<button
						onclick={applyFromDetail}
						disabled={applying || !editTitle.trim()}
						class="{btnBase} bg-green-600 text-white hover:bg-green-700 dark:bg-green-500 dark:hover:bg-green-600"
					>
						{applying ? 'Applying...' : 'Apply This Title'}
					</button>
					{#if feedback}
						<span
							class="text-xs {feedback.type === 'success'
								? 'text-green-600 dark:text-green-400'
								: 'text-red-600 dark:text-red-400'}"
						>
							{feedback.message}
						</span>
					{/if}
				</div>
			</div>
		</div>
	{/if}
</div>
