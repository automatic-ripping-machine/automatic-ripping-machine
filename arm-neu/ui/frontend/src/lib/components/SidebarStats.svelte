<script lang="ts">
	import type { HardwareInfoSchema as HardwareInfo, SystemStatsSchema as SystemStats } from '$lib/types/api.gen';
	import ProgressBar from './ProgressBar.svelte';
	import { transcoderEnabled } from '$lib/stores/config';

	interface Props {
		systemInfo: HardwareInfo | null;
		systemStats: SystemStats | null;
		transcoderInfo?: HardwareInfo | null;
		transcoderStats?: SystemStats | null;
		armOnline?: boolean;
		transcoderOnline?: boolean;
	}

	let { systemInfo, systemStats, transcoderInfo = null, transcoderStats = null, armOnline = true, transcoderOnline = true }: Props = $props();

	type Panel = 'ripper' | 'transcoder' | 'gpu';
	let activePanel = $state<Panel>('ripper');

	$effect(() => {
		if (!$transcoderEnabled && (activePanel === 'transcoder' || activePanel === 'gpu')) {
			activePanel = 'ripper';
		}
	});

	// Sticky last-known values so the panel does not blank out when a single
	// dashboard poll returns null (eg. arm-neu /system/stats hiccup, transient
	// timeout). Stays empty until first real value, then never reverts to null.
	let stickySystemStats = $state<SystemStats | null>(null);
	let stickyTranscoderStats = $state<SystemStats | null>(null);
	let stickySystemInfo = $state<HardwareInfo | null>(null);
	let stickyTranscoderInfo = $state<HardwareInfo | null>(null);

	$effect(() => { if (systemStats) stickySystemStats = systemStats; });
	$effect(() => { if (transcoderStats) stickyTranscoderStats = transcoderStats; });
	$effect(() => { if (systemInfo) stickySystemInfo = systemInfo; });
	$effect(() => { if (transcoderInfo) stickyTranscoderInfo = transcoderInfo; });

	const hasGpu = $derived($transcoderEnabled && transcoderOnline && stickyTranscoderStats?.gpu != null);

	const activeHw = $derived(activePanel === 'ripper' ? (armOnline ? stickySystemInfo : null) : (transcoderOnline ? stickyTranscoderInfo : null));
	const activeStats = $derived(activePanel === 'ripper' ? (armOnline ? stickySystemStats : null) : (transcoderOnline ? stickyTranscoderStats : null));

	// Map storage display names to file root keys for deep linking
	const storageNameToRoot: Record<string, string> = {
		'Raw': 'raw', 'Transcode': 'transcode', 'Work': 'transcode', 'Completed': 'completed',
	};
	const rootPaths = $derived(
		(stickySystemStats?.storage ?? []).reduce<Record<string, string>>((acc, sp) => {
			const key = storageNameToRoot[sp.name];
			if (key) acc[key] = sp.path.replace(/\/+$/, '');
			return acc;
		}, {})
	);
	function filesLink(sp: { name: string; path: string }): string | null {
		if (activePanel !== 'ripper') return null;
		const key = storageNameToRoot[sp.name];
		const path = key ? rootPaths[key] : null;
		return path ? `/files?path=${encodeURIComponent(path)}` : null;
	}

	function vendorPillClasses(vendor: string): string {
		switch (vendor.toLowerCase()) {
			case 'nvidia': return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
			case 'amd': return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
			case 'intel': return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400';
			default: return 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400';
		}
	}
</script>

<div data-stats class="border-t border-primary/20 px-3 py-3 dark:border-primary/20">
	<!-- Panel switcher — always visible -->
	<div class="mb-2 flex rounded-sm bg-primary/10 p-0.5 dark:bg-primary/10">
		<button
			onclick={() => activePanel = 'ripper'}
			class="flex-1 rounded-sm px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider transition-colors
				{activePanel === 'ripper'
					? 'bg-primary/20 text-primary-text shadow-xs dark:bg-primary/25 dark:text-primary-text-dark'
					: 'text-primary-text/50 hover:text-primary-text dark:text-primary-text-dark/50 dark:hover:text-primary-text-dark'}"
		>Ripper</button>
		{#if $transcoderEnabled}
		<button
			onclick={() => activePanel = 'transcoder'}
			class="flex-1 rounded-sm px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider transition-colors
				{activePanel === 'transcoder'
					? 'bg-primary/20 text-primary-text shadow-xs dark:bg-primary/25 dark:text-primary-text-dark'
					: 'text-primary-text/50 hover:text-primary-text dark:text-primary-text-dark/50 dark:hover:text-primary-text-dark'}"
		>Transcoder</button>
		{/if}
		{#if hasGpu}
			<button
				onclick={() => activePanel = 'gpu'}
				class="flex-1 rounded-sm px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider transition-colors
					{activePanel === 'gpu'
						? 'bg-primary/20 text-primary-text shadow-xs dark:bg-primary/25 dark:text-primary-text-dark'
						: 'text-primary-text/50 hover:text-primary-text dark:text-primary-text-dark/50 dark:hover:text-primary-text-dark'}"
			>GPU</button>
		{/if}
	</div>

	<!-- GPU panel -->
	{#if activePanel === 'gpu'}
		{#if !transcoderOnline}
			<p class="text-xs text-orange-500 dark:text-orange-400">Cannot reach the transcoder service</p>
		{:else if stickyTranscoderStats?.gpu}
			{@const gpu = stickyTranscoderStats.gpu}
			<div class="mb-2 flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400">
				<span class="rounded-full px-2 py-0.5 text-[10px] font-semibold capitalize {vendorPillClasses(gpu.vendor)}">{gpu.vendor}</span>
				{#if gpu.temperature_c != null}
					<span class="text-orange-500">{gpu.temperature_c.toFixed(0)}&deg;C</span>
				{/if}
			</div>
			<div class="space-y-2">
				{#if gpu.utilization_percent != null}
					<div>
						<div class="mb-0.5 flex items-center justify-between text-[11px] text-gray-500 dark:text-gray-400">
							<span>Load</span>
							<span>{gpu.utilization_percent.toFixed(0)}%</span>
						</div>
						<ProgressBar
							value={gpu.utilization_percent}
							color={gpu.utilization_percent >= 90 ? 'bg-red-500' : gpu.utilization_percent >= 70 ? 'bg-yellow-500' : 'bg-amber-500'}
							showLabel={false}
						/>
					</div>
				{/if}
				{#if gpu.encoder_percent != null}
					<div>
						<div class="mb-0.5 flex items-center justify-between text-[11px] text-gray-500 dark:text-gray-400">
							<span>Encoder</span>
							<span>{gpu.encoder_percent.toFixed(0)}%</span>
						</div>
						<ProgressBar
							value={gpu.encoder_percent}
							color={gpu.encoder_percent >= 90 ? 'bg-red-500' : gpu.encoder_percent >= 70 ? 'bg-yellow-500' : 'bg-amber-500'}
							showLabel={false}
						/>
					</div>
				{/if}
				{#if gpu.memory_used_mb != null && gpu.memory_total_mb != null}
					{@const vramPct = (gpu.memory_used_mb / gpu.memory_total_mb) * 100}
					<div>
						<div class="mb-0.5 flex items-center justify-between text-[11px] text-gray-500 dark:text-gray-400">
							<span>VRAM</span>
							<span>{(gpu.memory_used_mb / 1024).toFixed(1)} / {(gpu.memory_total_mb / 1024).toFixed(1)} GB</span>
						</div>
						<ProgressBar
							value={vramPct}
							color={vramPct >= 90 ? 'bg-red-500' : vramPct >= 70 ? 'bg-yellow-500' : 'bg-amber-500'}
							showLabel={false}
						/>
					</div>
				{/if}
				{#if gpu.power_draw_w != null}
					<div class="mb-0.5 flex items-center justify-between text-[11px] text-gray-500 dark:text-gray-400">
						<span>Power</span>
						<span>{gpu.power_draw_w.toFixed(0)}W{#if gpu.power_limit_w != null} / {gpu.power_limit_w.toFixed(0)}W{/if}</span>
					</div>
				{/if}
				{#if gpu.clock_core_mhz != null}
					<div class="mb-0.5 flex items-center justify-between text-[11px] text-gray-500 dark:text-gray-400">
						<span>Core Clock</span>
						<span>{gpu.clock_core_mhz.toFixed(0)} MHz</span>
					</div>
				{/if}
				{#if gpu.clock_memory_mhz != null}
					<div class="mb-0.5 flex items-center justify-between text-[11px] text-gray-500 dark:text-gray-400">
						<span>Memory Clock</span>
						<span>{gpu.clock_memory_mhz.toFixed(0)} MHz</span>
					</div>
				{/if}
			</div>
		{:else}
			<p class="text-xs text-gray-400 dark:text-gray-500">No GPU detected</p>
		{/if}

	<!-- Ripper / Transcoder panels -->
	{:else}
		<!-- Hardware specs for active panel -->
		{#if activePanel === 'ripper' && !armOnline}
			<p class="text-xs text-orange-500 dark:text-orange-400">Cannot reach the ARM ripping service</p>
		{:else if activePanel === 'transcoder' && !transcoderOnline}
			<p class="text-xs text-orange-500 dark:text-orange-400">Cannot reach the transcoder service</p>
		{:else if activeHw}
			<p class="truncate text-xs text-gray-600 dark:text-gray-400" title={activeHw.cpu ?? undefined}>{activeHw.cpu ?? 'Unknown CPU'}</p>
			<p class="mb-2 text-xs text-gray-600 dark:text-gray-400">
				{activeHw.memory_total_gb ? `${activeHw.memory_total_gb.toFixed(1)} GB RAM` : 'RAM: N/A'}
			</p>
		{/if}

		<!-- CPU & Memory -->
		{#if activeStats}
			<div class="space-y-2">
				<div>
					<div class="mb-0.5 flex items-center justify-between text-[11px] text-gray-500 dark:text-gray-400">
						<span>CPU</span>
						<span class="whitespace-nowrap">
							{activeStats.cpu_percent ?? 0}%
							{#if (activeStats.cpu_temp ?? 0) > 0}
								<span class="text-orange-500">&nbsp;{(activeStats.cpu_temp ?? 0).toFixed(0)}&deg;C</span>
							{/if}
						</span>
					</div>
					<ProgressBar
						value={activeStats.cpu_percent ?? 0}
						color={(activeStats.cpu_percent ?? 0) >= 90 ? 'bg-red-500' : (activeStats.cpu_percent ?? 0) >= 70 ? 'bg-yellow-500' : 'bg-cyan-500'}
						showLabel={false}
					/>
				</div>

				{#if activeStats.memory}
					<div>
						<div class="mb-0.5 flex items-center justify-between text-[11px] text-gray-500 dark:text-gray-400">
							<span>Mem</span>
							<span>{activeStats.memory.used_gb} / {activeStats.memory.total_gb} GB</span>
						</div>
						<ProgressBar
							value={activeStats.memory.percent}
							color={activeStats.memory.percent >= 90 ? 'bg-red-500' : activeStats.memory.percent >= 70 ? 'bg-yellow-500' : 'bg-violet-500'}
							showLabel={false}
						/>
					</div>
				{/if}
			</div>

			<!-- Storage -->
			{#if activeStats.storage?.length}
				<div class="mt-3 space-y-2">
					<p class="text-[10px] font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500">Storage</p>
					{#each activeStats.storage as sp}
						{@const link = filesLink(sp)}
						{#if link}
							<a href={link} class="block rounded-sm transition-colors hover:bg-primary/5 dark:hover:bg-primary/10 -mx-1 px-1">
								<div class="mb-0.5 flex items-center justify-between text-[11px] text-gray-500 dark:text-gray-400">
									<span>{sp.name}</span>
									<span>{sp.free_gb} GB free</span>
								</div>
								<ProgressBar
									value={sp.percent}
									color={sp.percent >= 90 ? 'bg-red-500' : sp.percent >= 70 ? 'bg-yellow-500' : 'bg-emerald-500'}
									showLabel={false}
								/>
							</a>
						{:else}
							<div>
								<div class="mb-0.5 flex items-center justify-between text-[11px] text-gray-500 dark:text-gray-400">
									<span>{sp.name}</span>
									<span>{sp.free_gb} GB free</span>
								</div>
								<ProgressBar
									value={sp.percent}
									color={sp.percent >= 90 ? 'bg-red-500' : sp.percent >= 70 ? 'bg-yellow-500' : 'bg-emerald-500'}
									showLabel={false}
								/>
							</div>
						{/if}
					{/each}
				</div>
			{/if}
		{/if}
	{/if}
</div>
