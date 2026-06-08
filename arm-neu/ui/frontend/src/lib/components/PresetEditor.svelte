<script lang="ts">
    import { onDestroy, onMount } from 'svelte';
    import type { Scheme, Preset, Overrides } from '$lib/types/api.gen';
    import type { PresetEditorState } from '$lib/types/presets';
    import { listHandbrakePresets } from '$lib/api/transcoder';
    interface Props {
        scope: 'global' | 'job';
        initialState: PresetEditorState;
        scheme: Scheme | null;
        presets: Preset[];
        offline: boolean;
        saving: boolean;
        onSave: (state: PresetEditorState) => Promise<void>;
        onSaveAsNew?: (state: { name: string; parent_slug: string; overrides: Overrides }) => Promise<void>;
        onRetry?: () => void;
    }

    let { scope, initialState, scheme, presets, offline, saving, onSave, onSaveAsNew, onRetry }: Props = $props();

    const initialSlug = initialState.preset_slug;
    let selectedSlug = $state<string>(initialSlug);
    let overrides = $state<Overrides>({
        shared: structuredClone(initialState.overrides?.shared ?? {}),
        tiers: structuredClone(initialState.overrides?.tiers ?? {})
    });

    // Once presets are loaded, default to the first built-in if no slug was preselected
    $effect(() => {
        if (selectedSlug === '' && presets.length > 0) {
            const firstBuiltin = presets.find(p => p.builtin && !p.unavailable);
            if (firstBuiltin) selectedSlug = firstBuiltin.slug;
        }
    });

    const dirtyCount = $derived(
        Object.keys(overrides.shared).length +
        Object.values(overrides.tiers).reduce((n, t) => n + Object.keys(t).length, 0)
    );
    const dirty = $derived(dirtyCount > 0);
    const selectedPreset = $derived(presets.find(p => p.slug === selectedSlug));
    const isUnavailable = $derived(selectedPreset?.unavailable === true);
    const canSave = $derived(!saving && !isUnavailable && (dirty || selectedSlug !== initialSlug));

    const builtinCount = $derived(presets.filter(p => p.builtin && !p.unavailable).length);
    const customCount = $derived(presets.filter(p => !p.builtin && !p.unavailable).length);

    function setShared(key: string, value: unknown) {
        if (value === '' || value === null || value === undefined) {
            delete overrides.shared[key];
        } else {
            overrides.shared[key] = value;
        }
        overrides = { ...overrides };
    }

    function setTier(tier: string, key: string, value: unknown) {
        if (!overrides.tiers[tier]) overrides.tiers[tier] = {};
        if (value === '' || value === null || value === undefined) {
            delete overrides.tiers[tier][key];
            if (Object.keys(overrides.tiers[tier]).length === 0) delete overrides.tiers[tier];
        } else {
            overrides.tiers[tier][key] = value;
        }
        overrides = { ...overrides };
    }

    function effectiveShared(key: string): unknown {
        if (key in overrides.shared) return overrides.shared[key];
        return selectedPreset?.shared?.[key] ?? '';
    }

    function effectiveTier(tier: string, key: string): unknown {
        if (overrides.tiers[tier]?.[key] !== undefined) return overrides.tiers[tier][key];
        const tierVal = selectedPreset?.tiers?.[tier]?.[key];
        if (tierVal !== undefined) return tierVal;
        return selectedPreset?.shared?.[key] ?? '';
    }

    function isSharedDirty(key: string): boolean {
        return key in overrides.shared;
    }

    function isTierDirty(tier: string, key: string): boolean {
        return overrides.tiers[tier]?.[key] !== undefined;
    }

    const TIER_LABELS: Record<string, string> = { dvd: 'DVD', bluray: 'Blu-ray', uhd: 'UHD' };
    const TIER_HINTS: Record<string, string> = { dvd: '< 720p', bluray: '720p–1080p', uhd: '> 1080p' };

    const dirtyRing = 'rounded-lg ring-2 ring-primary/40 dark:ring-primary/50';
    const inputClass = 'rounded-lg border border-primary/25 bg-primary/5 px-3 py-1.5 text-sm focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary dark:border-primary/30 dark:bg-primary/10 dark:text-white';

    let saveAsModalOpen = $state(false);
    let newPresetName = $state('');
    let saveAsNewError = $state<string>('');

    let undoToast = $state<{ message: string; previous: { slug: string; overrides: Overrides } } | null>(null);
    let undoTimer: ReturnType<typeof setTimeout> | null = null;
    onDestroy(() => { if (undoTimer) clearTimeout(undoTimer); });

    // HandBrake preset picker. The transcoder enumerates its built-in
    // preset list via /api/v1/handbrake-presets; the BFF passes through.
    // When the list is empty (transcoder offline, older version, parser
    // failure) we fall back to free-text entry so the field is never
    // un-editable.
    let handbrakePresetGroups = $state<Record<string, string[]>>({});
    const handbrakeKnown = $derived(
        new Set(Object.values(handbrakePresetGroups).flat())
    );
    const handbrakeAvailable = $derived(handbrakeKnown.size > 0);
    onMount(async () => {
        handbrakePresetGroups = await listHandbrakePresets();
    });

    function handleDropdownChange(newSlug: string) {
        const wasDirty = dirty;
        const previousSlug = selectedSlug;
        const previousName = selectedPreset?.name ?? previousSlug;
        const previousOverrides: Overrides = JSON.parse(JSON.stringify(overrides));
        selectedSlug = newSlug;
        overrides = { shared: {}, tiers: {} };
        if (wasDirty) {
            const totalCleared = Object.keys(previousOverrides.shared).length +
                Object.values(previousOverrides.tiers).reduce((n, t) => n + Object.keys(t).length, 0);
            undoToast = {
                message: `Cleared ${totalCleared} ${totalCleared === 1 ? 'change' : 'changes'} from ${previousName}`,
                previous: { slug: previousSlug, overrides: previousOverrides }
            };
            if (undoTimer) clearTimeout(undoTimer);
            undoTimer = setTimeout(() => { undoToast = null; }, 5000);
        }
    }

    function handleUndo() {
        if (!undoToast) return;
        selectedSlug = undoToast.previous.slug;
        overrides = undoToast.previous.overrides;
        undoToast = null;
        if (undoTimer) { clearTimeout(undoTimer); undoTimer = null; }
    }

    function handleSave() {
        if (!canSave) return;
        onSave({ preset_slug: selectedSlug, overrides: $state.snapshot(overrides) as Overrides });
    }

    function handleRevert() {
        overrides = { shared: {}, tiers: {} };
        selectedSlug = initialSlug;
    }

    async function handleSaveAsConfirm() {
        if (!onSaveAsNew || !newPresetName.trim()) return;
        saveAsNewError = '';
        try {
            await onSaveAsNew({
                name: newPresetName.trim(),
                parent_slug: selectedSlug,
                overrides: $state.snapshot(overrides) as Overrides,
            });
            saveAsModalOpen = false;
            newPresetName = '';
        } catch (e: unknown) {
            saveAsNewError = e instanceof Error ? e.message : 'Save failed';
        }
    }

    function disabledSaveReason(): string {
        if (saving) return 'Saving...';
        if (isUnavailable) return 'Selected preset is not available in the active scheme';
        if (!dirty && selectedSlug === initialSlug) return 'No changes to save';
        return '';
    }

    function slugify(name: string): string {
        return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'custom';
    }
</script>

{#if offline || !scheme}
    <div class="rounded-lg border border-amber-500/40 bg-amber-50 p-4 text-amber-900 dark:border-amber-500/30 dark:bg-amber-950/30 dark:text-amber-200">
        <p class="font-semibold">Transcoder service unavailable</p>
        <p class="mt-1 text-sm">Cannot load preset options. Check that arm-transcoder is running.</p>
        {#if onRetry}
            <button onclick={onRetry} class="mt-2 rounded-md bg-amber-600 px-3 py-1 text-sm font-medium text-white hover:bg-amber-700">
                Retry
            </button>
        {/if}
    </div>
{:else}
    <div class="space-y-4">
        {#if isUnavailable}
            <div class="rounded-lg border border-amber-500/40 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-500/30 dark:bg-amber-950/30 dark:text-amber-200">
                This preset was built for scheme <strong>{selectedPreset?.scheme}</strong> but the active scheme is <strong>{scheme.slug}</strong>. Pick a compatible preset to save changes.
            </div>
        {/if}
        <div class="flex items-baseline justify-between border-b border-gray-200 pb-2 dark:border-gray-700">
            <div>
                <p class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Active scheme</p>
                <p class="text-base font-semibold text-gray-900 dark:text-white">{scheme.name}</p>
            </div>
            <p class="text-xs text-gray-500 dark:text-gray-400">{builtinCount} built-in · {customCount} custom</p>
        </div>
        <div>
            <label for="preset-select" class="block text-sm font-medium text-gray-700 dark:text-gray-300">Preset</label>
            <select
                id="preset-select"
                value={selectedSlug}
                onchange={(e) => handleDropdownChange((e.target as HTMLSelectElement).value)}
                disabled={saving}
                class="mt-1 w-full rounded-lg border border-primary/25 bg-primary/5 px-3 py-1.5 text-sm focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary dark:border-primary/30 dark:bg-primary/10 dark:text-white"
            >
                <optgroup label="Built-in">
                    {#each presets.filter(p => p.builtin && !p.unavailable) as p (p.slug)}
                        <option value={p.slug}>{p.name}</option>
                    {/each}
                </optgroup>
                {#if presets.some(p => !p.builtin && !p.unavailable)}
                    <optgroup label="Custom">
                        {#each presets.filter(p => !p.builtin && !p.unavailable) as p (p.slug)}
                            <option value={p.slug}>{p.name}</option>
                        {/each}
                    </optgroup>
                {/if}
                {#if presets.some(p => p.unavailable)}
                    <optgroup label="Unavailable (other scheme)">
                        {#each presets.filter(p => p.unavailable) as p (p.slug)}
                            <option value={p.slug} disabled title={p.reason}>{p.name} ({p.scheme})</option>
                        {/each}
                    </optgroup>
                {/if}
            </select>
            {#if selectedPreset?.description}
                <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">{selectedPreset.description}</p>
            {/if}
        </div>

        <div>
            <div class="flex items-center justify-between">
                <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-300">Customize</h4>
                {#if dirty}
                    <span class="rounded-full bg-primary/20 px-2 py-0.5 text-xs font-medium text-primary dark:text-primary-300">
                        {dirtyCount} {dirtyCount === 1 ? 'change' : 'changes'}
                    </span>
                {/if}
            </div>

            <div class="mt-3 space-y-3">
                <div class="rounded-lg border border-gray-200 p-3 dark:border-gray-700">
                    <p class="mb-2 text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Shared</p>
                    <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
                        <label class="space-y-1">
                            <span class="text-xs text-gray-600 dark:text-gray-400">Audio encoder</span>
                            <div class={isSharedDirty('audio_encoder') ? dirtyRing : ''}>
                                <select
                                    value={effectiveShared('audio_encoder')}
                                    onchange={(e) => setShared('audio_encoder', (e.target as HTMLSelectElement).value)}
                                    disabled={saving || isUnavailable}
                                    class="{inputClass} w-full"
                                >
                                    {#each scheme.supported_audio_encoders as enc}
                                        <option value={enc}>{enc}</option>
                                    {/each}
                                </select>
                            </div>
                        </label>
                        <label class="space-y-1">
                            <span class="text-xs text-gray-600 dark:text-gray-400">Subtitle mode</span>
                            <div class={isSharedDirty('subtitle_mode') ? dirtyRing : ''}>
                                <select
                                    value={effectiveShared('subtitle_mode')}
                                    onchange={(e) => setShared('subtitle_mode', (e.target as HTMLSelectElement).value)}
                                    disabled={saving || isUnavailable}
                                    class="{inputClass} w-full"
                                >
                                    {#each scheme.supported_subtitle_modes as mode}
                                        <option value={mode}>{mode}</option>
                                    {/each}
                                </select>
                            </div>
                        </label>
                    </div>
                </div>

                {#each ['dvd', 'bluray', 'uhd'] as tier}
                    <div class="rounded-lg border border-gray-200 p-3 dark:border-gray-700">
                        <p class="mb-2 text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                            {TIER_LABELS[tier]} <span class="text-gray-400">· {TIER_HINTS[tier]}</span>
                        </p>
                        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
                            <label class="space-y-1">
                                <span class="text-xs text-gray-600 dark:text-gray-400">Encoder</span>
                                <div class={isTierDirty(tier, 'video_encoder') ? dirtyRing : ''}>
                                    <select
                                        value={effectiveTier(tier, 'video_encoder')}
                                        onchange={(e) => setTier(tier, 'video_encoder', (e.target as HTMLSelectElement).value)}
                                        disabled={saving || isUnavailable}
                                        class="{inputClass} w-full"
                                    >
                                        {#each scheme.supported_encoders as enc}
                                            <option value={enc.slug}>{enc.name}</option>
                                        {/each}
                                    </select>
                                </div>
                            </label>
                            <label class="space-y-1">
                                <span class="text-xs text-gray-600 dark:text-gray-400">Quality (CRF 0-51)</span>
                                <div class={isTierDirty(tier, 'video_quality') ? dirtyRing : ''}>
                                    <input
                                        type="number" min="0" max="51" step="1"
                                        data-testid="tier-{tier}-quality"
                                        value={effectiveTier(tier, 'video_quality')}
                                        oninput={(e) => {
                                            const raw = (e.target as HTMLInputElement).value;
                                            setTier(tier, 'video_quality', raw === '' ? '' : Number(raw));
                                        }}
                                        disabled={saving || isUnavailable}
                                        class="{inputClass} w-full"
                                    />
                                </div>
                            </label>
                            <label class="space-y-1 lg:col-span-2">
                                <span class="text-xs text-gray-600 dark:text-gray-400">HandBrake preset</span>
                                <div class={isTierDirty(tier, 'handbrake_preset') ? dirtyRing : ''}>
                                    {#if handbrakeAvailable && handbrakeKnown.has(String(effectiveTier(tier, 'handbrake_preset')))}
                                        <select
                                            value={effectiveTier(tier, 'handbrake_preset')}
                                            onchange={(e) => {
                                                const v = (e.target as HTMLSelectElement).value;
                                                setTier(tier, 'handbrake_preset', v === '__custom__' ? '' : v);
                                            }}
                                            disabled={saving || isUnavailable}
                                            class="{inputClass} w-full"
                                        >
                                            {#each Object.entries(handbrakePresetGroups) as [category, names]}
                                                <optgroup label={category}>
                                                    {#each names as name}
                                                        <option value={name}>{name}</option>
                                                    {/each}
                                                </optgroup>
                                            {/each}
                                            <option value="__custom__">Custom...</option>
                                        </select>
                                    {:else}
                                        <input
                                            type="text"
                                            value={effectiveTier(tier, 'handbrake_preset')}
                                            oninput={(e) => setTier(tier, 'handbrake_preset', (e.target as HTMLInputElement).value)}
                                            disabled={saving || isUnavailable}
                                            class="{inputClass} w-full"
                                            placeholder={handbrakeAvailable ? 'Custom preset name' : 'HandBrake preset name'}
                                        />
                                    {/if}
                                </div>
                                {#if handbrakeAvailable && handbrakeKnown.has(String(effectiveTier(tier, 'handbrake_preset')))}
                                    <button
                                        type="button"
                                        class="text-xs text-primary hover:underline"
                                        onclick={() => setTier(tier, 'handbrake_preset', '')}
                                    >Use a custom preset name</button>
                                {/if}
                            </label>
                            {#each Object.entries(scheme.advanced_fields ?? {}) as [key, def]}
                                <label class="space-y-1">
                                    <span class="text-xs text-gray-600 dark:text-gray-400">{key}</span>
                                    <div class={isTierDirty(tier, key) ? dirtyRing : ''}>
                                        {#if def.type === 'enum' && def.values}
                                            <select
                                                value={effectiveTier(tier, key) || def.default || ''}
                                                onchange={(e) => setTier(tier, key, (e.target as HTMLSelectElement).value)}
                                                disabled={saving || isUnavailable}
                                                class="{inputClass} w-full"
                                            >
                                                {#each def.values as v}
                                                    <option value={v}>{v}</option>
                                                {/each}
                                            </select>
                                        {:else}
                                            <input
                                                type="text"
                                                value={effectiveTier(tier, key)}
                                                oninput={(e) => setTier(tier, key, (e.target as HTMLInputElement).value)}
                                                disabled={saving || isUnavailable}
                                                class="{inputClass} w-full"
                                            />
                                        {/if}
                                    </div>
                                    {#if def.description}
                                        <span class="block text-xs text-gray-400">{def.description}</span>
                                    {/if}
                                </label>
                            {/each}
                        </div>
                    </div>
                {/each}
            </div>
        </div>

        <div class="flex items-center justify-between border-t border-gray-200 pt-3 dark:border-gray-700">
            <div class="flex items-center gap-3">
                <button
                    type="button"
                    onclick={handleSave}
                    disabled={!canSave}
                    title={disabledSaveReason()}
                    class="rounded-lg bg-primary px-4 py-1.5 text-sm font-semibold text-white hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
                >
                    {saving ? 'Saving...' : 'Save changes'}
                </button>
                {#if scope === 'global' && onSaveAsNew}
                    <button
                        type="button"
                        onclick={() => { saveAsModalOpen = true; newPresetName = ''; saveAsNewError = ''; }}
                        disabled={!dirty}
                        class="rounded-lg border border-primary px-4 py-2 text-sm font-semibold text-primary hover:bg-primary/10 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        Save as new preset
                    </button>
                {/if}
            </div>
            <button
                type="button"
                onclick={handleRevert}
                disabled={!dirty && selectedSlug === initialSlug}
                class="text-sm text-gray-500 hover:text-gray-700 disabled:opacity-50 dark:text-gray-400 dark:hover:text-gray-200"
            >
                Revert
            </button>
        </div>
    </div>

    {#if undoToast}
        <div class="fixed bottom-4 left-1/2 z-40 -translate-x-1/2 rounded-lg bg-gray-900 px-4 py-2 text-sm text-white shadow-xl dark:bg-gray-700">
            {undoToast.message}
            <button onclick={handleUndo} class="ml-3 underline">Undo</button>
        </div>
    {/if}

    {#if saveAsModalOpen}
        <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true" aria-labelledby="save-as-heading">
            <div class="w-full max-w-md rounded-lg bg-white p-5 shadow-xl dark:bg-gray-800">
                <h3 id="save-as-heading" class="text-lg font-semibold text-gray-900 dark:text-white">Save as new preset</h3>
                <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                    Saves your current customizations as a new preset based on <strong>{selectedPreset?.name}</strong>.
                </p>
                <label class="mt-3 block">
                    <span class="text-sm font-medium text-gray-700 dark:text-gray-300">Name</span>
                    <input
                        type="text"
                        bind:value={newPresetName}
                        placeholder="e.g. Weekend Rips"
                        class="{inputClass} mt-1 w-full"
                    />
                    {#if newPresetName.trim()}
                        <span class="mt-1 block text-xs text-gray-500 dark:text-gray-400">Will be saved as: <code>{slugify(newPresetName)}</code></span>
                    {/if}
                    {#if saveAsNewError}
                        <span class="mt-1 block text-xs text-red-600 dark:text-red-400">{saveAsNewError}</span>
                    {/if}
                </label>
                <div class="mt-4 flex justify-end gap-2">
                    <button type="button" onclick={() => { saveAsModalOpen = false; }}
                            class="rounded-lg px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700">
                        Cancel
                    </button>
                    <button type="button" onclick={handleSaveAsConfirm}
                            disabled={!newPresetName.trim()}
                            class="rounded-lg bg-primary px-3 py-1.5 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-50">
                        Create preset
                    </button>
                </div>
            </div>
        </div>
    {/if}
{/if}
