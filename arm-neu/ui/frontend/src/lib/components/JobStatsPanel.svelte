<script lang="ts">
	import type { JobStats } from '$lib/api/jobs';

	interface Props {
		stats?: JobStats;
		statusFilter: string;
		onfilter: (value: string) => void;
	}

	let { stats, statusFilter, onfilter }: Props = $props();

	const cards = [
		{ key: 'total' as const, label: 'Total', filter: '', border: 'border-l-indigo-500', bg: 'bg-indigo-50 dark:bg-indigo-900/20', text: 'text-indigo-700 dark:text-indigo-300' },
		{ key: 'active' as const, label: 'Active', filter: 'active', border: 'border-l-blue-500', bg: 'bg-blue-50 dark:bg-blue-900/20', text: 'text-blue-700 dark:text-blue-300' },
		{ key: 'success' as const, label: 'Success', filter: 'success', border: 'border-l-green-500', bg: 'bg-green-50 dark:bg-green-900/20', text: 'text-green-700 dark:text-green-300' },
		{ key: 'fail' as const, label: 'Failed', filter: 'fail', border: 'border-l-red-500', bg: 'bg-red-50 dark:bg-red-900/20', text: 'text-red-700 dark:text-red-300' },
		{ key: 'waiting' as const, label: 'Waiting', filter: 'waiting', border: 'border-l-amber-500', bg: 'bg-amber-50 dark:bg-amber-900/20', text: 'text-amber-700 dark:text-amber-300' }
	];
</script>

<div class="flex flex-wrap gap-3">
	{#each cards as card}
		<button
			onclick={() => onfilter(card.filter)}
			class="flex min-w-[120px] flex-1 cursor-pointer items-center gap-3 rounded-lg border-l-4 {card.border} {card.bg} px-4 py-3 transition-shadow hover:shadow-md {statusFilter === card.filter ? 'ring-2 ring-primary/40' : ''}"
		>
			<div>
				<div class="text-2xl font-bold {card.text}">{stats ? stats[card.key] : '—'}</div>
				<div class="text-xs font-medium text-gray-500 dark:text-gray-400">{card.label}</div>
			</div>
		</button>
	{/each}
</div>
