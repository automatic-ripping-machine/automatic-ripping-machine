<script lang="ts">
	import type { DriveSchema as Drive } from '$lib/types/api.gen';
	import { onMount } from 'svelte';
	import DiscTypeIcon from '$lib/components/DiscTypeIcon.svelte';

	let drives = $state<Drive[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	async function loadDrives() {
		loading = true;
		error = null;
		try {
			const resp = await fetch('/api/drives');
			if (resp.ok) {
				drives = await resp.json();
			} else {
				error = 'Failed to load drives';
			}
		} catch {
			error = 'Could not reach the server';
		} finally {
			loading = false;
		}
	}

	onMount(() => { loadDrives(); });
</script>

<div class="space-y-6">
	<div class="text-center">
		<h2 class="text-2xl font-bold text-gray-900 dark:text-white">Optical Drives</h2>
		<p class="mt-2 text-gray-600 dark:text-gray-400">
			ARM detects your optical drives automatically.
		</p>
	</div>

	{#if loading}
		<div class="py-8 text-center text-gray-400">Scanning for drives...</div>
	{:else if error}
		<div class="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
			{error}
		</div>
	{:else if drives.length === 0}
		<div class="rounded-lg border border-primary/20 bg-surface p-6 text-center dark:border-primary/20 dark:bg-surface-dark">
			<svg class="mx-auto h-12 w-12 text-gray-300 dark:text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
				<circle cx="12" cy="12" r="10" />
				<circle cx="12" cy="12" r="3" />
			</svg>
			<p class="mt-3 text-sm font-medium text-gray-500 dark:text-gray-400">
				No optical drives detected
			</p>
			<p class="mt-1 text-xs text-gray-400 dark:text-gray-500">
				ARM will detect drives when they become available. This is normal in VM or NAS environments.
			</p>
		</div>
	{:else}
		<div class="space-y-3">
			{#each drives as drive}
				<div class="rounded-lg border border-primary/20 bg-surface p-4 dark:border-primary/20 dark:bg-surface-dark">
					<div class="flex items-center justify-between">
						<h3 class="font-semibold text-gray-900 dark:text-white">
							{drive.name || drive.mount || `Drive ${drive.drive_id}`}
						</h3>
					</div>
					{#if drive.maker || drive.model}
						<p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
							{[drive.maker, drive.model].filter(Boolean).join(' ')}
						</p>
					{/if}
					<div class="mt-2 flex flex-wrap gap-1.5">
						{#if drive.capabilities?.includes('CD')}
							<span class="inline-flex items-center gap-1 rounded-sm bg-green-500/20 px-1.5 py-0.5 text-xs text-green-700 dark:text-green-400">
								<DiscTypeIcon disctype="music" size="h-3.5 w-3.5" />CD
							</span>
						{/if}
						{#if drive.capabilities?.includes('DVD')}
							<span class="inline-flex items-center gap-1 rounded-sm bg-primary/15 px-1.5 py-0.5 text-xs text-primary-text dark:text-primary-text-dark">
								<DiscTypeIcon disctype="dvd" size="h-3.5 w-3.5" />DVD
							</span>
						{/if}
						{#if drive.capabilities?.includes('BD')}
							<span class="inline-flex items-center gap-1 rounded-sm bg-purple-500/20 px-1.5 py-0.5 text-xs text-purple-700 dark:text-purple-400">
								<DiscTypeIcon disctype="bluray" size="h-3.5 w-3.5" />Blu-ray
							</span>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	{/if}

	<div class="text-center">
		<button
			type="button"
			onclick={loadDrives}
			disabled={loading}
			class="rounded-lg px-4 py-2 text-sm font-medium bg-primary/15 text-primary-text hover:bg-primary/25 dark:text-primary-text-dark dark:hover:bg-primary/30 disabled:opacity-50 transition-colors"
		>
			{loading ? 'Scanning...' : 'Scan Again'}
		</button>
	</div>
</div>
