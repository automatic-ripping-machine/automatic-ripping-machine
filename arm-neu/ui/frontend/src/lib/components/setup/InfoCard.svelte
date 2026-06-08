<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		label: string;
		children: Snippet;
	}

	let { label, children }: Props = $props();
</script>

<div class="rounded-lg border border-primary/20 bg-surface p-4 dark:border-primary/20 dark:bg-surface-dark">
	<div class="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">{label}</div>
	<div class="mt-1">
		{@render children()}
	</div>
</div>
