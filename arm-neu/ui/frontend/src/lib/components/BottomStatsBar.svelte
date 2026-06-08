<script lang="ts">
	import type { HardwareInfoSchema as HardwareInfo, SystemStatsSchema as SystemStats } from '$lib/types/api.gen';
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

	// Sticky last-known values so the bar does not blank out when a single
	// dashboard poll returns null.
	let stickySystemStats = $state<SystemStats | null>(null);
	let stickyTranscoderStats = $state<SystemStats | null>(null);
	$effect(() => { if (systemStats) stickySystemStats = systemStats; });
	$effect(() => { if (transcoderStats) stickyTranscoderStats = transcoderStats; });

	const hasGpu = $derived($transcoderEnabled && transcoderOnline && stickyTranscoderStats?.gpu != null);

	const activeStats = $derived(activePanel === 'ripper' ? (armOnline ? stickySystemStats : null) : (transcoderOnline ? stickyTranscoderStats : null));
	const isOffline = $derived(
		activePanel === 'gpu'
			? !transcoderOnline
			: activePanel === 'ripper' ? !armOnline : !transcoderOnline
	);
	const offlineMessage = $derived(activePanel === 'ripper' ? 'Cannot reach the ARM ripping service' : 'Cannot reach the transcoder service');

	function cpuColor(pct: number): string {
		return pct >= 90 ? 'bg-red-500' : pct >= 70 ? 'bg-yellow-500' : 'bg-cyan-500';
	}
	function memColor(pct: number): string {
		return pct >= 90 ? 'bg-red-500' : pct >= 70 ? 'bg-yellow-500' : 'bg-violet-500';
	}
	function storageColor(pct: number): string {
		return pct >= 90 ? 'bg-red-500' : pct >= 70 ? 'bg-yellow-500' : 'bg-emerald-500';
	}
	function gpuColor(pct: number): string {
		return pct >= 90 ? 'bg-red-500' : pct >= 70 ? 'bg-yellow-500' : 'bg-amber-500';
	}
	function vendorPillClasses(vendor: string): string {
		switch (vendor.toLowerCase()) {
			case 'nvidia': return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
			case 'amd': return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
			case 'intel': return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400';
			default: return 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400';
		}
	}

	// Map storage display names to file root keys for deep linking.
	// Storage paths differ between ripper and transcoder, but file roots
	// always use the ripper's paths, so we map by name instead.
	const storageNameToRoot: Record<string, string> = {
		'Raw': 'raw', 'Transcode': 'transcode', 'Work': 'transcode', 'Completed': 'completed',
	};

	// Use ripper storage paths for file links (file roots match ripper paths)
	const rootPaths = $derived(
		(stickySystemStats?.storage ?? []).reduce<Record<string, string>>((acc, sp) => {
			const key = storageNameToRoot[sp.name];
			if (key) acc[key] = sp.path.replace(/\/+$/, '');
			return acc;
		}, {})
	);

	function filesLink(sp: { name: string; path: string }): string | null {
		// Only link storage when viewing ripper stats — transcoder paths
		// are on a different filesystem and aren't browsable via file roots
		if (activePanel !== 'ripper') return null;
		const key = storageNameToRoot[sp.name];
		const path = key ? rootPaths[key] : null;
		return path ? `/files?path=${encodeURIComponent(path)}` : null;
	}
</script>

<div class="fixed bottom-0 left-0 right-0 z-30 hidden h-10 items-center gap-3 border-t border-primary/20 bg-surface px-4 lg:flex 2xl:hidden dark:border-primary/20 dark:bg-surface-dark">
	<!-- Panel toggle -->
	<div class="flex shrink-0 rounded-sm bg-primary/10 p-0.5 dark:bg-primary/10">
		<button
			onclick={() => activePanel = 'ripper'}
			class="rounded-sm px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wider transition-colors
				{activePanel === 'ripper'
					? 'bg-primary/20 text-primary-text shadow-xs dark:bg-primary/25 dark:text-primary-text-dark'
					: 'text-primary-text/50 hover:text-primary-text dark:text-primary-text-dark/50 dark:hover:text-primary-text-dark'}"
		>Ripper</button>
		{#if $transcoderEnabled}
		<button
			onclick={() => activePanel = 'transcoder'}
			class="rounded-sm px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wider transition-colors
				{activePanel === 'transcoder'
					? 'bg-primary/20 text-primary-text shadow-xs dark:bg-primary/25 dark:text-primary-text-dark'
					: 'text-primary-text/50 hover:text-primary-text dark:text-primary-text-dark/50 dark:hover:text-primary-text-dark'}"
		>Transcoder</button>
		{/if}
		{#if hasGpu}
			<button
				onclick={() => activePanel = 'gpu'}
				class="rounded-sm px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wider transition-colors
					{activePanel === 'gpu'
						? 'bg-primary/20 text-primary-text shadow-xs dark:bg-primary/25 dark:text-primary-text-dark'
						: 'text-primary-text/50 hover:text-primary-text dark:text-primary-text-dark/50 dark:hover:text-primary-text-dark'}"
			>GPU</button>
		{/if}
	</div>

	<div class="h-5 w-px shrink-0 bg-primary/15 dark:bg-primary/20"></div>

	{#if activePanel === 'gpu'}
		{#if !transcoderOnline}
			<span class="text-xs text-orange-500 dark:text-orange-400">{offlineMessage}</span>
		{:else if stickyTranscoderStats?.gpu}
			{@const gpu = stickyTranscoderStats.gpu}
			<!-- Vendor -->
			<span class="shrink-0 rounded-full px-2 py-0.5 text-[9px] font-semibold capitalize {vendorPillClasses(gpu.vendor)}">{gpu.vendor}</span>

			<div class="h-5 w-px shrink-0 bg-primary/15 dark:bg-primary/20"></div>

			<!-- Load -->
			{#if gpu.utilization_percent != null}
				<div class="flex items-center gap-2 text-[11px] text-gray-500 dark:text-gray-400">
					<span class="shrink-0">Load</span>
					<div class="h-1 w-16 rounded-full bg-primary/15 dark:bg-primary/15">
						<div class="h-1 rounded-full transition-all duration-500 {gpuColor(gpu.utilization_percent)}" style="width: {Math.min(100, gpu.utilization_percent)}%"></div>
					</div>
					<span class="shrink-0">{gpu.utilization_percent.toFixed(0)}%</span>
				</div>

				<div class="h-5 w-px shrink-0 bg-primary/15 dark:bg-primary/20"></div>
			{/if}

			<!-- Encoder -->
			{#if gpu.encoder_percent != null}
				<div class="flex items-center gap-2 text-[11px] text-gray-500 dark:text-gray-400">
					<span class="shrink-0">Encoder</span>
					<div class="h-1 w-16 rounded-full bg-primary/15 dark:bg-primary/15">
						<div class="h-1 rounded-full transition-all duration-500 {gpuColor(gpu.encoder_percent)}" style="width: {Math.min(100, gpu.encoder_percent)}%"></div>
					</div>
					<span class="shrink-0">{gpu.encoder_percent.toFixed(0)}%</span>
				</div>

				<div class="h-5 w-px shrink-0 bg-primary/15 dark:bg-primary/20"></div>
			{/if}

			<!-- VRAM -->
			{#if gpu.memory_used_mb != null && gpu.memory_total_mb != null}
				{@const vramPct = (gpu.memory_used_mb / gpu.memory_total_mb) * 100}
				<div class="flex items-center gap-2 text-[11px] text-gray-500 dark:text-gray-400">
					<span class="shrink-0">VRAM</span>
					<div class="h-1 w-16 rounded-full bg-primary/15 dark:bg-primary/15">
						<div class="h-1 rounded-full transition-all duration-500 {gpuColor(vramPct)}" style="width: {Math.min(100, vramPct)}%"></div>
					</div>
					<span class="shrink-0 whitespace-nowrap">{(gpu.memory_used_mb / 1024).toFixed(1)} / {(gpu.memory_total_mb / 1024).toFixed(1)} GB</span>
				</div>

				<div class="h-5 w-px shrink-0 bg-primary/15 dark:bg-primary/20"></div>
			{/if}

			<!-- Temperature -->
			{#if gpu.temperature_c != null}
				<span class="shrink-0 text-[11px] text-orange-500">{gpu.temperature_c.toFixed(0)}&deg;C</span>
				<div class="h-5 w-px shrink-0 bg-primary/15 dark:bg-primary/20"></div>
			{/if}

			<!-- Power -->
			{#if gpu.power_draw_w != null}
				<span class="shrink-0 text-[11px] text-gray-500 dark:text-gray-400">{gpu.power_draw_w.toFixed(0)}W{#if gpu.power_limit_w != null} / {gpu.power_limit_w.toFixed(0)}W{/if}</span>
				<div class="h-5 w-px shrink-0 bg-primary/15 dark:bg-primary/20"></div>
			{/if}

			<!-- Clocks -->
			{#if gpu.clock_core_mhz != null}
				<span class="shrink-0 text-[11px] text-gray-500 dark:text-gray-400">{gpu.clock_core_mhz.toFixed(0)} MHz</span>
			{/if}
		{:else}
			<span class="text-xs text-gray-400 dark:text-gray-500">No GPU detected</span>
		{/if}

	{:else if isOffline}
		<span class="text-xs text-orange-500 dark:text-orange-400">{offlineMessage}</span>
	{:else if activeStats}
		<!-- CPU -->
		<div class="flex items-center gap-2 text-[11px] text-gray-500 dark:text-gray-400">
			<span class="shrink-0">CPU</span>
			<div class="h-1 w-16 rounded-full bg-primary/15 dark:bg-primary/15">
				<div class="h-1 rounded-full transition-all duration-500 {cpuColor(activeStats.cpu_percent ?? 0)}" style="width: {Math.min(100, activeStats.cpu_percent ?? 0)}%"></div>
			</div>
			<span class="shrink-0">{activeStats.cpu_percent ?? 0}%</span>
		</div>

		<div class="h-5 w-px shrink-0 bg-primary/15 dark:bg-primary/20"></div>

		<!-- Memory -->
		{#if activeStats.memory}
			<div class="flex items-center gap-2 text-[11px] text-gray-500 dark:text-gray-400">
				<span class="shrink-0">Mem</span>
				<div class="h-1 w-16 rounded-full bg-primary/15 dark:bg-primary/15">
					<div class="h-1 rounded-full transition-all duration-500 {memColor(activeStats.memory.percent)}" style="width: {Math.min(100, activeStats.memory.percent)}%"></div>
				</div>
				<span class="shrink-0 whitespace-nowrap">{activeStats.memory.used_gb} / {activeStats.memory.total_gb} GB</span>
			</div>

			<div class="h-5 w-px shrink-0 bg-primary/15 dark:bg-primary/20"></div>
		{/if}

		<!-- Storage -->
		{#if activeStats.storage?.length}
			<div class="flex items-center gap-3 overflow-hidden text-[11px] text-gray-500 dark:text-gray-400">
				{#each activeStats.storage as sp}
					{@const link = filesLink(sp)}
					{#if link}
						<a href={link} class="flex shrink-0 items-center gap-1.5 transition-colors hover:text-primary-text dark:hover:text-primary-text-dark">
							<span class="text-gray-400 dark:text-gray-500">{sp.name}</span>
							<div class="h-1 w-12 rounded-full bg-primary/15 dark:bg-primary/15">
								<div class="h-1 rounded-full transition-all duration-500 {storageColor(sp.percent)}" style="width: {Math.min(100, sp.percent)}%"></div>
							</div>
							<span>{sp.free_gb} GB</span>
						</a>
					{:else}
						<div class="flex shrink-0 items-center gap-1.5">
							<span class="text-gray-400 dark:text-gray-500">{sp.name}</span>
							<div class="h-1 w-12 rounded-full bg-primary/15 dark:bg-primary/15">
								<div class="h-1 rounded-full transition-all duration-500 {storageColor(sp.percent)}" style="width: {Math.min(100, sp.percent)}%"></div>
							</div>
							<span>{sp.free_gb} GB</span>
						</div>
					{/if}
				{/each}
			</div>
		{/if}
	{/if}
</div>
