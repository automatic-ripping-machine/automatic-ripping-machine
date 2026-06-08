<script lang="ts">
	import type { LogContentResponse as LogContent } from '$lib/types/api.gen';
	import { fetchLogContent } from '$lib/api/logs';

	interface Props {
		filename: string;
		mode?: 'tail' | 'full';
		lines?: number;
		autoRefresh?: boolean;
		refreshInterval?: number;
		fetchFn?: (filename: string, mode: 'tail' | 'full', lines: number) => Promise<LogContent>;
	}

	let { filename, mode = 'tail', lines = 200, autoRefresh = true, refreshInterval = 5000, fetchFn = fetchLogContent }: Props = $props();

	let content = $state('');
	let error = $state<string | null>(null);
	let loading = $state(true);
	let container = $state<HTMLPreElement | undefined>(undefined);

	async function load() {
		try {
			const data = await fetchFn(filename, mode, lines);
			content = data.content;
			error = null;
			const el = container;
			if (mode === 'tail' && el) {
				requestAnimationFrame(() => {
					el.scrollTop = el.scrollHeight;
				});
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load log';
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		// Re-run when filename, mode, or lines changes
		filename; mode; lines;
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

{#if error}
	<div class="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
		{error}
	</div>
{:else if loading && !content}
	<div class="flex items-center justify-center p-8 text-gray-400">
		<svg class="mr-2 h-5 w-5 animate-spin" viewBox="0 0 24 24">
			<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" />
			<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
		</svg>
		Loading...
	</div>
{:else}
	<pre
		bind:this={container}
		class="max-h-[70vh] overflow-auto rounded-lg bg-gray-900 p-4 font-mono text-xs leading-relaxed text-gray-300"
	>{content}</pre>
{/if}
