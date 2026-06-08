<script lang="ts">
	import { onMount } from 'svelte';
	import { fetchLogs, fetchTranscoderLogs, deleteLog, logDownloadUrl } from '$lib/api/logs';
	import { fetchOrphanLogs, deleteLog as deleteOrphanLog, bulkDeleteLogs } from '$lib/api/maintenance';
	import type { OrphanLogsResponse } from '$lib/api/maintenance';
	import type { LogFileSchema as LogFile } from '$lib/types/api.gen';
	import { formatBytes, formatDateTime } from '$lib/utils/format';
	import LoadState from '$lib/components/LoadState.svelte';
	import SkeletonCard from '$lib/components/SkeletonCard.svelte';
	import { transcoderEnabled } from '$lib/stores/config';

	let deleting = $state<string | null>(null);
	let deleteFeedback = $state<{ type: 'success' | 'error'; message: string } | null>(null);

	let orphanModalOpen = $state(false);
	let orphanLogs = $state<OrphanLogsResponse | null>(null);
	let orphanLoading = $state(false);
	let orphanSelected = $state<Set<string>>(new Set());
	let orphanBusy = $state(false);
	let orphanFeedback = $state<{ type: 'success' | 'error'; message: string } | null>(null);

	async function handleDelete(filename: string) {
		if (!confirm(`Delete log file "${filename}"? This cannot be undone.`)) return;
		deleting = filename;
		deleteFeedback = null;
		try {
			await deleteLog(filename);
			armLogs = armLogs.filter(l => l.filename !== filename);
			deleteFeedback = { type: 'success', message: `Deleted ${filename}` };
			setTimeout(() => (deleteFeedback = null), 3000);
		} catch (e) {
			deleteFeedback = { type: 'error', message: e instanceof Error ? e.message : 'Failed to delete' };
			setTimeout(() => (deleteFeedback = null), 5000);
		} finally {
			deleting = null;
		}
	}

	let activeTab = $state<'arm' | 'transcoder'>('arm');

	$effect(() => {
		if (!$transcoderEnabled && activeTab === 'transcoder') activeTab = 'arm';
	});
	let armLogs = $state<LogFile[]>([]);
	let transcoderLogs = $state<LogFile[]>([]);
	let armLoading = $state(true);
	let armError = $state<Error | null>(null);
	let transcoderLoading = $state(true);
	let transcoderError = $state<Error | null>(null);

	let fileSortKey = $state<keyof LogFile>('modified');
	let fileSortDir = $state<'asc' | 'desc'>('desc');

	function toggleFileSort(key: keyof LogFile) {
		if (fileSortKey === key) {
			fileSortDir = fileSortDir === 'asc' ? 'desc' : 'asc';
		} else {
			fileSortKey = key;
			fileSortDir = key === 'modified' ? 'desc' : 'asc';
		}
	}

	function sortLogFiles(files: LogFile[]): LogFile[] {
		return [...files].sort((a, b) => {
			const av = a[fileSortKey];
			const bv = b[fileSortKey];
			let cmp: number;
			if (fileSortKey === 'size') {
				cmp = (av as number) - (bv as number);
			} else {
				cmp = String(av).localeCompare(String(bv));
			}
			return fileSortDir === 'asc' ? cmp : -cmp;
		});
	}

	let sortedArmLogs = $derived(sortLogFiles(armLogs));
	let sortedTranscoderLogs = $derived(sortLogFiles(transcoderLogs));

	function switchTab(tab: 'arm' | 'transcoder') {
		activeTab = tab;
		fileSortKey = 'modified';
		fileSortDir = 'desc';
	}

	async function openOrphanModal() {
		orphanModalOpen = true;
		orphanLoading = true;
		orphanFeedback = null;
		try {
			orphanLogs = await fetchOrphanLogs();
			orphanSelected = new Set();
		} catch {
			orphanLogs = null;
		}
		orphanLoading = false;
	}

	function toggleOrphanSelect(path: string) {
		const next = new Set(orphanSelected);
		if (next.has(path)) next.delete(path);
		else next.add(path);
		orphanSelected = next;
	}

	async function handleDeleteOrphan(path: string) {
		orphanBusy = true;
		try {
			await deleteOrphanLog(path);
			orphanFeedback = { type: 'success', message: 'Log deleted' };
			orphanLogs = await fetchOrphanLogs();
			orphanSelected = new Set();
		} catch (e) {
			orphanFeedback = { type: 'error', message: e instanceof Error ? e.message : 'Delete failed' };
		}
		orphanBusy = false;
	}

	async function handleBulkDeleteOrphans() {
		orphanBusy = true;
		try {
			const result = await bulkDeleteLogs([...orphanSelected]);
			orphanFeedback = {
				type: result.errors.length ? 'error' : 'success',
				message: `Deleted ${result.removed.length} log${result.removed.length !== 1 ? 's' : ''}${result.errors.length ? `, ${result.errors.length} error(s)` : ''}`
			};
			orphanLogs = await fetchOrphanLogs();
			orphanSelected = new Set();
		} catch (e) {
			orphanFeedback = { type: 'error', message: e instanceof Error ? e.message : 'Bulk delete failed' };
		}
		orphanBusy = false;
	}

	onMount(async () => {
		try {
			armLogs = await fetchLogs();
		} catch (e) {
			armError = e instanceof Error ? e : new Error('Failed to load ARM logs');
		} finally {
			armLoading = false;
		}
		try {
			transcoderLogs = await fetchTranscoderLogs();
		} catch (e) {
			transcoderError = e instanceof Error ? e : new Error('Failed to load transcoder logs');
		} finally {
			transcoderLoading = false;
		}
	});
</script>

<svelte:head>
	<title>ARM - Logs</title>
</svelte:head>

<div class="space-y-4">
	<div class="flex items-center justify-between">
		<h1 class="text-2xl font-bold text-gray-900 dark:text-white">Log Files</h1>
		<button type="button" onclick={openOrphanModal}
			class="rounded-lg px-3 py-1.5 text-sm font-medium text-primary-text hover:bg-primary/10 dark:text-primary-text-dark dark:hover:bg-primary/15">
			Orphan Logs
		</button>
	</div>

	<!-- Tab Bar -->
	<div class="border-b border-primary/20 dark:border-primary/20">
		<nav class="-mb-px flex gap-4" aria-label="Log tabs">
			<button
				type="button"
				onclick={() => switchTab('arm')}
				class="whitespace-nowrap border-b-2 px-1 py-2.5 text-sm font-medium transition-colors
					{activeTab === 'arm'
						? 'border-primary text-primary-text dark:border-primary-text-dark dark:text-primary-text-dark'
						: 'border-transparent text-gray-500 hover:border-primary/30 hover:text-gray-700 dark:text-gray-400 dark:hover:border-primary/30 dark:hover:text-gray-300'}"
			>
				ARM Ripper
			</button>
			{#if $transcoderEnabled}
			<button
				type="button"
				onclick={() => switchTab('transcoder')}
				class="whitespace-nowrap border-b-2 px-1 py-2.5 text-sm font-medium transition-colors
					{activeTab === 'transcoder'
						? 'border-primary text-primary-text dark:border-primary-text-dark dark:text-primary-text-dark'
						: 'border-transparent text-gray-500 hover:border-primary/30 hover:text-gray-700 dark:text-gray-400 dark:hover:border-primary/30 dark:hover:text-gray-300'}"
			>
				Transcoder
			</button>
			{/if}
		</nav>
	</div>

	{#if activeTab === 'arm'}
		<LoadState
			data={armLogs}
			loading={armLoading}
			error={armError}
			transitionKey="arm-logs-list"
		>
			{#snippet loadingSlot()}
				<div class="space-y-3">
					<SkeletonCard lines={2} />
					<SkeletonCard lines={2} />
					<SkeletonCard lines={2} />
				</div>
			{/snippet}
			{#snippet ready(items)}
				<div class="overflow-x-auto rounded-lg border border-primary/20 dark:border-primary/20">
					<table class="responsive-table w-full text-left text-sm">
						<thead class="bg-page text-gray-600 dark:bg-primary/5 dark:text-gray-400">
							<tr>
								<th class="cursor-pointer select-none px-4 py-3 font-medium" onclick={() => toggleFileSort('filename')}>
									Filename
									<span class="ml-0.5 text-[10px]">{fileSortKey === 'filename' ? (fileSortDir === 'asc' ? '▲' : '▼') : '▲▼'}</span>
								</th>
								<th class="cursor-pointer select-none px-4 py-3 font-medium" onclick={() => toggleFileSort('size')}>
									Size
									<span class="ml-0.5 text-[10px]">{fileSortKey === 'size' ? (fileSortDir === 'asc' ? '▲' : '▼') : '▲▼'}</span>
								</th>
								<th class="cursor-pointer select-none px-4 py-3 font-medium" onclick={() => toggleFileSort('modified')}>
									Last Modified
									<span class="ml-0.5 text-[10px]">{fileSortKey === 'modified' ? (fileSortDir === 'asc' ? '▲' : '▼') : '▲▼'}</span>
								</th>
								<th class="px-4 py-3 font-medium">Actions</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-gray-200 dark:divide-gray-700">
							{#each sortedArmLogs as log}
								<tr class="hover:bg-page dark:hover:bg-gray-800/50">
									<td class="px-4 py-3 break-all" data-label="Filename">
										<a href="/logs/{log.filename}" class="text-primary-text hover:underline dark:text-primary-text-dark">
											{log.filename}
										</a>
									</td>
									<td class="px-4 py-3 text-gray-500 dark:text-gray-400" data-label="Size">{formatBytes(log.size)}</td>
									<td class="px-4 py-3 text-gray-500 dark:text-gray-400" data-label="Last Modified">{formatDateTime(log.modified)}</td>
									<td class="px-4 py-3" data-label="Actions">
										<div class="flex items-center gap-1.5">
											<a
												href={logDownloadUrl(log.filename)}
												download
												class="rounded px-2 py-0.5 text-xs font-medium bg-primary-light-bg text-primary-text hover:bg-primary/25 dark:bg-primary-light-bg-dark dark:text-primary-text-dark dark:hover:bg-primary/30"
											>Download</a>
											<button
												onclick={() => handleDelete(log.filename)}
												disabled={deleting === log.filename}
												class="rounded px-2 py-0.5 text-xs font-medium bg-red-100 text-red-700 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400 dark:hover:bg-red-900/50 disabled:opacity-50"
											>
												{deleting === log.filename ? 'Deleting...' : 'Delete'}
											</button>
										</div>
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
				{#if deleteFeedback}
					<div class="mt-2 text-sm {deleteFeedback.type === 'success' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}">
						{deleteFeedback.message}
					</div>
				{/if}
			{/snippet}
			{#snippet empty()}
				<p class="py-8 text-center text-sm text-gray-500 dark:text-gray-400">No log files.</p>
			{/snippet}
		</LoadState>
	{:else}
		<LoadState
			data={transcoderLogs}
			loading={transcoderLoading}
			error={transcoderError}
			transitionKey="transcoder-logs-list"
		>
			{#snippet loadingSlot()}
				<div class="space-y-3">
					<SkeletonCard lines={2} />
					<SkeletonCard lines={2} />
					<SkeletonCard lines={2} />
				</div>
			{/snippet}
			{#snippet ready(items)}
				<div class="overflow-x-auto rounded-lg border border-primary/20 dark:border-primary/20">
					<table class="responsive-table w-full text-left text-sm">
						<thead class="bg-page text-gray-600 dark:bg-primary/5 dark:text-gray-400">
							<tr>
								<th class="cursor-pointer select-none px-4 py-3 font-medium" onclick={() => toggleFileSort('filename')}>
									Filename
									<span class="ml-0.5 text-[10px]">{fileSortKey === 'filename' ? (fileSortDir === 'asc' ? '▲' : '▼') : '▲▼'}</span>
								</th>
								<th class="cursor-pointer select-none px-4 py-3 font-medium" onclick={() => toggleFileSort('size')}>
									Size
									<span class="ml-0.5 text-[10px]">{fileSortKey === 'size' ? (fileSortDir === 'asc' ? '▲' : '▼') : '▲▼'}</span>
								</th>
								<th class="cursor-pointer select-none px-4 py-3 font-medium" onclick={() => toggleFileSort('modified')}>
									Last Modified
									<span class="ml-0.5 text-[10px]">{fileSortKey === 'modified' ? (fileSortDir === 'asc' ? '▲' : '▼') : '▲▼'}</span>
								</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-gray-200 dark:divide-gray-700">
							{#each sortedTranscoderLogs as log}
								<tr class="hover:bg-page dark:hover:bg-gray-800/50">
									<td class="px-4 py-3 break-all" data-label="Filename">
										<a href="/logs/transcoder/{log.filename}" class="text-primary-text hover:underline dark:text-primary-text-dark">
											{log.filename}
										</a>
									</td>
									<td class="px-4 py-3 text-gray-500 dark:text-gray-400" data-label="Size">{formatBytes(log.size)}</td>
									<td class="px-4 py-3 text-gray-500 dark:text-gray-400" data-label="Last Modified">{formatDateTime(log.modified)}</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/snippet}
			{#snippet empty()}
				<p class="py-8 text-center text-sm text-gray-500 dark:text-gray-400">No log files.</p>
			{/snippet}
		</LoadState>
	{/if}
</div>

<!-- Orphan Logs Modal -->
{#if orphanModalOpen}
	<div class="fixed inset-0 z-50 flex items-center justify-center">
		<button
			type="button"
			class="absolute inset-0 bg-black/50"
			aria-label="Close dialog"
			onclick={() => (orphanModalOpen = false)}
		></button>
		<div class="relative z-10 flex w-full max-w-lg flex-col rounded-lg bg-surface shadow-xl dark:bg-surface-dark" style="max-height: 80vh;">
			<!-- Header -->
			<div class="shrink-0 border-b border-gray-200 px-6 py-4 dark:border-gray-700">
				<h3 class="text-lg font-semibold text-gray-900 dark:text-white">Orphan Log Files</h3>
				<p class="mt-1 text-sm text-gray-500 dark:text-gray-400">Log files not associated with any job</p>
			</div>

			<!-- Body -->
			<div class="flex-1 overflow-y-auto px-6 py-4">
				{#if orphanFeedback}
					<div class="mb-3 rounded-lg px-3 py-2 text-sm {orphanFeedback.type === 'success' ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400' : 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400'}">
						{orphanFeedback.message}
					</div>
				{/if}

				{#if orphanLoading}
					<p class="py-8 text-center text-gray-400">Loading...</p>
				{:else if !orphanLogs || orphanLogs.files.length === 0}
					<p class="py-8 text-center text-gray-400">No orphan log files found.</p>
				{:else}
					<div class="space-y-1">
						{#each orphanLogs.files as file}
							<div class="flex items-center gap-3 rounded-lg px-3 py-2 hover:bg-gray-50 dark:hover:bg-gray-800/50">
								<input
									type="checkbox"
									checked={orphanSelected.has(file.path)}
									onchange={() => toggleOrphanSelect(file.path)}
									class="size-4 rounded border-gray-300 text-primary focus:ring-primary dark:border-gray-600"
								/>
								<div class="min-w-0 flex-1">
									<p class="truncate text-sm font-medium text-gray-900 dark:text-white">{file.relative_path}</p>
									<p class="text-xs text-gray-500 dark:text-gray-400">{formatBytes(file.size_bytes)}</p>
								</div>
								<button
									type="button"
									disabled={orphanBusy}
									onclick={() => handleDeleteOrphan(file.path)}
									class="shrink-0 rounded px-2 py-0.5 text-xs font-medium bg-red-100 text-red-700 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400 dark:hover:bg-red-900/50 disabled:opacity-50"
								>
									Delete
								</button>
							</div>
						{/each}
					</div>
				{/if}
			</div>

			<!-- Footer -->
			<div class="shrink-0 border-t border-gray-200 px-6 py-4 dark:border-gray-700">
				<div class="flex items-center justify-between">
					{#if orphanSelected.size > 0}
						<button
							type="button"
							disabled={orphanBusy}
							onclick={handleBulkDeleteOrphans}
							class="rounded-lg bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
						>
							Delete {orphanSelected.size} selected
						</button>
					{:else}
						<div></div>
					{/if}
					<button
						type="button"
						onclick={() => (orphanModalOpen = false)}
						class="rounded-lg px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
					>
						Close
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}
