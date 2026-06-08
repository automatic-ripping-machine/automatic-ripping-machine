<script lang="ts">
    import { onMount } from 'svelte';
    import type { JobSchema as Job } from '$lib/types/api.gen';
    import type { Scheme, Preset, Overrides } from '$lib/types/api.gen';
    import type { PresetEditorState } from '$lib/types/presets';
    import { fetchTranscoderScheme, fetchTranscoderPresets } from '$lib/api/settings';
    import { updateJobTranscodeConfig } from '$lib/api/jobs';
    import PresetEditor from './PresetEditor.svelte';

    interface Props {
        job: Job;
        onsaved?: () => void;
    }

    let { job, onsaved }: Props = $props();

    let scheme = $state<Scheme | null>(null);
    let presets = $state<Preset[]>([]);
    let offline = $state(false);
    let saving = $state(false);
    let feedback = $state<{ type: 'success' | 'error'; message: string } | null>(null);
    let loaded = $state(false);

    const initialState = $derived.by<PresetEditorState>(() => {
        const o = job.transcode_overrides as Record<string, unknown> | null | undefined;
        if (!o || typeof o !== 'object' || !('preset_slug' in o)) {
            return { preset_slug: '', overrides: { shared: {}, tiers: {} } };
        }
        const raw = o.overrides as Partial<Overrides> | undefined;
        return {
            preset_slug: (o.preset_slug as string) ?? '',
            overrides: {
                shared: raw?.shared ?? {},
                tiers: raw?.tiers ?? {}
            }
        };
    });

    async function loadData() {
        offline = false;
        const [s, p] = await Promise.all([fetchTranscoderScheme(), fetchTranscoderPresets()]);
        if (s === null || p === null) {
            offline = true;
            return;
        }
        scheme = s;
        presets = p.presets;
    }

    async function handleSave(state: PresetEditorState) {
        saving = true;
        feedback = null;
        try {
            await updateJobTranscodeConfig(job.job_id, {
                preset_slug: state.preset_slug,
                overrides: state.overrides
            });
            feedback = { type: 'success', message: 'Overrides saved' };
            onsaved?.();
        } catch (e) {
            feedback = { type: 'error', message: e instanceof Error ? e.message : 'Save failed' };
        } finally {
            saving = false;
        }
    }

    onMount(async () => {
        await loadData();
        loaded = true;
    });
</script>

{#if !loaded}
    <p class="text-sm text-gray-400">Loading transcoder settings...</p>
{:else}
    <div class="space-y-3">
        <p class="text-xs text-gray-500 dark:text-gray-400">
            Override transcoder settings for this job only. Changes apply to this job's transcode.
        </p>
        <PresetEditor
            scope="job"
            initialState={initialState}
            scheme={scheme}
            presets={presets}
            offline={offline}
            saving={saving}
            onSave={handleSave}
            onRetry={loadData}
        />
        {#if feedback}
            <span class="text-xs {feedback.type === 'success' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}">
                {feedback.message}
            </span>
        {/if}
    </div>
{/if}
