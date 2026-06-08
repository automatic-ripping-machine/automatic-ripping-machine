<script lang="ts">
	import type { JobSchema as Job, JobConfigSnapshot, JobConfigUpdateRequest as JobConfigUpdate } from '$lib/types/api.gen';
	import { updateJobConfig, updateJobNaming, fetchNamingVariables, fetchNamingPreview } from '$lib/api/jobs';
	import type { NamingPreviewTrack } from '$lib/api/jobs';
	import { onMount } from 'svelte';

	interface Props {
		job: Job;
		config: JobConfigSnapshot;
		isMusic?: boolean;
		multiTitle?: boolean;
		onsaved?: () => void;
	}

	let { job, config, isMusic = false, multiTitle = false, onsaved }: Props = $props();

	let ripmethod = $state(String(config.RIPMETHOD ?? 'mkv').toLowerCase());
	let disctype = $state(String(config.DISCTYPE ?? job.disctype ?? 'dvd').toLowerCase());
	let mainfeature = $state(
		config.MAINFEATURE === true
		|| String(config.MAINFEATURE ?? '').toLowerCase() === 'true'
		|| String(config.MAINFEATURE ?? '') === '1'
	);
	let minlength = $state(Number(config.MINLENGTH) || 120);
	let maxlength = $state(Number(config.MAXLENGTH) || 99999);
	let audioFormat = $state(String(config.AUDIO_FORMAT ?? 'flac').toLowerCase());

	// Naming patterns for current media type. JobConfigSnapshot is
	// permissive (extra='allow') because arm-neu's per-job config has
	// ~90 keys; cast to a plain string-map for the pattern lookup.
	const cfgStr = config as unknown as Record<string, string | null | undefined>;
	let namingPatterns = $derived.by(() => {
		const vtype = job.video_type?.toLowerCase();
		if (isMusic || disctype === 'music') {
			return {
				label: 'Music',
				title: cfgStr.MUSIC_TITLE_PATTERN ?? '{artist} - {album}',
				folder: cfgStr.MUSIC_FOLDER_PATTERN ?? '{artist}/{album} ({year})',
				titleKey: 'MUSIC_TITLE_PATTERN',
				folderKey: 'MUSIC_FOLDER_PATTERN',
			};
		}
		if (vtype === 'series') {
			return {
				label: 'TV',
				title: cfgStr.TV_TITLE_PATTERN ?? '{show} S{season}E{episode}',
				folder: cfgStr.TV_FOLDER_PATTERN ?? '{show}/Season {season}',
				titleKey: 'TV_TITLE_PATTERN',
				folderKey: 'TV_FOLDER_PATTERN',
			};
		}
		return {
			label: 'Movie',
			title: cfgStr.MOVIE_TITLE_PATTERN ?? '{title} ({year})',
			folder: cfgStr.MOVIE_FOLDER_PATTERN ?? '{title} ({year})',
			titleKey: 'MOVIE_TITLE_PATTERN',
			folderKey: 'MOVIE_FOLDER_PATTERN',
		};
	});

	// Naming override state
	let overrideEnabled = $state(!!job.title_pattern_override || !!job.folder_pattern_override);
	let titlePattern = $state(job.title_pattern_override || namingPatterns.title);
	let folderPattern = $state(job.folder_pattern_override || namingPatterns.folder);
	let validVars = $state<string[]>([]);
	let namingSaving = $state(false);
	let namingFeedback = $state<{ type: 'success' | 'error'; message: string } | null>(null);
	let namingPreviewText = $state('');
	let lastFocusedInput = $state<HTMLInputElement | null>(null);
	let patternValidation = $state<{ valid: boolean; errors: string[] }>({ valid: true, errors: [] });

	// Fetch variables on mount
	onMount(async () => {
		try {
			const result = await fetchNamingVariables();
			validVars = result.variables;
		} catch { /* fallback: empty */ }
	});

	// Validate pattern client-side
	function validateLocally(pattern: string): string[] {
		const tokens = [...pattern.matchAll(/\{(\w+)\}/g)].map(m => m[1]);
		return tokens.filter(t => validVars.length > 0 && !validVars.includes(t));
	}

	function handlePatternInput() {
		const titleErrors = validateLocally(titlePattern);
		const folderErrors = validateLocally(folderPattern);
		const errors = [...new Set([...titleErrors, ...folderErrors])];
		patternValidation = { valid: errors.length === 0, errors };
		// Debounced preview
		clearTimeout(previewTimer);
		previewTimer = window.setTimeout(loadPreview, 500);
	}

	let previewTimer = 0;
	async function loadPreview() {
		try {
			const result = await fetchNamingPreview(job.job_id);
			if (result.success && result.tracks.length > 0) {
				namingPreviewText = result.tracks[0].rendered_title;
			}
		} catch { /* ignore */ }
	}

	function insertVariable(varName: string) {
		if (!lastFocusedInput) return;
		const input = lastFocusedInput;
		const start = input.selectionStart ?? input.value.length;
		const end = input.selectionEnd ?? start;
		const text = `{${varName}}`;
		const before = input.value.slice(0, start);
		const after = input.value.slice(end);
		input.value = before + text + after;
		input.dispatchEvent(new Event('input', { bubbles: true }));
		// Restore cursor after insertion
		const newPos = start + text.length;
		input.setSelectionRange(newPos, newPos);
		input.focus();
		// Update state
		if (input.dataset.field === 'title') titlePattern = input.value;
		else folderPattern = input.value;
		handlePatternInput();
	}

	async function saveNamingOverrides() {
		namingSaving = true;
		namingFeedback = null;
		try {
			await updateJobNaming(job.job_id, {
				title_pattern_override: overrideEnabled ? titlePattern : null,
				folder_pattern_override: overrideEnabled ? folderPattern : null,
			});
			namingFeedback = { type: 'success', message: 'Saved' };
			onsaved?.();
		} catch (e) {
			namingFeedback = { type: 'error', message: e instanceof Error ? e.message : 'Save failed' };
		} finally {
			namingSaving = false;
		}
	}

	function toggleOverride() {
		if (overrideEnabled) {
			if (!confirm('Clear pattern overrides? This will revert to global settings.')) return;
			overrideEnabled = false;
			titlePattern = namingPatterns.title;
			folderPattern = namingPatterns.folder;
			saveNamingOverrides();
		} else {
			overrideEnabled = true;
		}
	}

	let saving = $state(false);
	let feedback = $state<{ type: 'success' | 'error'; message: string } | null>(null);

	async function handleSave() {
		saving = true;
		feedback = null;
		try {
			const data: Partial<JobConfigUpdate> = {
				RIPMETHOD: ripmethod as 'mkv' | 'backup',
				DISCTYPE: disctype as 'dvd' | 'bluray' | 'bluray4k' | 'music' | 'data',
				MAINFEATURE: mainfeature,
				MINLENGTH: minlength,
				MAXLENGTH: maxlength,
				AUDIO_FORMAT: audioFormat
			};
			await updateJobConfig(job.job_id, data);
			feedback = { type: 'success', message: 'Settings saved' };
			onsaved?.();
		} catch (e) {
			feedback = { type: 'error', message: e instanceof Error ? e.message : 'Save failed' };
		} finally {
			saving = false;
		}
	}

	const inputClass =
		'rounded-lg border border-primary/25 bg-primary/5 px-3 py-1.5 text-sm text-gray-900 focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary dark:border-primary/30 dark:bg-primary/10 dark:text-white';
	const labelClass = 'text-sm font-medium text-gray-700 dark:text-gray-300';
	const btnBase =
		'rounded-lg px-3 py-1.5 text-sm font-medium disabled:opacity-50 transition-colors';
</script>

<div class="space-y-4">
	<div class="grid grid-cols-2 gap-3 sm:grid-cols-3">
		{#if !isMusic}
			<label class="space-y-1">
				<span class={labelClass}>Rip Method</span>
				<select bind:value={ripmethod} class="{inputClass} w-full">
					<option value="mkv">MKV</option>
					<option value="backup">Backup (ISO)</option>
				</select>
			</label>
		{/if}

		<label class="space-y-1">
			<span class={labelClass}>Disc Type</span>
			<select bind:value={disctype} class="{inputClass} w-full">
				<option value="dvd">DVD</option>
				<option value="bluray">Blu-ray</option>
				<option value="bluray4k">4K UHD</option>
				<option value="music">Music</option>
				<option value="data">Data</option>
			</select>
		</label>

		{#if !isMusic && !multiTitle}
			<div class="space-y-1">
				<label class="flex items-center gap-2">
					<input
						type="checkbox"
						bind:checked={mainfeature}
						class="h-4 w-4 rounded-sm border-primary/25 text-primary focus:ring-primary dark:border-primary/30 dark:bg-primary/10"
					/>
					<span class={labelClass}>Main Feature Only</span>
				</label>
				<p class="text-xs text-gray-500 dark:text-gray-400">Auto-enable only the best track; when off, all tracks are enabled</p>
			</div>
		{/if}

		{#if !isMusic}
			<label class="space-y-1">
				<span class={labelClass}>Min Length (s)</span>
				<input type="number" bind:value={minlength} min="0" class="{inputClass} w-full" />
			</label>

			<label class="space-y-1">
				<span class={labelClass}>Max Length (s)</span>
				<input type="number" bind:value={maxlength} min="0" class="{inputClass} w-full" />
			</label>
		{/if}
	</div>

	{#if isMusic}
		<div class="grid grid-cols-2 gap-3 sm:grid-cols-3">
			<label class="space-y-1">
				<span class={labelClass}>Audio Format</span>
				<select bind:value={audioFormat} class="{inputClass} w-full">
					<optgroup label="Common">
						<option value="flac">FLAC</option>
						<option value="mp3">MP3</option>
						<option value="vorbis">Ogg Vorbis</option>
						<option value="opus">Opus</option>
						<option value="m4a">AAC (M4A)</option>
						<option value="wav">WAV</option>
					</optgroup>
					<optgroup label="Other">
						<option value="wv">WavPack</option>
						<option value="ape">Monkey's Audio</option>
						<option value="mpc">Musepack</option>
						<option value="spx">Speex</option>
						<option value="mp2">MP2</option>
						<option value="tta">TTA</option>
						<option value="aiff">AIFF</option>
						<option value="mka">Matroska Audio</option>
					</optgroup>
				</select>
			</label>
		</div>
	{/if}

	<!-- Naming patterns (editable with per-job override) -->
	<div class="rounded-lg border {overrideEnabled ? 'border-green-500/30' : 'border-primary/15'} bg-primary/[0.03] p-3 dark:border-primary/20 dark:bg-primary/5">
		<div class="mb-2 flex items-center justify-between">
			<span class="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
				{namingPatterns.label} Naming
			</span>
			<button
				onclick={toggleOverride}
				class="flex items-center gap-1.5 text-[10px] font-medium {overrideEnabled ? 'text-green-500' : 'text-gray-400'}"
			>
				Override
				<div class="h-4 w-7 rounded-full transition-colors {overrideEnabled ? 'bg-green-500' : 'bg-gray-300 dark:bg-gray-600'}" style="position:relative;">
					<div class="absolute top-0.5 h-3 w-3 rounded-full bg-white shadow transition-transform {overrideEnabled ? 'translate-x-3.5' : 'translate-x-0.5'}"></div>
				</div>
			</button>
		</div>

		{#if overrideEnabled && validVars.length > 0}
			<div class="mb-2 flex flex-wrap gap-1">
				{#each validVars as v}
					<button
						onclick={() => insertVariable(v)}
						class="rounded bg-blue-100 px-1.5 py-0.5 text-[10px] font-mono text-blue-700 transition-colors hover:bg-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:hover:bg-blue-800/40"
					>
						{`{${v}}`}
					</button>
				{/each}
			</div>
		{/if}

		<div class="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
			<div>
				<span class="text-[10px] font-medium text-gray-400 dark:text-gray-500">Title</span>
				{#if overrideEnabled}
					<input
						type="text"
						data-field="title"
						bind:value={titlePattern}
						onfocus={(e) => { lastFocusedInput = e.currentTarget; }}
						oninput={handlePatternInput}
						class="w-full rounded border px-1.5 py-0.5 font-mono text-xs {patternValidation.valid ? 'border-green-500/40 text-gray-900 dark:border-green-500/30 dark:text-white' : 'border-red-500 text-red-700 dark:text-red-400'} bg-surface dark:bg-surface-dark"
					/>
				{:else}
					<p class="font-mono text-xs text-gray-500 dark:text-gray-500">{namingPatterns.title}</p>
				{/if}
			</div>
			<div>
				<span class="text-[10px] font-medium text-gray-400 dark:text-gray-500">Folder</span>
				{#if overrideEnabled}
					<input
						type="text"
						data-field="folder"
						bind:value={folderPattern}
						onfocus={(e) => { lastFocusedInput = e.currentTarget; }}
						oninput={handlePatternInput}
						class="w-full rounded border px-1.5 py-0.5 font-mono text-xs {patternValidation.valid ? 'border-green-500/40 text-gray-900 dark:border-green-500/30 dark:text-white' : 'border-red-500 text-red-700 dark:text-red-400'} bg-surface dark:bg-surface-dark"
					/>
				{:else}
					<p class="font-mono text-xs text-gray-500 dark:text-gray-500">{namingPatterns.folder}</p>
				{/if}
			</div>
		</div>

		{#if overrideEnabled}
			{#if !patternValidation.valid}
				<p class="mt-1 text-[10px] text-red-500">Unknown variable{patternValidation.errors.length > 1 ? 's' : ''}: {patternValidation.errors.map(e => `{${e}}`).join(', ')}</p>
			{:else if namingPreviewText}
				<p class="mt-1 text-[10px] text-green-500">Preview: {namingPreviewText}</p>
			{/if}
			<div class="mt-2 flex items-center gap-2">
				<button
					onclick={saveNamingOverrides}
					disabled={namingSaving || !patternValidation.valid}
					class="{btnBase} bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 dark:bg-green-500"
				>
					{namingSaving ? 'Saving...' : 'Save Pattern'}
				</button>
				{#if namingFeedback}
					<span class="text-[10px] {namingFeedback.type === 'success' ? 'text-green-500' : 'text-red-500'}">{namingFeedback.message}</span>
				{/if}
			</div>
		{/if}
	</div>

	<div class="flex items-center gap-2">
		<button
			onclick={handleSave}
			disabled={saving}
			class="{btnBase} bg-green-600 text-white hover:bg-green-700 dark:bg-green-500 dark:hover:bg-green-600"
		>
			{saving ? 'Saving...' : 'Save Settings'}
		</button>
		{#if feedback}
			<span
				class="text-xs {feedback.type === 'success'
					? 'text-green-600 dark:text-green-400'
					: 'text-red-600 dark:text-red-400'}"
			>
				{feedback.message}
			</span>
		{/if}
	</div>
</div>
