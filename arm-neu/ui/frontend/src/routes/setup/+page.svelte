<script lang="ts">
	import type { SetupStatus } from '$lib/types/api.gen';
	import SetupWizard from '$lib/components/setup/SetupWizard.svelte';

	let { data }: { data: { status: SetupStatus | null } } = $props();
</script>

<svelte:head>
	<title>ARM - Setup</title>
</svelte:head>

<div class="min-h-screen bg-page dark:bg-page-dark">
	{#if data.status}
		<SetupWizard status={data.status} />
	{:else}
		<div class="flex min-h-screen items-center justify-center">
			<div class="rounded-lg border border-red-200 bg-red-50 p-6 text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
				Failed to load setup status
			</div>
		</div>
	{/if}
</div>
