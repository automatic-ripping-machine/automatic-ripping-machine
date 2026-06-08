<script lang="ts">
	import { onMount } from 'svelte';
	import {
		runPreflight,
		fixPreflight,
		type PreflightResult,
		type PreflightCheck,
		type PreflightPath,
	} from '$lib/api/system';

	const KEY_LABELS: Record<string, string> = {
		omdb_key: 'OMDb',
		tmdb_key: 'TMDb',
		tvdb_key: 'TVDB',
		makemkv_key: 'MakeMKV',
	};

	const KEY_SIGNUP_URLS: Record<string, string> = {
		omdb_key: 'https://www.omdbapi.com/apikey.aspx',
		tmdb_key: 'https://www.themoviedb.org/settings/api',
		tvdb_key: 'https://thetvdb.com/api-information',
	};

	let result = $state<PreflightResult | null>(null);
	let loading = $state(true);
	let fixing = $state(false);
	let error = $state<string | null>(null);

	type Status = 'pass' | 'warn' | 'fail';

	function checkStatus(c: PreflightCheck): Status {
		if (c.success) return 'pass';
		if (c.message === 'Not configured') return 'warn';
		return 'fail';
	}

	function pathStatus(p: PreflightPath): Status {
		if (!p.exists) return 'fail';
		if (!p.match) return 'fail';
		if (p.require_writable && !p.writable) return 'fail';
		return 'pass';
	}

	function chownCommand(p: PreflightPath, r: PreflightResult): string {
		const target = p.host_path || p.container_path;
		return `sudo chown -R ${r.arm_uid}:${r.arm_gid} ${target}`;
	}

	let fixableItems = $derived.by(() => {
		if (!result) return [] as string[];
		const items: string[] = [];
		for (const c of result.checks) {
			if (!c.success && c.fixable) items.push(c.name);
		}
		for (const p of result.paths) {
			if (pathStatus(p) === 'fail' && p.fixable) items.push(p.name);
		}
		return items;
	});

	async function load() {
		loading = true;
		error = null;
		try {
			result = await runPreflight();
		} catch {
			error = 'Failed to run readiness checks';
		} finally {
			loading = false;
		}
	}

	async function fix() {
		if (fixableItems.length === 0) return;
		fixing = true;
		try {
			result = await fixPreflight(fixableItems);
		} catch {
			error = 'Fix attempt failed';
		} finally {
			fixing = false;
		}
	}

	function copyToClipboard(text: string) {
		navigator.clipboard.writeText(text);
	}

	onMount(() => {
		load();
	});
</script>

<div class="space-y-6">
	<div class="text-center">
		<h2 class="text-2xl font-bold text-gray-900 dark:text-white">Readiness Checks</h2>
		<p class="mt-2 text-gray-600 dark:text-gray-400">
			Verifying API keys and path permissions.
		</p>
	</div>

	{#if loading}
		<div class="py-8 text-center text-gray-400">
			<svg class="mx-auto h-8 w-8 animate-spin text-primary" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
				<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
				<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
			</svg>
			<p class="mt-3">Running checks...</p>
		</div>
	{:else if error && !result}
		<div class="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
			{error}
		</div>
	{:else if result}
		<!-- ARM Identity -->
		<div>
			<h3 class="mb-2 text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">ARM Identity</h3>
			<div class="rounded-lg border border-primary/20 bg-surface p-4 dark:border-primary/20 dark:bg-surface-dark">
				<div class="flex items-center gap-2">
					<svg class="h-5 w-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
						<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
					</svg>
					<span class="text-sm font-medium text-gray-900 dark:text-white">
						UID:{result.arm_uid} / GID:{result.arm_gid}
					</span>
				</div>
			</div>
		</div>

		<!-- API Keys -->
		<div>
			<h3 class="mb-2 text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">API Keys</h3>
			<div class="space-y-2">
				{#each result.checks as check}
					{@const status = checkStatus(check)}
					<div class="rounded-lg border border-primary/20 bg-surface p-4 dark:border-primary/20 dark:bg-surface-dark">
						<div class="flex items-center justify-between">
							<div class="flex items-center gap-2">
								{#if status === 'pass'}
									<svg class="h-5 w-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
										<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
									</svg>
								{:else if status === 'warn'}
									<svg class="h-5 w-5 text-amber-500" fill="currentColor" viewBox="0 0 20 20">
										<path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
									</svg>
								{:else}
									<svg class="h-5 w-5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
										<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
									</svg>
								{/if}
								<span class="text-sm font-medium text-gray-900 dark:text-white">
									{KEY_LABELS[check.name] ?? check.name}
								</span>
							</div>
							<div class="flex items-center gap-2">
								<span class="text-xs {status === 'pass' ? 'text-green-600 dark:text-green-400' : status === 'warn' ? 'text-amber-600 dark:text-amber-400' : 'text-red-600 dark:text-red-400'}">
									{check.message}
								</span>
								{#if status === 'warn' && KEY_SIGNUP_URLS[check.name]}
									<a
										href={KEY_SIGNUP_URLS[check.name]}
										target="_blank"
										rel="noopener noreferrer"
										class="rounded-md bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700 hover:bg-amber-200 dark:bg-amber-900/30 dark:text-amber-400 dark:hover:bg-amber-900/50 transition-colors"
									>
										Get key
									</a>
								{/if}
							</div>
						</div>
					</div>
				{/each}
			</div>
		</div>

		<!-- Paths & Permissions -->
		<div>
			<h3 class="mb-2 text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Paths & Permissions</h3>
			<div class="space-y-2">
				{#each result.paths as path}
					{@const status = pathStatus(path)}
					<div class="rounded-lg border border-primary/20 bg-surface p-4 dark:border-primary/20 dark:bg-surface-dark">
						<div class="flex items-center justify-between">
							<div class="flex items-center gap-2">
								{#if status === 'pass'}
									<svg class="h-5 w-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
										<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
									</svg>
								{:else}
									<svg class="h-5 w-5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
										<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
									</svg>
								{/if}
								<div>
									<span class="text-sm font-medium text-gray-900 dark:text-white">{path.name}</span>
									<div class="text-xs text-gray-400 dark:text-gray-500">{path.container_path}</div>
								</div>
							</div>
							<div class="text-right">
								{#if status === 'pass'}
									<span class="text-xs text-green-600 dark:text-green-400">
										{#if !path.require_writable && !path.writable}Read-only{:else}OK{/if}
									</span>
								{:else}
									<span class="text-xs text-red-600 dark:text-red-400">
										{#if !path.exists}Missing{:else if !path.match}Owner mismatch{:else}Not writable{/if}
									</span>
								{/if}
							</div>
						</div>
						{#if status === 'fail' && !path.fixable}
							{@const cmd = chownCommand(path, result)}
							<div class="mt-2 flex items-center gap-2">
								<code class="flex-1 rounded-sm bg-gray-100 px-2 py-1 text-xs text-gray-800 dark:bg-gray-800 dark:text-gray-300 truncate" title={cmd}>
									{cmd}
								</code>
								<button
									type="button"
									onclick={() => copyToClipboard(cmd)}
									class="shrink-0 rounded-md bg-gray-100 p-1 text-gray-500 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700 transition-colors"
									title="Copy command"
								>
									<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
										<path stroke-linecap="round" stroke-linejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9.75a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
									</svg>
								</button>
							</div>
						{/if}
					</div>
				{/each}
			</div>
		</div>

		<!-- Action buttons -->
		<div class="flex items-center justify-center gap-3">
			<button
				type="button"
				onclick={load}
				disabled={loading}
				class="rounded-lg px-4 py-2 text-sm font-medium bg-primary/15 text-primary-text hover:bg-primary/25 dark:text-primary-text-dark dark:hover:bg-primary/30 disabled:opacity-50 transition-colors"
			>
				{loading ? 'Checking...' : 'Re-run Checks'}
			</button>
			{#if fixableItems.length > 0}
				<button
					type="button"
					onclick={fix}
					disabled={fixing}
					class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-on-primary hover:bg-primary-hover disabled:opacity-50 transition-colors"
				>
					{fixing ? 'Fixing...' : `Fix ${fixableItems.length} Issue${fixableItems.length === 1 ? '' : 's'}`}
				</button>
			{/if}
		</div>
	{/if}
</div>
