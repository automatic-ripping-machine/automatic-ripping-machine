<script lang="ts">
	import type { DispatchRow } from '$lib/types/notifications';

	let { rows }: { rows: DispatchRow[] } = $props();

	function statusIcon(status: DispatchRow['status']): string {
		if (status === 'success') return '✓';
		if (status === 'failed') return '⚠';
		return '⏱';
	}
</script>

{#if rows.length === 0}
	<p class="text-sm text-gray-500 dark:text-gray-400">No sends yet.</p>
{:else}
	<ul class="space-y-1">
		{#each rows as row (row.id)}
			<li class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
				<span
					class:text-status-success={row.status === 'success'}
					class:text-status-error={row.status === 'failed'}
					class:text-gray-400={row.status !== 'success' && row.status !== 'failed'}
				>{statusIcon(row.status)}</span>
				<span class="font-medium">{row.event_key}</span>
				<span class="text-gray-400">{row.created_at ?? ''}</span>
				{#if row.last_error}
					<span class="text-status-error">· {row.last_error}</span>
				{/if}
			</li>
		{/each}
	</ul>
{/if}
