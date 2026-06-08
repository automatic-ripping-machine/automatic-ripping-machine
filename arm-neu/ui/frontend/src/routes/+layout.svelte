<script lang="ts">
	import '../app.css';
	import { page } from '$app/stores';
	import { theme, toggleTheme } from '$lib/stores/theme';
	import { colorScheme, schemeLocksMode, loadThemesFromApi } from '$lib/stores/colorScheme';
	import { dashboard } from '$lib/stores/dashboard';
	import { transcoderEnabled } from '$lib/stores/config';
	import { setRippingEnabled } from '$lib/api/dashboard';
	import SidebarStats from '$lib/components/SidebarStats.svelte';
	import BottomStatsBar from '$lib/components/BottomStatsBar.svelte';
	import { goto } from '$app/navigation';
	import { showImportWizard } from '$lib/stores/importWizard';
	import ImportWizard from '$lib/components/ImportWizard.svelte';
	import { onMount } from 'svelte';
	let { children } = $props();

	let sidebarOpen = $state(false);
	let mobileDrawerView = $state<'menu' | 'stats'>('menu');
	let togglingPause = $state(false);
	let quickMenuOpen = $state(false);
	const rippingCount = $derived(($dashboard.active_jobs ?? []).filter(j => {
		const s = j.status?.toLowerCase();
		return s !== 'transcoding' && s !== 'waiting_transcode';
	}).length);

	function closeQuickMenu() {
		quickMenuOpen = false;
	}

	function handleQuickAction(action: string) {
		closeQuickMenu();
		if (action === 'import-folder') {
			showImportWizard.set(true);
		} else if (action === 'restart-arm') {
			if (confirm('Restart the ARM ripping service? Active rips will be interrupted.')) {
				fetch('/api/system/restart', { method: 'POST' });
			}
		} else if (action === 'restart-transcoder') {
			if (confirm('Restart the transcoder service? Active transcodes will be interrupted.')) {
				fetch('/api/system/restart-transcoder', { method: 'POST' });
			}
		} else if (action === 'settings') {
			goto('/settings');
		}
	}

	let isSetupPage = $derived($page.url.pathname.startsWith('/setup'));

	async function toggleRipping() {
		if (togglingPause) return;
		togglingPause = true;
		const newValue = !$dashboard.ripping_enabled;
		dashboard.update(d => ({ ...d, ripping_enabled: newValue }));
		try {
			await setRippingEnabled(newValue);
		} catch {
			// Revert on failure — next poll will also reconcile
			dashboard.update(d => ({ ...d, ripping_enabled: !newValue }));
		} finally {
			togglingPause = false;
		}
	}

	onMount(() => {
		// Load themes from API (falls back to built-in if backend unreachable)
		loadThemesFromApi();
		// Start dashboard polling (provides sidebar stats on all pages)
		dashboard.start();
		return () => dashboard.stop();
	});

	const allNavItems = [
		{ href: '/', label: 'Dashboard', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' },
		{ href: '/notifications', label: 'Notifications', icon: 'M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9' },
		{ href: '/logs', label: 'Logs', icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z' },
		{ href: '/files', label: 'Files', icon: 'M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z' },
		{ href: '/transcoder', label: 'Transcoder', icon: 'M7 4V2a1 1 0 012 0v2h6V2a1 1 0 012 0v2h1a2 2 0 012 2v12a2 2 0 01-2 2H6a2 2 0 01-2-2V6a2 2 0 012-2h1zm0 8h10m-10 4h6' },
		{ href: '/settings', label: 'Settings', icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z' },
	];
	const navItems = $derived($transcoderEnabled ? allNavItems : allNavItems.filter(i => i.href !== '/transcoder'));

	function isActive(href: string, pathname: string): boolean {
		if (href === '/') return pathname === '/';
		return pathname.startsWith(href);
	}
</script>

{#if isSetupPage}
	<div class={$theme}>
		{@render children()}
	</div>
{:else}
<div class="flex h-screen overflow-hidden">
	<!-- Sidebar -->
	<aside class="hidden w-64 shrink-0 border-r border-primary/20 bg-surface dark:border-primary/20 dark:bg-surface-dark lg:block">
		<div class="flex h-full flex-col">
			<div data-logo class="flex items-center justify-center py-6">
				<img src="/img/arm-logo-black.png" alt="ARM" class="h-24 w-24 dark:hidden" />
				<img src="/img/arm-logo-white.png" alt="ARM" class="hidden h-24 w-24 dark:block" />
			</div>
			<hr class="border-primary/20 dark:border-primary/20" />
			<nav class="flex-1 space-y-1 px-3 py-4">
				{#each navItems as item}
					<a
						href={item.href}
						data-active={isActive(item.href, $page.url.pathname) || undefined}
						class="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors
							{isActive(item.href, $page.url.pathname)
								? 'bg-primary-light-bg text-primary-text dark:bg-primary-light-bg-dark/30 dark:text-primary-text-dark'
								: 'text-gray-700 hover:bg-primary/10 dark:text-gray-300 dark:hover:bg-primary/15'}"
					>
						<svg class="h-5 w-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={item.icon} />
						</svg>
						{item.label}
						{#if item.href === '/notifications' && ($dashboard.notification_count ?? 0) > 0}
							<span class="ml-auto rounded-full bg-amber-500 px-2 py-0.5 text-xs font-medium text-white">{$dashboard.notification_count}</span>
						{/if}
					</a>
				{/each}
			</nav>
			<hr class="border-primary/20 dark:border-primary/20" />
			<div class="hidden 2xl:block">
				<SidebarStats systemInfo={$dashboard.system_info} systemStats={$dashboard.system_stats} transcoderInfo={$dashboard.transcoder_info} transcoderStats={$dashboard.transcoder_system_stats} armOnline={$dashboard.arm_online} transcoderOnline={$dashboard.transcoder_online} />
			</div>
		</div>
	</aside>

	<!-- Main content -->
	<div class="flex flex-1 flex-col overflow-hidden">
		<!-- Top bar -->
		<header class="flex h-14 items-center justify-between border-b border-primary/20 bg-surface px-4 dark:border-primary/20 dark:bg-surface-dark lg:px-6">
			<button
				onclick={() => sidebarOpen = !sidebarOpen}
				aria-label="Toggle sidebar"
				class="rounded-lg p-2 text-gray-500 hover:bg-primary/10 dark:text-gray-400 dark:hover:bg-primary/15 lg:hidden"
			>
				<svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
				</svg>
			</button>

			<!-- Stats bar (desktop only) -->
			<div class="hidden lg:flex items-center gap-3 text-sm">
				<!-- Service health dots -->
				<div class="flex items-center gap-3">
					<a href="/settings#system" class="flex items-center gap-1.5 hover:opacity-75 transition-opacity">
						<div class="h-2 w-2 shrink-0 rounded-full {$dashboard.arm_online ? 'bg-green-500' : 'bg-red-500'}"></div>
						<span class="text-gray-700 dark:text-gray-200">ARM</span>
					</a>
					<a href="/settings#system" class="flex items-center gap-1.5 hover:opacity-75 transition-opacity">
						<div class="h-2 w-2 shrink-0 rounded-full {$dashboard.db_available ? 'bg-green-500' : 'bg-yellow-500'}"></div>
						<span class="text-gray-700 dark:text-gray-200">DB</span>
					</a>
					<a href="/transcoder" class="flex items-center gap-1.5 hover:opacity-75 transition-opacity">
						<div class="h-2 w-2 shrink-0 rounded-full {$dashboard.transcoder_online && ($dashboard.transcoder_stats?.worker_running ?? true) ? 'bg-green-500' : $dashboard.transcoder_online ? 'bg-yellow-500' : 'bg-gray-400'}"></div>
						<span class="text-gray-700 dark:text-gray-200">Transcode</span>
					</a>
					<a href="/settings#ripping/makemkv" class="flex items-center gap-1.5 hover:opacity-75 transition-opacity"
						title={$dashboard.makemkv_key_valid === true
							? `MakeMKV key valid${$dashboard.makemkv_key_checked_at ? ' — checked ' + new Date($dashboard.makemkv_key_checked_at).toLocaleString() : ''}`
							: $dashboard.makemkv_key_valid === false
								? 'MakeMKV key invalid — click to update'
								: 'MakeMKV key not checked yet'}
					>
						<div class="h-2 w-2 shrink-0 rounded-full {$dashboard.makemkv_key_valid === true ? 'bg-green-500' : 'bg-red-500'}"></div>
						<span class="text-gray-700 dark:text-gray-200">Key</span>
					</a>
				</div>
				<!-- Divider -->
				<div class="h-6 w-px bg-black dark:bg-white/30"></div>
				<!-- Live activity -->
				<div class="flex items-center gap-3 text-xs">
					<a href="/settings#drives" class="text-gray-600 dark:text-gray-300 hover:text-primary dark:hover:text-primary transition-colors">{$dashboard.db_available ? $dashboard.drives_online : '--'} drive{$dashboard.drives_online !== 1 ? 's' : ''}</a>
					{#if rippingCount > 0}
						<span class="font-semibold text-blue-600 dark:text-blue-400">{rippingCount} ripping</span>
					{/if}
					{#if $dashboard.active_transcodes.length > 0}
						<span class="font-semibold text-indigo-600 dark:text-indigo-400">{$dashboard.active_transcodes.length} transcoding</span>
					{/if}
					{#if $dashboard.transcoder_online && (Number($dashboard.transcoder_stats?.pending) || 0) > 0}
						<span class="font-semibold text-yellow-600 dark:text-yellow-400">{$dashboard.transcoder_stats?.pending} queued</span>
					{/if}
					{#if ($dashboard.notification_count ?? 0) > 0}
						<a href="/notifications" class="font-semibold text-amber-600 hover:text-amber-700 dark:text-amber-400 dark:hover:text-amber-300">{$dashboard.notification_count} notification{$dashboard.notification_count !== 1 ? 's' : ''}</a>
					{/if}
				</div>
			</div>

			<div class="flex items-center gap-4 ml-auto">
				<!-- Auto-Start toggle -->
				{#if $dashboard.db_available}
					<button
						onclick={toggleRipping}
						disabled={togglingPause}
						class="flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors {$dashboard.ripping_enabled
							? 'bg-primary-light-bg text-primary-text dark:bg-primary-light-bg-dark/30 dark:text-primary-text-dark'
							: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'}"
					>
						<div class="relative h-5 w-9 rounded-lg transition-colors {$dashboard.ripping_enabled ? 'bg-primary' : 'bg-amber-500'}">
							<div class="absolute top-0.5 h-4 w-4 rounded-lg bg-white shadow transition-transform {$dashboard.ripping_enabled ? 'translate-x-4' : 'translate-x-0.5'}"></div>
						</div>
						{$dashboard.ripping_enabled ? 'Auto-Start' : 'Paused'}
					</button>
				{/if}
				<!-- Quick actions menu -->
				<div class="relative">
					<button
						onclick={() => quickMenuOpen = !quickMenuOpen}
						class="rounded-lg p-2 text-gray-500 hover:bg-primary/10 dark:text-gray-300 dark:hover:bg-primary/15"
						title="Quick actions"
					>
						<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
						</svg>
					</button>
					{#if quickMenuOpen}
						<!-- Backdrop -->
						<button type="button" class="fixed inset-0 z-40" onclick={closeQuickMenu} aria-label="Close menu"></button>
						<!-- Dropdown -->
						<div class="absolute right-0 z-50 mt-1 w-52 rounded-lg border border-primary/20 bg-surface py-1 shadow-lg dark:border-primary/30 dark:bg-surface-dark">
							<button
								type="button"
								onclick={() => handleQuickAction('import-folder')}
								class="flex w-full items-center gap-2 px-4 py-2 text-left text-sm text-gray-700 hover:bg-primary/5 dark:text-gray-300 dark:hover:bg-primary/10"
							>
								<svg class="h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
								</svg>
								Import
							</button>
							<div class="my-1 border-t border-primary/10 dark:border-primary/20"></div>
							<button
								type="button"
								onclick={() => handleQuickAction('restart-arm')}
								class="flex w-full items-center gap-2 px-4 py-2 text-left text-sm text-gray-700 hover:bg-primary/5 dark:text-gray-300 dark:hover:bg-primary/10"
							>
								<svg class="h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
								</svg>
								Restart ARM
							</button>
							{#if $transcoderEnabled}
							<button
								type="button"
								onclick={() => handleQuickAction('restart-transcoder')}
								class="flex w-full items-center gap-2 px-4 py-2 text-left text-sm text-gray-700 hover:bg-primary/5 dark:text-gray-300 dark:hover:bg-primary/10"
							>
								<svg class="h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
								</svg>
								Restart Transcoder
							</button>
							{/if}
							<div class="my-1 border-t border-primary/10 dark:border-primary/20"></div>
							<button
								type="button"
								onclick={() => handleQuickAction('settings')}
								class="flex w-full items-center gap-2 px-4 py-2 text-left text-sm text-gray-700 hover:bg-primary/5 dark:text-gray-300 dark:hover:bg-primary/10"
							>
								<svg class="h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
								</svg>
								Settings
							</button>
						</div>
					{/if}
				</div>
				<!-- Dark mode toggle (hidden when theme locks the mode) -->
				{#if !$schemeLocksMode}
					<button
						onclick={toggleTheme}
						class="rounded-lg p-2 text-gray-500 hover:bg-primary/10 dark:text-gray-300 dark:hover:bg-primary/15"
					>
						{#if $theme === 'dark'}
							<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
							</svg>
						{:else}
							<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
							</svg>
						{/if}
					</button>
				{/if}
			</div>
		</header>

		<!-- Mobile sidebar overlay -->
		{#if sidebarOpen}
			<div class="fixed inset-0 z-40 lg:hidden">
				<button class="absolute inset-0 bg-black/50" aria-label="Close sidebar" onclick={() => sidebarOpen = false}></button>
				<aside class="relative z-50 flex h-full w-64 flex-col bg-surface shadow-xl dark:bg-surface-dark">
					<div data-logo class="flex items-center justify-center py-4">
						<img src="/img/arm-logo-black.png" alt="ARM" class="h-20 w-20 dark:hidden" />
						<img src="/img/arm-logo-white.png" alt="ARM" class="hidden h-20 w-20 dark:block" />
					</div>
					<hr class="border-primary/20 dark:border-primary/20" />
					<!-- Drawer view toggle (mobile) -->
					<div class="px-3 pt-3">
						<div class="flex rounded-sm bg-primary/10 p-0.5 dark:bg-primary/10">
							<button
								onclick={() => mobileDrawerView = 'menu'}
								class="flex-1 rounded-sm px-2 py-1 text-[11px] font-semibold uppercase tracking-wider transition-colors
									{mobileDrawerView === 'menu'
										? 'bg-primary/20 text-primary-text shadow-xs dark:bg-primary/25 dark:text-primary-text-dark'
										: 'text-primary-text/50 hover:text-primary-text dark:text-primary-text-dark/50 dark:hover:text-primary-text-dark'}"
							>Menu</button>
							<button
								onclick={() => mobileDrawerView = 'stats'}
								class="flex-1 rounded-sm px-2 py-1 text-[11px] font-semibold uppercase tracking-wider transition-colors
									{mobileDrawerView === 'stats'
										? 'bg-primary/20 text-primary-text shadow-xs dark:bg-primary/25 dark:text-primary-text-dark'
										: 'text-primary-text/50 hover:text-primary-text dark:text-primary-text-dark/50 dark:hover:text-primary-text-dark'}"
							>Stats</button>
						</div>
					</div>
					{#if mobileDrawerView === 'menu'}
						<nav class="flex-1 overflow-y-auto space-y-1 px-3 py-4">
							{#each navItems as item}
								<a
									href={item.href}
									onclick={() => sidebarOpen = false}
									data-active={isActive(item.href, $page.url.pathname) || undefined}
									class="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors
										{isActive(item.href, $page.url.pathname)
											? 'bg-primary-light-bg text-primary-text dark:bg-primary-light-bg-dark/30 dark:text-primary-text-dark'
											: 'text-gray-700 hover:bg-primary/10 dark:text-gray-300 dark:hover:bg-primary/15'}"
								>
									<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={item.icon} />
									</svg>
									{item.label}
									{#if item.href === '/notifications' && ($dashboard.notification_count ?? 0) > 0}
										<span class="ml-auto rounded-full bg-amber-500 px-2 py-0.5 text-xs font-medium text-white">{$dashboard.notification_count}</span>
								{/if}
								</a>
							{/each}
						</nav>
					{:else}
						<div class="flex-1 overflow-y-auto">
							<SidebarStats systemInfo={$dashboard.system_info} systemStats={$dashboard.system_stats} transcoderInfo={$dashboard.transcoder_info} transcoderStats={$dashboard.transcoder_system_stats} armOnline={$dashboard.arm_online} transcoderOnline={$dashboard.transcoder_online} />
						</div>
					{/if}
				</aside>
			</div>
		{/if}

		<!-- Page content -->
		<main class="flex-1 overflow-y-auto p-4 lg:p-6 lg:pb-16 2xl:pb-6">
			{@render children()}
		</main>

		<!-- Bottom stats bar — visible only at lg (1024-1279px), visibility controlled by component root -->
		<BottomStatsBar systemInfo={$dashboard.system_info} systemStats={$dashboard.system_stats} transcoderInfo={$dashboard.transcoder_info} transcoderStats={$dashboard.transcoder_system_stats} armOnline={$dashboard.arm_online} transcoderOnline={$dashboard.transcoder_online} />
	</div>
</div>
{/if}

<!-- Folder import wizard (global, triggered from gear menu) -->
<ImportWizard
	open={$showImportWizard}
	onclose={() => showImportWizard.set(false)}
	oncreated={() => { showImportWizard.set(false); }}
/>
