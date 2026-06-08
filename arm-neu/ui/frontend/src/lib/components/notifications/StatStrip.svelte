<script lang="ts">
	let { total, issues, subscribedEvents }: { total: number; issues: number; subscribedEvents: number } = $props();
	const issueClass = $derived(issues > 0 ? 'text-status-error' : 'text-status-success');
</script>

<div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
	<div class="rounded-lg border border-primary/15 bg-page p-4 dark:border-primary/20 dark:bg-primary/5">
		<p class="text-[10.5px] font-semibold uppercase tracking-[0.12em] text-gray-500 dark:text-gray-400">Channels</p>
		<p class="mt-1 text-2xl font-semibold text-primary">{total}</p>
	</div>
	<div class="rounded-lg border border-primary/15 bg-page p-4 dark:border-primary/20 dark:bg-primary/5">
		<p class="text-[10.5px] font-semibold uppercase tracking-[0.12em] text-gray-500 dark:text-gray-400">Issues</p>
		<p class="mt-1 text-2xl font-semibold {issueClass}">{issues}</p>
	</div>
	<div class="rounded-lg border border-primary/15 bg-page p-4 dark:border-primary/20 dark:bg-primary/5">
		<p class="text-[10.5px] font-semibold uppercase tracking-[0.12em] text-gray-500 dark:text-gray-400">Subscribed events</p>
		<p class="mt-1 text-2xl font-semibold text-gray-700 dark:text-gray-200">{subscribedEvents}</p>
	</div>
</div>
