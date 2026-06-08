<script lang="ts">
	import type { SetupStatus } from '$lib/types/api.gen';
	import { onMount } from 'svelte';
	import InfoCard from './InfoCard.svelte';
	import StatusIcon from './StatusIcon.svelte';
	import { transcoderEnabled } from '$lib/stores/config';

	interface Props {
		status: SetupStatus;
	}

	let { status }: Props = $props();

	let systemInfo = $state<{ cpu: string; memory_total_gb: number } | null>(null);
	let transcoderOnline = $state<boolean | null>(null);
	let transcoderStats = $state<{ pending: number; completed: number; worker_running: boolean } | null>(null);

	onMount(async () => {
		try {
			const resp = await fetch('/api/system-info');
			if (resp.ok) systemInfo = await resp.json();
		} catch { /* non-critical */ }

		if (!$transcoderEnabled) return;
		try {
			const resp = await fetch('/api/dashboard');
			if (resp.ok) {
				const data = await resp.json();
				transcoderOnline = data.transcoder_online ?? false;
				transcoderStats = data.transcoder_stats ?? null;
			}
		} catch { /* non-critical */ }
	});
</script>

<div class="space-y-6">
	<div class="text-center">
		<h2 class="text-2xl font-bold text-gray-900 dark:text-white">Welcome to ARM</h2>
		<p class="mt-2 text-gray-600 dark:text-gray-400">
			Let's make sure your system is configured correctly.
		</p>
	</div>

	<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
		<InfoCard label="ARM Version">
			<span class="text-lg font-medium text-gray-900 dark:text-white">{status.arm_version}</span>
		</InfoCard>

		<InfoCard label="Database">
			<span class="flex items-center gap-2">
				<StatusIcon ok={!!status.db_initialized} />
				<span class="text-lg font-medium {status.db_initialized ? 'setup-status-ok' : 'setup-status-warn'}">
					{status.db_initialized ? 'Initialized' : 'Not initialized'}
				</span>
			</span>
		</InfoCard>

		{#if systemInfo}
			<InfoCard label="CPU">
				<span class="truncate text-sm font-medium text-gray-900 dark:text-white" title={systemInfo.cpu}>
					{systemInfo.cpu}
				</span>
			</InfoCard>

			<InfoCard label="Memory">
				<span class="text-lg font-medium text-gray-900 dark:text-white">
					{systemInfo.memory_total_gb.toFixed(1)} GB
				</span>
			</InfoCard>
		{/if}
	</div>

	<div class="grid grid-cols-1 gap-4 {$transcoderEnabled ? 'sm:grid-cols-3' : 'sm:grid-cols-1'}">
		<InfoCard label="Drives">
			<span class="text-sm font-medium text-gray-900 dark:text-white">{status.setup_steps?.drives ?? '?'}</span>
		</InfoCard>

		{#if $transcoderEnabled}
			<InfoCard label="Transcoder">
				{#if transcoderOnline === null}
					<span class="text-sm setup-status-wait">Checking...</span>
				{:else}
					<span class="flex items-center gap-2">
						<StatusIcon ok={transcoderOnline} />
						<span class="text-sm font-medium {transcoderOnline ? 'setup-status-ok' : 'setup-status-off'}">
							{transcoderOnline ? 'Online' : 'Offline'}
						</span>
					</span>
				{/if}
			</InfoCard>

			<InfoCard label="Transcoder DB">
				{#if transcoderOnline === null}
					<span class="text-sm setup-status-wait">Checking...</span>
				{:else}
					<span class="flex items-center gap-2">
						<StatusIcon ok={!!(transcoderOnline && transcoderStats)} />
						<span class="text-sm font-medium {transcoderOnline && transcoderStats ? 'setup-status-ok' : 'setup-status-off'}">
							{transcoderOnline && transcoderStats ? 'Ready' : 'Unavailable'}
						</span>
					</span>
				{/if}
			</InfoCard>
		{/if}
	</div>
</div>
