<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { fetchRoots, fetchDirectory, renameFile, moveFile, deleteFile, createDirectory, fixPermissions } from '$lib/api/files';
	import type { FileRoot, DirectoryListing, FileEntry } from '$lib/types/api.gen';
	import { formatBytes, formatDateTime } from '$lib/utils/format';
	import { fetchOrphanFolders, deleteFolder as deleteOrphanFolder, bulkDeleteFolders, cleanupTranscoder } from '$lib/api/maintenance';
	import type { OrphanFoldersResponse } from '$lib/api/maintenance';
	import FileIcon from '$lib/components/FileIcon.svelte';
	import BreadcrumbNav from '$lib/components/BreadcrumbNav.svelte';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
	import FileRow from '$lib/components/FileRow.svelte';
	import LoadState from '$lib/components/LoadState.svelte';

	let roots = $state<FileRoot[]>([]);
	let currentPath = $state<string>('');
	let listing = $state<DirectoryListing | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let filesError = $derived<Error | null>(error ? new Error(error) : null);
	let feedback = $state<{ type: 'success' | 'error'; message: string } | null>(null);

	// Sort state
	let sortKey = $state<'name' | 'size' | 'modified'>('name');
	let sortDir = $state<'asc' | 'desc'>('asc');

	// Selection state
	let selectedPaths = $state(new Set<string>());

	// Delete confirmation (single item)
	let deleteDialog = $state({ open: false, path: '', name: '' });

	// Bulk delete confirmation
	let bulkDeleteOpen = $state(false);

	// Move dialog — browsable directory picker
	let moveDialogOpen = $state(false);
	let pickerPath = $state('');
	let pickerListing = $state<DirectoryListing | null>(null);
	let pickerLoading = $state(false);
	let pickerRoot = $state('');  // the root path this picker is scoped to

	// New folder
	let creatingFolder = $state(false);
	let newFolderName = $state('');

	// Orphan folders modal
	let orphanFoldersOpen = $state(false);
	let orphanFoldersData = $state<OrphanFoldersResponse | null>(null);
	let orphanFoldersLoading = $state(false);
	let orphanFoldersSelected = $state<Set<string>>(new Set());
	let orphanFoldersBusy = $state(false);
	let orphanFoldersFeedback = $state<{ type: 'success' | 'error'; message: string } | null>(null);

	// Transcoder cleanup
	let transcoderCleanupOpen = $state(false);
	let transcoderBusy = $state(false);

	let isReadonly = $derived(listing?.readonly === true);

	// Find the most specific (longest path) matching root for the current path
	let activeRootPath = $derived.by(() => {
		let best = '';
		for (const r of roots) {
			if ((currentPath === r.path || currentPath.startsWith(r.path + '/')) && r.path.length > best.length) {
				best = r.path;
			}
		}
		return best;
	});

	let sortedEntries = $derived.by(() => {
		if (!listing) return [];
		return [...listing.entries].sort((a, b) => {
			if (a.type !== b.type) return a.type === 'directory' ? -1 : 1;
			let cmp: number;
			if (sortKey === 'size') {
				cmp = (a.size ?? 0) - (b.size ?? 0);
			} else if (sortKey === 'modified') {
				cmp = (a.modified ?? '').localeCompare(b.modified ?? '');
			} else {
				cmp = a.name.toLowerCase().localeCompare(b.name.toLowerCase());
			}
			return sortDir === 'asc' ? cmp : -cmp;
		});
	});

	// Subfolders in the picker (excluding items being moved)
	let pickerFolders = $derived.by(() => {
		if (!pickerListing) return [];
		const selectedNames = new Set([...selectedPaths].map(p => p.split('/').pop()!));
		return pickerListing.entries.filter(
			e => e.type === 'directory' && !selectedNames.has(e.name)
		);
	});

	// Can we go up from picker? Only if not already at the root
	let pickerCanGoUp = $derived(pickerPath !== pickerRoot && pickerListing?.parent != null);

	let allSelected = $derived(
		sortedEntries.length > 0 && sortedEntries.every(e => selectedPaths.has(listing!.path + '/' + e.name))
	);

	function toggleSort(key: 'name' | 'size' | 'modified') {
		if (sortKey === key) {
			sortDir = sortDir === 'asc' ? 'desc' : 'asc';
		} else {
			sortKey = key;
			sortDir = key === 'modified' ? 'desc' : 'asc';
		}
	}

	function sortIcon(key: string): string {
		if (sortKey !== key) return '';
		return sortDir === 'asc' ? ' \u25B2' : ' \u25BC';
	}

	function clearFeedback() {
		setTimeout(() => (feedback = null), 3000);
	}

	function toggleSelect(path: string) {
		const next = new Set(selectedPaths);
		if (next.has(path)) next.delete(path);
		else next.add(path);
		selectedPaths = next;
	}

	function toggleSelectAll() {
		if (!listing) return;
		if (allSelected) {
			selectedPaths = new Set();
		} else {
			selectedPaths = new Set(sortedEntries.map(e => listing!.path + '/' + e.name));
		}
	}

	const rootOrder: Record<string, number> = { raw: 0, transcode: 1, completed: 2, music: 3 };

	async function loadRoots() {
		try {
			roots = (await fetchRoots()).sort((a, b) => (rootOrder[a.key ?? ''] ?? 99) - (rootOrder[b.key ?? ''] ?? 99));
			if (roots.length > 0 && !currentPath) {
				currentPath = roots[0].path;
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load roots';
		}
	}

	async function navigate(path: string) {
		loading = true;
		error = null;
		currentPath = path;
		selectedPaths = new Set();
		try {
			listing = await fetchDirectory(path);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load directory';
			listing = null;
		} finally {
			loading = false;
		}
	}

	async function handleRename(path: string, newName: string) {
		try {
			await renameFile(path, newName);
			feedback = { type: 'success', message: `Renamed to ${newName}` };
			clearFeedback();
			await navigate(currentPath);
		} catch (e) {
			feedback = { type: 'error', message: e instanceof Error ? e.message : 'Rename failed' };
			clearFeedback();
		}
	}

	async function handleFixPermissions(path: string, name: string) {
		try {
			const result = await fixPermissions(path);
			feedback = { type: 'success', message: `Fixed permissions on ${name} (${result.fixed} item${result.fixed !== 1 ? 's' : ''})` };
			clearFeedback();
			await navigate(currentPath);
		} catch (e) {
			feedback = { type: 'error', message: e instanceof Error ? e.message : 'Failed to fix permissions' };
			clearFeedback();
		}
	}

	function handleDeleteRequest(path: string, name: string) {
		deleteDialog = { open: true, path, name };
	}

	async function confirmDelete() {
		try {
			await deleteFile(deleteDialog.path);
			feedback = { type: 'success', message: `Deleted ${deleteDialog.name}` };
			clearFeedback();
			deleteDialog = { open: false, path: '', name: '' };
			await navigate(currentPath);
		} catch (e) {
			feedback = { type: 'error', message: e instanceof Error ? e.message : 'Delete failed' };
			clearFeedback();
		}
	}

	// --- Bulk move with browsable picker ---
	async function openMoveDialog() {
		if (selectedPaths.size === 0) return;
		// Determine which root the current path belongs to
		const root = roots.find(r => currentPath === r.path || currentPath.startsWith(r.path + '/'));
		if (!root) return;
		pickerRoot = root.path;
		pickerPath = currentPath;
		moveDialogOpen = true;
		await loadPickerPath(currentPath);
	}

	async function loadPickerPath(path: string) {
		pickerLoading = true;
		try {
			pickerListing = await fetchDirectory(path);
			pickerPath = path;
		} catch {
			// stay on current listing
		} finally {
			pickerLoading = false;
		}
	}

	async function pickerNavigate(path: string) {
		await loadPickerPath(path);
	}

	async function pickerGoUp() {
		if (pickerListing?.parent && pickerPath !== pickerRoot) {
			await loadPickerPath(pickerListing.parent);
		}
	}

	function closeMoveDialog() {
		moveDialogOpen = false;
		pickerListing = null;
	}

	function pickerRelativePath(): string {
		if (!pickerPath || !pickerRoot) return '';
		if (pickerPath === pickerRoot) {
			const root = roots.find(r => r.path === pickerRoot);
			return root ? root.label : '/';
		}
		const root = roots.find(r => r.path === pickerRoot);
		const prefix = root ? root.label : '';
		return prefix + '/' + pickerPath.slice(pickerRoot.length + 1);
	}

	async function confirmBulkMove() {
		if (!pickerPath) return;
		let moved = 0;
		let failed = 0;
		for (const path of selectedPaths) {
			try {
				await moveFile(path, pickerPath);
				moved++;
			} catch {
				failed++;
			}
		}
		closeMoveDialog();
		selectedPaths = new Set();
		if (failed > 0) {
			feedback = { type: 'error', message: `Moved ${moved}, failed ${failed}` };
		} else {
			feedback = { type: 'success', message: `Moved ${moved} item${moved !== 1 ? 's' : ''}` };
		}
		clearFeedback();
		await navigate(currentPath);
	}

	// --- Bulk delete ---
	async function confirmBulkDelete() {
		let deleted = 0;
		let failed = 0;
		// Sort longest paths first so children are deleted before parents,
		// then skip paths whose ancestor was already deleted.
		const paths = [...selectedPaths].sort((a, b) => b.length - a.length);
		const deletedPaths: string[] = [];
		for (const path of paths) {
			if (deletedPaths.some((dp) => path.startsWith(dp + '/'))) {
				deleted++;
				continue;
			}
			try {
				await deleteFile(path);
				deleted++;
				deletedPaths.push(path);
			} catch {
				failed++;
			}
		}
		bulkDeleteOpen = false;
		selectedPaths = new Set();
		if (failed > 0) {
			feedback = { type: 'error', message: `Deleted ${deleted}, failed ${failed}` };
		} else {
			feedback = { type: 'success', message: `Deleted ${deleted} item${deleted !== 1 ? 's' : ''}` };
		}
		clearFeedback();
		await navigate(currentPath);
	}

	// --- New folder ---
	function startNewFolder() {
		newFolderName = '';
		creatingFolder = true;
	}

	async function confirmNewFolder() {
		if (!newFolderName.trim() || !currentPath) return;
		try {
			await createDirectory(currentPath, newFolderName.trim());
			feedback = { type: 'success', message: `Created folder "${newFolderName.trim()}"` };
			clearFeedback();
			creatingFolder = false;
			newFolderName = '';
			await navigate(currentPath);
		} catch (e) {
			feedback = { type: 'error', message: e instanceof Error ? e.message : 'Failed to create folder' };
			clearFeedback();
		}
	}

	function cancelNewFolder() {
		creatingFolder = false;
		newFolderName = '';
	}

	function handleNewFolderKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') confirmNewFolder();
		if (e.key === 'Escape') cancelNewFolder();
	}

	// --- Orphan folders ---
	async function openOrphanFoldersModal() {
		orphanFoldersOpen = true;
		orphanFoldersLoading = true;
		orphanFoldersFeedback = null;
		try {
			orphanFoldersData = await fetchOrphanFolders();
			orphanFoldersSelected = new Set();
		} catch { orphanFoldersData = null; }
		orphanFoldersLoading = false;
	}

	function toggleOrphanFolderSelect(path: string) {
		const next = new Set(orphanFoldersSelected);
		if (next.has(path)) next.delete(path);
		else next.add(path);
		orphanFoldersSelected = next;
	}

	async function handleDeleteOrphanFolder(path: string) {
		const name = path.split('/').pop();
		orphanFoldersBusy = true;
		try {
			await deleteOrphanFolder(path);
			orphanFoldersFeedback = { type: 'success', message: `Folder "${name}" deleted` };
			orphanFoldersData = await fetchOrphanFolders();
			orphanFoldersSelected = new Set();
		} catch (e) {
			orphanFoldersFeedback = { type: 'error', message: e instanceof Error ? e.message : 'Delete failed' };
		}
		orphanFoldersBusy = false;
	}

	async function handleBulkDeleteOrphanFolders() {
		orphanFoldersBusy = true;
		try {
			const result = await bulkDeleteFolders([...orphanFoldersSelected]);
			orphanFoldersFeedback = {
				type: result.errors.length ? 'error' : 'success',
				message: `Deleted ${result.removed.length} folder${result.removed.length !== 1 ? 's' : ''}${result.errors.length ? `, ${result.errors.length} error(s)` : ''}`
			};
			orphanFoldersData = await fetchOrphanFolders();
			orphanFoldersSelected = new Set();
		} catch (e) {
			orphanFoldersFeedback = { type: 'error', message: e instanceof Error ? e.message : 'Bulk delete failed' };
		}
		orphanFoldersBusy = false;
	}

	// --- Transcoder cleanup ---
	async function handleCleanupTranscoder() {
		transcoderBusy = true;
		try {
			const result = await cleanupTranscoder();
			feedback = {
				type: result.errors.length ? 'error' : 'success',
				message: `Deleted ${result.deleted} transcoder job${result.deleted !== 1 ? 's' : ''}${result.errors.length ? `, ${result.errors.length} error(s)` : ''}`
			};
			clearFeedback();
		} catch (e) {
			feedback = { type: 'error', message: e instanceof Error ? e.message : 'Cleanup failed' };
			clearFeedback();
		}
		transcoderBusy = false;
		transcoderCleanupOpen = false;
	}

	// React to ?path= query param changes (works for both initial load and in-page nav)
	let lastParamPath = '';
	$effect(() => {
		const paramPath = $page.url.searchParams.get('path');
		if (paramPath) {
			const cleaned = paramPath.replace(/\/+$/, '');
			if (cleaned !== lastParamPath) {
				lastParamPath = cleaned;
				navigate(cleaned);
			}
		}
	});

	onMount(async () => {
		await loadRoots();
		const paramPath = $page.url.searchParams.get('path');
		if (paramPath) {
			currentPath = paramPath.replace(/\/+$/, '');
			lastParamPath = currentPath;
		}
		if (currentPath) {
			await navigate(currentPath);
		} else {
			loading = false;
		}
	});
</script>

<svelte:head>
	<title>ARM - Files</title>
</svelte:head>

<div class="space-y-4">
	<h1 class="text-2xl font-bold text-gray-900 dark:text-white">Files</h1>

	<!-- Warning banner -->
	<div class="rounded-lg border border-primary/30 bg-primary-light-bg px-4 py-3 text-sm text-primary-dark dark:border-primary/30 dark:bg-primary-light-bg-dark/20 dark:text-primary-text-dark">
		<span class="font-semibold">Warning:</span> Modify files at your own risk. This will not update database records and will cause issues for any in-progress rips or transcodes.
	</div>

	<!-- Feedback toast -->
	{#if feedback}
		<div
			class="rounded-lg border px-4 py-2 text-sm {feedback.type === 'success'
				? 'border-green-200 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-900/20 dark:text-green-400'
				: 'border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400'}"
		>
			{feedback.message}
		</div>
	{/if}

	<!-- Error -->
	{#if error}
		<div class="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
			{error}
		</div>
	{/if}

	<!-- Root tabs -->
	{#if roots.length > 0}
		<div class="border-b border-primary/20 dark:border-primary/20">
			<nav class="-mb-px flex gap-4" aria-label="File root tabs">
				{#each roots as root}
					<button
						type="button"
						onclick={() => navigate(root.path)}
							class="whitespace-nowrap border-b-2 px-1 py-2.5 text-sm font-medium transition-colors
							{root.path === activeRootPath
								? 'border-primary text-primary-text dark:border-primary-text-dark dark:text-primary-text-dark'
								: 'border-transparent text-gray-500 hover:border-primary/30 hover:text-gray-700 dark:text-gray-400 dark:hover:border-primary/30 dark:hover:text-gray-300'}"
					>
						{root.label}
					</button>
				{/each}
			</nav>
		</div>
		{@const activeRoot = roots.find(r => r.path === activeRootPath)}
		{#if activeRoot}
			<details class="mt-2 text-xs text-gray-400 dark:text-gray-500">
				<summary class="cursor-pointer select-none font-semibold uppercase tracking-wide hover:text-gray-500 dark:hover:text-gray-400">Paths</summary>
				<div class="mt-1">
					<p><span class="font-medium">Container:</span> <code class="font-mono">{activeRoot.path}</code></p>
					{#if activeRoot.host_path}
						<p><span class="font-medium">Host:</span> <code class="font-mono">{activeRoot.host_path}</code></p>
					{/if}
				</div>
			</details>
		{/if}
	{/if}

	<!-- Read-only mount banner -->
	{#if isReadonly}
		<div class="flex items-center gap-2 rounded-lg border border-amber-300/50 bg-amber-50/50 px-4 py-2.5 dark:border-amber-700/50 dark:bg-amber-900/20">
			<svg class="h-4 w-4 shrink-0 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
				<path stroke-linecap="round" stroke-linejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
			</svg>
			<p class="text-sm text-amber-700 dark:text-amber-400">This directory is on a read-only mount. File operations are disabled.</p>
		</div>
	{/if}

	<!-- Breadcrumb + toolbar row -->
	{#if currentPath && roots.length > 0}
		<div class="flex items-center justify-between gap-3">
			<BreadcrumbNav path={currentPath} {roots} onnavigate={navigate} />
			<div class="flex shrink-0 items-center gap-1">
				<!-- Bulk move (visible when items selected) -->
				{#if selectedPaths.size > 0}
					<button
						type="button"
						onclick={openMoveDialog}
						disabled={isReadonly}
						class="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-on-primary hover:bg-primary/90 disabled:opacity-50 disabled:pointer-events-none"
					>
						<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
						</svg>
						Move {selectedPaths.size}
					</button>
					<button
						type="button"
						onclick={() => (bulkDeleteOpen = true)}
						disabled={isReadonly}
						class="inline-flex items-center gap-1.5 rounded-lg bg-red-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-50 disabled:pointer-events-none"
					>
						<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
						</svg>
						Delete {selectedPaths.size}
					</button>
				{/if}
				<!-- Orphan folders -->
				<button
					type="button"
					onclick={openOrphanFoldersModal}
					class="rounded-lg p-2 text-gray-500 hover:bg-primary/10 dark:text-gray-400 dark:hover:bg-primary/15"
					title="Orphan folders"
				>
					<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 11v4m-2-2h4" />
					</svg>
				</button>
				<!-- Transcoder cleanup -->
				<button
					type="button"
					onclick={() => (transcoderCleanupOpen = true)}
					class="rounded-lg p-2 text-gray-500 hover:bg-primary/10 dark:text-gray-400 dark:hover:bg-primary/15"
					title="Clean up transcoder jobs"
				>
					<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z" />
					</svg>
				</button>
				<!-- New folder -->
				<button
					type="button"
					onclick={startNewFolder}
					disabled={isReadonly}
					class="rounded-lg p-2 text-gray-500 hover:bg-primary/10 dark:text-gray-400 dark:hover:bg-primary/15 disabled:opacity-30 disabled:pointer-events-none"
					title={isReadonly ? 'Read-only mount' : 'New folder'}
				>
					<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 13h6m-3-3v6m-9 1V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
					</svg>
				</button>
				<!-- Refresh -->
				<button
					type="button"
					onclick={() => navigate(currentPath)}
					disabled={loading}
					class="rounded-lg p-2 text-gray-500 hover:bg-primary/10 dark:text-gray-400 dark:hover:bg-primary/15 disabled:opacity-50"
					title="Refresh"
				>
					<svg class="h-5 w-5" class:animate-spin={loading} fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
					</svg>
				</button>
			</div>
		</div>
	{/if}

	<!-- File listing -->
	<LoadState
		data={listing}
		loading={loading && !listing}
		error={filesError}
		isEmpty={() => false}
		transitionKey={`files-${currentPath}`}
	>
		{#snippet loadingSlot()}
			<div class="overflow-hidden rounded-lg border border-primary/20 bg-surface dark:border-primary/20 dark:bg-surface-dark">
				<table class="w-full">
					<thead>
						<tr class="border-b border-gray-200 text-left text-xs font-medium uppercase text-gray-500 dark:border-gray-700 dark:text-gray-400">
							<th class="w-10 px-3 py-2"></th>
							<th class="px-3 py-2">Name</th>
							<th class="hidden px-3 py-2 lg:table-cell">Permissions</th>
							<th class="px-3 py-2 text-right">Size</th>
							<th class="hidden px-3 py-2 md:table-cell">Modified</th>
							<th class="px-3 py-2 text-right">Actions</th>
						</tr>
					</thead>
					<tbody>
						{#each Array(8) as _}
							<FileRow />
						{/each}
					</tbody>
				</table>
			</div>
		{/snippet}
		{#snippet ready(lst)}
			<div class="overflow-hidden rounded-lg border border-primary/20 bg-surface dark:border-primary/20 dark:bg-surface-dark">
				{#if lst.parent}
					<button
						type="button"
						onclick={() => lst.parent && navigate(lst.parent)}
						class="flex w-full items-center gap-2 border-b border-gray-100 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50 dark:border-gray-700/50 dark:text-gray-400 dark:hover:bg-gray-800/50"
					>
						<span class="w-10"></span>
						<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 17l-5-5m0 0l5-5m-5 5h12" />
						</svg>
						..
					</button>
				{/if}

				<!-- Inline new folder row -->
				{#if creatingFolder}
					<div class="flex items-center gap-2 border-b border-gray-100 bg-primary/5 px-3 py-2 dark:border-gray-700/50 dark:bg-primary/10">
						<span class="w-10"></span>
						<svg class="h-5 w-5 shrink-0 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 13h6m-3-3v6m-9 1V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
						</svg>
						<input
							type="text"
							bind:value={newFolderName}
							onkeydown={handleNewFolderKeydown}
							placeholder="Folder name"
							class="flex-1 rounded border border-gray-300 bg-white px-2 py-1 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
						/>
						<button type="button" onclick={confirmNewFolder} class="rounded p-1 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20" title="Create">
							<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
							</svg>
						</button>
						<button type="button" onclick={cancelNewFolder} class="rounded p-1 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700" title="Cancel">
							<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
							</svg>
						</button>
					</div>
				{/if}

				{#if sortedEntries.length === 0 && !creatingFolder}
					<div class="p-8 text-center text-sm text-gray-500 dark:text-gray-400">
						This directory is empty
					</div>
				{:else if sortedEntries.length > 0}
					<table class="w-full">
						<thead>
							<tr class="border-b border-gray-200 text-left text-xs font-medium uppercase text-gray-500 dark:border-gray-700 dark:text-gray-400">
								<th class="w-10 px-3 py-2">
									<input
										type="checkbox"
										checked={allSelected}
										onchange={toggleSelectAll}
										class="h-4 w-4 rounded border-gray-300 text-primary accent-primary dark:border-gray-600"
									/>
								</th>
								<th class="px-3 py-2">
									<button type="button" onclick={() => toggleSort('name')} class="hover:text-gray-700 dark:hover:text-gray-300">
										Name{sortIcon('name')}
									</button>
								</th>
								<th class="hidden px-3 py-2 lg:table-cell">Permissions</th>
								<th class="px-3 py-2 text-right">
									<button type="button" onclick={() => toggleSort('size')} class="hover:text-gray-700 dark:hover:text-gray-300">
										Size{sortIcon('size')}
									</button>
								</th>
								<th class="hidden px-3 py-2 md:table-cell">
									<button type="button" onclick={() => toggleSort('modified')} class="hover:text-gray-700 dark:hover:text-gray-300">
										Modified{sortIcon('modified')}
									</button>
								</th>
								<th class="px-3 py-2 text-right">Actions</th>
							</tr>
						</thead>
						<tbody>
							{#each sortedEntries as entry (entry.name)}
								<FileRow
									{entry}
									currentPath={lst.path}
									selected={selectedPaths.has((lst.path ?? '') + '/' + entry.name)}
									readonly={isReadonly}
									onnavigate={navigate}
									onrename={handleRename}
									ondelete={handleDeleteRequest}
									ontoggle={toggleSelect}
									onfixpermissions={handleFixPermissions}
								/>
							{/each}
						</tbody>
					</table>
				{/if}
			</div>
		{/snippet}
		{#snippet empty()}
			<div class="rounded-lg border border-primary/20 bg-surface p-8 text-center dark:border-primary/20 dark:bg-surface-dark">
				<p class="text-gray-500 dark:text-gray-400">No media directories configured</p>
			</div>
		{/snippet}
	</LoadState>
</div>

<!-- Delete confirmation -->
<ConfirmDialog
	open={deleteDialog.open}
	title="Delete {deleteDialog.name}"
	message="Are you sure you want to delete '{deleteDialog.name}'? This action cannot be undone."
	confirmLabel="Delete"
	variant="danger"
	onconfirm={confirmDelete}
	oncancel={() => (deleteDialog = { open: false, path: '', name: '' })}
/>

<!-- Bulk delete confirmation -->
<ConfirmDialog
	open={bulkDeleteOpen}
	title="Delete {selectedPaths.size} item{selectedPaths.size !== 1 ? 's' : ''}"
	message="This will permanently delete {selectedPaths.size} selected item{selectedPaths.size !== 1 ? 's' : ''}, including all contents of any folders. This cannot be undone."
	confirmLabel="Delete All"
	variant="danger"
	onconfirm={confirmBulkDelete}
	oncancel={() => (bulkDeleteOpen = false)}
/>

<!-- Transcoder cleanup confirmation -->
<ConfirmDialog
	open={transcoderCleanupOpen}
	title="Clean Up Transcoder"
	message="Delete all completed and failed transcoder jobs from the transcoder database?"
	confirmLabel="Clean Up"
	variant="danger"
	onconfirm={handleCleanupTranscoder}
	oncancel={() => (transcoderCleanupOpen = false)}
/>

<!-- Orphan folders modal -->
{#if orphanFoldersOpen}
	<div class="fixed inset-0 z-50 flex items-center justify-center">
		<button
			type="button"
			class="absolute inset-0 bg-black/50"
			aria-label="Close dialog"
			onclick={() => (orphanFoldersOpen = false)}
		></button>
		<div class="relative z-10 flex w-full max-w-lg flex-col rounded-lg bg-surface shadow-xl dark:bg-surface-dark" style="max-height: 80vh;">
			<!-- Header -->
			<div class="shrink-0 border-b border-gray-200 px-6 py-4 dark:border-gray-700">
				<h3 class="text-lg font-semibold text-gray-900 dark:text-white">Orphan Folders</h3>
				<p class="mt-1 text-sm text-gray-500 dark:text-gray-400">Folders not associated with any job</p>
			</div>

			<!-- Feedback -->
			{#if orphanFoldersFeedback}
				<div class="shrink-0 border-b border-gray-100 px-6 py-2 dark:border-gray-700/50">
					<div class="rounded-lg border px-3 py-1.5 text-sm {orphanFoldersFeedback.type === 'success'
						? 'border-green-200 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-900/20 dark:text-green-400'
						: 'border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400'}">
						{orphanFoldersFeedback.message}
					</div>
				</div>
			{/if}

			<!-- Content (scrollable) -->
			<div class="min-h-0 flex-1 overflow-y-auto">
				{#if orphanFoldersLoading}
					<div class="flex items-center justify-center p-8">
						<svg class="mr-2 h-5 w-5 animate-spin text-gray-400" viewBox="0 0 24 24">
							<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" />
							<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
						</svg>
						<span class="text-sm text-gray-500 dark:text-gray-400">Loading...</span>
					</div>
				{:else if orphanFoldersData && orphanFoldersData.folders.length > 0}
					{#each orphanFoldersData.folders as folder (folder.path)}
						<div class="flex items-center gap-3 border-b border-gray-100 px-6 py-2.5 dark:border-gray-700/50">
							<input
								type="checkbox"
								checked={orphanFoldersSelected.has(folder.path)}
								onchange={() => toggleOrphanFolderSelect(folder.path)}
								disabled={orphanFoldersBusy}
								class="h-4 w-4 rounded border-gray-300 text-primary accent-primary dark:border-gray-600"
							/>
							<svg class="h-5 w-5 shrink-0 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
							</svg>
							<div class="min-w-0 flex-1">
								<div class="truncate text-sm font-medium text-gray-900 dark:text-white">{folder.name}</div>
								<div class="text-xs text-gray-500 dark:text-gray-400">{formatBytes(folder.size_bytes)}</div>
							</div>
							<span class="rounded-full px-2 py-0.5 text-xs font-medium
								{folder.category === 'raw'
									? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'
									: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'}">
								{folder.category}
							</span>
							<button
								type="button"
								onclick={() => handleDeleteOrphanFolder(folder.path)}
								disabled={orphanFoldersBusy}
								class="rounded p-1 text-red-500 hover:bg-red-50 disabled:opacity-50 dark:hover:bg-red-900/20"
								title="Delete folder"
							>
								<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
								</svg>
							</button>
						</div>
					{/each}
				{:else if orphanFoldersData}
					<div class="p-8 text-center text-sm text-gray-500 dark:text-gray-400">
						No orphan folders found
					</div>
				{:else}
					<div class="p-8 text-center text-sm text-red-500 dark:text-red-400">
						Failed to load orphan folders
					</div>
				{/if}
			</div>

			<!-- Footer -->
			<div class="shrink-0 border-t border-gray-200 px-6 py-4 dark:border-gray-700">
				<div class="flex items-center justify-between">
					<div>
						{#if orphanFoldersSelected.size > 0}
							<button
								type="button"
								onclick={handleBulkDeleteOrphanFolders}
								disabled={orphanFoldersBusy}
								class="inline-flex items-center gap-1.5 rounded-lg bg-red-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-50"
							>
								<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
								</svg>
								Delete {orphanFoldersSelected.size} selected
							</button>
						{/if}
					</div>
					<button
						type="button"
						onclick={() => (orphanFoldersOpen = false)}
						class="rounded-lg px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
					>
						Close
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}

<!-- Bulk move dialog — browsable directory picker -->
{#if moveDialogOpen}
	<div class="fixed inset-0 z-50 flex items-center justify-center">
		<button
			type="button"
			class="absolute inset-0 bg-black/50"
			aria-label="Close dialog"
			onclick={closeMoveDialog}
		></button>
		<div class="relative z-10 flex w-full max-w-lg flex-col rounded-lg bg-surface shadow-xl dark:bg-surface-dark" style="max-height: 80vh;">
			<!-- Header -->
			<div class="shrink-0 border-b border-gray-200 px-6 py-4 dark:border-gray-700">
				<h3 class="text-lg font-semibold text-gray-900 dark:text-white">
					Move {selectedPaths.size} item{selectedPaths.size !== 1 ? 's' : ''}
				</h3>
				<p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
					Browse to the destination folder
				</p>
			</div>

			<!-- Current picker location -->
			<div class="shrink-0 border-b border-gray-100 bg-gray-50 px-6 py-2 dark:border-gray-700/50 dark:bg-gray-800/50">
				<div class="flex items-center gap-2 text-sm">
					<svg class="h-4 w-4 shrink-0 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
					</svg>
					<span class="font-medium text-gray-900 dark:text-white">{pickerRelativePath()}</span>
					{#if pickerPath === currentPath}
						<span class="rounded bg-gray-200 px-1.5 py-0.5 text-xs text-gray-600 dark:bg-gray-700 dark:text-gray-400">current</span>
					{/if}
				</div>
			</div>

			<!-- Folder list (scrollable) -->
			<div class="min-h-0 flex-1 overflow-y-auto">
				{#if pickerLoading}
					<div class="flex items-center justify-center p-8">
						<svg class="mr-2 h-5 w-5 animate-spin text-gray-400" viewBox="0 0 24 24">
							<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" />
							<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
						</svg>
					</div>
				{:else}
					<!-- Go up -->
					{#if pickerCanGoUp}
						<button
							type="button"
							onclick={pickerGoUp}
							class="flex w-full items-center gap-3 border-b border-gray-100 px-6 py-2.5 text-sm text-gray-600 hover:bg-gray-50 dark:border-gray-700/50 dark:text-gray-400 dark:hover:bg-gray-800/50"
						>
							<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 17l-5-5m0 0l5-5m-5 5h12" />
							</svg>
							..
						</button>
					{/if}

					{#if pickerFolders.length === 0 && !pickerCanGoUp}
						<div class="p-6 text-center text-sm text-gray-500 dark:text-gray-400">
							No subfolders
						</div>
					{/if}

					{#each pickerFolders as folder (folder.name)}
						<button
							type="button"
							onclick={() => pickerNavigate(pickerPath + '/' + folder.name)}
							class="flex w-full items-center gap-3 border-b border-gray-100 px-6 py-2.5 text-sm text-gray-900 hover:bg-primary/5 dark:border-gray-700/50 dark:text-white dark:hover:bg-primary/10"
						>
							<svg class="h-5 w-5 shrink-0 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
							</svg>
							{folder.name}
							<svg class="ml-auto h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
							</svg>
						</button>
					{/each}
				{/if}
			</div>

			<!-- Footer -->
			<div class="shrink-0 border-t border-gray-200 px-6 py-4 dark:border-gray-700">
				<div class="flex justify-end gap-3">
					<button
						type="button"
						onclick={closeMoveDialog}
						class="rounded-lg px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
					>
						Cancel
					</button>
					<button
						type="button"
						onclick={confirmBulkMove}
						disabled={pickerPath === currentPath}
						class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-on-primary hover:bg-primary/90 disabled:opacity-50"
						title={pickerPath === currentPath ? 'Navigate to a different folder first' : ''}
					>
						Move here
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}
