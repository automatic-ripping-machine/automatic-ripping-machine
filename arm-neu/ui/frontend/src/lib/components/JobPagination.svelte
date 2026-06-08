<script lang="ts">
	interface Props {
		page: number;
		pages: number;
		perPage: number;
		total: number;
		onpage: (page: number) => void;
	}

	let { page, pages, perPage, total, onpage }: Props = $props();
</script>

{#if pages > 1}
	<div class="flex items-center justify-between">
		<p class="text-sm text-gray-500 dark:text-gray-400">
			Showing {(page - 1) * perPage + 1}&ndash;{Math.min(page * perPage, total)} of {total}
		</p>
		<div class="flex gap-1">
			<button
				disabled={page <= 1}
				onclick={() => onpage(page - 1)}
				class="rounded-sm px-3 py-1 text-sm disabled:opacity-50 bg-primary/15 dark:bg-primary/15 dark:text-gray-300"
			>Prev</button>
			{#each Array.from({ length: pages }, (_, i) => i + 1) as p}
				{#if p === page || p === 1 || p === pages || Math.abs(p - page) <= 1}
					<button
						onclick={() => onpage(p)}
						class="rounded-sm px-3 py-1 text-sm {p === page ? 'bg-primary text-on-primary' : 'bg-primary/15 dark:bg-primary/15 dark:text-gray-300'}"
					>{p}</button>
				{:else if Math.abs(p - page) === 2}
					<span class="px-1 text-gray-400">...</span>
				{/if}
			{/each}
			<button
				disabled={page >= pages}
				onclick={() => onpage(page + 1)}
				class="rounded-sm px-3 py-1 text-sm disabled:opacity-50 bg-primary/15 dark:bg-primary/15 dark:text-gray-300"
			>Next</button>
		</div>
	</div>
{/if}
