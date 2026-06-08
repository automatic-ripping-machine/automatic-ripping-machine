<script lang="ts">
	import { scanFolder, createFolderJob, scanIso, createIsoJob } from '$lib/api/import-jobs';
	import type { IsoScanResult } from '$lib/api/import-jobs';
	import { searchMetadata, fetchMediaDetail } from '$lib/api/jobs';
	import type { FolderScanResult, SearchResultSchema as SearchResult, MediaDetailSchema as MediaDetail, FolderCreateRequest } from '$lib/types/api.gen';
	import IngressBrowser from '$lib/components/IngressBrowser.svelte';

	import PosterImage from './PosterImage.svelte';

	interface Props {
		open: boolean;
		onclose: () => void;
		oncreated: () => void;
	}

	let { open, onclose, oncreated }: Props = $props();

	// Wizard state
	let step = $state(1);
	let selectedPath = $state('');
	let selectedKind = $state<'dir' | 'iso'>('dir');
	let scanning = $state(false);
	let scanError = $state<string | null>(null);
	// Unified scan result: holds either FolderScanResult or IsoScanResult.
	// We keep it loose because callers branch on selectedKind to read fields.
	let scanResult = $state<FolderScanResult | IsoScanResult | null>(null);

	// Step 2 editable fields
	let editTitle = $state('');
	let editYear = $state('');
	let editType = $state<'movie' | 'series'>('movie');
	let editImdbId = $state('');
	let editPosterUrl = $state('');
	let editSeason = $state('');
	let editDiscNumber = $state('');
	let editDiscTotal = $state('');

	// Search state
	let searchQuery = $state('');
	let searching = $state(false);
	let searchResults = $state<SearchResult[]>([]);
	let searchError = $state<string | null>(null);
	let loadingDetail = $state(false);
	let detail = $state<MediaDetail | null>(null);

	// Step 3
	let importing = $state(false);
	let importError = $state<string | null>(null);

	const inputBase =
		'rounded-lg border border-primary/25 bg-primary/5 px-3 py-1.5 text-sm text-gray-900 focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary dark:border-primary/30 dark:bg-primary/10 dark:text-white';
	const btnBase =
		'rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-50 transition-colors';

	function formatSize(bytes: number): string {
		if (bytes === 0) return '0 B';
		const units = ['B', 'KB', 'MB', 'GB', 'TB'];
		const i = Math.floor(Math.log(bytes) / Math.log(1024));
		return `${(bytes / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0)} ${units[i]}`;
	}

	function reset() {
		step = 1;
		selectedPath = '';
		selectedKind = 'dir';
		scanning = false;
		scanError = null;
		scanResult = null;
		editTitle = '';
		editYear = '';
		editType = 'movie';
		editImdbId = '';
		editPosterUrl = '';
		searchQuery = '';
		searching = false;
		searchResults = [];
		searchError = null;
		loadingDetail = false;
		detail = null;
		importing = false;
		importError = null;
	}

	function handleClose() {
		reset();
		onclose();
	}

	function handleSelect(selection: { path: string; kind: 'dir' | 'iso' }) {
		selectedPath = selection.path;
		selectedKind = selection.kind;
	}

	// Convenience accessors for fields that differ between FolderScanResult and IsoScanResult.
	function scanFolderSize(r: FolderScanResult | IsoScanResult | null): number {
		if (!r) return 0;
		if ('iso_size' in r && typeof r.iso_size === 'number') return r.iso_size;
		if ('folder_size_bytes' in r && typeof r.folder_size_bytes === 'number') return r.folder_size_bytes;
		return 0;
	}

	function scanVolumeId(r: FolderScanResult | IsoScanResult | null): string | null {
		if (!r) return null;
		if ('volume_id' in r) return (r as IsoScanResult).volume_id ?? null;
		return null;
	}

	async function goToStep2() {
		if (!selectedPath) return;
		scanning = true;
		scanError = null;
		try {
			const result = selectedKind === 'iso'
				? await scanIso(selectedPath)
				: await scanFolder(selectedPath);
			scanResult = result;
			editTitle = result.title_suggestion ?? '';
			editYear = result.year_suggestion || '';
			editType = 'movie';
			editImdbId = '';
			editPosterUrl = '';
			// Folder-only fields (season/disc) only exist on FolderScanResult.
			if (selectedKind === 'dir' && 'season' in result) {
				const folderResult = result as FolderScanResult;
				editSeason = folderResult.season?.toString() || '';
				editDiscNumber = folderResult.disc_number?.toString() || '';
				editDiscTotal = folderResult.disc_total?.toString() || '';
			} else {
				editSeason = '';
				editDiscNumber = '';
				editDiscTotal = '';
			}
			searchQuery = result.title_suggestion ?? '';
			searchResults = [];
			searchError = null;
			detail = null;
			step = 2;
		} catch (e) {
			scanError = e instanceof Error ? e.message : 'Scan failed';
		} finally {
			scanning = false;
		}
	}

	async function handleSearch() {
		if (!searchQuery.trim()) return;
		searching = true;
		searchError = null;
		searchResults = [];
		detail = null;
		try {
			searchResults = await searchMetadata(searchQuery.trim(), editYear.trim() || undefined);
			if (searchResults.length === 0) {
				searchError = 'No results found.';
			}
		} catch (e) {
			searchError = e instanceof Error ? e.message : 'Search failed';
		} finally {
			searching = false;
		}
	}

	async function goToOmdbStep() {
		// Re-seed the search with the current title so a user who edited
		// the metadata on step 2 lands on results matching that edit.
		searchQuery = editTitle.trim() || searchQuery;
		step = 3;
		if (searchResults.length === 0 && !searching && searchQuery.trim()) {
			await handleSearch();
		}
	}

	async function handleSelectResult(result: SearchResult) {
		if (result.imdb_id) {
			loadingDetail = true;
			try {
				detail = await fetchMediaDetail(result.imdb_id);
				editTitle = detail.title;
				editYear = detail.year;
				editType = detail.media_type === 'series' ? 'series' : 'movie';
				editImdbId = detail.imdb_id ?? '';
				editPosterUrl = detail.poster_url ?? '';
			} catch {
				// Fall back to search result
				editTitle = result.title;
				editYear = result.year;
				editType = result.media_type === 'series' ? 'series' : 'movie';
				editImdbId = result.imdb_id ?? '';
				editPosterUrl = result.poster_url ?? '';
			} finally {
				loadingDetail = false;
			}
		} else {
			editTitle = result.title;
			editYear = result.year;
			editType = result.media_type === 'series' ? 'series' : 'movie';
			editPosterUrl = result.poster_url ?? '';
		}
	}

	function handleSearchKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') handleSearch();
	}

	async function handleImport() {
		if (!scanResult) return;
		importing = true;
		importError = null;
		try {
			const common = {
				source_path: selectedPath,
				title: editTitle.trim(),
				year: editYear.trim() || null,
				video_type: editType,
				disctype: scanResult.disc_type ?? '',
				imdb_id: editImdbId.trim() || null,
				poster_url: editPosterUrl.trim() || null,
				season: editSeason ? Number(editSeason) : null,
				disc_number: editDiscNumber ? Number(editDiscNumber) : null,
				disc_total: editDiscTotal ? Number(editDiscTotal) : null,
			};
			if (selectedKind === 'iso') {
				await createIsoJob(common);
			} else {
				await createFolderJob(common as FolderCreateRequest);
			}
			reset();
			oncreated();
		} catch (e) {
			importError = e instanceof Error ? e.message : 'Import failed';
		} finally {
			importing = false;
		}
	}
</script>

{#if open}
	<div class="fixed inset-0 z-50 flex items-end sm:items-center sm:justify-center">
		<!-- Backdrop -->
		<button
			type="button"
			class="absolute inset-0 bg-black/50"
			aria-label="Close dialog"
			onclick={handleClose}
		></button>

		<!-- Dialog -->
		<div class="relative z-10 flex h-full w-full flex-col bg-surface shadow-xl dark:bg-surface-dark sm:h-[75vh] sm:max-w-2xl sm:rounded-lg">
			<!-- Header -->
			<div class="flex items-center justify-between border-b border-primary/20 px-6 py-3 dark:border-primary/20">
				<h3 class="text-lg font-semibold text-gray-900 dark:text-white">Import</h3>
				<button
					type="button"
					onclick={handleClose}
					class="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-300"
					aria-label="Close"
				>
					<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>

			<!-- Body -->
			<div class="flex min-h-0 flex-1 flex-col px-6 py-4">
				{#if step === 1}
					<!-- Step 1: Pick Source -->
					{#if scanError}
						<div class="mb-2 shrink-0 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
							{scanError}
						</div>
					{/if}
					<IngressBrowser onselect={handleSelect} />

				{:else if step === 2}
					<!-- Step 2: Verify metadata -->
					{#if scanResult}
						<div class="min-h-0 flex-1 overflow-y-auto">
							<!-- Source block header -->
							<h4 class="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">Source</h4>
							<!-- Scan info badges -->
							<div class="mb-3 flex flex-wrap gap-3 text-sm">
								<span class="rounded-sm bg-blue-100 px-2 py-0.5 font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
									{(scanResult.disc_type ?? 'unknown').toUpperCase()}
								</span>
								<span class="text-gray-500 dark:text-gray-400">{formatSize(scanFolderSize(scanResult))}</span>
								<span class="text-gray-500 dark:text-gray-400">{scanResult.stream_count} streams</span>
								<span class="text-gray-500 dark:text-gray-400">Label: {scanResult.label}</span>
								{#if selectedKind === 'iso' && scanVolumeId(scanResult)}
									<span class="w-full text-xs text-gray-500 dark:text-gray-400">Volume ID: <span class="font-mono">{scanVolumeId(scanResult)}</span></span>
								{/if}
							</div>

							<!-- Poster preview + editable fields -->
							<div class="flex gap-4">
								{#if editPosterUrl}
									<PosterImage
										url={editPosterUrl}
										alt={editTitle}
										class="h-36 w-24 shrink-0 rounded-md object-cover"
									/>
								{:else}
									<div class="flex h-36 w-24 shrink-0 items-center justify-center rounded-md bg-primary/10 text-gray-400 dark:bg-primary/15">
										<svg class="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15.75 10.5l4.72-4.72a.75.75 0 011.28.53v11.38a.75.75 0 01-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 002.25-2.25v-9a2.25 2.25 0 00-2.25-2.25h-9A2.25 2.25 0 002.25 7.5v9a2.25 2.25 0 002.25 2.25z" />
										</svg>
									</div>
								{/if}
								<div class="grid flex-1 grid-cols-2 gap-3">
									<label class="col-span-2">
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
									<label class="col-span-2">
										<span class="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">IMDb ID</span>
										<input type="text" bind:value={editImdbId} placeholder="tt..." class="w-full {inputBase}" />
									</label>
									<label>
										<span class="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">Season</span>
										<input type="number" bind:value={editSeason} min="1" placeholder="-" class="w-full {inputBase}" />
									</label>
									<label>
										<span class="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">Disc</span>
										<div class="flex items-center gap-1">
											<input type="number" bind:value={editDiscNumber} min="1" placeholder="-" class="w-full {inputBase}" />
											<span class="text-xs text-gray-400">of</span>
											<input type="number" bind:value={editDiscTotal} min="1" placeholder="-" class="w-full {inputBase}" />
										</div>
									</label>
								</div>
							</div>
						</div>
					{/if}

				{:else if step === 3}
					<!-- Step 3: OMDB Match -->
					<div class="flex min-h-0 flex-1 flex-col">
						<div class="shrink-0 space-y-3 pb-3">
							<p class="text-sm text-gray-500 dark:text-gray-400">
								Search OMDB to refine the auto-detected metadata. Selecting a result fills in the title, year, type, IMDb ID, and poster.
							</p>
							<div class="flex gap-2">
								<input
									type="text"
									bind:value={searchQuery}
									onkeydown={handleSearchKeydown}
									placeholder="Search title..."
									class="flex-1 {inputBase}"
								/>
								<button
									type="button"
									onclick={handleSearch}
									disabled={searching || !searchQuery.trim()}
									class="{btnBase} bg-primary text-on-primary hover:bg-primary/90"
								>
									{searching ? 'Searching...' : 'Search'}
								</button>
							</div>

							{#if searchError}
								<p class="text-sm text-gray-500 dark:text-gray-400">{searchError}</p>
							{/if}

							{#if loadingDetail}
								<p class="text-sm text-gray-400">Loading details...</p>
							{/if}
						</div>

						<div class="min-h-0 flex-1 overflow-y-auto">
							{#if searchResults.length > 0}
								<div class="grid grid-cols-3 gap-2 sm:grid-cols-4">
									{#each searchResults as result}
										<button
											type="button"
											onclick={() => handleSelectResult(result)}
											class="flex flex-col overflow-hidden rounded-lg border text-left transition-all {result.imdb_id && result.imdb_id === editImdbId ? 'border-primary ring-2 ring-primary' : 'border-primary/20 hover:border-primary/40 dark:border-primary/20 dark:hover:border-primary/40'}"
										>
											{#if result.poster_url}
												<PosterImage
													url={result.poster_url}
													alt={result.title}
													class="aspect-[2/3] w-full object-cover"
												/>
											{:else}
												<div class="flex aspect-[2/3] w-full items-center justify-center bg-primary/10 text-gray-400 dark:bg-primary/15">
													<svg class="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
														<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15.75 10.5l4.72-4.72a.75.75 0 011.28.53v11.38a.75.75 0 01-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 002.25-2.25v-9a2.25 2.25 0 00-2.25-2.25h-9A2.25 2.25 0 002.25 7.5v9a2.25 2.25 0 002.25 2.25z" />
													</svg>
												</div>
											{/if}
											<div class="p-1.5">
												<p class="text-xs font-medium text-gray-900 dark:text-white line-clamp-2">{result.title}</p>
												<span class="text-[10px] text-gray-500 dark:text-gray-400">{result.year}</span>
											</div>
										</button>
									{/each}
								</div>
							{/if}
						</div>
					</div>

				{:else if step === 4}
					<!-- Step 4: Confirm -->
					<!-- Pinned: summary card -->
					<div class="shrink-0 rounded-lg border border-primary/20 p-4 dark:border-primary/20">
						<div class="flex gap-4">
							{#if editPosterUrl}
								<PosterImage
									url={editPosterUrl}
									alt={editTitle}
									class="h-40 w-28 shrink-0 rounded-md object-cover"
								/>
							{:else}
								<div class="flex h-40 w-28 shrink-0 items-center justify-center rounded-md bg-primary/10 text-gray-400 dark:bg-primary/15">
									<svg class="h-10 w-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15.75 10.5l4.72-4.72a.75.75 0 011.28.53v11.38a.75.75 0 01-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 002.25-2.25v-9a2.25 2.25 0 00-2.25-2.25h-9A2.25 2.25 0 002.25 7.5v9a2.25 2.25 0 002.25 2.25z" />
									</svg>
								</div>
							{/if}
							<div class="space-y-2 text-sm">
								<h4 class="text-lg font-semibold text-gray-900 dark:text-white">{editTitle}</h4>
								{#if editYear}
									<p class="text-gray-500 dark:text-gray-400">{editYear}</p>
								{/if}
								<div class="flex flex-wrap gap-2">
									<span class="rounded-sm bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-400">
										{editType}
									</span>
									{#if scanResult}
										<span class="rounded-sm bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
											{(scanResult.disc_type ?? 'unknown').toUpperCase()}
										</span>
									{/if}
								</div>
								{#if editImdbId}
									<p class="text-xs text-gray-500 dark:text-gray-400">IMDb: {editImdbId}</p>
								{/if}
							</div>
						</div>
					</div>

					<!-- Scrollable: source path + errors -->
					<div class="min-h-0 flex-1 overflow-y-auto pt-4">
						<div class="space-y-3 text-sm text-gray-500 dark:text-gray-400">
							<div class="flex items-center gap-2">
								<svg class="h-4 w-4 shrink-0 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
								</svg>
								<span>Source: <span class="font-medium text-gray-700 dark:text-gray-300">{selectedPath}</span></span>
							</div>
							{#if editSeason}
								<p>Season {editSeason}{#if editDiscNumber}, Disc {editDiscNumber}{#if editDiscTotal} of {editDiscTotal}{/if}{/if}</p>
							{/if}
						</div>
						{#if importError}
							<div class="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
								{importError}
							</div>
						{/if}
					</div>
				{/if}
			</div>

			<!-- Footer -->
			<div class="flex items-center justify-between border-t border-primary/20 px-6 py-3 dark:border-primary/20">
				<div class="w-20">
					{#if step > 1}
						<button
							type="button"
							onclick={() => step--}
							class="rounded-lg px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
						>
							Back
						</button>
					{/if}
				</div>
				<!-- Progress dots -->
				<div class="flex items-center gap-2">
					{#each [1, 2, 3, 4] as s}
						<div
							class="h-2 w-2 rounded-full transition-colors {s === step
								? 'bg-primary'
								: s < step
									? 'bg-primary/50'
									: 'bg-gray-300 dark:bg-gray-600'}"
						></div>
					{/each}
				</div>
				<div class="flex justify-end gap-2">
					{#if step === 1}
						<button
							type="button"
							onclick={goToStep2}
							disabled={!selectedPath || scanning}
							class="{btnBase} bg-primary text-on-primary hover:bg-primary/90"
						>
							{scanning ? 'Scanning...' : 'Next'}
						</button>
					{:else if step === 2}
						<button
							type="button"
							onclick={goToOmdbStep}
							disabled={!editTitle.trim()}
							class="{btnBase} border border-primary/30 text-gray-700 hover:bg-primary/5 dark:text-gray-300 dark:hover:bg-primary/10"
						>
							Search OMDB
						</button>
						<button
							type="button"
							onclick={() => step = 4}
							disabled={!editTitle.trim()}
							class="{btnBase} bg-primary text-on-primary hover:bg-primary/90"
						>
							Looks good
						</button>
					{:else if step === 3}
						<button
							type="button"
							onclick={() => step = 4}
							disabled={!editTitle.trim()}
							class="{btnBase} bg-primary text-on-primary hover:bg-primary/90"
						>
							Next
						</button>
					{:else if step === 4}
						<button
							type="button"
							onclick={handleImport}
							disabled={importing}
							class="{btnBase} bg-primary text-on-primary hover:bg-primary/90"
						>
							{importing ? 'Importing...' : 'Import'}
						</button>
					{/if}
				</div>
			</div>
		</div>
	</div>
{/if}
