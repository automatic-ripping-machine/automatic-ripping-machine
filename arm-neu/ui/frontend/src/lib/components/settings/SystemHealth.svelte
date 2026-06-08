<script lang="ts">
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

	function timeAgo(ts: number): string {
		const diff = Math.floor((Date.now() - ts) / 1000);
		if (diff < 60) return 'just now';
		const mins = Math.floor(diff / 60);
		if (mins < 60) return `${mins} min ago`;
		const hrs = Math.floor(mins / 60);
		return `${hrs} hr ago`;
	}

	let result = $state<PreflightResult | null>(null);
	let loading = $state(false);
	let fixing = $state(false);
	let error = $state<string | null>(null);
	let lastChecked = $state<number | null>(null);
	let expanded = $state(false);

	let failedChecks = $derived.by(() => {
		if (!result) return [] as PreflightCheck[];
		return result.checks.filter((c) => checkStatus(c) !== 'pass');
	});

	let failedPaths = $derived.by(() => {
		if (!result) return [] as PreflightPath[];
		return result.paths.filter((p) => pathStatus(p) !== 'pass');
	});

	let passingChecks = $derived.by(() => {
		if (!result) return [] as PreflightCheck[];
		return result.checks.filter((c) => checkStatus(c) === 'pass');
	});

	let passingPaths = $derived.by(() => {
		if (!result) return [] as PreflightPath[];
		return result.paths.filter((p) => pathStatus(p) === 'pass');
	});

	let validKeyCount = $derived.by(() => {
		if (!result) return 0;
		return result.checks.filter((c) => c.success).length;
	});

	let writablePathCount = $derived.by(() => {
		if (!result) return 0;
		return result.paths.filter((p) => pathStatus(p) === 'pass').length;
	});

	let hasIssues = $derived.by(() => {
		if (!result) return false;
		const checkFails = result.checks.some(
			(c) => !c.success && c.message !== 'Not configured'
		);
		const pathFails = result.paths.some(
			(p) => pathStatus(p) !== 'pass'
		);
		return checkFails || pathFails;
	});

	let warningCount = $derived.by(() => {
		if (!result) return 0;
		const checkCount = result.checks.filter(
			(c) => !c.success && c.message !== 'Not configured'
		).length;
		const pathCount = result.paths.filter(
			(p) => pathStatus(p) !== 'pass'
		).length;
		return checkCount + pathCount;
	});

	let fixableItems = $derived.by(() => {
		if (!result) return [] as string[];
		const items: string[] = [];
		for (const c of result.checks) {
			if (!c.success && c.fixable) items.push(c.name);
		}
		for (const p of result.paths) {
			if (pathStatus(p) !== 'pass' && p.fixable) items.push(p.name);
		}
		return items;
	});

	async function runChecks() {
		loading = true;
		error = null;
		try {
			result = await runPreflight();
			lastChecked = Date.now();
			// Auto-expand when issues found, collapse when all pass
			expanded = result.checks.some((c) => !c.success && c.message !== 'Not configured')
				|| result.paths.some((p) => pathStatus(p) !== 'pass');
		} catch {
			error = 'Failed to run health checks';
		} finally {
			loading = false;
		}
	}

	async function fix() {
		if (fixableItems.length === 0) return;
		fixing = true;
		try {
			result = await fixPreflight(fixableItems);
			lastChecked = Date.now();
			// Re-evaluate expansion
			expanded = result.checks.some((c) => !c.success && c.message !== 'Not configured')
				|| result.paths.some((p) => pathStatus(p) !== 'pass');
		} catch {
			error = 'Fix attempt failed';
		} finally {
			fixing = false;
		}
	}

	function copyToClipboard(text: string) {
		navigator.clipboard.writeText(text);
	}

	function toggleExpanded() {
		expanded = !expanded;
	}

	// Force re-render of timeAgo by ticking every 30s
	let tick = $state(0);
	$effect(() => {
		const interval = setInterval(() => { tick += 1; }, 30000);
		return () => clearInterval(interval);
	});
	// Use tick in the derived to force re-evaluation
	let lastCheckedText = $derived.by(() => {
		void tick;
		if (!lastChecked) return '';
		return timeAgo(lastChecked);
	});
</script>

<div class="rounded-xl border border-primary/20 bg-surface p-6 shadow-sm dark:border-primary/20 dark:bg-surface-dark">
	{#if !result && !loading && !error}
		<!-- Neutral state: not yet run -->
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-3">
				<svg class="h-5 w-5 text-gray-400 dark:text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
					<path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
				</svg>
				<div>
					<h3 class="text-sm font-semibold text-gray-900 dark:text-white">System Health</h3>
					<p class="text-xs text-gray-500 dark:text-gray-400">Check API keys and path permissions</p>
				</div>
			</div>
			<button
				type="button"
				onclick={runChecks}
				class="rounded-lg bg-primary/15 px-4 py-2 text-sm font-medium text-primary-text hover:bg-primary/25 dark:text-primary-text-dark dark:hover:bg-primary/30 transition-colors"
			>
				Run Checks
			</button>
		</div>
	{:else if loading && !result}
		<!-- Loading state: first run -->
		<div class="flex items-center gap-3">
			<svg class="h-5 w-5 animate-spin text-primary" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
				<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
				<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
			</svg>
			<span class="text-sm text-gray-500 dark:text-gray-400">Running health checks...</span>
		</div>
	{:else if error && !result}
		<!-- Error state -->
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-3">
				<svg class="h-5 w-5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
					<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
				</svg>
				<div>
					<h3 class="text-sm font-semibold text-gray-900 dark:text-white">System Health</h3>
					<p class="text-xs text-red-600 dark:text-red-400">{error}</p>
				</div>
			</div>
			<button
				type="button"
				onclick={runChecks}
				class="rounded-lg bg-primary/15 px-4 py-2 text-sm font-medium text-primary-text hover:bg-primary/25 dark:text-primary-text-dark dark:hover:bg-primary/30 transition-colors"
			>
				Retry
			</button>
		</div>
	{:else if result}
		<!-- Results: summary bar (always visible, clickable) -->
		<button
			type="button"
			onclick={toggleExpanded}
			class="flex w-full items-center justify-between text-left"
		>
			<div class="flex items-center gap-3">
				{#if hasIssues}
					<svg class="h-5 w-5 text-amber-500" fill="currentColor" viewBox="0 0 20 20">
						<path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
					</svg>
				{:else}
					<svg class="h-5 w-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
						<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
					</svg>
				{/if}
				<div>
					<h3 class="text-sm font-semibold text-gray-900 dark:text-white">
						{#if hasIssues}
							{warningCount} issue{warningCount === 1 ? '' : 's'} found
						{:else}
							All checks passed
						{/if}
					</h3>
					<p class="text-xs text-gray-500 dark:text-gray-400">
						{validKeyCount} key{validKeyCount === 1 ? '' : 's'} valid
						- {writablePathCount} path{writablePathCount === 1 ? '' : 's'} OK
						- ARM {result.arm_uid}:{result.arm_gid}
						- Last checked {lastCheckedText}
					</p>
				</div>
			</div>
			<div class="flex items-center gap-2">
				{#if loading}
					<svg class="h-4 w-4 animate-spin text-primary" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
						<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
						<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
					</svg>
				{/if}
				<svg
					class="h-5 w-5 text-gray-400 transition-transform duration-200 {expanded ? 'rotate-180' : ''}"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
					stroke-width="1.5"
				>
					<path stroke-linecap="round" stroke-linejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
				</svg>
			</div>
		</button>

		<!-- Expanded detail area -->
		{#if expanded}
			<div class="mt-4 space-y-4 border-t border-primary/10 pt-4 dark:border-primary/10">
				<!-- Failed checks and paths (issues at top) -->
				{#if failedChecks.length > 0 || failedPaths.length > 0}
					<div class="space-y-2">
						{#each failedChecks as check}
							{@const status = checkStatus(check)}
							<div class="flex items-center justify-between rounded-lg border border-primary/15 bg-surface px-4 py-3 dark:border-primary/15 dark:bg-surface-dark">
								<div class="flex items-center gap-2">
									{#if status === 'warn'}
										<svg class="h-4 w-4 text-amber-500" fill="currentColor" viewBox="0 0 20 20">
											<path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
										</svg>
									{:else}
										<svg class="h-4 w-4 text-red-500" fill="currentColor" viewBox="0 0 20 20">
											<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
										</svg>
									{/if}
									<span class="text-sm font-medium text-gray-900 dark:text-white">
										{KEY_LABELS[check.name] ?? check.name}
									</span>
								</div>
								<span class="text-xs {status === 'warn' ? 'text-amber-600 dark:text-amber-400' : 'text-red-600 dark:text-red-400'}">
									{check.message}
								</span>
							</div>
						{/each}

						{#each failedPaths as path}
							<div class="rounded-lg border border-primary/15 bg-surface px-4 py-3 dark:border-primary/15 dark:bg-surface-dark">
								<div class="flex items-center justify-between">
									<div class="flex items-center gap-2">
										<svg class="h-4 w-4 text-red-500" fill="currentColor" viewBox="0 0 20 20">
											<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
										</svg>
										<div>
											<span class="text-sm font-medium text-gray-900 dark:text-white">{path.name}</span>
											<div class="flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500">
												{#if path.host_path}
													<span title="Host path">{path.host_path}</span>
													<span class="text-gray-300 dark:text-gray-600">-></span>
												{/if}
												<span title="Container path">{path.container_path}</span>
											</div>
										</div>
									</div>
									<div class="text-right">
										<span class="text-xs text-red-600 dark:text-red-400">
											{#if !path.exists}Missing{:else if !path.match}Owner {path.owner_uid}:{path.owner_gid} (expected {path.expected_uid}:{path.expected_gid}){:else if path.require_writable}Not writable{:else}Read-only{/if}
										</span>
									</div>
								</div>
								{#if !path.fixable}
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
				{/if}

				<!-- Passing checks (dimmed, below separator if issues exist) -->
				{#if passingChecks.length > 0 || passingPaths.length > 0}
					{#if failedChecks.length > 0 || failedPaths.length > 0}
						<div class="border-t border-primary/10 pt-3 dark:border-primary/10">
							<p class="mb-2 text-xs font-medium uppercase tracking-wide text-gray-400 dark:text-gray-500">Passing</p>
						</div>
					{/if}
					<div class="space-y-1.5 opacity-60">
						{#each passingChecks as check}
							<div class="flex items-center justify-between rounded-lg px-4 py-2">
								<div class="flex items-center gap-2">
									<svg class="h-4 w-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
										<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
									</svg>
									<span class="text-sm text-gray-700 dark:text-gray-300">
										{KEY_LABELS[check.name] ?? check.name}
									</span>
								</div>
								<span class="text-xs text-green-600 dark:text-green-400">{check.message}</span>
							</div>
						{/each}
						{#each passingPaths as path}
							<div class="flex items-center justify-between rounded-lg px-4 py-2">
								<div class="flex items-center gap-2">
									<svg class="h-4 w-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
										<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
									</svg>
									<span class="text-sm text-gray-700 dark:text-gray-300">{path.name}</span>
								</div>
								<span class="text-xs text-green-600 dark:text-green-400">OK</span>
							</div>
						{/each}
					</div>
				{/if}

				<!-- Action buttons -->
				<div class="flex items-center gap-3 pt-2">
					<button
						type="button"
						onclick={runChecks}
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
			</div>
		{/if}
	{/if}
</div>
