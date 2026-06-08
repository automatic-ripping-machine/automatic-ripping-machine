<script lang="ts">
	interface Props {
		steps: { id: string; label: string }[];
		currentIndex: number;
	}

	let { steps, currentIndex }: Props = $props();
</script>

<nav class="flex items-center justify-center gap-2" aria-label="Setup progress">
	{#each steps as step, i}
		{#if i > 0}
			<div class="h-px w-8 {i <= currentIndex ? 'bg-primary' : 'bg-gray-300 dark:bg-gray-600'}"></div>
		{/if}
		<div class="flex items-center gap-2">
			<div
				class="flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium transition-colors
					{i < currentIndex
					? 'bg-primary text-on-primary'
					: i === currentIndex
						? 'bg-primary text-on-primary ring-2 ring-primary/30'
						: 'bg-gray-200 text-gray-500 dark:bg-gray-700 dark:text-gray-400'}"
			>
				{#if i < currentIndex}
					<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
					</svg>
				{:else}
					{i + 1}
				{/if}
			</div>
			<span class="hidden text-sm font-medium sm:inline
				{i <= currentIndex ? 'text-gray-900 dark:text-white' : 'text-gray-400 dark:text-gray-500'}">
				{step.label}
			</span>
		</div>
	{/each}
</nav>
