<script lang="ts">
	import type { LogEntrySchema as LogEntry, StructuredLogResponse as StructuredLogContent } from '$lib/types/api.gen';
	import { fetchStructuredLogContent } from '$lib/api/logs';

	type FetchFn = (
		filename: string,
		mode: 'tail' | 'full',
		lines: number,
		level?: string,
		search?: string
	) => Promise<StructuredLogContent>;

	interface Props {
		filename: string;
		mode?: 'tail' | 'full';
		lines?: number;
		autoRefresh?: boolean;
		refreshInterval?: number;
		fetchFn?: FetchFn;
	}

	let {
		filename,
		mode = 'tail',
		lines = 200,
		autoRefresh = true,
		refreshInterval = 5000,
		fetchFn = fetchStructuredLogContent,
	}: Props = $props();

	let entries = $state<LogEntry[]>([]);
	let error = $state<string | null>(null);
	let loading = $state(true);
	let levelFilter = $state<string>('');
	let searchQuery = $state('');
	let searchInput = $state('');
	let searchTimeout: ReturnType<typeof setTimeout> | null = null;

	type SortableKey = 'timestamp' | 'level' | 'logger' | 'event';
	let sortKey = $state<SortableKey | ''>('');
	let sortDir = $state<'asc' | 'desc'>('asc');

	function toggleSort(key: SortableKey) {
		if (sortKey === key) {
			sortDir = sortDir === 'asc' ? 'desc' : 'asc';
		} else {
			sortKey = key;
			sortDir = key === 'timestamp' ? 'desc' : 'asc';
		}
	}

	let sortedEntries = $derived.by(() => {
		if (!sortKey) return entries;
		const k = sortKey;
		return [...entries].sort((a, b) => {
			const av = a[k] ?? '';
			const bv = b[k] ?? '';
			const cmp = String(av).localeCompare(String(bv));
			return sortDir === 'asc' ? cmp : -cmp;
		});
	});

	const levelColors: Record<string, string> = {
		error: 'border-l-red-500 bg-red-950/30',
		critical: 'border-l-red-500 bg-red-950/30',
		warning: 'border-l-yellow-500 bg-yellow-950/20',
		info: 'border-l-emerald-500/50',
		debug: 'border-l-gray-600',
	};

	const levelBadgeColors: Record<string, string> = {
		error: 'bg-red-900/60 text-red-300',
		critical: 'bg-red-900/60 text-red-300',
		warning: 'bg-yellow-900/60 text-yellow-300',
		info: 'bg-emerald-900/40 text-emerald-400',
		debug: 'bg-gray-700/60 text-gray-400',
	};

	function handleSearchInput(value: string) {
		searchInput = value;
		if (searchTimeout) clearTimeout(searchTimeout);
		searchTimeout = setTimeout(() => {
			searchQuery = searchInput;
		}, 300);
	}

	async function load() {
		try {
			const data = await fetchFn(
				filename,
				mode,
				lines,
				levelFilter || undefined,
				searchQuery || undefined
			);
			entries = data.entries.toReversed();
			error = null;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load log';
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		filename; mode; lines; levelFilter; searchQuery;
		loading = true;
		load();
	});

	let timer: ReturnType<typeof setInterval> | null = null;
	$effect(() => {
		if (autoRefresh && mode === 'tail') {
			timer = setInterval(load, refreshInterval);
		}
		return () => {
			if (timer) clearInterval(timer);
		};
	});
</script>

<!-- Filters -->
<div class="mb-3 flex flex-wrap items-center gap-3">
	<select
		bind:value={levelFilter}
		class="rounded-lg border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-gray-300 focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary"
	>
		<option value="">All Levels</option>
		<option value="error">Error</option>
		<option value="warning">Warning</option>
		<option value="info">Info</option>
		<option value="debug">Debug</option>
	</select>
	<div class="relative flex-1">
		<input
			type="text"
			value={searchInput}
			oninput={(e) => handleSearchInput(e.currentTarget.value)}
			placeholder="Search log events..."
			class="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-1.5 pl-8 text-sm text-gray-300 placeholder-gray-500 focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary"
		/>
		<svg class="absolute left-2.5 top-2 h-4 w-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
		</svg>
	</div>
	{#if entries.length > 0}
		<span class="text-xs text-gray-500">{entries.length} entries</span>
	{/if}
</div>

{#if error}
	<div class="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
		{error}
	</div>
{:else if loading && entries.length === 0}
	<div class="flex items-center justify-center p-8 text-gray-400">
		<svg class="mr-2 h-5 w-5 animate-spin" viewBox="0 0 24 24">
			<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" />
			<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
		</svg>
		Loading...
	</div>
{:else}
	<div class="max-h-[70vh] overflow-auto rounded-lg bg-gray-900">
		<table class="w-full text-left text-xs">
			<thead class="sticky top-0 bg-gray-800 text-gray-400">
				<tr>
					<th class="w-[140px] cursor-pointer select-none px-3 py-2 font-medium" onclick={() => toggleSort('timestamp')}>
						Time
						<span class="ml-0.5 text-[10px]">{sortKey === 'timestamp' ? (sortDir === 'asc' ? '▲' : '▼') : '▲▼'}</span>
					</th>
					<th class="w-[60px] cursor-pointer select-none px-2 py-2 font-medium" onclick={() => toggleSort('level')}>
						Level
						<span class="ml-0.5 text-[10px]">{sortKey === 'level' ? (sortDir === 'asc' ? '▲' : '▼') : '▲▼'}</span>
					</th>
					<th class="w-[160px] cursor-pointer select-none px-2 py-2 font-medium" onclick={() => toggleSort('logger')}>
						Logger
						<span class="ml-0.5 text-[10px]">{sortKey === 'logger' ? (sortDir === 'asc' ? '▲' : '▼') : '▲▼'}</span>
					</th>
					<th class="cursor-pointer select-none px-3 py-2 font-medium" onclick={() => toggleSort('event')}>
						Event
						<span class="ml-0.5 text-[10px]">{sortKey === 'event' ? (sortDir === 'asc' ? '▲' : '▼') : '▲▼'}</span>
					</th>
					<th class="w-[80px] px-2 py-2 font-medium">Context</th>
				</tr>
			</thead>
			<tbody class="font-mono">
				{#each sortedEntries as entry}
					<tr class="border-l-2 border-b border-b-gray-800/50 {levelColors[entry.level] ?? 'border-l-gray-700'}">
						<td class="whitespace-nowrap px-3 py-1.5 text-gray-500">
							{#if entry.timestamp}
								{entry.timestamp.replace('T', ' ').replace('Z', '').slice(0, 19)}
							{/if}
						</td>
						<td class="px-2 py-1.5">
							<span class="inline-block rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase {levelBadgeColors[entry.level] ?? 'bg-gray-700 text-gray-400'}">
								{entry.level}
							</span>
						</td>
						<td class="max-w-[160px] truncate px-2 py-1.5 text-gray-500">
							{entry.logger.replace('arm.', '')}
						</td>
						<td class="px-3 py-1.5 text-gray-300">
							{entry.event}
						</td>
						<td class="whitespace-nowrap px-2 py-1.5 text-gray-600">
							{#if entry.job_id != null}
								<span title="Job #{entry.job_id}">#{entry.job_id}</span>
							{/if}
							{#if entry.label}
								<span class="ml-1" title="Label: {entry.label}">{entry.label}</span>
							{/if}
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
{/if}
