<script lang="ts">
	import Skeleton from './Skeleton.svelte';

	interface Props {
		class?: string;
		lines?: number;
	}
	let { class: cls = '', lines = 3 }: Props = $props();
</script>

<div
	class="rounded-lg border border-primary/20 bg-surface p-4 space-y-3 dark:border-primary/20 dark:bg-surface-dark {cls}"
	aria-busy="true"
	aria-live="polite"
>
	<Skeleton variant="line" width="60%" height="1.25rem" />
	{#each { length: Math.max(0, lines - 1) } as _}
		<Skeleton variant="line" width="100%" height="0.875rem" />
	{/each}
</div>
