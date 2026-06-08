<script lang="ts">
	import { page } from '$app/stores';
	import StructuredLogViewer from '$lib/components/StructuredLogViewer.svelte';

	let mode = $state<'tail' | 'full'>('tail');
	let lines = $state(200);

	const filename = $derived($page.params.filename ?? '');
</script>

<svelte:head>
	<title>ARM - {filename}</title>
</svelte:head>

<div class="space-y-4">
	<div class="flex flex-wrap items-center justify-between gap-4">
		<div class="flex items-center gap-3">
			<a href="/logs" class="inline-flex items-center gap-1 text-sm text-primary-text hover:underline dark:text-primary-text-dark">
				<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
				</svg>
				Logs
			</a>
			<h1 class="text-xl font-bold text-gray-900 dark:text-white">{filename}</h1>
		</div>
		<div class="flex gap-2">
			<button
				onclick={() => mode = 'tail'}
				class="rounded-lg px-3 py-1.5 text-sm {mode === 'tail' ? 'bg-primary text-on-primary' : 'bg-primary/15 text-gray-700 dark:bg-primary/15 dark:text-gray-300'}"
			>Tail</button>
			<button
				onclick={() => mode = 'full'}
				class="rounded-lg px-3 py-1.5 text-sm {mode === 'full' ? 'bg-primary text-on-primary' : 'bg-primary/15 text-gray-700 dark:bg-primary/15 dark:text-gray-300'}"
			>Full</button>
		</div>
	</div>

	<StructuredLogViewer {filename} {mode} {lines} autoRefresh={mode === 'tail'} />
</div>
