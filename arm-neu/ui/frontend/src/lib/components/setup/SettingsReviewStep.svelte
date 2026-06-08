<script lang="ts">
	import { onMount } from 'svelte';
	import { transcoderEnabled } from '$lib/stores/config';

	let settings = $state<Record<string, string | null> | null>(null);
	let loading = $state(true);

	const allKeyPaths = [
		{ key: 'RAW_PATH', label: 'Raw Path', desc: 'Where ripped files are stored temporarily' },
		{ key: 'COMPLETED_PATH', label: 'Completed Path', desc: 'Where finished media files are moved' },
		{ key: 'TRANSCODE_PATH', label: 'Transcode Path', desc: 'Working directory for transcoding' },
		{ key: 'RIPMETHOD', label: 'Rip Method', desc: 'How discs are ripped (mkv or backup)' },
		{ key: 'METADATA_PROVIDER', label: 'Metadata Provider', desc: 'Service for looking up movie/show info' },
	];
	const keyPaths = $derived(
		$transcoderEnabled ? allKeyPaths : allKeyPaths.filter(k => k.key !== 'TRANSCODE_PATH')
	);

	onMount(async () => {
		try {
			const resp = await fetch('/api/settings');
			if (resp.ok) {
				const data = await resp.json();
				settings = data.arm_config;
			}
		} catch { /* non-critical */ }
		loading = false;
	});
</script>

<div class="space-y-6">
	<div class="text-center">
		<h2 class="text-2xl font-bold text-gray-900 dark:text-white">Review Settings</h2>
		<p class="mt-2 text-gray-600 dark:text-gray-400">
			Verify your key configuration values. You can change these later in Settings.
		</p>
	</div>

	{#if loading}
		<div class="py-8 text-center text-gray-400">Loading settings...</div>
	{:else if settings}
		<div class="space-y-3">
			{#each keyPaths as { key, label, desc }}
				<div class="rounded-lg border border-primary/20 bg-surface p-4 dark:border-primary/20 dark:bg-surface-dark">
					<div class="flex items-center justify-between">
						<div>
							<div class="text-sm font-medium text-gray-900 dark:text-white">{label}</div>
							<div class="text-xs text-gray-400 dark:text-gray-500">{desc}</div>
						</div>
						<code class="rounded-sm bg-gray-100 px-2 py-1 text-xs text-gray-800 dark:bg-gray-800 dark:text-gray-300">
							{settings[key] ?? 'not set'}
						</code>
					</div>
				</div>
			{/each}
		</div>

		<div class="text-center">
			<a
				href="/settings"
				class="text-sm text-primary-text hover:underline dark:text-primary-text-dark"
			>
				Edit all settings →
			</a>
		</div>
	{:else}
		<div class="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
			Could not load settings.
		</div>
	{/if}
</div>
