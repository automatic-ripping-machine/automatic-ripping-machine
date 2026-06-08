<script lang="ts">
	import type { JobSchema as Job, SearchResultSchema as SearchResult, MediaDetailSchema as MediaDetail, TitleUpdateRequest as TitleUpdate } from '$lib/types/api.gen';
	import { searchMetadata, fetchMediaDetail, updateJobTitle } from '$lib/api/jobs';
	import PosterImage from './PosterImage.svelte';

	interface Props {
		job: Job;
		onapply?: () => void;
		onapplydetail?: (d: { plot?: string | null }) => void;
		onepisodes?: () => void;
	}

	let { job, onapply, onapplydetail, onepisodes }: Props = $props();

	let query = $state(job.title || job.label || '');
	let yearInput = $state(job.year || '');
	let imdbInput = $state('');
	let searching = $state(false);
	let results = $state<SearchResult[]>([]);
	let searchError = $state<string | null>(null);

	let selectedImdb = $state<string | null>(null);
	let detail = $state<MediaDetail | null>(null);
	let loadingDetail = $state(false);

	let applying = $state(false);
	let feedback = $state<{ type: 'success' | 'error'; message: string; showEpisodes?: boolean } | null>(null);

	// Editable metadata fields (populated from detail)
	let editTitle = $state('');
	let editYear = $state('');
	let editType = $state<'movie' | 'series'>('movie');
	let editImdbId = $state('');
	let editPosterUrl = $state('');
	let editSeason = $state('');
	let editEpisode = $state('');

	$effect(() => {
		if (detail) {
			editTitle = detail.title;
			editYear = detail.year;
			editType = detail.media_type === 'series' ? 'series' : 'movie';
			editImdbId = detail.imdb_id ?? '';
			editPosterUrl = detail.poster_url ?? '';
			// Preserve existing season/episode when switching detail
			if (!editSeason) editSeason = job.season || job.season_auto || '';
			if (!editEpisode) editEpisode = job.episode || job.episode_auto || '';
		}
	});

	async function handleSearch() {
		const imdb = imdbInput.trim();
		if (imdb) {
			// Direct IMDb ID lookup — skip search
			searching = true;
			searchError = null;
			results = [];
			selectedImdb = null;
			detail = null;
			try {
				detail = await fetchMediaDetail(imdb);
				selectedImdb = imdb;
			} catch (e) {
				searchError = e instanceof Error ? e.message : 'IMDb lookup failed';
			} finally {
				searching = false;
			}
			return;
		}
		if (!query.trim()) return;
		searching = true;
		searchError = null;
		results = [];
		selectedImdb = null;
		detail = null;
		try {
			results = await searchMetadata(query.trim(), yearInput.trim() || undefined);
			if (results.length === 0) {
				searchError = 'No results found. Try a different search term.';
			}
		} catch (e) {
			searchError = e instanceof Error ? e.message : 'Search failed';
		} finally {
			searching = false;
		}
	}

	async function handleSelect(result: SearchResult) {
		if (!result.imdb_id) {
			// No IMDb ID — apply directly from search result
			detail = { ...result, plot: null, background_url: null };
			selectedImdb = null;
			return;
		}
		if (selectedImdb === result.imdb_id) {
			selectedImdb = null;
			detail = null;
			return;
		}
		selectedImdb = result.imdb_id;
		loadingDetail = true;
		detail = null;
		try {
			detail = await fetchMediaDetail(result.imdb_id);
		} catch {
			// Fall back to search result data
			detail = { ...result, plot: null, background_url: null };
		} finally {
			loadingDetail = false;
		}
	}

	async function applyTitle(data: Partial<TitleUpdate>) {
		applying = true;
		feedback = null;
		try {
			await updateJobTitle(job.job_id, data);
			const isSeries = data.video_type === 'series';
			feedback = { type: 'success', message: 'Title updated', showEpisodes: isSeries };
			onapply?.();
		} catch (e) {
			feedback = { type: 'error', message: e instanceof Error ? e.message : 'Update failed' };
		} finally {
			applying = false;
		}
	}

	function applyFromDetail() {
		if (!editTitle.trim()) return;
		const data: Partial<TitleUpdate> = {
			title: editTitle.trim(),
			year: editYear.trim() || undefined,
			video_type: editType,
			imdb_id: editImdbId.trim() || undefined,
			poster_url: editPosterUrl.trim() || undefined,
		};
		if (editType === 'series') {
			if (editSeason.trim()) data.season = editSeason.trim();
			if (editEpisode.trim()) data.episode = editEpisode.trim();
		}
		applyTitle(data);
		onapplydetail?.({ plot: detail?.plot });
	}

	function backToResults() {
		detail = null;
		selectedImdb = null;
	}

	function handleSearchKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') handleSearch();
	}

	const btnBase =
		'rounded-lg px-3 py-1.5 text-sm font-medium disabled:opacity-50 transition-colors';
	const inputBase =
		'rounded-lg border border-primary/25 bg-primary/5 px-3 py-1.5 text-sm text-gray-900 focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary dark:border-primary/30 dark:bg-primary/10 dark:text-white';
</script>

<div class="space-y-4">
	<!-- Search form -->
	<div class="flex flex-wrap gap-2">
		<input
			type="text"
			bind:value={query}
			onkeydown={handleSearchKeydown}
			onfocus={(e) => (e.target as HTMLInputElement).select()}
			placeholder="Title..."
			class="flex-1 min-w-[200px] {inputBase}"
		/>
		<input
			type="text"
			bind:value={yearInput}
			onkeydown={handleSearchKeydown}
			placeholder="Year"
			class="w-20 {inputBase}"
		/>
		<input
			type="text"
			bind:value={imdbInput}
			onkeydown={handleSearchKeydown}
			placeholder="IMDb ID (tt...)"
			class="w-36 {inputBase}"
		/>
		<button
			onclick={handleSearch}
			disabled={searching || (!query.trim() && !imdbInput.trim())}
			class="{btnBase} bg-primary text-on-primary hover:bg-primary-hover dark:bg-primary dark:hover:bg-primary-hover"
		>
			{searching ? 'Searching...' : 'Search'}
		</button>
		<span class="inline-flex items-center rounded-md px-1.5 py-0.5 text-[10px] font-semibold bg-gray-100 text-gray-500 dark:bg-gray-700/50 dark:text-gray-400" title="Metadata provider configured in Settings">
			OMDb/TMDb
		</span>
	</div>

	{#if searchError}
		{#if searchError.toLowerCase().includes('api key')}
			<div class="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:border-amber-600/40 dark:bg-amber-900/20 dark:text-amber-300">
				<p class="font-medium">{searchError}</p>
				<p class="mt-1 text-xs text-amber-600 dark:text-amber-400">Configure API keys in <a href="/settings" class="underline hover:no-underline">Settings</a>.</p>
			</div>
		{:else}
			<p class="text-sm text-gray-500 dark:text-gray-400">{searchError}</p>
		{/if}
	{/if}

	<!-- Results grid (hidden when detail is shown) -->
	{#if !detail && results.length > 0}
		<div class="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
			{#each results as result}
				<button
					onclick={() => handleSelect(result)}
					class="group flex flex-col overflow-hidden rounded-lg border text-left transition-all {selectedImdb === result.imdb_id
						? 'border-primary ring-2 ring-primary/30'
						: 'border-primary/20 hover:border-primary/40 dark:border-primary/20 dark:hover:border-primary/40'}"
				>
					{#if result.poster_url}
						<PosterImage url={result.poster_url} alt={result.title} class="aspect-[2/3] w-full object-cover" />
					{:else}
						<div
							class="flex aspect-[2/3] w-full items-center justify-center bg-primary/10 text-gray-400 dark:bg-primary/15"
						>
							<svg class="h-10 w-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="1.5"
									d="M15.75 10.5l4.72-4.72a.75.75 0 011.28.53v11.38a.75.75 0 01-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 002.25-2.25v-9a2.25 2.25 0 00-2.25-2.25h-9A2.25 2.25 0 002.25 7.5v9a2.25 2.25 0 002.25 2.25z"
								/>
							</svg>
						</div>
					{/if}
					<div class="p-2">
						<p
							class="text-sm font-medium text-gray-900 group-hover:text-primary-text dark:text-white dark:group-hover:text-primary-text-dark line-clamp-2"
						>
							{result.title}
						</p>
						<div class="mt-1 flex items-center gap-1.5">
							<span class="text-xs text-gray-500 dark:text-gray-400">{result.year}</span>
							<span
								class="rounded-sm px-1 py-0.5 text-[10px] font-medium uppercase {result.media_type === 'series'
									? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400'
									: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'}"
							>
								{result.media_type}
							</span>
						</div>
					</div>
				</button>
			{/each}
		</div>
	{/if}

	<!-- Detail panel with editable fields -->
	{#if loadingDetail}
		<div class="rounded-lg border border-primary/20 bg-page p-4 text-sm text-gray-500 dark:border-primary/20 dark:bg-page-dark dark:text-gray-400">
			Loading details...
		</div>
	{:else if detail}
		<div class="overflow-hidden rounded-lg border border-primary/20 dark:border-primary/20">
			{#if detail.background_url}
				<div
					class="relative h-40 bg-cover bg-center"
					style="background-image: url({detail.background_url})"
				>
					<div class="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent"></div>
				</div>
			{/if}
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
				<!-- Editable fields -->
				<div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
					<label class="sm:col-span-2">
						<span class="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">Title</span>
						<input type="text" bind:value={editTitle} class="w-full {inputBase}" />
					</label>
					<label>
						<span class="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">Year</span>
						<input type="text" bind:value={editYear} class="w-full {inputBase}" />
					</label>
					<label>
						<span class="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">Type</span>
						<select bind:value={editType} class="w-full {inputBase}">
							<option value="movie">Movie</option>
							<option value="series">Series</option>
						</select>
					</label>
					<label>
						<span class="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">IMDb ID</span>
						<input type="text" bind:value={editImdbId} placeholder="tt..." class="w-full {inputBase}" />
					</label>
					<label>
						<span class="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">Poster URL</span>
						<input type="text" bind:value={editPosterUrl} placeholder="https://..." class="w-full {inputBase}" />
					</label>
					{#if editType === 'series'}
						<label>
							<span class="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">Season</span>
							<input type="number" bind:value={editSeason} min="1" placeholder="1" class="w-full {inputBase}" />
						</label>
						<label>
							<span class="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">Episode</span>
							<input type="text" bind:value={editEpisode} placeholder="e.g. 1 or 1-6" class="w-full {inputBase}" />
						</label>
					{/if}
				</div>
				{#if detail.plot}
					<p class="text-sm text-gray-700 dark:text-gray-300">{detail.plot}</p>
				{/if}
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
						{#if feedback.showEpisodes && onepisodes}
							<button
								onclick={onepisodes}
								class="rounded-md bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-600"
							>
								Match Episodes
							</button>
						{/if}
					{/if}
				</div>
			</div>
		</div>
	{/if}
</div>
