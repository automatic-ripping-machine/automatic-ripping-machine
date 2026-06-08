<script lang="ts">
	import { slide } from 'svelte/transition';
	import { onMount } from 'svelte';
	import LoadState from '$lib/components/LoadState.svelte';
	import SkeletonCard from '$lib/components/SkeletonCard.svelte';
	import { fetchSettings, saveArmConfig, saveTranscoderConfig, testMetadataKey, testTranscoderConnection, testTranscoderWebhook, fetchSystemInfo, fetchAbcdeConfig, saveAbcdeConfig } from '$lib/api/settings';
	import type { ConnectionTestResult, WebhookTestResult, SystemInfoData } from '$lib/api/settings';
	import type { SettingsResponse as SettingsData, DriveSchema as Drive } from '$lib/types/api.gen';
	import { theme, toggleTheme } from '$lib/stores/theme';
	import { colorScheme, COLOR_SCHEMES, schemeLocksMode, allSchemes, loadThemesFromApi } from '$lib/stores/colorScheme';
	import { uploadTheme, deleteTheme as deleteThemeApi } from '$lib/api/themes';
	import { createPollingStore } from '$lib/stores/polling';
	import { fetchDrives, fetchDriveDiagnostic, rescanDrives } from '$lib/api/drives';
	import type { DiagnosticResult } from '$lib/api/drives';
	import DriveCard from '$lib/components/DriveCard.svelte';
	import { restartArm, restartTranscoder } from '$lib/api/system';
	import { fetchImageCacheStats, clearImageCache, type ImageCacheStats } from '$lib/api/maintenance';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
	import SystemHealth from '$lib/components/settings/SystemHealth.svelte';
	import PresetEditor from '$lib/components/PresetEditor.svelte';
	import { fetchTranscoderScheme, fetchTranscoderPresets, createCustomPreset } from '$lib/api/settings';
	import type { Scheme, Preset, Overrides } from '$lib/types/api.gen';
	import type { PresetEditorState } from '$lib/types/presets';
	import { transcoderEnabled } from '$lib/stores/config';
	import { dashboard } from '$lib/stores/dashboard';
	import { get } from 'svelte/store';
	import NotificationsTab from '$lib/components/notifications/NotificationsTab.svelte';
	import ToastHost from '$lib/components/ToastHost.svelte';

	let settings = $state<SettingsData | null>(null);
	let settingsLoading = $state(true);
	let settingsError = $state<Error | null>(null);

	// --- Transcoder form state ---
	let tcForm = $state<Record<string, unknown>>({});
	let tcOriginal = $state<Record<string, unknown>>({});
	let tcSaving = $state(false);
	let tcFeedback = $state<{ type: 'success' | 'error'; message: string } | null>(null);

	// --- ARM form state ---
	let armForm = $state<Record<string, string | null>>({});
	let armOriginal = $state<Record<string, string | null>>({});
	let armSaving = $state(false);
	let armFeedback = $state<{ type: 'success' | 'error'; message: string } | null>(null);
	let armRevealedKeys = $state<Set<string>>(new Set());
	let armCollapsed = $state<Record<string, boolean>>({});

	// --- Preset editor state ---
	let presetScheme = $state<Scheme | null>(null);
	let presets = $state<Preset[]>([]);
	let presetOffline = $state(false);
	let presetSaving = $state(false);

	const presetInitialState = $derived.by<PresetEditorState>(() => {
		// $state.snapshot converts the reactive proxy tree to plain data so
		// child components never see Svelte $state proxies through props.
		// Passing proxies triggers DOMException 'Proxy object could not be
		// cloned' when the browser structured-clones the prop payload.
		const cfg = $state.snapshot(settings?.transcoder_config?.config) as
			| Record<string, unknown>
			| undefined;
		const raw = cfg?.global_overrides as Partial<Overrides> | undefined;
		return {
			preset_slug: (cfg?.selected_preset_slug as string) ?? '',
			overrides: {
				shared: raw?.shared ?? {},
				tiers: raw?.tiers ?? {}
			}
		};
	});

	async function loadPresetData() {
		presetOffline = false;
		const [s, p] = await Promise.all([fetchTranscoderScheme(), fetchTranscoderPresets()]);
		if (s === null || p === null) {
			presetOffline = true;
			return;
		}
		presetScheme = s;
		presets = p.presets;
	}

	async function handlePresetSave(state: PresetEditorState) {
		presetSaving = true;
		try {
			await saveTranscoderConfig({
				selected_preset_slug: state.preset_slug,
				global_overrides: state.overrides
			});
			await loadSettings();
		} finally {
			presetSaving = false;
		}
	}

	async function handlePresetSaveAsNew(body: { name: string; parent_slug: string; overrides: Overrides }) {
		presetSaving = true;
		try {
			const newPreset = await createCustomPreset(body);
			await loadPresetData();
			await saveTranscoderConfig({
				selected_preset_slug: newPreset.slug,
				global_overrides: { shared: {}, tiers: {} }
			});
			await loadSettings();
		} finally {
			presetSaving = false;
		}
	}

	// --- Restart state ---
	let armRestarting = $state(false);
	let armRestartFeedback = $state<{ type: 'success' | 'error'; message: string } | null>(null);
	let tcRestarting = $state(false);
	let tcRestartFeedback = $state<{ type: 'success' | 'error'; message: string } | null>(null);

	async function handleRestart(service: 'arm' | 'transcoder') {
		const label = service === 'arm' ? 'ARM ripping service' : 'Transcoder service';
		const warning = service === 'arm'
			? 'Restart the ARM ripping service? Active rips will be interrupted.'
			: 'Restart the transcoder service? Active transcodes will be interrupted.';
		if (!confirm(warning)) return;

		if (service === 'arm') {
			armRestarting = true;
			armRestartFeedback = null;
		} else {
			tcRestarting = true;
			tcRestartFeedback = null;
		}

		try {
			const fn = service === 'arm' ? restartArm : restartTranscoder;
			await fn();
			const fb = { type: 'success' as const, message: `${label} is restarting` };
			if (service === 'arm') armRestartFeedback = fb;
			else tcRestartFeedback = fb;
			setTimeout(() => {
				if (service === 'arm') { armRestarting = false; armRestartFeedback = null; }
				else { tcRestarting = false; tcRestartFeedback = null; }
			}, 5000);
		} catch {
			const fb = { type: 'error' as const, message: `Failed to restart ${label}` };
			if (service === 'arm') { armRestartFeedback = fb; armRestarting = false; }
			else { tcRestartFeedback = fb; tcRestarting = false; }
		}
	}

	// --- Tab state ---
	const allTabs = ['ripping', 'music', 'transcoding', 'notifications', 'appearance', 'drives', 'system'] as const;
	type Tab = typeof allTabs[number];
	const validTabs = $derived(
		$transcoderEnabled ? allTabs : (allTabs.filter(t => t !== 'transcoding') as readonly Tab[])
	);

	function parseHash(): { tab: Tab; panel: string | null } {
		if (typeof window === 'undefined') return { tab: 'ripping', panel: null };
		const hash = window.location.hash.replace('#', '');
		const [tabPart, ...panelParts] = hash.split('/');
		const tcEnabled = get(transcoderEnabled);
		const allowedTabs: readonly Tab[] = tcEnabled
			? allTabs
			: (allTabs.filter(t => t !== 'transcoding') as readonly Tab[]);
		const tab = allowedTabs.includes(tabPart as Tab) ? (tabPart as Tab) : 'ripping';
		const panel = panelParts.length > 0 ? decodeURIComponent(panelParts.join('/')) : null;
		return { tab, panel };
	}

	let activeTab = $state<Tab>(parseHash().tab);
	let pendingPanel = $state<string | null>(parseHash().panel);

	// --- Drives polling store ---
	const drives = createPollingStore(fetchDrives, [] as Drive[], 10000);
	const driveError = drives.error;

	// --- Drive diagnostics ---
	let diagRunning = $state(false);
	let diagResult = $state<DiagnosticResult | null>(null);
	let diagError = $state<string | null>(null);
	let diagOpen = $state(false);
	let rescanning = $state(false);
	let diagLastRun = $state<string | null>(null);

	async function runDiagnostic() {
		if (diagRunning) return;
		diagRunning = true;
		diagError = null;
		try {
			diagResult = await fetchDriveDiagnostic();
			diagLastRun = new Date().toLocaleTimeString();
			diagOpen = true;
		} catch (e) {
			diagError = e instanceof Error ? e.message : 'Diagnostic failed';
			diagResult = null;
		} finally {
			diagRunning = false;
		}
	}

	// --- Search/filter ---
	let armSearch = $state('');

	// --- Metadata test ---
	let metadataTestResult = $state<{ success: boolean; message: string } | null>(null);
	let metadataTesting = $state(false);

	// --- Transcoder connection test ---
	let connTesting = $state(false);
	let connResult = $state<ConnectionTestResult | null>(null);

	// --- Transcoder webhook test ---
	let webhookTesting = $state(false);
	let webhookResult = $state<WebhookTestResult | null>(null);
	let webhookSecret = $state('');

	// --- System Info state ---
	let systemInfo = $state<SystemInfoData | null>(null);
	let systemInfoLoading = $state(false);
	let systemInfoLoaded = $state(false);

	// --- abcde.conf editor state ---
	let abcdeContent = $state('');
	let abcdeOriginal = $state('');
	let abcdePath = $state('');
	let abcdeExists = $state(false);
	let abcdeLoading = $state(false);
	let abcdeSaving = $state(false);
	let abcdeLoaded = $state(false);
	let abcdeFeedback = $state<{ type: 'success' | 'error'; message: string } | null>(null);
	let abcdeDirty = $derived(abcdeContent !== abcdeOriginal);
	let abcdeCollapsed = $state(false);

	// --- Theme management ---
	let themeUploading = $state(false);
	let themeFeedback = $state<{ type: 'success' | 'error'; message: string } | null>(null);
	let themeJsonFile = $state<File | null>(null);
	let themeName = $state('');
	let themeCssText = $state('');

	// --- Image cache state ---
	let cacheStats = $state<ImageCacheStats | null>(null);
	let cacheLoading = $state(false);
	let cacheBusy = $state(false);
	let cacheConfirmOpen = $state(false);
	let cacheFeedback = $state<{ type: 'success' | 'error'; message: string } | null>(null);

	async function loadCacheStats() {
		cacheLoading = true;
		try { cacheStats = await fetchImageCacheStats(); }
		catch { cacheStats = null; }
		cacheLoading = false;
	}

	async function handleClearCache() {
		cacheBusy = true;
		cacheConfirmOpen = false;
		try {
			const result = await clearImageCache();
			const cleared = result.cleared ?? 0;
			const freedMb = ((result.freed_bytes ?? 0) / 1048576).toFixed(1);
			cacheFeedback = { type: 'success', message: `Cleared ${cleared} cached image${cleared !== 1 ? 's' : ''} (${freedMb} MB)` };
			cacheStats = await fetchImageCacheStats();
		} catch (e) {
			cacheFeedback = { type: 'error', message: e instanceof Error ? e.message : 'Failed to clear cache' };
		}
		cacheBusy = false;
	}

	async function handleThemeUpload() {
		if (!themeJsonFile) return;
		const name = themeName.trim();
		if (!name) {
			themeFeedback = { type: 'error', message: 'Theme name is required' };
			return;
		}
		themeUploading = true;
		themeFeedback = null;
		try {
			const text = await themeJsonFile.text();
			const data = JSON.parse(text);
			// Override label and derive id from the name field
			data.label = name;
			data.id = name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
			if (!data.id || !data.tokens) {
				throw new Error('Invalid theme: missing required fields (tokens)');
			}
			// Re-create the file with patched data
			const patched = new File([JSON.stringify(data)], `${data.id}.json`, { type: 'application/json' });
			await uploadTheme(patched, themeCssText);
			await loadThemesFromApi();
			themeFeedback = { type: 'success', message: `Theme "${data.label}" uploaded` };
			themeJsonFile = null;
			themeName = '';
			themeCssText = '';
		} catch (e) {
			themeFeedback = { type: 'error', message: e instanceof Error ? e.message : 'Upload failed' };
		} finally {
			themeUploading = false;
		}
	}

	function handleJsonFileSelect(event: Event) {
		const input = event.target as HTMLInputElement;
		themeJsonFile = input.files?.[0] ?? null;
	}

	async function handleThemeDelete(id: string, label: string) {
		if (!confirm(`Delete user theme "${label}"?`)) return;
		themeFeedback = null;
		try {
			await deleteThemeApi(id);
			await loadThemesFromApi();
			if ($colorScheme === id) $colorScheme = 'blue';
			themeFeedback = { type: 'success', message: `Theme "${label}" deleted` };
		} catch (e) {
			themeFeedback = { type: 'error', message: e instanceof Error ? e.message : 'Delete failed' };
		}
	}

	function triggerDownload(blob: Blob, filename: string) {
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = filename;
		a.click();
		URL.revokeObjectURL(url);
	}

	async function handleThemeDownload(id: string) {
		const enc = encodeURIComponent(id);
		try {
			// Download JSON
			const jsonRes = await fetch(`/api/themes/${enc}/download`);
			if (jsonRes.ok) {
				const jsonBlob = await jsonRes.blob();
				triggerDownload(jsonBlob, `${id}.json`);
			}
			// Download CSS if the theme has any
			const cssRes = await fetch(`/api/themes/${enc}/css`);
			if (cssRes.ok) {
				const cssBlob = await cssRes.blob();
				triggerDownload(cssBlob, `${id}.css`);
			}
		} catch { /* download failed silently */ }
	}

	async function loadAbcdeConfig() {
		if (abcdeLoaded) return;
		abcdeLoading = true;
		try {
			const data = await fetchAbcdeConfig();
			abcdeContent = data.content;
			abcdeOriginal = data.content;
			abcdePath = data.path;
			abcdeExists = data.exists;
			abcdeLoaded = true;
		} catch {
			// silently fail, will show empty state
		} finally {
			abcdeLoading = false;
		}
	}

	async function handleAbcdeSave() {
		abcdeSaving = true;
		abcdeFeedback = null;
		try {
			await saveAbcdeConfig(abcdeContent);
			abcdeOriginal = abcdeContent;
			abcdeExists = true;
			abcdeFeedback = { type: 'success', message: 'abcde.conf saved' };
		} catch (e) {
			abcdeFeedback = { type: 'error', message: e instanceof Error ? e.message : 'Failed to save' };
		} finally {
			abcdeSaving = false;
			clearFeedback(() => (abcdeFeedback = null));
		}
	}

	function handleAbcdeDiscard() {
		abcdeContent = abcdeOriginal;
	}

	// --- abcde.conf search ---
	let abcdeSearch = $state('');
	let abcdeSearchIndex = $state(0);
	let abcdeTextarea = $state<HTMLTextAreaElement | null>(null);

	let abcdeMatches = $derived.by<number[]>(() => {
		if (!abcdeSearch) return [];
		const q = abcdeSearch.toLowerCase();
		const text = abcdeContent.toLowerCase();
		const positions: number[] = [];
		let idx = 0;
		while ((idx = text.indexOf(q, idx)) !== -1) {
			positions.push(idx);
			idx += 1;
		}
		return positions;
	});

	function abcdeSearchNav(delta: number) {
		if (abcdeMatches.length === 0) return;
		abcdeSearchIndex = (abcdeSearchIndex + delta + abcdeMatches.length) % abcdeMatches.length;
		const pos = abcdeMatches[abcdeSearchIndex];
		if (abcdeTextarea) {
			abcdeTextarea.focus();
			abcdeTextarea.setSelectionRange(pos, pos + abcdeSearch.length);
			// Scroll selection into view by briefly blurring/focusing
			const linesBefore = abcdeContent.substring(0, pos).split('\n').length;
			const lineHeight = abcdeTextarea.scrollHeight / abcdeContent.split('\n').length;
			abcdeTextarea.scrollTop = Math.max(0, (linesBefore - 3) * lineHeight);
		}
	}

	async function loadSystemInfo() {
		if (systemInfoLoaded) return;
		systemInfoLoading = true;
		try {
			systemInfo = await fetchSystemInfo();
			systemInfoLoaded = true;
		} catch (e) {
			// silently fail, will show empty state
		} finally {
			systemInfoLoading = false;
		}
	}

	// Set to true while we are mutating window.location.hash ourselves,
	// so the hashchange listener can skip the work setTab already did
	// (otherwise tab clicks scroll twice — once here, once in the listener).
	let programmaticHashChange = false;

	function setTab(tab: Tab) {
		activeTab = tab;
		pendingPanel = null;
		programmaticHashChange = true;
		window.location.hash = tab;
		if (tab === 'music') loadAbcdeConfig();
		if (tab === 'system') loadSystemInfo();
		if (tab === 'appearance') loadCacheStats();
		// Reset scroll to top when switching tabs
		document.querySelector('main')?.scrollTo(0, 0);
	}

	function scrollToPanel(label: string) {
		armCollapsed[label] = false;
		// Scroll after DOM has fully settled — 600ms gives settings
		// form fields time to render without causing scroll lock
		setTimeout(() => {
			const el = document.getElementById(`panel-${label.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`);
			if (!el) return;
			// Find the scrollable <main> ancestor and scroll within it
			const scrollContainer = el.closest('main');
			if (scrollContainer) {
				const containerRect = scrollContainer.getBoundingClientRect();
				const elRect = el.getBoundingClientRect();
				scrollContainer.scrollTop += elRect.top - containerRect.top - 16;
			} else {
				el.scrollIntoView({ behavior: 'instant', block: 'start' });
			}
		}, 600);
	}

	onMount(() => {
		// Rescan drives to pick up hardware info (model, serial) that
		// may not have been available at container startup.
		rescanDrives().catch(() => {}).then(() => drives.start());
		loadSettings().then(() => {
			if (pendingPanel) {
				// Find the panel label case-insensitively
				const groups = TAB_ARM_GROUPS[activeTab] ?? [];
				const match = groups.find((g) => g.label.toLowerCase().replace(/[^a-z0-9]+/g, '-') === pendingPanel!.toLowerCase().replace(/[^a-z0-9]+/g, '-'));
				if (match) scrollToPanel(match.label);
				pendingPanel = null;
			}
		});
		loadPresetData();
		// Handle initial hash tab (trigger side effects)
		if (activeTab === 'music') loadAbcdeConfig();
		if (activeTab === 'system') loadSystemInfo();
		if (activeTab === 'appearance') loadCacheStats();
		function onHashChange() {
			if (programmaticHashChange) {
				programmaticHashChange = false;
				return;
			}
			const { tab, panel } = parseHash();
			activeTab = tab;
			if (tab === 'music') loadAbcdeConfig();
			if (tab === 'system') loadSystemInfo();
			if (tab === 'appearance') loadCacheStats();
			if (panel) {
				const groups = TAB_ARM_GROUPS[tab] ?? [];
				const match = groups.find((g) => g.label.toLowerCase().replace(/[^a-z0-9]+/g, '-') === panel.toLowerCase().replace(/[^a-z0-9]+/g, '-'));
				if (match) scrollToPanel(match.label);
			} else {
				// Reset scroll to top when switching tabs without a panel target
				document.querySelector('main')?.scrollTo(0, 0);
			}
		}
		window.addEventListener('hashchange', onHashChange);
		return () => { drives.stop(); window.removeEventListener('hashchange', onHashChange); };
	});

	async function loadSettings() {
		settingsLoading = true;
		settingsError = null;
		try {
			settings = await fetchSettings();
			if (settings?.transcoder_config?.config) {
				tcForm = { ...settings.transcoder_config.config };
				tcOriginal = { ...settings.transcoder_config.config };
			}
			if (settings?.arm_config) {
				armForm = { ...settings.arm_config };
				armOriginal = { ...settings.arm_config };
			}
			// Collapse Emby Integration by default
			armCollapsed['Emby Integration'] = true;
		} catch (e) {
			settingsError = e instanceof Error ? e : new Error('Failed to load settings');
		} finally {
			settingsLoading = false;
		}
	}

	function clearFeedback(setter: (v: null) => void) {
		setTimeout(() => setter(null), 4000);
	}

	// --- Transcoder dirty check ---
	let tcDirty = $derived(JSON.stringify(tcForm) !== JSON.stringify(tcOriginal));

	async function handleTcSave() {
		tcSaving = true;
		tcFeedback = null;
		const changed: Record<string, unknown> = {};
		for (const [key, val] of Object.entries(tcForm)) {
			if (JSON.stringify(val) !== JSON.stringify(tcOriginal[key])) {
				changed[key] = val;
			}
		}
		try {
			const result = await saveTranscoderConfig(changed);
			if (result.applied) {
				Object.assign(tcForm, result.applied);
				tcOriginal = { ...tcForm };
			}
			tcFeedback = { type: 'success', message: 'Transcoder settings saved' };
		} catch (e) {
			tcFeedback = { type: 'error', message: e instanceof Error ? e.message : 'Failed to save' };
		} finally {
			tcSaving = false;
			clearFeedback(() => (tcFeedback = null));
		}
	}

	// --- ARM dirty check ---
	let armDirty = $derived(JSON.stringify(armForm) !== JSON.stringify(armOriginal));

	async function handleArmSave() {
		armSaving = true;
		armFeedback = null;
		try {
			const result = await saveArmConfig(armForm);
			if (result.warning) {
				armFeedback = { type: 'success', message: `Saved (${result.warning})` };
			} else {
				armFeedback = { type: 'success', message: 'ARM settings saved' };
			}
			armOriginal = { ...armForm };
		} catch (e) {
			armFeedback = { type: 'error', message: e instanceof Error ? e.message : 'Failed to save' };
		} finally {
			armSaving = false;
			clearFeedback(() => (armFeedback = null));
		}
	}

	// Any tab dirty — sticky bar persists across tab switches
	let anyDirty = $derived(armDirty || tcDirty);
	let anySaving = $derived(armSaving || tcSaving);
	let anyFeedback = $derived(armFeedback ?? tcFeedback);

	function handleSaveAll() {
		if (armDirty) handleArmSave();
		if (tcDirty) handleTcSave();
	}

	function handleDiscardAll() {
		if (armDirty) armForm = { ...armOriginal };
		if (tcDirty) tcForm = { ...tcOriginal };
	}

	let dirtyTabLabel = $derived(
		armDirty && tcDirty ? 'ARM & Transcoder' : armDirty ? 'ARM settings' : 'Transcoder'
	);

	// Transcoder base paths (read-only, for display in directories panel)
	let tcPaths = $derived(settings?.transcoder_config?.paths);

	// --- GPU support labels (transcoder only) ---
	const GPU_LABELS: Record<string, string> = {
		ffmpeg_nvenc_h265: 'FFmpeg NVENC H.265',
		ffmpeg_nvenc_h264: 'FFmpeg NVENC H.264',
		ffmpeg_vaapi_h265: 'FFmpeg VAAPI H.265',
		ffmpeg_vaapi_h264: 'FFmpeg VAAPI H.264',
		ffmpeg_amf_h265: 'FFmpeg AMF H.265',
		ffmpeg_amf_h264: 'FFmpeg AMF H.264',
		ffmpeg_qsv_h265: 'FFmpeg QSV H.265',
		ffmpeg_qsv_h264: 'FFmpeg QSV H.264',
		vaapi_device: 'VAAPI Render Device',
	};

	const HW_GROUPS = [
		{ label: 'Nvidia NVENC', keys: ['ffmpeg_nvenc_h265', 'ffmpeg_nvenc_h264'] },
		{ label: 'Intel QuickSync', keys: ['ffmpeg_qsv_h265', 'ffmpeg_qsv_h264'] },
		{ label: 'AMD VCN', keys: ['ffmpeg_amf_h265', 'ffmpeg_amf_h264'] },
		{ label: 'VAAPI (AMD/Intel)', keys: ['ffmpeg_vaapi_h265', 'ffmpeg_vaapi_h264', 'vaapi_device'] },
	];

	function hasAny(gpu: Record<string, boolean>, keys: string[]): boolean {
		return keys.some((k) => gpu[k]);
	}

	// --- Transcoder field labels ---
	const TC_LABELS: Record<string, string> = {
		delete_source: 'Delete Source After Transcode',
		output_extension: 'Output Extension',
		movies_subdir: 'Movies Subdirectory',
		tv_subdir: 'TV Shows Subdirectory',
		audio_subdir: 'Audio Subdirectory',
		max_concurrent: 'Max Concurrent Transcodes',
		stabilize_seconds: 'Stabilize Wait (seconds)',
		minimum_free_space_gb: 'Min Free Disk Space (GB)',
		max_retry_count: 'Max Retry Attempts',
		log_level: 'Log Level',
		log_level_libraries: 'Log Level (Libraries)',
	};

	// Transcoder boolean fields rendered as toggle switches
	const TC_BOOL_KEYS = new Set(['delete_source']);

	// Keys rendered in their own sub-panels (excluded from the Operational loop)
	const TC_PRESET_SET = new Set([
		// Directory panel keys
		'movies_subdir',
		'tv_subdir',
		'audio_subdir',
		'output_extension',
		'delete_source',
		// Preset-managed keys (rendered in the PresetEditor section, not as raw fields)
		'global_overrides',
		'selected_preset_slug',
		// Logging keys rendered in their own sub-panel below Operational
		'log_level',
		'log_level_libraries',
	]);

	const TC_LOGGING_KEYS = ['log_level', 'log_level_libraries'];

	// Transcoder number fields: key → [min, max, step?]
	const TC_NUMBER_FIELDS: Record<string, [number, number, number?]> = {
		max_concurrent: [1, 10],
		stabilize_seconds: [10, 600],
		minimum_free_space_gb: [1, 500, 0.5],
		max_retry_count: [0, 10],
	};

	// Help text for transcoder fields
	const TC_HELP: Record<string, string> = {
		log_level_libraries:
			'Log level for third-party libraries (aiosqlite, httpcore, httpx, uvicorn). Defaults to WARNING to reduce noise.',
	};

	// Returns the valid options array for select-type transcoder fields, or null.
	// Always includes the current value so the select never shows blank.
	function tcSelectOptions(key: string): string[] | null {
		if (!settings?.transcoder_config) return null;
		const tc = settings.transcoder_config;
		const map: Record<string, string[] | undefined> = {
			log_level: tc.valid_log_levels ?? undefined,
			log_level_libraries: tc.valid_log_levels ?? undefined,
		};
		const opts = map[key] ?? null;
		if (!opts) return null;

		// Ensure the current value is in the options list
		const current = tcForm[key];
		if (current && typeof current === 'string' && !opts.includes(current)) {
			return [current, ...opts];
		}
		return opts;
	}

	// --- ARM human-readable labels ---
	const ARM_LABELS: Record<string, { label: string; description: string }> = {
		// Video Ripping
		VIDEOTYPE: { label: 'Video Type', description: 'auto, series, or movie — how to identify inserted discs' },
		RIPMETHOD: { label: 'Rip Method', description: 'mkv (MakeMKV), backup (full disc), or backup_dvd' },
		PREVENT_99: { label: 'Track 99 Protection', description: 'Eject discs with DRM fake-title schemes instead of risking a hang' },
		ARM_CHECK_UDF: { label: 'Check UDF Filesystem', description: 'Distinguish UDF video discs from data discs' },
		GET_VIDEO_TITLE: { label: 'Lookup Video Title', description: 'Query metadata services for the movie/series title' },
		MINLENGTH: { label: 'Minimum Track Length', description: 'Minimum title length in seconds to rip' },
		MAXLENGTH: { label: 'Maximum Track Length', description: 'Maximum title length in seconds to rip' },
		MAINFEATURE: { label: 'Main Feature Only', description: 'Rip only the longest title on the disc' },
		MANUAL_WAIT: { label: 'Wait for Manual ID', description: 'Pause for user to manually identify the disc' },
		MANUAL_WAIT_TIME: { label: 'Manual Wait Time', description: 'Seconds to wait for manual identification' },
		ALLOW_DUPLICATES: { label: 'Allow Duplicates', description: 'Allow ripping a disc that has already been ripped' },
		MKV_ARGS: { label: 'MakeMKV Arguments', description: 'Extra command-line arguments passed to MakeMKV' },
		MAKEMKV_PERMA_KEY: { label: 'MakeMKV License Key', description: 'Permanent key from <a href="https://www.makemkv.com/buy/" target="_blank" rel="noopener" class="underline text-primary hover:text-primary-hover">makemkv.com/buy</a> — free beta keys are also available on the <a href="https://forum.makemkv.com/forum/viewtopic.php?t=1053" target="_blank" rel="noopener" class="underline text-primary hover:text-primary-hover">MakeMKV forum</a>' },
		DATA_RIP_PARAMETERS: { label: 'Data Rip Parameters', description: 'Extra parameters for data disc ripping' },
		MAX_CONCURRENT_MAKEMKVINFO: { label: 'Max Concurrent Disc Scans', description: 'Limit parallel makemkvinfo processes (0 = unlimited)' },
		AUTO_EJECT: { label: 'Auto-Eject After Rip', description: 'Eject the disc when ripping completes' },
		RIP_POSTER: { label: 'Download Poster', description: 'Save movie poster artwork during ripping' },
		MAKEMKV_COMMUNITY_KEYDB: { label: 'Use FindVUK', description: 'Download FindVUK community keydb.cfg for Blu-ray decryption keys' },
		ARM_CHILDREN: { label: 'ARM Child Servers', description: 'Comma-delimited list of child ARM server URLs' },
		DELRAWFILES: { label: 'Delete Raw Files', description: 'Remove raw MakeMKV output after processing' },
		DRIVE_READY_TIMEOUT: { label: 'Drive Ready Timeout', description: 'Seconds to wait for the drive to become ready after disc insertion' },
		PRESCAN_TIMEOUT: { label: 'Pre-Scan Timeout', description: 'Seconds to wait for MakeMKV pre-scan to complete per attempt. Community recommends 600 for slow or damaged DVD/BD media.' },
		PRESCAN_CACHE_MB: { label: 'Pre-Scan Cache Size', description: 'MakeMKV cache in MB for pre-scan phases. Community recommends 64-128 for scratched or damaged discs.' },
		PRESCAN_RETRIES: { label: 'Pre-Scan Retries', description: 'Number of pre-scan attempts before giving up. Community recommends 3-5 for problematic drives.' },
		DISC_ENUM_TIMEOUT: { label: 'Disc Enum Timeout', description: 'Seconds to wait for MakeMKV disc enumeration. Community recommends 120 for drives that are slow to spin up.' },
		// TV Series
		USE_DISC_LABEL_FOR_TV: { label: 'Use Disc Label for TV', description: 'Parse disc label for season/episode info on TV series discs' },
		GROUP_TV_DISCS_UNDER_SERIES: { label: 'Group TV Discs Under Series', description: 'Group multi-disc TV sets under a single series folder' },
		// Music Ripping
		GET_AUDIO_TITLE: { label: 'Audio Metadata Source', description: 'none, musicbrainz, or freecddb for CD track info' },
		AUDIO_FORMAT: { label: 'Audio Format', description: 'Output format for music CD ripping (passed to abcde -o)' },
		ABCDE_CONFIG_FILE: { label: 'abcde Config File', description: 'Path to the abcde configuration file for CD ripping' },
		RIP_SPEED_PROFILE: { label: 'Rip Speed Profile', description: '"safe" = full paranoia (best for scratched discs), "fast" = less paranoia (~2-4x faster), "fastest" = no error correction (pristine discs only)' },
		CD_RIP_TIMEOUT: { label: 'CD Rip Timeout', description: 'Seconds to wait for cdparanoia output before killing a stalled rip. Set 0 to disable. Default 600 (10 min).' },
		MUSIC_MULTI_DISC_SUBFOLDERS: { label: 'Multi-Disc Subfolders', description: 'Create per-disc subfolders for multi-CD sets (e.g. Artist/Album/Disc 1/)' },
		MUSIC_DISC_FOLDER_PATTERN: { label: 'Disc Folder Pattern', description: 'Folder name for each disc in a multi-disc set. {num} = disc number. Examples: "Disc {num}", "CD {num}"' },
		// Metadata
		METADATA_PROVIDER: { label: 'Metadata Provider', description: 'omdb or tmdb for movie/TV lookups' },
		OMDB_API_KEY: { label: 'OMDb API Key', description: 'API key for the Open Movie Database' },
		TMDB_API_KEY: { label: 'TMDb API Key', description: 'API key for The Movie Database' },
		// General
		ARM_NAME: { label: 'Machine Name', description: 'Friendly name for this ARM instance, used in notifications' },
		DISABLE_LOGIN: { label: 'Disable Login', description: 'Skip authentication — leave all pages open' },
		DATE_FORMAT: { label: 'Date Format', description: 'strftime format string for timestamps' },
		ARM_API_KEY: { label: 'CRC Lookup API Key', description: 'API key for the ARM disc CRC lookup service' },
		// Web Server
		WEBSERVER_IP: { label: 'Web Server IP', description: 'IP address the ARM web UI binds to' },
		WEBSERVER_PORT: { label: 'Web Server Port', description: 'Port the ARM web UI listens on' },
		UI_BASE_URL: { label: 'UI Base URL', description: 'Base URL for the ARM web interface (for reverse proxies)' },
		// Paths & Storage
		RAW_PATH: { label: 'Raw Output Path', description: 'Directory where MakeMKV writes ripped files' },
		TRANSCODE_PATH: { label: 'Transcode Path', description: 'Staging directory for transcoding work' },
		COMPLETED_PATH: { label: 'Completed Path', description: 'Final destination for finished media files' },
		MUSIC_PATH: { label: 'Music Path', description: 'Output directory for music CD rips (used by abcde)' },
		INGRESS_PATH: { label: 'Folder Import Path', description: 'Folder where the Import wizard looks for folders (BDMV/VIDEO_TS) and ISO files.' },
		EXTRAS_SUB: { label: 'Extras Subdirectory', description: 'Subfolder name for bonus features and extras' },
		INSTALLPATH: { label: 'Install Path', description: 'ARM installation directory' },
		LOGPATH: { label: 'Log Path', description: 'Directory for ARM log files' },
		LOGLEVEL: { label: 'Log Level', description: 'Logging verbosity: DEBUG, INFO, WARNING, ERROR, CRITICAL' },
		LOGLIFE: { label: 'Log Retention (days)', description: 'Number of days to keep log files' },
		DBFILE: { label: 'Database File', description: 'Path to the ARM SQLite database' },
		UMASK: { label: 'File Umask', description: 'Umask applied to files created by ARM' },
		SET_MEDIA_PERMISSIONS: { label: 'Set Media Permissions', description: 'Apply chmod to completed media files' },
		CHMOD_VALUE: { label: 'Chmod Value', description: 'Permission bits to apply (e.g. 777)' },
		SET_MEDIA_OWNER: { label: 'Set Media Owner', description: 'Apply chown to completed media files' },
		CHOWN_USER: { label: 'Owner User', description: 'User to own completed media files' },
		CHOWN_GROUP: { label: 'Owner Group', description: 'Group to own completed media files' },
		// Emby
		EMBY_REFRESH: { label: 'Emby Library Refresh', description: 'Trigger an Emby library scan after ripping' },
		EMBY_SERVER: { label: 'Emby Server', description: 'Emby server hostname or IP' },
		EMBY_PORT: { label: 'Emby Port', description: 'Emby server port' },
		EMBY_CLIENT: { label: 'Emby Client Name', description: 'Client identifier sent to Emby' },
		EMBY_DEVICE: { label: 'Emby Device Name', description: 'Device name sent to Emby' },
		EMBY_DEVICEID: { label: 'Emby Device ID', description: 'Unique device identifier for Emby' },
		EMBY_USERNAME: { label: 'Emby Username', description: 'Emby account username' },
		EMBY_USERID: { label: 'Emby User ID', description: 'Emby internal user ID' },
		EMBY_PASSWORD: { label: 'Emby Password', description: 'Emby account password' },
		EMBY_API_KEY: { label: 'Emby API Key', description: 'API key for Emby server access' },
		// TVDB
		TVDB_API_KEY: { label: 'TVDB API Key', description: 'API key for TheTVDB v4 — get one free at thetvdb.com/dashboard' },
		TVDB_MATCH_TOLERANCE: { label: 'Match Tolerance (sec)', description: 'Max runtime difference in seconds for a track-to-episode match (default 300)' },
		TVDB_MAX_SEASON_SCAN: { label: 'Max Season Scan', description: 'How many seasons to scan when auto-detecting season (default 10)' },
		// Naming Patterns
		MOVIE_TITLE_PATTERN: { label: 'Movie Title Pattern', description: 'Pattern for movie display titles' },
		MOVIE_FOLDER_PATTERN: { label: 'Movie Folder Pattern', description: 'Pattern for movie folder names (use / for nested directories)' },
		TV_TITLE_PATTERN: { label: 'TV Title Pattern', description: 'Pattern for TV series display titles' },
		TV_FOLDER_PATTERN: { label: 'TV Folder Pattern', description: 'Pattern for TV series folder names (use / for nested directories)' },
		MUSIC_TITLE_PATTERN: { label: 'Music Title Pattern', description: 'Pattern for music display titles' },
		MUSIC_FOLDER_PATTERN: { label: 'Music Folder Pattern', description: 'Pattern for music folder names (use / for nested directories)' },
		// Transcoder Integration
		SKIP_TRANSCODE: { label: 'Skip Transcoding (Global Default)', description: 'When enabled, ripped files are finalized directly without sending to the transcoder. Can be overridden per-job from the review panel.' },
		TRANSCODER_URL: { label: 'Transcoder Webhook URL', description: 'URL of the arm-transcoder webhook endpoint (leave empty to disable)' },
		TRANSCODER_WEBHOOK_SECRET: { label: 'Transcoder Webhook Secret', description: 'Used by the ripper for outbound transcoder webhooks. arm-ui reads its own copy from ARM_UI_TRANSCODER_WEBHOOK_SECRET at startup; rotating requires updating the env on both services + restarting the containers.' },
		LOCAL_RAW_PATH: { label: 'Local Raw Path', description: 'Local scratch storage where ARM rips to (for file move before notify)' },
		SHARED_RAW_PATH: { label: 'Shared Raw Path', description: 'Shared/NFS storage the transcoder reads from (for file move before notify)' },
	};

	let armInfoKeys = $state<Set<string>>(new Set());
	let endpointInfoKeys = $state<Set<string>>(new Set());

	function toggleInfo(key: string) {
		const next = new Set(armInfoKeys);
		if (next.has(key)) next.delete(key);
		else next.add(key);
		armInfoKeys = next;
	}

	function toggleEndpointInfo(name: string) {
		const next = new Set(endpointInfoKeys);
		if (next.has(name)) next.delete(name);
		else next.add(name);
		endpointInfoKeys = next;
	}

	// --- ARM config groups, organized by tab ---
	type ArmGroup = { label: string; subpanels: { label?: string; keys: string[] }[] };

	const TAB_ARM_GROUPS: Record<string, ArmGroup[]> = {
		ripping: [
			{ label: 'Disc Identification', subpanels: [
				{ keys: ['VIDEOTYPE', 'GET_VIDEO_TITLE', 'ARM_CHECK_UDF', 'MANUAL_WAIT', 'MANUAL_WAIT_TIME', 'DRIVE_READY_TIMEOUT', 'ARM_CHILDREN'] },
			]},
			{ label: 'Track Selection', subpanels: [
				{ keys: ['MINLENGTH', 'MAXLENGTH', 'MAINFEATURE', 'PREVENT_99', 'ALLOW_DUPLICATES'] },
			]},
			{ label: 'TV Series', subpanels: [
				{ keys: ['USE_DISC_LABEL_FOR_TV', 'GROUP_TV_DISCS_UNDER_SERIES'] },
			]},
			{ label: 'Rip Method', subpanels: [
				{ keys: ['RIPMETHOD', 'MKV_ARGS', 'DATA_RIP_PARAMETERS'] },
			]},
			{ label: 'MakeMKV', subpanels: [
				{ keys: ['MAKEMKV_PERMA_KEY', 'MAKEMKV_COMMUNITY_KEYDB', 'MAX_CONCURRENT_MAKEMKVINFO', 'PRESCAN_TIMEOUT', 'PRESCAN_CACHE_MB', 'PRESCAN_RETRIES', 'DISC_ENUM_TIMEOUT'] },
			]},
			{ label: 'Post-Rip', subpanels: [
				{ keys: $transcoderEnabled
					? ['SKIP_TRANSCODE', 'AUTO_EJECT', 'DELRAWFILES', 'RIP_POSTER']
					: ['AUTO_EJECT', 'DELRAWFILES', 'RIP_POSTER'] },
			]},
			{ label: 'Media Directories', subpanels: [
				{ keys: ['RAW_PATH', 'TRANSCODE_PATH', 'COMPLETED_PATH', 'MUSIC_PATH', 'INGRESS_PATH', 'EXTRAS_SUB'] },
			]},
			{ label: 'File Permissions', subpanels: [
				{ keys: ['UMASK', 'SET_MEDIA_PERMISSIONS', 'CHMOD_VALUE', 'SET_MEDIA_OWNER', 'CHOWN_USER', 'CHOWN_GROUP'] },
			]},
			{ label: 'Naming Patterns', subpanels: [
				{ label: 'Movie',  keys: ['MOVIE_TITLE_PATTERN', 'MOVIE_FOLDER_PATTERN'] },
				{ label: 'TV',     keys: ['TV_TITLE_PATTERN', 'TV_FOLDER_PATTERN'] },
			]},
			{ label: 'Metadata', subpanels: [
				{ keys: ['METADATA_PROVIDER', 'OMDB_API_KEY', 'TMDB_API_KEY', 'TVDB_API_KEY', 'TVDB_MATCH_TOLERANCE', 'TVDB_MAX_SEASON_SCAN', 'ARM_API_KEY'] },
			]},
		],
		music: [
			{ label: 'Metadata', subpanels: [
				{ keys: ['GET_AUDIO_TITLE'] },
			]},
			{ label: 'CD Ripping', subpanels: [
				{ keys: ['RIP_SPEED_PROFILE', 'CD_RIP_TIMEOUT'] },
			]},
			{ label: 'Naming Patterns', subpanels: [
				{ keys: ['MUSIC_TITLE_PATTERN', 'MUSIC_FOLDER_PATTERN'] },
			]},
			{ label: 'Multi-Disc Sets', subpanels: [
				{ keys: ['MUSIC_MULTI_DISC_SUBFOLDERS', 'MUSIC_DISC_FOLDER_PATTERN'] },
			]},
		],
		notifications: [],
		transcoding: [
			...($transcoderEnabled ? [{ label: 'Transcoder Connection', subpanels: [
				{ keys: ['TRANSCODER_URL', 'TRANSCODER_WEBHOOK_SECRET', 'LOCAL_RAW_PATH', 'SHARED_RAW_PATH'] },
			]}] : []),
		],
		system: [
			{ label: 'Identity', subpanels: [
				{ keys: ['ARM_NAME', 'DISABLE_LOGIN', 'DATE_FORMAT'] },
			]},
			{ label: 'Web Server', subpanels: [
				{ keys: ['WEBSERVER_IP', 'WEBSERVER_PORT', 'UI_BASE_URL'] },
			]},
			{ label: 'System Paths & Logging', subpanels: [
				{ keys: ['INSTALLPATH', 'LOGPATH', 'DBFILE', 'LOGLEVEL', 'LOGLIFE'] },
			]},
			{ label: 'Emby Integration', subpanels: [
				{ label: 'Connection', keys: ['EMBY_REFRESH', 'EMBY_SERVER', 'EMBY_PORT'] },
				{ label: 'Authentication', keys: ['EMBY_USERNAME', 'EMBY_USERID', 'EMBY_PASSWORD', 'EMBY_API_KEY'] },
				{ label: 'Client Identity', keys: ['EMBY_CLIENT', 'EMBY_DEVICE', 'EMBY_DEVICEID'] },
			]},
		],
	};

	// All ARM groups flattened (for unmapped key detection)
	// Include keys rendered in the abcde.conf panel so they don't appear as "Other"
	const ALL_ARM_GROUPS = [
		...Object.values(TAB_ARM_GROUPS).flat(),
		{ label: '_abcde', subpanels: [{ keys: ['AUDIO_FORMAT', 'ABCDE_CONFIG_FILE'] }] },
	];

	const HIDDEN_KEYS = new Set([
		'OMDB_API_KEY',
		'EMBY_USERID',
		'EMBY_PASSWORD',
		'EMBY_API_KEY',
		'ARM_API_KEY',
		'TMDB_API_KEY',
		'TVDB_API_KEY',
		'TRANSCODER_WEBHOOK_SECRET',
		'MAKEMKV_PERMA_KEY',
	]);

	// Map of API-key form fields to the provider name used by the unified
	// /api/v1/metadata/test-key endpoint. OMDB/TMDB are mutually exclusive
	// (METADATA_PROVIDER picks one); TVDB and MakeMKV are always shown.
	const KEY_TEST_PROVIDERS: Record<string, string> = {
		OMDB_API_KEY: 'omdb',
		TMDB_API_KEY: 'tmdb',
		TVDB_API_KEY: 'tvdb',
		MAKEMKV_PERMA_KEY: 'makemkv',
	};
	const METADATA_PROVIDER_KEYS = new Set(['OMDB_API_KEY', 'TMDB_API_KEY']);

	function isMetadataKeyHidden(key: string): boolean {
		if (!METADATA_PROVIDER_KEYS.has(key)) return false;
		const provider = (armForm['METADATA_PROVIDER'] ?? 'omdb').toString().toLowerCase();
		if (key === 'OMDB_API_KEY') return provider !== 'omdb';
		if (key === 'TMDB_API_KEY') return provider !== 'tmdb';
		return false;
	}

	function keyTestProvider(key: string): string | null {
		return KEY_TEST_PROVIDERS[key] ?? null;
	}

	let metadataTestKey = $state<string | null>(null);

	async function handleTestKey(key: string) {
		const provider = keyTestProvider(key);
		if (!provider) return;
		metadataTesting = true;
		metadataTestKey = key;
		metadataTestResult = null;
		try {
			const currentKey = armForm[key]?.toString().trim() || undefined;
			metadataTestResult = await testMetadataKey(currentKey, provider);
		} catch {
			metadataTestResult = { success: false, message: 'Failed to reach test endpoint' };
		} finally {
			metadataTesting = false;
			clearFeedback(() => {
				metadataTestResult = null;
				metadataTestKey = null;
			});
		}
	}

	async function handleTestConnection() {
		connTesting = true;
		connResult = null;
		try {
			connResult = await testTranscoderConnection();
		} catch {
			connResult = { reachable: false, auth_ok: false, auth_required: false, gpu_support: null, worker_running: false, queue_size: 0, error: 'Failed to reach test endpoint' };
		} finally {
			connTesting = false;
		}
	}

	async function handleTestWebhook() {
		webhookTesting = true;
		webhookResult = null;
		try {
			webhookResult = await testTranscoderWebhook(webhookSecret);
		} catch {
			webhookResult = { reachable: false, secret_ok: false, secret_required: false, error: 'Failed to reach test endpoint' };
		} finally {
			webhookTesting = false;
		}
	}

	const SELECT_OPTIONS: Record<string, string[]> = {
		VIDEOTYPE: ['auto', 'series', 'movie'],
		RIPMETHOD: ['mkv', 'backup', 'backup_dvd'],
		LOGLEVEL: ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
		METADATA_PROVIDER: ['omdb', 'tmdb'],
		GET_AUDIO_TITLE: ['none', 'musicbrainz', 'freecddb'],
		AUDIO_FORMAT: ['flac', 'mp3', 'vorbis', 'opus', 'm4a', 'wav', 'mka', 'wv', 'ape', 'mpc', 'spx', 'mp2', 'tta', 'aiff'],
	};

	// --- Search/filter logic ---
	function matchesSearch(key: string): boolean {
		if (!armSearch.trim()) return true;
		const q = armSearch.toLowerCase();
		const label = ARM_LABELS[key]?.label ?? key;
		const desc = ARM_LABELS[key]?.description ?? '';
		return (
			key.toLowerCase().includes(q) ||
			label.toLowerCase().includes(q) ||
			desc.toLowerCase().includes(q)
		);
	}

	function getArmGroups(config: Record<string, string | null>, tabGroups: ArmGroup[], includeUnmapped = false) {
		const allKeys = new Set(Object.keys(config));
		const mapped = new Set<string>();
		const groups: ArmGroup[] = [];

		for (const group of tabGroups) {
			const subpanels: { label?: string; keys: string[] }[] = [];
			for (const sp of group.subpanels) {
				const present = sp.keys.filter((k) => allKeys.has(k) && matchesSearch(k));
				sp.keys.filter((k) => allKeys.has(k)).forEach((k) => mapped.add(k));
				if (present.length > 0) {
					subpanels.push({ label: sp.label, keys: present });
				}
			}
			if (subpanels.length > 0) {
				groups.push({ label: group.label, subpanels });
			}
		}

		if (includeUnmapped) {
			// Track all keys mapped across ALL tabs (not just this one)
			const allMapped = new Set<string>();
			for (const g of ALL_ARM_GROUPS) {
				for (const sp of g.subpanels) {
					sp.keys.forEach((k) => allMapped.add(k));
				}
			}
			const unmapped = [...allKeys].filter((k) => !allMapped.has(k) && matchesSearch(k));
			if (unmapped.length > 0) {
				groups.push({ label: 'Other', subpanels: [{ keys: unmapped }] });
			}
		}

		return groups;
	}

	function isBoolStr(v: string | null): boolean {
		if (!v) return false;
		return v.toLowerCase() === 'true' || v.toLowerCase() === 'false';
	}

	function isIntStr(v: string | null): boolean {
		if (v === null || v === '') return false;
		return /^\d+$/.test(v);
	}

	function toggleBool(key: string) {
		const cur = (armForm[key] ?? 'false').toString().toLowerCase();
		armForm[key] = cur === 'true' ? 'false' : 'true';
	}

	function toggleCollapse(label: string) {
		armCollapsed[label] = !armCollapsed[label];
	}

	function toggleReveal(key: string) {
		const next = new Set(armRevealedKeys);
		if (next.has(key)) next.delete(key);
		else next.add(key);
		armRevealedKeys = next;
	}

	function getComment(key: string): string {
		if (!settings?.arm_metadata) return '';
		const raw = settings.arm_metadata[key];
		if (!raw || typeof raw !== 'string') return '';
		// Strip leading # characters and trim
		return raw.replace(/^#\s*/gm, '').trim();
	}

	// --- Dirty field check ---
	function isFieldDirty(key: string): boolean {
		return JSON.stringify(armForm[key]) !== JSON.stringify(armOriginal[key]);
	}

	function isTcFieldDirty(key: string): boolean {
		return JSON.stringify(tcForm[key]) !== JSON.stringify(tcOriginal[key]);
	}

	function formatBytes(bytes: number): string {
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
		if (bytes < 1073741824) return `${(bytes / 1048576).toFixed(1)} MB`;
		return `${(bytes / 1073741824).toFixed(1)} GB`;
	}

	// Input class shared across all ARM fields
	const inputClass = 'w-full rounded-md border border-primary/25 bg-primary/5 px-3 py-2 text-sm focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary dark:border-primary/30 dark:bg-primary/10 dark:text-white';
</script>

<svelte:head>
	<title>ARM - Settings</title>
</svelte:head>

<!-- Reusable snippet for a single ARM config field -->
{#snippet armField(key: string)}
	{@const val = armForm[key] ?? ''}
	{@const comment = getComment(key)}
	{@const dirty = isFieldDirty(key)}
	<div class="relative {dirty ? 'rounded-lg ring-2 ring-primary/40 dark:ring-primary/50' : ''}">
		<div class="{dirty ? 'px-3 py-3' : ''}">
			<div class="mb-1 flex items-center gap-1">
				<label for="arm-{key}" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
					{ARM_LABELS[key]?.label ?? key}
				</label>
				{#if dirty}
					<span class="ml-1 h-1.5 w-1.5 rounded-full bg-primary" title="Modified"></span>
				{/if}
				<button
					type="button"
					onclick={() => toggleInfo(key)}
					class="inline-flex h-4 w-4 items-center justify-center rounded-full text-[10px] font-bold
						{armInfoKeys.has(key)
						? 'bg-primary-light-bg text-primary-text dark:bg-primary-light-bg-dark/40 dark:text-primary-text-dark'
						: 'bg-primary/10 text-gray-500 dark:bg-primary/15 dark:text-gray-400'}
						hover:bg-primary/20 dark:hover:bg-primary/20"
					title={key}
				>i</button>
			</div>
			{#if armInfoKeys.has(key)}
				<p class="mb-1 text-xs font-mono text-gray-400">{key}</p>
			{/if}

			{#if SELECT_OPTIONS[key]}
				{@const opts = SELECT_OPTIONS[key]}
				{@const curVal = val?.toString() ?? ''}
				<select
					id="arm-{key}"
					class={inputClass}
					value={curVal}
					onchange={(e) => {
						armForm[key] = (e.target as HTMLSelectElement).value;
						if (key === 'METADATA_PROVIDER') metadataTestResult = null;
					}}
				>
					{#if curVal && !opts.includes(curVal)}
						<option value={curVal}>{curVal}</option>
					{/if}
					{#each opts as opt}
						<option value={opt}>{opt || '(None)'}</option>
					{/each}
				</select>
			{:else if isBoolStr(val?.toString())}
				<div class="flex items-center gap-2 mt-1">
					<button
						type="button"
						onclick={() => toggleBool(key)}
						class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out
							{val?.toString().toLowerCase() === 'true'
							? 'bg-primary'
							: 'bg-primary/30 dark:bg-primary/20'}"
						role="switch"
						aria-checked={val?.toString().toLowerCase() === 'true'}
						aria-label={key}
					>
						<span
							class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out
								{val?.toString().toLowerCase() === 'true'
								? 'translate-x-5'
								: 'translate-x-0'}"
						></span>
					</button>
					<span class="text-xs font-medium {val?.toString().toLowerCase() === 'true' ? 'text-primary-text dark:text-primary-text-dark' : 'text-gray-400'}">
						{val?.toString().toLowerCase() === 'true' ? 'Enabled' : 'Disabled'}
					</span>
				</div>
			{:else if HIDDEN_KEYS.has(key)}
				<div class="flex gap-1">
					<input
						id="arm-{key}"
						type={armRevealedKeys.has(key) ? 'text' : 'password'}
						class="flex-1 rounded-md border border-primary/25 bg-primary/5 px-3 py-2 text-sm focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary dark:border-primary/30 dark:bg-primary/10 dark:text-white"
						value={val?.toString() ?? ''}
						oninput={(e) => (armForm[key] = (e.target as HTMLInputElement).value)}
					/>
					<button
						type="button"
						onclick={() => toggleReveal(key)}
						class="rounded-md border border-primary/25 px-2 py-2 text-xs text-gray-600 hover:bg-primary/10 dark:border-primary/30 dark:text-gray-400 dark:hover:bg-primary/15"
					>
						{armRevealedKeys.has(key) ? 'Hide' : 'Show'}
					</button>
					{#if keyTestProvider(key)}
						<button
							type="button"
							onclick={() => handleTestKey(key)}
							disabled={metadataTesting}
							class="rounded-md border border-primary/25 px-2 py-2 text-xs font-medium text-primary-text hover:bg-primary/10 disabled:opacity-50 dark:border-primary/30 dark:text-primary-text-dark dark:hover:bg-primary/15"
						>
							{metadataTesting && metadataTestKey === key ? 'Testing...' : 'Test'}
						</button>
					{/if}
				</div>
				{#if metadataTestKey === key && metadataTestResult}
					<p class="mt-1 text-xs font-medium {metadataTestResult.success ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}">
						{metadataTestResult.message}
					</p>
				{/if}
			{:else if isIntStr(val?.toString())}
				<input
					id="arm-{key}"
					type="number"
					class={inputClass}
					value={val?.toString() ?? ''}
					oninput={(e) => (armForm[key] = (e.target as HTMLInputElement).value)}
				/>
			{:else}
				<input
					id="arm-{key}"
					type="text"
					class={inputClass}
					value={val?.toString() ?? ''}
					oninput={(e) => (armForm[key] = (e.target as HTMLInputElement).value)}
				/>
			{/if}

			{#if ARM_LABELS[key]?.description}
				<p class="mt-1 text-xs text-gray-400">{@html ARM_LABELS[key].description}</p>
			{:else if comment}
				<p class="mt-1 text-xs text-gray-400">{comment}</p>
			{/if}

			{#if key.endsWith('_PATTERN') && settings?.naming_variables}
				{@const patternVars = Object.entries(settings.naming_variables).sort(([a], [b]) => a.localeCompare(b))}
				<div class="mt-1.5 flex flex-wrap gap-1">
					{#each patternVars as [varName, varDesc]}
						<span
							class="inline-flex items-center rounded px-1.5 py-0.5 text-[11px] font-mono
								bg-primary/10 text-gray-600 dark:bg-primary/15 dark:text-gray-300
								cursor-default"
							title={varDesc}
						>{'{' + varName + '}'}</span>
					{/each}
				</div>
			{/if}
		</div>
	</div>
{/snippet}

<!-- Reusable snippet for GPU support cards.
     Filters to the detected vendor's group(s); falls back to showing all
     groups when nothing is detected so the user can see what's missing. -->
{#snippet gpuCards(gpu: Record<string, boolean>)}
	{@const detected = HW_GROUPS.filter((g) => hasAny(gpu, g.keys))}
	{@const visibleGroups = detected.length > 0 ? detected : HW_GROUPS}
	<section>
		<h2 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">
			Hardware Encoding
		</h2>
		<div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
			{#each visibleGroups as group}
				{@const available = hasAny(gpu, group.keys)}
				<div
					class="rounded-lg border border-primary/20 bg-surface p-4 shadow-xs dark:border-primary/20 dark:bg-surface-dark"
				>
					<div class="mb-3 flex items-center gap-2">
						<span
							class="inline-flex h-5 w-5 items-center justify-center rounded-full text-xs font-bold {available
								? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400'
								: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400'}"
							>{available ? '\u2713' : '\u2717'}</span
						>
						<h3 class="font-semibold text-gray-900 dark:text-white">{group.label}</h3>
					</div>
					<ul class="space-y-1">
						{#each group.keys as key}
							<li class="flex items-center gap-2 text-sm">
								<span
									class="inline-flex h-4 w-4 items-center justify-center rounded-full text-[10px] font-bold {gpu[key]
										? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400'
										: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400'}"
									>{gpu[key] ? '\u2713' : '\u2717'}</span
								>
								<span class="text-gray-600 dark:text-gray-400"
									>{GPU_LABELS[key] ?? key}</span
								>
							</li>
						{/each}
					</ul>
				</div>
			{/each}
		</div>
	</section>
{/snippet}

<div class="space-y-6 pb-20">
	<h1 class="text-2xl font-bold text-gray-900 dark:text-white">Settings</h1>

	<LoadState
		data={settings}
		loading={settingsLoading}
		error={settingsError}
		transitionKey={`settings-${activeTab}`}
	>
		{#snippet loadingSlot()}
			<div class="space-y-4">
				<SkeletonCard lines={5} />
				<SkeletonCard lines={4} />
			</div>
		{/snippet}
		{#snippet ready(_)}
		{@const settings = _}
		<!-- Tab Bar -->
		{@const tabClass = (tab: string) => `whitespace-nowrap border-b-2 px-1 py-2.5 text-sm font-medium transition-colors ${activeTab === tab ? 'border-primary text-primary-text dark:border-primary-text-dark dark:text-primary-text-dark' : 'border-transparent text-gray-500 hover:border-primary/30 hover:text-gray-700 dark:text-gray-400 dark:hover:border-primary/30 dark:hover:text-gray-300'}`}
		<!-- overflow-y-hidden prevents the 1px vertical scroll that
			 -mb-px + border-b-2 would otherwise trigger inside overflow-x-auto.
			 mb-2 adds breathing room below the tab strip on top of the
			 outer space-y-6 - tabs feel cramped against headings otherwise. -->
		<div class="mb-2 overflow-x-auto overflow-y-hidden border-b border-primary/20 dark:border-primary/20">
			<nav class="-mb-px flex gap-4" aria-label="Settings tabs">
				<button type="button" onclick={() => setTab('ripping')} class={tabClass('ripping')}>Ripping</button>
				<button type="button" onclick={() => setTab('music')} class={tabClass('music')}>Music</button>
				{#if $transcoderEnabled}
				<button type="button" onclick={() => setTab('transcoding')} class={tabClass('transcoding')}>Transcoding</button>
				{/if}
				<button type="button" onclick={() => setTab('notifications')} class={tabClass('notifications')}>Notifications</button>
				<button type="button" onclick={() => setTab('drives')} class={tabClass('drives')}>Drives</button>
				<button type="button" onclick={() => setTab('appearance')} class={tabClass('appearance')}>Appearance</button>
				<button type="button" onclick={() => setTab('system')} class={tabClass('system')}>System</button>
			</nav>
		</div>

		<!-- Transcoding Tab -->
		{#if activeTab === 'transcoding' && $transcoderEnabled}
		<div class="space-y-6">
			<h2 class="text-lg font-semibold text-gray-900 dark:text-white">Transcoding</h2>
			<div class="rounded-lg border border-primary/30 bg-primary-light-bg px-4 py-3 text-sm text-primary-dark dark:border-primary/30 dark:bg-primary-light-bg-dark/20 dark:text-primary-text-dark">
				These settings configure the <strong>dedicated transcoder service</strong>, a separate GPU-accelerated container that handles all transcoding. ARM rips discs and notifies this service to transcode.
			</div>

			<!-- Service Status -->
			<section>
				<h2 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Service Status</h2>
				<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
					<!-- Connection card -->
					<div class="rounded-lg border border-primary/20 bg-surface p-4 shadow-xs dark:border-primary/20 dark:bg-surface-dark">
						<h3 class="mb-3 font-semibold text-gray-900 dark:text-white">Connection</h3>
						<button
							type="button"
							onclick={handleTestConnection}
							disabled={connTesting}
							class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-on-primary hover:bg-primary-hover disabled:opacity-50 dark:bg-primary dark:hover:bg-primary-hover"
						>
							{connTesting ? 'Testing...' : 'Test Connection'}
						</button>
						{#if connResult}
							<ul class="mt-3 space-y-1.5">
								<li class="flex items-center gap-2 text-sm">
									<span class="inline-flex h-4 w-4 items-center justify-center rounded-full text-[10px] font-bold {connResult.reachable ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400' : 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400'}">{connResult.reachable ? '\u2713' : '\u2717'}</span>
									<span class="text-gray-600 dark:text-gray-400">Reachable</span>
								</li>
								{#if connResult.reachable}
									<li class="flex items-center gap-2 text-sm">
										<span class="inline-flex h-4 w-4 items-center justify-center rounded-full text-[10px] font-bold {connResult.auth_ok ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400' : connResult.auth_required ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400' : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'}">{connResult.auth_ok ? '\u2713' : connResult.auth_required ? '\u2717' : '\u2014'}</span>
										<span class="text-gray-600 dark:text-gray-400">API key {connResult.auth_ok ? 'valid' : connResult.auth_required ? 'invalid or missing' : 'not required'}</span>
									</li>
									<li class="flex items-center gap-2 text-sm">
										<span class="inline-flex h-4 w-4 items-center justify-center rounded-full text-[10px] font-bold {connResult.worker_running ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400' : 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400'}">{connResult.worker_running ? '\u2713' : '!'}</span>
										<span class="text-gray-600 dark:text-gray-400">Worker {connResult.worker_running ? 'running' : 'stopped'} &middot; {connResult.queue_size} queued</span>
									</li>
								{/if}
								{#if connResult.error}
									<li class="text-xs text-red-600 dark:text-red-400">{connResult.error}</li>
								{/if}
							</ul>
						{/if}
					</div>

					<!-- Webhook card -->
					<div class="rounded-lg border border-primary/20 bg-surface p-4 shadow-xs dark:border-primary/20 dark:bg-surface-dark">
						<h3 class="mb-3 font-semibold text-gray-900 dark:text-white">Webhook</h3>
						<div class="mb-3">
							<label for="webhook-secret" class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">Webhook Secret</label>
							<input
								id="webhook-secret"
								type="password"
								class={inputClass}
								placeholder="Enter secret to test..."
								bind:value={webhookSecret}
							/>
							<p class="mt-1 text-xs text-gray-400">Enter a candidate secret to validate it end-to-end against the transcoder. The deployed secret&apos;s configured/missing status is shown in the Authentication panel below.</p>
						</div>
						<button
							type="button"
							onclick={handleTestWebhook}
							disabled={webhookTesting || !webhookSecret.trim()}
							class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-on-primary hover:bg-primary-hover disabled:opacity-50 dark:bg-primary dark:hover:bg-primary-hover"
						>
							{webhookTesting ? 'Testing...' : 'Test Webhook'}
						</button>
						{#if webhookResult}
							<ul class="mt-3 space-y-1.5">
								<li class="flex items-center gap-2 text-sm">
									<span class="inline-flex h-4 w-4 items-center justify-center rounded-full text-[10px] font-bold {webhookResult.reachable ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400' : 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400'}">{webhookResult.reachable ? '\u2713' : '\u2717'}</span>
									<span class="text-gray-600 dark:text-gray-400">Reachable</span>
								</li>
								{#if webhookResult.reachable}
									<li class="flex items-center gap-2 text-sm">
										<span class="inline-flex h-4 w-4 items-center justify-center rounded-full text-[10px] font-bold {webhookResult.secret_ok ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400' : 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400'}">{webhookResult.secret_ok ? '\u2713' : '\u2717'}</span>
										<span class="text-gray-600 dark:text-gray-400">Secret {webhookResult.secret_ok ? 'accepted' : webhookResult.secret_required ? 'rejected' : 'invalid'}</span>
									</li>
								{/if}
								{#if webhookResult.error}
									<li class="text-xs text-red-600 dark:text-red-400">{webhookResult.error}</li>
								{/if}
							</ul>
						{/if}
					</div>

					<!-- Authentication info card (full width) -->
					{#if settings.transcoder_auth_status}
						<div class="rounded-lg border border-primary/20 bg-surface p-4 shadow-xs md:col-span-2 dark:border-primary/20 dark:bg-surface-dark">
							<h3 class="mb-3 font-semibold text-gray-900 dark:text-white">Authentication</h3>
							<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
								<div class="flex items-center gap-2 text-sm">
									<span class="inline-flex h-5 w-5 items-center justify-center rounded-full text-xs font-bold {settings.transcoder_auth_status.require_api_auth ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400' : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'}">{settings.transcoder_auth_status.require_api_auth ? '\u2713' : '\u2014'}</span>
									<span class="text-gray-700 dark:text-gray-300">API authentication {settings.transcoder_auth_status.require_api_auth ? 'enabled' : 'disabled'}</span>
								</div>
								<div class="flex items-center gap-2 text-sm">
									<span class="inline-flex h-5 w-5 items-center justify-center rounded-full text-xs font-bold {settings.transcoder_auth_status.webhook_secret_configured ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400' : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'}">{settings.transcoder_auth_status.webhook_secret_configured ? '\u2713' : '\u2014'}</span>
									<span class="text-gray-700 dark:text-gray-300">Transcoder webhook secret {settings.transcoder_auth_status.webhook_secret_configured ? 'configured' : 'not configured'}</span>
								</div>
								<div class="flex items-center gap-2 text-sm" title="Loaded from ARM_UI_TRANSCODER_WEBHOOK_SECRET at startup; rotation needs a container restart.">
									<span class="inline-flex h-5 w-5 items-center justify-center rounded-full text-xs font-bold {settings.arm_ui_webhook_secret_configured ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400' : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'}">{settings.arm_ui_webhook_secret_configured ? '\u2713' : '\u2014'}</span>
									<span class="text-gray-700 dark:text-gray-300">arm-ui webhook secret {settings.arm_ui_webhook_secret_configured ? 'configured' : 'not configured'}</span>
								</div>
								{#if settings.transcoder_auth_status.webhook_secret_configured !== settings.arm_ui_webhook_secret_configured}
									<div class="flex items-center gap-2 text-sm text-amber-700 dark:text-amber-400 md:col-span-2">
										<span class="inline-flex h-5 w-5 items-center justify-center rounded-full text-xs font-bold bg-amber-100 dark:bg-amber-900/40">!</span>
										<span>Webhook secrets are asymmetric - outbound webhooks will fail authentication until both sides agree.</span>
									</div>
								{/if}
							</div>
							<p class="mt-3 text-xs text-gray-400">API authentication is configured via Docker environment variables (REQUIRE_API_AUTH, API_KEY) on the transcoder container. The webhook secret must be set on both sides: WEBHOOK_SECRET on the transcoder and ARM_UI_TRANSCODER_WEBHOOK_SECRET on arm-ui (rotation requires a restart).</p>
						</div>
					{/if}
				</div>
			</section>

			{#if settings.transcoder_gpu_support}
				{@render gpuCards(settings.transcoder_gpu_support)}
			{/if}

			{#if settings.transcoder_config?.config}
				<section>
					<h2 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">
						Configuration
					</h2>

					<div
						class="space-y-4 rounded-lg border border-primary/20 bg-surface p-4 dark:border-primary/20 dark:bg-surface-dark"
					>
						<!-- Encoding sub-panel -->
						<section class="space-y-3">
							<h3 class="text-base font-semibold text-gray-700 dark:text-gray-300">Transcoder - Encoding</h3>
							<div class={armForm['SKIP_TRANSCODE']?.toLowerCase() === 'true' ? 'opacity-40 pointer-events-none' : ''}>
								{#if presetScheme || presetOffline}
									<PresetEditor
										scope="global"
										initialState={presetInitialState}
										scheme={presetScheme}
										{presets}
										offline={presetOffline}
										saving={presetSaving}
										onSave={handlePresetSave}
										onSaveAsNew={handlePresetSaveAsNew}
										onRetry={loadPresetData}
									/>
								{:else}
									<p class="text-sm text-gray-400">Loading presets...</p>
								{/if}
							</div>
							{#if armForm['SKIP_TRANSCODE']?.toLowerCase() === 'true'}
								<p class="mt-1 text-xs text-amber-600 dark:text-amber-400">
									Transcoding is skipped globally — these settings are inactive
								</p>
							{/if}
						</section>

						<!-- Directories sub-panel -->
						<div class="space-y-4 rounded-md border border-primary/15 bg-page p-4 dark:border-primary/20 dark:bg-primary/5">
							<h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300">Output Directories</h3>
							{#if tcPaths}
								<div class="grid grid-cols-1 gap-2 text-xs md:grid-cols-3">
									<div class="rounded-sm bg-primary/10 px-2 py-1 dark:bg-primary/15">
										<span class="font-medium text-gray-500 dark:text-gray-400">Raw:</span>
										<span class="ml-1 font-mono text-gray-700 dark:text-gray-200">{tcPaths.raw_path}</span>
									</div>
									<div class="rounded-sm bg-primary/10 px-2 py-1 dark:bg-primary/15">
										<span class="font-medium text-gray-500 dark:text-gray-400">Completed:</span>
										<span class="ml-1 font-mono text-gray-700 dark:text-gray-200">{tcPaths.completed_path}</span>
									</div>
									<div class="rounded-sm bg-primary/10 px-2 py-1 dark:bg-primary/15">
										<span class="font-medium text-gray-500 dark:text-gray-400">Work:</span>
										<span class="ml-1 font-mono text-gray-700 dark:text-gray-200">{tcPaths.work_path}</span>
									</div>
								</div>
							{/if}
							<div class="grid grid-cols-1 gap-4 md:grid-cols-3">
								{#each ['movies_subdir', 'tv_subdir', 'audio_subdir'] as key}
									<div class="relative {isTcFieldDirty(key) ? 'rounded-lg ring-2 ring-primary/40 dark:ring-primary/50' : ''}">
										<div class="{isTcFieldDirty(key) ? 'px-3 py-3' : ''}">
											<div class="mb-1 flex items-center gap-1">
												<label for="tc-{key}" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
													{TC_LABELS[key] ?? key}
												</label>
												{#if isTcFieldDirty(key)}
													<span class="ml-1 h-1.5 w-1.5 rounded-full bg-primary" title="Modified"></span>
												{/if}
											</div>
											<input
												id="tc-{key}"
												type="text"
												class={inputClass}
												bind:value={tcForm[key]}
											/>
											{#if tcPaths}
												<p class="mt-1 text-xs font-mono text-gray-400">
													{tcPaths.completed_path}/{tcForm[key]}
												</p>
											{/if}
										</div>
									</div>
								{/each}
							</div>
							<div class="relative {isTcFieldDirty('delete_source') ? 'rounded-lg ring-2 ring-primary/40 dark:ring-primary/50' : ''}">
								<div class="{isTcFieldDirty('delete_source') ? 'px-3 py-3' : ''}">
									<label
										for="tc-delete_source"
										class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
									>
										{TC_LABELS['delete_source'] ?? 'Delete Source'}
									</label>
									<div class="flex items-center gap-2 mt-1">
										<button
											type="button"
											onclick={() => (tcForm.delete_source = !tcForm.delete_source)}
											class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out
												{tcForm.delete_source ? 'bg-primary' : 'bg-primary/30 dark:bg-primary/20'}"
											role="switch"
											aria-checked={!!tcForm.delete_source}
											aria-label="Delete Source After Transcode"
										>
											<span
												class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out
													{tcForm.delete_source ? 'translate-x-5' : 'translate-x-0'}"
											></span>
										</button>
										<span class="text-xs font-medium {tcForm.delete_source ? 'text-primary-text dark:text-primary-text-dark' : 'text-gray-400'}">
											{tcForm.delete_source ? 'Enabled' : 'Disabled'}
										</span>
									</div>
								</div>
							</div>
						</div>

						<!-- Operational settings -->
						{#if (settings.transcoder_config.updatable_keys ?? []).filter((k) => !TC_PRESET_SET.has(k)).length > 0}
							<div class="space-y-4 rounded-md border border-primary/15 bg-page p-4 dark:border-primary/20 dark:bg-primary/5">
								<h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300">Operational</h3>
								<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
									{#each (settings.transcoder_config.updatable_keys ?? []).filter((k) => !TC_PRESET_SET.has(k)) as key}
										{@const selectOpts = tcSelectOptions(key)}
										<div class="relative {isTcFieldDirty(key) ? 'rounded-lg ring-2 ring-primary/40 dark:ring-primary/50' : ''}">
											<div class="{isTcFieldDirty(key) ? 'px-3 py-3' : ''}">
												<div class="mb-1 flex items-center gap-1">
													<label for="tc-{key}" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
														{TC_LABELS[key] ?? key}
													</label>
													{#if isTcFieldDirty(key)}
														<span class="ml-1 h-1.5 w-1.5 rounded-full bg-primary" title="Modified"></span>
													{/if}
												</div>

												{#if selectOpts}
													<select
														id="tc-{key}"
														class={inputClass}
														bind:value={tcForm[key]}
													>
														{#each selectOpts as opt}
															<option value={opt}>{opt}</option>
														{/each}
													</select>
												{:else if TC_BOOL_KEYS.has(key)}
													<div class="flex items-center gap-2 mt-1">
														<button
															type="button"
															onclick={() => (tcForm[key] = !tcForm[key])}
															class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out
																{tcForm[key] ? 'bg-primary' : 'bg-primary/30 dark:bg-primary/20'}"
															role="switch"
															aria-checked={!!tcForm[key]}
															aria-label={TC_LABELS[key] ?? key}
														>
															<span
																class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out
																	{tcForm[key] ? 'translate-x-5' : 'translate-x-0'}"
															></span>
														</button>
														<span class="text-xs font-medium {tcForm[key] ? 'text-primary-text dark:text-primary-text-dark' : 'text-gray-400'}">
															{tcForm[key] ? 'Enabled' : 'Disabled'}
														</span>
													</div>
												{:else if TC_NUMBER_FIELDS[key]}
													{@const range = TC_NUMBER_FIELDS[key]}
													<input
														id="tc-{key}"
														type="number"
														min={range[0]}
														max={range[1]}
														step={range[2] ?? 1}
														class={inputClass}
														bind:value={tcForm[key]}
													/>
												{:else}
													<input
														id="tc-{key}"
														type="text"
														class={inputClass}
														bind:value={tcForm[key]}
													/>
												{/if}

												{#if TC_HELP[key]}
													<p class="mt-1 text-xs text-gray-400">{TC_HELP[key]}</p>
												{/if}
											</div>
										</div>
									{/each}
								</div>
							</div>
						{/if}

						<!-- Logging settings -->
						{#if (settings.transcoder_config?.updatable_keys ?? []).some((k) => TC_LOGGING_KEYS.includes(k))}
							<div class="space-y-4 rounded-md border border-primary/15 bg-page p-4 dark:border-primary/20 dark:bg-primary/5">
								<h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300">Logging</h3>
								<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
									{#each TC_LOGGING_KEYS.filter((k) => (settings.transcoder_config?.updatable_keys ?? []).includes(k)) as key}
										{@const selectOpts = tcSelectOptions(key)}
										<div class="relative {isTcFieldDirty(key) ? 'rounded-lg ring-2 ring-primary/40 dark:ring-primary/50' : ''}">
											<div class="{isTcFieldDirty(key) ? 'px-3 py-3' : ''}">
												<div class="mb-1 flex items-center gap-1">
													<label for="tc-{key}" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
														{TC_LABELS[key] ?? key}
													</label>
													{#if isTcFieldDirty(key)}
														<span class="ml-1 h-1.5 w-1.5 rounded-full bg-primary" title="Modified"></span>
													{/if}
												</div>
												{#if selectOpts}
													<select
														id="tc-{key}"
														class={inputClass}
														bind:value={tcForm[key]}
													>
														{#each selectOpts as opt}
															<option value={opt}>{opt}</option>
														{/each}
													</select>
												{:else}
													<input
														id="tc-{key}"
														type="text"
														class={inputClass}
														bind:value={tcForm[key]}
													/>
												{/if}
												{#if TC_HELP[key]}
													<p class="mt-1 text-xs text-gray-400">{TC_HELP[key]}</p>
												{/if}
											</div>
										</div>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				</section>
			{:else}
				<p class="text-sm text-gray-400">Transcoder offline or not configured.</p>
			{/if}

			<!-- Transcoder connection config (relocated from Notifications) -->
			<section>
				<div class="mb-4 flex items-center justify-between gap-3">
					<h2 class="text-lg font-semibold text-gray-900 dark:text-white">Connection Settings</h2>
					{@render armSearchBar()}
				</div>
				{@render armSettingsSection('transcoding')}
			</section>
		</div>
		{/if}

		<!-- Reusable ARM settings renderer -->
		{#snippet armSettingsSection(tabKey: string, includeUnmapped?: boolean)}
			{#if settings?.arm_config}
				{@const groups = getArmGroups(settings.arm_config, TAB_ARM_GROUPS[tabKey] ?? [], includeUnmapped ?? false)}
				{#if groups.length === 0 && armSearch}
					<p class="py-4 text-center text-sm text-gray-400">No settings match "{armSearch}"</p>
				{:else}
					<div class="space-y-2">
						{#each groups as group}
							<div id="panel-{group.label.toLowerCase().replace(/[^a-z0-9]+/g, '-')}" class="scroll-mt-4 rounded-lg border border-primary/20 bg-surface dark:border-primary/20 dark:bg-surface-dark">
								<button
									type="button"
									onclick={() => toggleCollapse(group.label)}
									class="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-semibold text-gray-900 hover:bg-page dark:text-white dark:hover:bg-primary/10"
								>
									<span>{group.label}</span>
									<svg
										class="h-4 w-4 transform transition-transform {armCollapsed[group.label] ? '' : 'rotate-180'}"
										fill="none" stroke="currentColor" viewBox="0 0 24 24"
									>
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
									</svg>
								</button>
								{#if !armCollapsed[group.label] || armSearch}
									<div class="border-t border-primary/20 px-4 py-3 dark:border-primary/20">
										<div class="space-y-4">
											{#each group.subpanels as subpanel}
												{#if subpanel.label}
													<div class="space-y-4 rounded-md border border-primary/15 bg-page p-4 dark:border-primary/20 dark:bg-primary/5">
														<h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300">{subpanel.label}</h3>
														<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
															{#each subpanel.keys as key}
																{#if !isMetadataKeyHidden(key)}
																	{@render armField(key)}
																{/if}
															{/each}
														</div>
													</div>
												{:else}
													<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
														{#each subpanel.keys as key}
															{#if !isMetadataKeyHidden(key)}
																{@render armField(key)}
															{/if}
														{/each}
													</div>
												{/if}
											{/each}
											</div>
									</div>
								{/if}
							</div>
						{/each}
					</div>
				{/if}
			{:else}
				<p class="text-sm text-gray-400">No ARM configuration found.</p>
			{/if}
		{/snippet}

		<!-- Search bar snippet (shared across ARM-backed tabs) -->
		{#snippet armSearchBar()}
			<div class="relative">
				<svg class="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
				</svg>
				<input
					type="text"
					placeholder="Filter settings..."
					class="w-56 rounded-md border border-primary/25 bg-primary/5 py-1.5 pl-8 pr-3 text-sm focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary dark:border-primary/30 dark:bg-primary/10 dark:text-white dark:placeholder-gray-500"
					bind:value={armSearch}
				/>
				{#if armSearch}
					<button
						type="button"
						onclick={() => (armSearch = '')}
						aria-label="Clear search"
						class="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
					>
						<svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
						</svg>
					</button>
				{/if}
			</div>
		{/snippet}

		<!-- Ripping Tab -->
		{#if activeTab === 'ripping'}
			<section>
				<div class="mb-4 flex items-center justify-between gap-3">
					<h2 class="text-lg font-semibold text-gray-900 dark:text-white">Ripping</h2>
					{@render armSearchBar()}
				</div>
				{@render armSettingsSection('ripping')}
			</section>
		{/if}

		<!-- Music Tab -->
		{#if activeTab === 'music'}
			<section>
				<div class="mb-4 flex items-center justify-between gap-3">
					<h2 class="text-lg font-semibold text-gray-900 dark:text-white">Music</h2>
					{@render armSearchBar()}
				</div>
				{@render armSettingsSection('music')}
			</section>

			<!-- Encoding & abcde.conf -->
			<section class="mt-2">
				<div class="rounded-lg border border-primary/20 bg-surface dark:border-primary/20 dark:bg-surface-dark">
					<button
						type="button"
						onclick={() => (abcdeCollapsed = !abcdeCollapsed)}
						class="flex w-full items-center justify-between px-4 py-3 text-left text-sm font-semibold text-gray-900 hover:bg-page dark:text-white dark:hover:bg-primary/10"
					>
						<span>Encoding</span>
						<svg
							class="h-4 w-4 transform transition-transform {abcdeCollapsed ? '' : 'rotate-180'}"
							fill="none" stroke="currentColor" viewBox="0 0 24 24"
						>
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
						</svg>
					</button>
					{#if !abcdeCollapsed}
						<div class="border-t border-primary/20 px-4 py-3 dark:border-primary/20">
							<!-- ARM encoding fields -->
							{#if settings?.arm_config}
								<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
									{#each ['AUDIO_FORMAT', 'ABCDE_CONFIG_FILE'] as key}
										{#if settings.arm_config[key] !== undefined}
											{@render armField(key)}
										{/if}
									{/each}
								</div>
							{/if}

							<!-- abcde.conf file editor -->
							<div class="mt-4">
								<div class="mb-2 flex items-center justify-between gap-3">
									<h4 class="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
										abcde.conf
										{#if abcdePath}
											<span class="ml-1 font-normal normal-case tracking-normal text-gray-400">{abcdePath}</span>
										{/if}
									</h4>
									{#if abcdeExists || abcdeDirty}
										<div class="flex items-center gap-1.5">
											<div class="relative">
												<svg class="pointer-events-none absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
												</svg>
												<input
													type="text"
													placeholder="Search..."
													class="w-44 rounded-md border border-primary/25 bg-primary/5 py-1 pl-7 pr-2 text-xs focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary dark:border-primary/30 dark:bg-primary/10 dark:text-white dark:placeholder-gray-500"
													bind:value={abcdeSearch}
													onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); abcdeSearchNav(e.shiftKey ? -1 : 1); } }}
												/>
											</div>
											{#if abcdeSearch}
												<span class="text-xs text-gray-400 tabular-nums">{abcdeMatches.length > 0 ? `${abcdeSearchIndex + 1}/${abcdeMatches.length}` : '0'}</span>
												<button type="button" onclick={() => abcdeSearchNav(-1)} disabled={abcdeMatches.length === 0} class="rounded p-0.5 text-gray-400 hover:text-gray-600 disabled:opacity-30 dark:hover:text-gray-300" aria-label="Previous match">
													<svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" /></svg>
												</button>
												<button type="button" onclick={() => abcdeSearchNav(1)} disabled={abcdeMatches.length === 0} class="rounded p-0.5 text-gray-400 hover:text-gray-600 disabled:opacity-30 dark:hover:text-gray-300" aria-label="Next match">
													<svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg>
												</button>
											{/if}
										</div>
									{/if}
								</div>
								{#if abcdeLoading}
									<p class="py-4 text-center text-sm text-gray-400">Loading abcde.conf...</p>
								{:else if !abcdeLoaded}
									<p class="py-4 text-center text-sm text-gray-400">Failed to load abcde.conf</p>
								{:else if !abcdeExists && !abcdeDirty}
									<div class="rounded-md border border-primary/15 bg-page p-6 text-center dark:border-primary/20 dark:bg-primary/5">
										<p class="text-sm text-gray-500 dark:text-gray-400">
											No abcde.conf file found at <code class="rounded bg-gray-200 px-1 py-0.5 font-mono text-xs dark:bg-gray-700">{abcdePath}</code>
										</p>
										<p class="mt-1 text-xs text-gray-400 dark:text-gray-500">Start typing below to create one.</p>
									</div>
									<textarea
										bind:this={abcdeTextarea}
										class="mt-3 w-full rounded-md border border-primary/25 bg-primary/5 p-3 font-mono text-sm leading-relaxed focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary dark:border-primary/30 dark:bg-primary/10 dark:text-white dark:placeholder-gray-500"
										rows="10"
										placeholder="# abcde.conf — paste or type your configuration here"
										bind:value={abcdeContent}
									></textarea>
								{:else}
									<textarea
										bind:this={abcdeTextarea}
										class="w-full rounded-md border border-primary/25 bg-primary/5 p-3 font-mono text-sm leading-relaxed focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary dark:border-primary/30 dark:bg-primary/10 dark:text-white dark:placeholder-gray-500"
										rows="20"
										bind:value={abcdeContent}
									></textarea>
								{/if}

								{#if abcdeDirty || abcdeFeedback}
									<div class="mt-3 flex items-center gap-3">
										{#if abcdeDirty}
											<button
												type="button"
												onclick={handleAbcdeSave}
												disabled={abcdeSaving}
												class="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-white shadow-xs hover:bg-primary/80 disabled:opacity-50"
											>
												{abcdeSaving ? 'Saving...' : 'Save'}
											</button>
											<button
												type="button"
												onclick={handleAbcdeDiscard}
												class="rounded-md border border-primary/25 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-page dark:border-primary/30 dark:text-gray-300 dark:hover:bg-primary/10"
											>
												Discard
											</button>
										{/if}
										{#if abcdeFeedback}
											<span class="text-sm {abcdeFeedback.type === 'success' ? 'text-green-500' : 'text-red-500'}">
												{abcdeFeedback.message}
											</span>
										{/if}
									</div>
								{/if}
							</div>
						</div>
					{/if}
				</div>
			</section>
		{/if}

		<!-- Notifications Tab -->
		{#if activeTab === 'notifications'}
			<NotificationsTab />
		{/if}

		<!-- System Info Tab -->
		{#if activeTab === 'system'}
			{#if systemInfoLoading}
				<div class="py-8 text-center text-gray-400">Loading system info...</div>
			{:else if systemInfo}
				<div class="space-y-6">
					<h2 class="text-lg font-semibold text-gray-900 dark:text-white">System</h2>

					<!-- Health check (API keys + path permissions) -->
					<SystemHealth />

					<!-- Versions -->
					<section>
						<h2 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Versions</h2>
						<div class="grid grid-cols-2 gap-4 {Object.keys(systemInfo.versions).length === 4 ? 'md:grid-cols-4' : Object.keys(systemInfo.versions).length === 3 ? 'md:grid-cols-3' : Object.keys(systemInfo.versions).length === 2 ? 'md:grid-cols-2' : 'md:grid-cols-5'}">
							{#each Object.entries(systemInfo.versions) as [name, version]}
								{@const subtitle = name === 'transcoder' ? $dashboard.transcoder_system_stats?.gpu?.vendor : null}
								<div class="rounded-lg border border-primary/20 bg-surface p-4 shadow-xs dark:border-primary/20 dark:bg-surface-dark">
									<p class="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">{name}</p>
									<div class="mt-1 flex items-center gap-2">
										<div class="h-2 w-2 rounded-full {version === 'offline' ? 'bg-red-400' : version === 'unknown' ? 'bg-gray-400' : 'bg-green-400'}"></div>
										<p class="text-sm font-semibold text-gray-900 dark:text-white">{version}</p>
									</div>
									{#if subtitle}
										<p class="mt-0.5 text-[10px] font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">{subtitle}</p>
									{/if}
								</div>
							{/each}
						</div>
					</section>

					<!-- Service Endpoints -->
					{#if systemInfo.endpoints}
						<section>
							<h2 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Service Endpoints</h2>
							<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
								{#each Object.entries(systemInfo.endpoints) as [name, ep]}
									{@const envVar = name === 'arm' ? 'ARM_UI_ARM_URL' : name === 'transcoder' ? 'ARM_UI_TRANSCODER_URL' : name.toUpperCase() + '_URL'}
								<div class="rounded-lg border border-primary/20 bg-surface p-4 shadow-xs dark:border-primary/20 dark:bg-surface-dark">
										<div class="flex items-center justify-between">
											<p class="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">{name}</p>
											<span class="inline-flex items-center gap-1.5 text-xs font-medium {ep.reachable ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}">
												<div class="h-2 w-2 rounded-full {ep.reachable ? 'bg-green-500' : 'bg-red-500'}"></div>
												{ep.reachable ? 'Reachable' : 'Unreachable'}
											</span>
										</div>
										<div class="mt-2 flex items-center gap-2">
											<p class="font-mono text-sm text-gray-900 dark:text-white">{ep.url}</p>
											<button
												type="button"
												onclick={() => toggleEndpointInfo(name)}
												class="inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-[10px] font-bold
													{endpointInfoKeys.has(name)
													? 'bg-primary-light-bg text-primary-text dark:bg-primary-light-bg-dark/40 dark:text-primary-text-dark'
													: 'bg-primary/10 text-gray-500 dark:bg-primary/15 dark:text-gray-400'}
													hover:bg-primary/20 dark:hover:bg-primary/20"
												title={envVar}
											>i</button>
										</div>
										{#if endpointInfoKeys.has(name)}
											<p class="mt-1 font-mono text-xs text-gray-400 dark:text-gray-500">{envVar}</p>
										{/if}
									</div>
								{/each}
							</div>
						</section>
					{/if}

					<!-- Paths -->
					{#if systemInfo.paths.length > 0}
						<section>
							<h2 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Paths</h2>
							<div class="overflow-x-auto rounded-lg border border-primary/20 dark:border-primary/20">
								<table class="responsive-table w-full text-left text-sm">
									<thead class="bg-page text-gray-600 dark:bg-primary/5 dark:text-gray-400">
										<tr>
											<th class="px-4 py-3 font-medium">Setting</th>
											<th class="px-4 py-3 font-medium">Path</th>
											<th class="px-4 py-3 font-medium">Status</th>
										</tr>
									</thead>
									<tbody class="divide-y divide-gray-200 dark:divide-gray-700">
										{#each systemInfo.paths as p}
											<tr class="hover:bg-page dark:hover:bg-gray-800/50">
												<td class="px-4 py-2 font-mono text-xs font-medium text-gray-500 dark:text-gray-400" data-label="Setting">{p.setting}</td>
												<td class="px-4 py-2 font-mono text-xs text-gray-900 dark:text-white break-all" data-label="Path">{p.path}</td>
												<td class="px-4 py-2" data-label="Status">
													{#if !p.exists}
														<span class="inline-flex items-center gap-1 text-xs text-red-500">
															<svg class="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" /></svg>
															Missing
														</span>
													{:else if p.writable}
														<span class="inline-flex items-center gap-1 text-xs text-green-500">
															<svg class="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" /></svg>
															OK
														</span>
													{:else}
														<span class="inline-flex items-center gap-1 text-xs text-amber-500">
															<svg class="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" /></svg>
															Read-only
														</span>
													{/if}
												</td>
											</tr>
										{/each}
									</tbody>
								</table>
							</div>
						</section>
					{/if}

					<!-- Database -->
					<section>
						<h2 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Database</h2>
						<div class="rounded-lg border border-primary/20 bg-surface p-4 shadow-xs dark:border-primary/20 dark:bg-surface-dark">
							<dl class="grid grid-cols-2 gap-4 text-sm md:grid-cols-4">
								<div>
									<dt class="text-gray-500 dark:text-gray-400">Path</dt>
									<dd class="mt-1 font-mono text-xs text-gray-900 dark:text-white">{systemInfo.database.path ?? 'N/A'}</dd>
								</div>
								<div>
									<dt class="text-gray-500 dark:text-gray-400">Size</dt>
									<dd class="mt-1 font-medium text-gray-900 dark:text-white">{systemInfo.database.size_bytes != null ? formatBytes(systemInfo.database.size_bytes) : 'N/A'}</dd>
								</div>
								<div>
									<dt class="text-gray-500 dark:text-gray-400">Status</dt>
									<dd class="mt-1">
										<span class="inline-flex items-center gap-1.5 text-sm font-medium {systemInfo.database.available ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}">
											<div class="h-2 w-2 rounded-full {systemInfo.database.available ? 'bg-green-500' : 'bg-red-500'}"></div>
											{systemInfo.database.available ? 'Connected' : 'Unavailable'}
										</span>
									</dd>
								</div>
								<div>
									<dt class="text-gray-500 dark:text-gray-400">Migrations</dt>
									<dd class="mt-1">
										{#if systemInfo.database.up_to_date === true}
											<span class="inline-flex items-center gap-1.5 text-sm font-medium text-green-600 dark:text-green-400">
												<div class="h-2 w-2 rounded-full bg-green-500"></div>
												Up to date
											</span>
										{:else if systemInfo.database.up_to_date === false}
											<span class="inline-flex items-center gap-1.5 text-sm font-medium text-amber-600 dark:text-amber-400">
												<div class="h-2 w-2 rounded-full bg-amber-500"></div>
												Needs migration
											</span>
										{:else}
											<span class="text-sm text-gray-400">Unknown</span>
										{/if}
									</dd>
								</div>
							</dl>
							{#if systemInfo.database.migration_current && systemInfo.database.migration_current !== 'unknown' && systemInfo.database.migration_current !== 'offline'}
								<div class="mt-3 border-t border-primary/10 pt-3 dark:border-primary/15">
									<p class="font-mono text-xs text-gray-400 dark:text-gray-500">
										revision: {systemInfo.database.migration_current}{systemInfo.database.migration_head && systemInfo.database.migration_head !== systemInfo.database.migration_current ? ` → head: ${systemInfo.database.migration_head}` : ''}
									</p>
								</div>
							{/if}
						</div>
					</section>

					<!-- Drives link -->
					<section class="flex items-center gap-2">
						<h2 class="text-lg font-semibold text-gray-900 dark:text-white">Drives</h2>
						<button
							type="button"
							onclick={() => setTab('drives')}
							class="text-sm text-primary hover:text-primary-hover hover:underline dark:text-primary dark:hover:text-primary-hover"
						>
							View in Drives tab
						</button>
					</section>
				</div>
			{:else}
				<p class="py-8 text-center text-gray-400">Failed to load system info.</p>
			{/if}

			<!-- Editable ARM system settings below diagnostics -->
			<section>
				<div class="mb-4 flex items-center justify-between gap-3">
					<h2 class="text-lg font-semibold text-gray-900 dark:text-white">Configuration</h2>
					{@render armSearchBar()}
				</div>
				{@render armSettingsSection('system', true)}
			</section>

			<!-- Service Control -->
			<section class="mt-6">
				<h2 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Service Control</h2>
				<div class="space-y-3">
					<!-- ARM Restart -->
					<div class="rounded-lg border border-red-200 bg-red-50/50 p-4 dark:border-red-800 dark:bg-red-900/10">
						<div class="flex items-center justify-between">
							<div>
								<p class="text-sm font-medium text-gray-900 dark:text-white">Restart ARM Service</p>
								<p class="text-xs text-gray-500 dark:text-gray-400">Restarts the ARM ripping service. Active rips will be interrupted.</p>
								{#if armRestartFeedback}
									<p class="mt-1 text-xs {armRestartFeedback.type === 'success' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}">{armRestartFeedback.message}</p>
								{/if}
							</div>
							<button
								type="button"
								disabled={armRestarting}
								onclick={() => handleRestart('arm')}
								class="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
							>
								{armRestarting ? 'Restarting...' : 'Restart'}
							</button>
						</div>
					</div>
					<!-- Transcoder Restart -->
					{#if $transcoderEnabled}
					<div class="rounded-lg border border-red-200 bg-red-50/50 p-4 dark:border-red-800 dark:bg-red-900/10">
						<div class="flex items-center justify-between">
							<div>
								<p class="text-sm font-medium text-gray-900 dark:text-white">Restart Transcoder Service</p>
								<p class="text-xs text-gray-500 dark:text-gray-400">Restarts the transcoder service. Active transcodes will be interrupted.</p>
								{#if tcRestartFeedback}
									<p class="mt-1 text-xs {tcRestartFeedback.type === 'success' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}">{tcRestartFeedback.message}</p>
								{/if}
							</div>
							<button
								type="button"
								disabled={tcRestarting}
								onclick={() => handleRestart('transcoder')}
								class="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
							>
								{tcRestarting ? 'Restarting...' : 'Restart'}
							</button>
						</div>
					</div>
					{/if}
				</div>
			</section>
		{/if}

		<!-- Appearance Tab -->
		{#if activeTab === 'appearance'}
			<h2 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Appearance</h2>
			<section class="space-y-6">
				<!-- Feedback toast -->
				{#if themeFeedback}
					<div class="rounded-lg border p-3 text-sm {themeFeedback.type === 'success' ? 'border-green-200 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-900/20 dark:text-green-400' : 'border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400'}">
						{themeFeedback.message}
					</div>
				{/if}

				<!-- Built-in Themes -->
				<div class="rounded-lg border border-primary/20 bg-surface p-6 shadow-xs dark:border-primary/20 dark:bg-surface-dark">
					<h3 class="mb-1 text-base font-semibold text-gray-900 dark:text-white">Color Scheme</h3>
					<p class="mb-4 text-sm text-gray-500 dark:text-gray-400">Choose an accent color for buttons, links, and highlights throughout the UI.</p>
					<div class="flex flex-wrap gap-3">
						{#each $allSchemes.filter(s => s.builtin !== false) as scheme}
							<button
								type="button"
								onclick={() => ($colorScheme = scheme.id)}
								class="group relative flex flex-col items-center gap-1.5 rounded-lg border-2 px-4 py-3 transition-colors
									{$colorScheme === scheme.id
									? 'border-primary bg-primary-light-bg dark:border-primary-text-dark dark:bg-primary-light-bg-dark/20'
									: 'border-primary/15 hover:border-primary/30 dark:border-primary/15 dark:hover:border-primary/30'}"
							>
								<span class="h-8 w-8 rounded-full" style="background-color: {scheme.swatch}"></span>
								<span class="text-xs font-medium text-gray-700 dark:text-gray-300">{scheme.label}</span>
								{#if scheme.description}
									<span class="absolute -top-8 left-1/2 -translate-x-1/2 whitespace-nowrap rounded bg-gray-800 px-2 py-1 text-[10px] text-white opacity-0 transition-opacity group-hover:opacity-100 dark:bg-gray-700">{scheme.description}</span>
								{/if}
							</button>
						{/each}
					</div>
					<div class="mt-3 flex gap-2">
						<button
							type="button"
							onclick={() => handleThemeDownload($colorScheme)}
							class="inline-flex items-center gap-1 rounded-md bg-primary/10 px-3 py-1.5 text-xs font-medium text-primary-text transition-colors hover:bg-primary/20 dark:text-primary-text-dark"
						>
							<svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
							Export current theme
						</button>
					</div>
				</div>

				<!-- User Themes -->
				{#if $allSchemes.filter(s => s.builtin === false).length > 0}
					<div class="rounded-lg border border-primary/20 bg-surface p-6 shadow-xs dark:border-primary/20 dark:bg-surface-dark">
						<h3 class="mb-1 text-base font-semibold text-gray-900 dark:text-white">User Themes</h3>
						<p class="mb-4 text-sm text-gray-500 dark:text-gray-400">Custom themes loaded from your themes directory.</p>
						<div class="flex flex-wrap gap-3">
							{#each $allSchemes.filter(s => s.builtin === false) as scheme}
								<div class="relative">
									<button
										type="button"
										onclick={() => ($colorScheme = scheme.id)}
										class="flex flex-col items-center gap-1.5 rounded-lg border-2 px-4 py-3 transition-colors
											{$colorScheme === scheme.id
											? 'border-primary bg-primary-light-bg dark:border-primary-text-dark dark:bg-primary-light-bg-dark/20'
											: 'border-primary/15 hover:border-primary/30 dark:border-primary/15 dark:hover:border-primary/30'}"
									>
										<span class="h-8 w-8 rounded-full" style="background-color: {scheme.swatch}"></span>
										<span class="text-xs font-medium text-gray-700 dark:text-gray-300">{scheme.label}</span>
										{#if scheme.author}
											<span class="text-[10px] text-gray-400">by {scheme.author}</span>
										{/if}
									</button>
									<div class="absolute -right-1 -top-1 flex gap-0.5">
										<button
											type="button"
											onclick={() => handleThemeDownload(scheme.id)}
											class="rounded-full bg-gray-200 p-0.5 text-gray-500 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-400 dark:hover:bg-gray-600"
											title="Download"
										>
											<svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
										</button>
										<button
											type="button"
											onclick={() => handleThemeDelete(scheme.id, scheme.label)}
											class="rounded-full bg-red-100 p-0.5 text-red-500 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400 dark:hover:bg-red-900/50"
											title="Delete"
										>
											<svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
										</button>
									</div>
								</div>
							{/each}
						</div>
					</div>
				{/if}

				<!-- Upload Theme -->
				<div class="rounded-lg border border-primary/20 bg-surface p-6 shadow-xs dark:border-primary/20 dark:bg-surface-dark">
					<h3 class="mb-1 text-base font-semibold text-gray-900 dark:text-white">Import Theme</h3>
					<p class="mb-4 text-sm text-gray-500 dark:text-gray-400">Upload a theme JSON file and optional custom CSS.</p>
					<div class="space-y-4">
						<!-- Theme name -->
						<div>
							<label for="theme-name-input" class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">Theme Name <span class="text-red-500">*</span></label>
							<input
								id="theme-name-input"
								type="text"
								bind:value={themeName}
								placeholder="My Theme"
								disabled={themeUploading}
								class="w-full rounded-lg border border-primary/25 bg-primary/5 px-3 py-2 text-sm dark:border-primary/30 dark:bg-primary/10 dark:text-white"
							/>
						</div>
						<!-- JSON file picker -->
						<div>
							<span class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">Theme JSON <span class="text-red-500">*</span></span>
							<label class="inline-flex cursor-pointer items-center gap-2 rounded-lg bg-primary/10 px-4 py-2 text-sm font-medium text-primary-text transition-colors hover:bg-primary/20 dark:text-primary-text-dark">
								<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
								{themeJsonFile ? themeJsonFile.name : 'Choose .json file'}
								<input type="file" accept=".json" class="hidden" onchange={handleJsonFileSelect} disabled={themeUploading} />
							</label>
						</div>
						<!-- CSS textarea -->
						<div>
							<label for="theme-css-input" class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">Custom CSS <span class="text-xs text-gray-400">(optional)</span></label>
							<textarea
								id="theme-css-input"
								bind:value={themeCssText}
								placeholder={'[data-scheme="my-theme"] {\n  /* custom styles */\n}'}
								rows="6"
								disabled={themeUploading}
								class="w-full rounded-lg border border-primary/25 bg-primary/5 px-3 py-2 font-mono text-sm dark:border-primary/30 dark:bg-primary/10 dark:text-white"
							></textarea>
						</div>
						<!-- Upload button -->
						<div class="flex items-center gap-3">
							<button
								type="button"
								onclick={handleThemeUpload}
								disabled={!themeJsonFile || !themeName.trim() || themeUploading}
								class="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-on-primary transition-colors hover:bg-primary-hover disabled:opacity-50"
							>
								{themeUploading ? 'Uploading...' : 'Upload Theme'}
							</button>
							{#if themeFeedback}
								<span class="text-sm {themeFeedback.type === 'success' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}">
									{themeFeedback.message}
								</span>
							{/if}
						</div>
					</div>
				</div>

				<!-- Dark Mode -->
				<div class="rounded-lg border border-primary/20 bg-surface p-6 shadow-xs dark:border-primary/20 dark:bg-surface-dark">
					<div class="flex items-center justify-between">
						<div>
							<h3 class="text-base font-semibold text-gray-900 dark:text-white">Dark Mode</h3>
							{#if $schemeLocksMode}
								<p class="text-sm text-gray-500 dark:text-gray-400">Locked by theme</p>
							{:else}
								<p class="text-sm text-gray-500 dark:text-gray-400">Toggle between light and dark mode.</p>
							{/if}
						</div>
						{#if !$schemeLocksMode}
							<div class="flex items-center gap-2">
								<button
									type="button"
									onclick={toggleTheme}
									class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out
										{$theme === 'dark' ? 'bg-primary' : 'bg-primary/30 dark:bg-primary/20'}"
									role="switch"
									aria-checked={$theme === 'dark'}
									aria-label="Dark mode"
								>
									<span
										class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out
											{$theme === 'dark' ? 'translate-x-5' : 'translate-x-0'}"
									></span>
								</button>
								<span class="text-xs font-medium {$theme === 'dark' ? 'text-primary-text dark:text-primary-text-dark' : 'text-gray-400'}">
									{$theme === 'dark' ? 'On' : 'Off'}
								</span>
							</div>
						{/if}
					</div>
				</div>

				<!-- Image Cache -->
				<div class="rounded-lg border border-primary/20 bg-surface p-6 shadow-xs dark:border-primary/20 dark:bg-surface-dark">
					<div class="flex items-center justify-between">
						<div>
							<h3 class="text-base font-semibold text-gray-900 dark:text-white">Image Cache</h3>
							<p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
								{#if cacheLoading}Loading...
								{:else if cacheStats}{cacheStats.count} cached image{cacheStats.count !== 1 ? 's' : ''} ({cacheStats.size_mb} MB)
								{:else}Unable to load cache stats
								{/if}
							</p>
						</div>
						<button type="button"
							onclick={() => (cacheConfirmOpen = true)}
							disabled={cacheBusy || !cacheStats?.count}
							class="rounded-lg px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-500/10 disabled:opacity-50 dark:text-red-400 dark:hover:bg-red-500/15">
							Clear Cache
						</button>
					</div>
					{#if cacheFeedback}
						<p class="mt-2 text-sm {cacheFeedback.type === 'success' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}">
							{cacheFeedback.message}
						</p>
					{/if}
				</div>

				<!-- Feature request prompt -->
				<div class="flex justify-center pt-2">
					<span class="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-4 py-2 text-xs text-gray-500 dark:text-gray-400">
						<svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5.002 5.002 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>
						Not seeing what you want? Submit your feature requests on GitHub.
					</span>
				</div>
			</section>
		{/if}

		{#if activeTab === 'drives'}
			<h2 class="mb-4 text-lg font-semibold text-gray-900 dark:text-white">Drives</h2>
			<section class="space-y-6">
				{#if $driveError}
					<div class="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
						{$driveError}
					</div>
				{:else if $drives.length === 0}
					<p class="py-8 text-center text-gray-400">No drives detected.</p>
				{:else}
					<div class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
						{#each $drives as drive (drive.drive_id)}
							<DriveCard {drive} onupdate={() => drives.refresh()} globalDefaults={{
								prescan_cache_mb: Number(settings?.arm_config?.PRESCAN_CACHE_MB) || 1,
								prescan_timeout: Number(settings?.arm_config?.PRESCAN_TIMEOUT) || 300,
								prescan_retries: Number(settings?.arm_config?.PRESCAN_RETRIES) || 3,
								disc_enum_timeout: Number(settings?.arm_config?.DISC_ENUM_TIMEOUT) || 60,
							}} />
						{/each}
					</div>
				{/if}

				<!-- Maintenance & Diagnostics -->
				<hr class="my-2 opacity-20" />
				<div class="flex flex-wrap items-center gap-2">
					<span class="text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Maintenance</span>
					<button
						onclick={async () => { rescanning = true; await rescanDrives(); await drives.refresh(); rescanning = false; }}
						disabled={rescanning}
						class="ml-auto rounded-lg border border-primary/20 px-3 py-1.5 text-xs font-medium text-primary-text transition-colors hover:bg-primary/10 disabled:opacity-50 dark:border-primary/20 dark:text-primary-text-dark dark:hover:bg-primary/15"
						title="Re-detect optical drives and refresh database records"
					>{rescanning ? 'Scanning...' : 'Rescan'}</button>
					<button
						onclick={async () => { rescanning = true; await rescanDrives(true); await drives.refresh(); rescanning = false; }}
						disabled={rescanning}
						class="rounded-lg border border-amber-300 px-3 py-1.5 text-xs font-medium text-amber-700 transition-colors hover:bg-amber-50 disabled:opacity-50 dark:border-amber-700 dark:text-amber-400 dark:hover:bg-amber-900/20"
						title="Delete all stale drive records and re-detect from hardware"
					>{rescanning ? 'Scanning...' : 'Force Rescan'}</button>
				</div>
				<div data-diag>
					<button
						onclick={() => { diagOpen = !diagOpen; }}
						class="flex w-full items-center gap-2 rounded-lg border border-primary/15 bg-primary/5 px-3.5 py-2.5 text-sm font-medium text-primary-text transition-colors hover:bg-primary/10 dark:border-primary/15 dark:text-primary-text-dark dark:hover:bg-primary/15"
					>
						<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
						</svg>
						Udev & Drive Diagnostics
						<svg class="ml-auto h-4 w-4 transition-transform duration-200 {diagOpen ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
						</svg>
					</button>

					{#if diagOpen}
						<div class="mt-2.5 rounded-lg border border-primary/10 bg-white/[0.02] p-3 dark:border-primary/10" transition:slide={{ duration: 200 }}>
							<div class="mb-2.5 flex items-center justify-between">
								<button
									onclick={runDiagnostic}
									disabled={diagRunning}
									class="inline-flex items-center gap-2 rounded-lg bg-primary/15 px-3.5 py-1.5 text-sm font-medium text-primary-text transition-colors hover:bg-primary/25 disabled:opacity-50 dark:text-primary-text-dark dark:hover:bg-primary/30"
								>
									<svg class="h-4 w-4 {diagRunning ? 'animate-spin' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
									</svg>
									{diagRunning ? 'Running...' : 'Run Check'}
								</button>
								{#if diagLastRun}
									<span class="text-[10px] text-gray-400 dark:text-gray-500">Last run: {diagLastRun}</span>
								{/if}
								{#if diagError}
									<span class="text-sm text-red-600 dark:text-red-400">{diagError}</span>
								{/if}
							</div>

							{#if diagResult}
								<!-- Status bar -->
								<div class="mb-2 flex flex-wrap items-center gap-3 rounded-lg border px-3 py-2 text-xs
									{diagResult.issues.length > 0 || diagResult.drives.some(d => d.issues.length > 0)
										? 'border-amber-500/15 bg-amber-500/5'
										: 'border-green-500/15 bg-green-500/5'}">
									<span class="inline-flex items-center gap-1.5">
										<div class="h-1.5 w-1.5 rounded-full {diagResult.udevd_running ? 'bg-green-500' : 'bg-red-500'}"></div>
										<span class="font-medium text-gray-700 dark:text-gray-300">udevd {diagResult.udevd_running ? 'running' : 'not running'}</span>
									</span>
									<span class="text-gray-500 dark:text-gray-400">
										Kernel: {diagResult.kernel_drives.length > 0 ? diagResult.kernel_drives.join(', ') : 'none'}
									</span>
									<span class="text-gray-500 dark:text-gray-400">
										{diagResult.drives.length} drive{diagResult.drives.length !== 1 ? 's' : ''}
									</span>
									<span class="font-medium {diagResult.issues.length > 0 || diagResult.drives.some(d => d.issues.length > 0) ? 'text-amber-600 dark:text-amber-400' : 'text-green-600 dark:text-green-400'}">
										{diagResult.issues.length > 0 || diagResult.drives.some(d => d.issues.length > 0) ? 'Issues Found' : 'All OK'}
									</span>
								</div>

								<!-- System-level issues -->
								{#if diagResult.issues.length > 0}
									<div class="mb-2 rounded-lg border border-red-500/15 bg-red-500/5 p-2.5">
										{#each diagResult.issues as issue}
											<div class="flex items-start gap-1.5 text-xs">
												<svg class="mt-0.5 h-3 w-3 flex-shrink-0 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
												</svg>
												<span class="text-red-700 dark:text-red-300">{issue}</span>
											</div>
										{/each}
									</div>
								{/if}

								<!-- Per-drive issues only -->
								{#each diagResult.drives.filter(d => d.issues.length > 0) as diag}
									<div class="mb-1.5 rounded-lg border border-amber-500/15 bg-amber-500/5 p-2.5">
										{#each diag.issues as issue}
											<div class="flex items-start gap-1.5 text-xs">
												<svg class="mt-0.5 h-3 w-3 flex-shrink-0 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
												</svg>
												<span class="text-amber-700 dark:text-amber-400">
													<span class="font-medium">/dev/{diag.devname}</span> — {issue}
												</span>
											</div>
										{/each}
									</div>
								{/each}
							{:else if !diagRunning}
								<p class="text-center text-xs text-gray-400 dark:text-gray-500">Click "Run Check" to scan drives and udev configuration.</p>
							{/if}
						</div>
					{/if}
				</div>
			</section>
		{/if}
		{/snippet}
	</LoadState>
</div>

<!-- Sticky save bar -->
{#if anyDirty}
	<div class="fixed bottom-0 left-0 right-0 z-50 border-t border-primary/30 bg-surface/95 shadow-lg backdrop-blur-sm dark:border-primary/30 dark:bg-surface-dark/95">
		<div class="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
			<div class="flex items-center gap-3">
				<span class="h-2 w-2 shrink-0 rounded-full bg-primary animate-pulse"></span>
				<span class="text-sm font-bold text-gray-700 dark:text-gray-300">Unsaved {dirtyTabLabel} changes</span>
				{#if anyFeedback}
					<span
						class="text-sm {anyFeedback.type === 'success'
							? 'text-green-600 dark:text-green-400'
							: 'text-red-600 dark:text-red-400'}"
					>
						{anyFeedback.message}
					</span>
				{/if}
			</div>
			<div class="flex items-center gap-2">
				<button
					type="button"
					onclick={handleDiscardAll}
					class="rounded-lg px-4 py-2 text-sm font-medium text-gray-600 ring-1 ring-gray-300 hover:bg-gray-100 dark:text-gray-400 dark:ring-gray-600 dark:hover:bg-gray-800"
				>
					Discard
				</button>
				<button
					type="button"
					onclick={handleSaveAll}
					disabled={anySaving}
					class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-on-primary hover:bg-primary-hover disabled:opacity-50 dark:bg-primary dark:hover:bg-primary-hover"
				>
					{anySaving ? 'Saving...' : 'Save Changes'}
				</button>
			</div>
		</div>
	</div>
{/if}

<ConfirmDialog
	open={cacheConfirmOpen}
	title="Clear Image Cache"
	message="Delete all cached poster images? They will be re-fetched on next view."
	confirmLabel="Clear"
	variant="danger"
	onconfirm={handleClearCache}
	oncancel={() => (cacheConfirmOpen = false)}
/>

<ToastHost />
