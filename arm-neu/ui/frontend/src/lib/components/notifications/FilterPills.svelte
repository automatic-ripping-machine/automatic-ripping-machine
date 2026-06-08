<script lang="ts">
	export type ChannelFilter = 'all' | 'enabled' | 'paused' | 'issues';
	let {
		active,
		counts,
		onselect
	}: {
		active: ChannelFilter;
		counts: Record<ChannelFilter, number>;
		onselect?: (f: ChannelFilter) => void;
	} = $props();

	const pills: { key: ChannelFilter; label: string }[] = [
		{ key: 'all', label: 'All' },
		{ key: 'enabled', label: 'Enabled' },
		{ key: 'paused', label: 'Paused' },
		{ key: 'issues', label: 'Issues' }
	];
</script>

<div class="inline-flex gap-1 rounded-md border border-primary/15 bg-page p-0.5 dark:border-primary/20 dark:bg-primary/5">
	{#each pills as p}
		<button
			type="button"
			onclick={() => onselect?.(p.key)}
			class="rounded px-2.5 py-1 text-xs font-medium {active === p.key
				? 'bg-primary/15 text-primary'
				: 'text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200'}"
		>{p.label} · {counts[p.key]}</button>
	{/each}
</div>
