<script lang="ts">
	import type { FileRoot } from '$lib/types/api.gen';
	interface Props {
		path: string;
		roots: FileRoot[];
		onnavigate: (path: string) => void;
	}

	let { path, roots, onnavigate }: Props = $props();

	let segments = $derived.by(() => {
		// Find which root this path belongs to
		const root = roots.find(
			(r) => path === r.path || path.startsWith(r.path + '/')
		);
		if (!root) return [];

		const result: { label: string; path: string }[] = [
			{ label: root.label, path: root.path }
		];

		if (path !== root.path) {
			const relative = path.slice(root.path.length + 1);
			const parts = relative.split('/');
			let current = root.path;
			for (const part of parts) {
				current += '/' + part;
				result.push({ label: part, path: current });
			}
		}

		return result;
	});
</script>

<nav class="flex items-center gap-1 text-sm text-gray-600 dark:text-gray-400">
	{#each segments as segment, i}
		{#if i > 0}
			<svg class="h-4 w-4 shrink-0 text-gray-400 dark:text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
			</svg>
		{/if}
		{#if i === segments.length - 1}
			<span class="font-medium text-gray-900 dark:text-white">{segment.label}</span>
		{:else}
			<button
				type="button"
				onclick={() => onnavigate(segment.path)}
				class="transition-colors hover:text-primary dark:hover:text-primary-text-dark"
			>
				{segment.label}
			</button>
		{/if}
	{/each}
</nav>
