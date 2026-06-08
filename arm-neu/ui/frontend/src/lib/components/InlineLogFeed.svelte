<script lang="ts">
	import type { LogEntrySchema as LogEntry, StructuredLogResponse as StructuredLogContent } from '$lib/types/api.gen';
	import { fetchStructuredLogContent } from '$lib/api/logs';

	interface Props {
		logfile: string;
		maxEntries?: number;
		levelFilter?: string;
		autoRefresh?: boolean;
		containerClass?: string;
		fetchFn?: (
			filename: string,
			mode: 'tail' | 'full',
			lines: number,
			level?: string,
			search?: string
		) => Promise<StructuredLogContent>;
		logLinkBase?: string;
		title?: string;
	}

	let {
		logfile,
		maxEntries = 10,
		levelFilter,
		autoRefresh = true,
		containerClass,
		fetchFn = fetchStructuredLogContent,
		logLinkBase = '/logs',
		title = 'Recent Log',
	}: Props = $props();

	let entries = $state<LogEntry[]>([]);
	let error = $state<string | null>(null);
	let loading = $state(true);
	let expanded = $state(false);

	// User-facing filter state. Starts from the levelFilter prop but is
	// overwritable from the filter bar. Server-side filtering (backend honors
	// level and search query params); we debounce the search input to avoid
	// hammering the server as the user types.
	let activeLevel = $state<string>(levelFilter ?? '');
	let searchInput = $state<string>('');
	let activeSearch = $state<string>('');
	let searchDebounce: ReturnType<typeof setTimeout> | null = null;
	let hasFilter = $derived(!!activeLevel || !!activeSearch);

	function onLevelChange(e: Event) {
		activeLevel = (e.target as HTMLSelectElement).value;
		load();
	}

	function onSearchInput(e: Event) {
		const val = (e.target as HTMLInputElement).value;
		searchInput = val;
		if (searchDebounce) clearTimeout(searchDebounce);
		searchDebounce = setTimeout(() => { activeSearch = val.trim(); load(); }, 300);
	}

	function clearFilters() {
		activeLevel = '';
		searchInput = '';
		activeSearch = '';
		if (searchDebounce) { clearTimeout(searchDebounce); searchDebounce = null; }
		load();
	}

	let errorCount = $derived(entries.filter((e) => e.level === 'error' || e.level === 'critical').length);
	let warningCount = $derived(entries.filter((e) => e.level === 'warning').length);

	const LEVEL_OPTIONS = [
		{ value: '', label: 'All levels' },
		{ value: 'debug', label: 'Debug+' },
		{ value: 'info', label: 'Info+' },
		{ value: 'warning', label: 'Warning+' },
		{ value: 'error', label: 'Error+' },
		{ value: 'critical', label: 'Critical' },
	];

	const levelBadgeColors: Record<string, string> = {
		error: 'bg-red-900/60 text-red-300',
		critical: 'bg-red-900/60 text-red-300',
		warning: 'bg-yellow-900/60 text-yellow-300',
		info: 'bg-emerald-900/40 text-emerald-400',
		debug: 'bg-gray-700/60 text-gray-400',
	};

	const borderColors: Record<string, string> = {
		error: 'border-l-red-500',
		critical: 'border-l-red-500',
		warning: 'border-l-yellow-500',
		info: 'border-l-transparent',
		debug: 'border-l-transparent',
	};

	let failCount = $state(0);
	const MAX_FAILURES = 3;

	async function load() {
		if (failCount >= MAX_FAILURES) return;
		try {
			const data = await fetchFn(
				logfile,
				'tail',
				maxEntries,
				activeLevel || undefined,
				activeSearch || undefined
			);
			entries = data.entries.toReversed();
			error = null;
			failCount = 0;
		} catch (e) {
			const msg = e instanceof Error ? e.message : 'Failed to load log';
			if (msg.includes('404')) {
				failCount++;
				if (failCount >= MAX_FAILURES) {
					if (timer) { clearInterval(timer); timer = null; }
				}
			}
			error = msg;
		} finally {
			loading = false;
		}
	}

	// Track the last logfile we reset state for, so we only reset on actual
	// logfile changes (not on every filter change that might re-run the
	// surrounding effect).
	let lastResetLogfile = '';
	$effect(() => {
		// Reset stale state whenever the target log file changes. Without this,
		// navigating from one job's detail page to another would flash the
		// previous job's entries while the new fetch 404s, or permanently
		// freeze after MAX_FAILURES with no way to recover. Filter state is
		// also cleared so a fresh job starts unfiltered.
		const currentLogfile = logfile;
		if (currentLogfile !== lastResetLogfile) {
			lastResetLogfile = currentLogfile;
			entries = [];
			error = null;
			failCount = 0;
			activeLevel = levelFilter ?? '';
			searchInput = '';
			activeSearch = '';
		}
		maxEntries; // track as dep
		loading = true;
		load();
	});

	let timer: ReturnType<typeof setInterval> | null = null;
	$effect(() => {
		if (autoRefresh) {
			timer = setInterval(load, 5000);
		}
		return () => {
			if (timer) clearInterval(timer);
		};
	});
</script>

{#if error && !error.includes('404')}
	<div class={containerClass ?? ''}>
		<div class="text-sm text-red-400">{error}</div>
	</div>
{:else if entries.length > 0 || hasFilter}
	<div class={containerClass ?? ''}>
		<div class="rounded-lg border border-gray-200 dark:border-gray-700">
			<!-- Summary header -->
			<button
				onclick={() => (expanded = !expanded)}
				class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition-colors hover:bg-gray-50 dark:hover:bg-gray-800/50"
			>
				<svg
					class="h-4 w-4 text-gray-400 transition-transform {expanded ? 'rotate-90' : ''}"
					fill="none" stroke="currentColor" viewBox="0 0 24 24"
				>
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
				</svg>
				<span class="font-medium text-gray-700 dark:text-gray-300">{title}</span>
				{#if hasFilter}
					<span class="rounded-sm bg-primary/10 px-1.5 py-0.5 text-xs font-medium text-primary-text dark:bg-primary/15 dark:text-primary-text-dark">
						filtered
					</span>
				{/if}
				{#if errorCount > 0}
					<span class="rounded-sm bg-red-100 px-1.5 py-0.5 text-xs font-medium text-red-700 dark:bg-red-900/30 dark:text-red-400">
						{errorCount} error{errorCount !== 1 ? 's' : ''}
					</span>
				{/if}
				{#if warningCount > 0}
					<span class="rounded-sm bg-yellow-100 px-1.5 py-0.5 text-xs font-medium text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400">
						{warningCount} warning{warningCount !== 1 ? 's' : ''}
					</span>
				{/if}
				<span class="ml-auto text-xs text-gray-400">{entries.length} entries</span>
			</button>

			{#if expanded}
				<div class="border-t border-gray-200 dark:border-gray-700">
					<!-- Filter bar -->
					<div class="flex flex-wrap items-center gap-2 border-b border-gray-100 bg-gray-50 px-3 py-2 dark:border-gray-800 dark:bg-gray-800/30">
						<label class="flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-400">
							<span>Level</span>
							<select
								value={activeLevel}
								onchange={onLevelChange}
								aria-label="Minimum log level"
								class="rounded border border-gray-300 bg-white px-1.5 py-0.5 text-xs dark:border-gray-600 dark:bg-gray-900 dark:text-gray-200"
							>
								{#each LEVEL_OPTIONS as opt}
									<option value={opt.value}>{opt.label}</option>
								{/each}
							</select>
						</label>
						<label class="flex flex-1 items-center gap-1.5 text-xs text-gray-600 dark:text-gray-400">
							<span class="sr-only">Search log entries</span>
							<input
								type="search"
								value={searchInput}
								oninput={onSearchInput}
								placeholder="Search..."
								aria-label="Search log entries"
								class="min-w-0 flex-1 rounded border border-gray-300 bg-white px-2 py-0.5 text-xs dark:border-gray-600 dark:bg-gray-900 dark:text-gray-200"
							/>
						</label>
						{#if hasFilter}
							<button
								type="button"
								onclick={clearFilters}
								class="rounded px-2 py-0.5 text-xs text-gray-600 hover:bg-gray-200 dark:text-gray-400 dark:hover:bg-gray-700"
							>
								Clear
							</button>
						{/if}
					</div>
					<div class="max-h-64 overflow-auto">
						{#if entries.length === 0}
							<div class="px-3 py-3 text-center text-xs text-gray-500 dark:text-gray-400">
								{#if hasFilter}
									No entries match the current filter.
								{:else}
									No entries.
								{/if}
							</div>
						{:else}
							{#each entries as entry}
								<div class="flex items-start gap-2 border-b border-l-2 border-b-gray-100 px-3 py-1.5 font-mono text-xs dark:border-b-gray-800 {borderColors[entry.level] ?? 'border-l-transparent'}">
									<span class="inline-block w-12 shrink-0 rounded px-1 py-0.5 text-center text-[10px] font-semibold uppercase {levelBadgeColors[entry.level] ?? 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'}">
										{entry.level}
									</span>
									{#if entry.timestamp}
										<span class="shrink-0 text-gray-400">{entry.timestamp.replace('T', ' ').replace('Z', '').slice(11, 19)}</span>
									{/if}
									<span class="min-w-0 break-words text-gray-700 dark:text-gray-300">{entry.event}</span>
								</div>
							{/each}
						{/if}
					</div>
					<div class="border-t border-gray-200 px-3 py-2 dark:border-gray-700">
						<a
							href="{logLinkBase}/{logfile}"
							class="text-xs text-primary-text hover:underline dark:text-primary-text-dark"
						>
							View full log &rarr;
						</a>
					</div>
				</div>
			{/if}
		</div>
	</div>
{/if}
