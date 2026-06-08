<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { fetchIngressRoot, fetchIngressDirectory } from '$lib/api/import-jobs';
	import { showImportWizard } from '$lib/stores/importWizard';
	import type { FileEntry } from '$lib/types/api.gen';
	import { Folder, FolderArchive, Disc, File as FileIcon } from 'lucide-svelte';

	// NOTE: kind/importable are computed client-side until the BFF (arm-neu PR #333)
	// emits them per entry. Once the BFF lands those fields and api.gen.ts picks
	// them up via codegen, this fallback computation can be replaced by direct
	// reads of entry.kind / entry.importable.
	type EntryKind = 'dir' | 'iso' | 'other';

	interface DecoratedEntry extends FileEntry {
		kind: EntryKind;
		importable: boolean;
	}

	interface Props {
		onselect: (selection: { path: string; kind: 'dir' | 'iso' }) => void;
	}

	let { onselect }: Props = $props();

	let ingressPath = $state<string | null>(null);
	let currentPath = $state('');
	let entries = $state<FileEntry[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let needsConfig = $state(false);
	let selectedPath = $state<string | null>(null);
	let filter = $state('');
	let scrollContainer = $state<HTMLDivElement | null>(null);
	let sortKey = $state<'name' | 'size' | 'modified'>('name');
	let sortDir = $state<'asc' | 'desc'>('asc');

	function classifyEntry(entry: FileEntry, allEntries: readonly FileEntry[]): { kind: EntryKind; importable: boolean } {
		// Prefer server-computed fields when present; codegen may not yet expose them.
		const raw = entry as FileEntry & { kind?: EntryKind; importable?: boolean };
		if (raw.kind) {
			return { kind: raw.kind, importable: raw.importable ?? false };
		}
		if (entry.type === 'directory') {
			// A folder is importable when it (or a sibling, in the disc-internal case)
			// contains BDMV/VIDEO_TS. We can only see siblings so the importable signal
			// here is heuristic: a top-level dir is treated as potentially importable
			// (true) and the user discovers the actual disc structure on the next nav.
			// Disc-structure internals (BDMV/VIDEO_TS themselves) are still flagged via
			// the existing isDiscStructureDir helper and rendered greyed.
			return { kind: 'dir', importable: true };
		}
		if (entry.name.toLowerCase().endsWith('.iso')) {
			return { kind: 'iso', importable: true };
		}
		return { kind: 'other', importable: false };
	}

	let decoratedEntries = $derived<DecoratedEntry[]>(
		entries.map((e) => ({ ...e, ...classifyEntry(e, entries) }))
	);

	let visibleEntries = $derived(
		decoratedEntries.filter((e) => e.kind === 'dir' || e.kind === 'iso' || e.kind === 'other')
	);

	let allDirectories = $derived(visibleEntries.filter((e) => e.kind === 'dir'));
	let filterEnabled = $derived(visibleEntries.length > 5);
	let sortedEntries = $derived(
		[...visibleEntries]
			.filter((e) => !filter || e.name.toLowerCase().includes(filter.toLowerCase()))
			.sort((a, b) => {
				let cmp: number;
				if (sortKey === 'size') cmp = (a.size ?? 0) - (b.size ?? 0);
				else if (sortKey === 'modified') cmp = (a.modified ?? '').localeCompare(b.modified ?? '');
				else cmp = a.name.toLowerCase().localeCompare(b.name.toLowerCase());
				return sortDir === 'asc' ? cmp : -cmp;
			})
	);

	function toggleSort(key: 'name' | 'size' | 'modified') {
		if (sortKey === key) { sortDir = sortDir === 'asc' ? 'desc' : 'asc'; }
		else { sortKey = key; sortDir = key === 'modified' ? 'desc' : 'asc'; }
	}

	function sortIcon(key: string): string {
		if (sortKey !== key) return '';
		return sortDir === 'asc' ? ' ▴' : ' ▾';
	}

	function formatSize(bytes: number): string {
		if (bytes === 0) return '0 B';
		const units = ['B', 'KB', 'MB', 'GB', 'TB'];
		const i = Math.floor(Math.log(bytes) / Math.log(1024));
		return `${(bytes / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0)} ${units[i]}`;
	}

	function isDiscStructureDir(name: string): boolean {
		const upper = name.toUpperCase();
		return upper === 'BDMV' || upper === 'VIDEO_TS' || upper === 'CERTIFICATE' || upper === 'AUDIO_TS';
	}

	/** True if the current listing contains BDMV or VIDEO_TS - this folder IS a disc. */
	let currentIsDisc = $derived(
		entries.some((e) => e.type === 'directory' && (e.name.toUpperCase() === 'BDMV' || e.name.toUpperCase() === 'VIDEO_TS'))
	);

	/** Badge for entries that are disc structure internals. */
	function discBadgeFor(name: string): string | null {
		const upper = name.toUpperCase();
		if (upper === 'BDMV' || upper === 'CERTIFICATE') return 'Blu-ray';
		if (upper === 'VIDEO_TS' || upper === 'AUDIO_TS') return 'DVD';
		return null;
	}

	async function loadDirectory(path: string) {
		loading = true;
		error = null;
		filter = '';
		try {
			const listing = await fetchIngressDirectory(path);
			currentPath = listing.path ?? '';
			entries = listing.entries;
			scrollContainer?.scrollTo(0, 0);
		} catch (e) {
			const msg = e instanceof Error ? e.message : 'Failed to load directory';
			error = msg.includes('unreachable') || msg.includes('503')
				? 'ARM service is starting up - try again in a moment'
				: msg;
		} finally {
			loading = false;
		}
	}

	function handleSelect(entry: DecoratedEntry) {
		if (!entry.importable) return;
		const fullPath = currentPath ? `${currentPath}/${entry.name}` : entry.name;
		selectedPath = fullPath;
		const kind: 'dir' | 'iso' = entry.kind === 'iso' ? 'iso' : 'dir';
		onselect({ path: fullPath, kind });
	}

	function handleOpen(entry: DecoratedEntry) {
		// Don't drill into disc structure internals or non-directory entries
		if (entry.kind !== 'dir') return;
		if (isDiscStructureDir(entry.name)) return;
		const fullPath = currentPath ? `${currentPath}/${entry.name}` : entry.name;
		selectedPath = null;
		loadDirectory(fullPath);
	}

	// When we navigate into a disc folder, auto-select the current path
	$effect(() => {
		if (currentIsDisc && currentPath) {
			selectedPath = currentPath;
			onselect({ path: currentPath, kind: 'dir' });
		}
	});

	function goBack() {
		if (!currentPath || currentPath === ingressPath) return;
		const parent = currentPath.replace(/\/[^/]+$/, '');
		if (!parent || !ingressPath || !parent.startsWith(ingressPath)) return;
		selectedPath = null;
		loadDirectory(parent);
	}

	async function init() {
		loading = true;
		error = null;
		needsConfig = false;
		try {
			const roots = await fetchIngressRoot();
			const ingress = roots.find((r) => r.key === 'ingress');
			if (!ingress) {
				needsConfig = true;
				loading = false;
				return;
			}
			ingressPath = ingress.path;
			await loadDirectory(ingress.path);
		} catch (e) {
			const msg = e instanceof Error ? e.message : 'Failed to load file roots';
			error = msg.includes('unreachable') || msg.includes('503')
				? 'ARM service is starting up - try again in a moment'
				: msg;
			loading = false;
		}
	}

	onMount(() => { init(); });
</script>

<div class="flex min-h-0 flex-1 flex-col">
	{#if needsConfig}
		<div class="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-700 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-400">
			<p class="font-medium">Folder Import Path is not configured</p>
			<p class="mt-1">Set the <strong>Folder Import Path</strong> in
				<button
					type="button"
					class="underline hover:text-amber-900 dark:hover:text-amber-300"
					onclick={() => { showImportWizard.set(false); goto('/settings#ripping/media-directories'); }}
				>Settings &rarr; Ripping &rarr; Media Directories</button>
				to the directory containing your BDMV/VIDEO_TS folders or ISO files.</p>
		</div>
	{:else if error}
		<div class="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
			<p>{error}</p>
			<button
				type="button"
				onclick={init}
				class="mt-2 rounded-md bg-red-100 px-3 py-1 text-xs font-medium text-red-800 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-300 dark:hover:bg-red-900/50"
			>Retry</button>
		</div>
	{:else if loading && entries.length === 0}
		<div class="py-8 text-center text-gray-400">Loading...</div>
	{:else}
		<!-- Navigation bar (pinned) -->
		<div class="shrink-0 space-y-2 pb-2">
			<!-- Path bar -->
			<div class="flex items-center gap-1 rounded-lg border border-primary/20 bg-primary/5 px-3 py-1.5 text-sm dark:border-primary/20 dark:bg-primary/10">
				<svg class="h-4 w-4 shrink-0 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
				</svg>
				<span class="truncate text-gray-700 dark:text-gray-300">{currentPath || ingressPath}</span>
			</div>
			{#if !currentIsDisc}
				<p class="text-xs text-gray-400 dark:text-gray-500">Navigate to a folder containing BDMV or VIDEO_TS, or pick an ISO file.</p>
			{/if}

			<!-- Filter -->
			<input
				type="text"
				bind:value={filter}
				disabled={!filterEnabled}
				placeholder="Filter entries..."
				class="w-full rounded-lg border border-primary/25 bg-primary/5 px-3 py-1.5 text-sm text-gray-900 placeholder-gray-400 focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary dark:border-primary/30 dark:bg-primary/10 dark:text-white dark:placeholder-gray-500 disabled:cursor-not-allowed disabled:opacity-40"
			/>

			<!-- Disc detected banner -->
			{#if currentIsDisc}
				<div class="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-700 dark:border-green-800 dark:bg-green-900/20 dark:text-green-400">
					Disc folder detected - this folder is ready to import.
				</div>
			{/if}
		</div>

		<!-- Directory table (scrollable) -->
		<div bind:this={scrollContainer} class="min-h-0 flex-1 overflow-y-auto transition-opacity {loading ? 'pointer-events-none opacity-50' : ''}">
			<div class="rounded-lg border border-primary/20 dark:border-primary/20">
				<table class="w-full table-fixed text-left text-sm">
					<colgroup>
						<col />
						<col class="w-20" />
						<col class="w-28" />
					</colgroup>
					<thead class="bg-page text-gray-600 dark:bg-primary/5 dark:text-gray-400">
						<tr>
							<th class="px-4 py-2 font-medium">
								<button type="button" onclick={() => toggleSort('name')} class="hover:text-gray-700 dark:hover:text-gray-300">Name{sortIcon('name')}</button>
							</th>
							<th class="px-4 py-2 font-medium">
								<button type="button" onclick={() => toggleSort('size')} class="hover:text-gray-700 dark:hover:text-gray-300">Size{sortIcon('size')}</button>
							</th>
							<th class="px-4 py-2 font-medium">
								<button type="button" onclick={() => toggleSort('modified')} class="hover:text-gray-700 dark:hover:text-gray-300">Modified{sortIcon('modified')}</button>
							</th>
						</tr>
					</thead>
					<tbody class="divide-y divide-gray-200 dark:divide-gray-700">
					{#if currentPath && currentPath !== ingressPath}
						<tr
							class="cursor-pointer transition-colors hover:bg-primary/5 dark:hover:bg-primary/10"
							onclick={goBack}
						>
							<td class="px-4 py-2">
								<div class="flex items-center gap-2">
									<svg class="h-4 w-4 shrink-0 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 17l-5-5m0 0l5-5m-5 5h12" />
									</svg>
									<span class="text-gray-500 dark:text-gray-400">..</span>
								</div>
							</td>
							<td class="px-4 py-2"></td>
							<td class="px-4 py-2"></td>
						</tr>
					{/if}
					{#if sortedEntries.length === 0}
						<tr><td colspan="3" class="px-4 py-6 text-center text-gray-400 dark:text-gray-500">No entries found.</td></tr>
					{/if}
						{#each sortedEntries as entry (entry.name)}
							{@const fullPath = currentPath ? `${currentPath}/${entry.name}` : entry.name}
							{@const isStructureDir = entry.kind === 'dir' && isDiscStructureDir(entry.name)}
							{@const badge = discBadgeFor(entry.name)}
							{@const disabled = !entry.importable || isStructureDir}
							<tr
								data-kind={entry.kind}
								data-disabled={disabled ? '' : undefined}
								aria-disabled={disabled ? 'true' : undefined}
								class="transition-colors {disabled
									? 'cursor-default opacity-50'
									: `cursor-pointer hover:bg-primary/5 dark:hover:bg-primary/10 ${selectedPath === fullPath ? 'bg-primary/15 dark:bg-primary/15' : ''}`}"
								onclick={() => { if (!disabled) handleSelect(entry); }}
								ondblclick={() => { if (!disabled) handleOpen(entry); }}
							>
								<td class="px-4 py-2">
									<div class="flex items-center gap-2 overflow-hidden">
										<span class="shrink-0">
											{#if entry.kind === 'iso'}
												<Disc class="h-4 w-4 text-primary" />
											{:else if entry.kind === 'dir' && entry.importable && !isStructureDir}
												<FolderArchive class="h-4 w-4 text-primary" />
											{:else if entry.kind === 'dir'}
												<Folder class="h-4 w-4 text-gray-500" />
											{:else}
												<FileIcon class="h-4 w-4 text-gray-400" />
											{/if}
										</span>
										<span class="truncate {disabled ? 'text-gray-400 dark:text-gray-500' : 'text-gray-900 dark:text-white'}">{entry.name}</span>
										{#if badge}
											<span class="shrink-0 rounded-sm bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
												{badge}
											</span>
										{/if}
									</div>
								</td>
								<td class="px-4 py-2 text-gray-500 dark:text-gray-400">{formatSize(entry.size ?? 0)}</td>
								<td class="whitespace-nowrap px-4 py-2 text-gray-500 dark:text-gray-400">
									{entry.modified ? new Date(entry.modified).toLocaleDateString() : '--'}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	{/if}
</div>
