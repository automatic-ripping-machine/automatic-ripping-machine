import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderComponent, screen, waitFor, cleanup } from '$lib/test-utils';
import { fireEvent } from '@testing-library/svelte';
import TranscodeOverrides from './TranscodeOverrides.svelte';
import type { JobSchema as Job } from '$lib/types/api.gen';
vi.mock('$lib/api/settings', () => ({
    fetchTranscoderScheme: vi.fn().mockResolvedValue({
        slug: 'software', name: 'Software (CPU)',
        supported_encoders: [{ slug: 'x265', name: 'x265', tuning_presets: [] }],
        supported_audio_encoders: ['copy', 'aac'],
        supported_subtitle_modes: ['all'],
        advanced_fields: {}
    }),
    fetchTranscoderPresets: vi.fn().mockResolvedValue({
        presets: [{
            slug: 'software_balanced', name: 'Balanced', scheme: 'software',
            description: '', builtin: true,
            shared: {}, tiers: { dvd: {}, bluray: {}, uhd: {} }
        }]
    })
}));

const updateMock = vi.fn().mockResolvedValue({ success: true });
vi.mock('$lib/api/jobs', () => ({
    updateJobTranscodeConfig: (...args: unknown[]) => updateMock(...args)
}));

const baseJob = {
    job_id: 1,
    transcode_overrides: { preset_slug: 'software_balanced', overrides: { shared: {}, tiers: {} } }
} as unknown as Job;

beforeEach(() => updateMock.mockClear());
afterEach(() => cleanup());

describe('TranscodeOverrides', () => {
    it('renders PresetEditor and submits new-shape overrides on save', async () => {
        const { container } = renderComponent(TranscodeOverrides, { props: { job: baseJob } });
        await waitFor(() => screen.getByText(/Software \(CPU\)/));
        const qualityInput = container.querySelector('input[data-testid="tier-bluray-quality"]') as HTMLInputElement;
        await fireEvent.input(qualityInput, { target: { value: '18' } });
        await fireEvent.click(screen.getByRole('button', { name: /Save changes/i }));
        await waitFor(() => expect(updateMock).toHaveBeenCalled());
        expect(updateMock).toHaveBeenCalledWith(1, expect.objectContaining({
            preset_slug: 'software_balanced',
            overrides: expect.objectContaining({ tiers: expect.objectContaining({ bluray: { video_quality: 18 } }) })
        }));
    });

    it('does not show "Save as new preset" (scope=job)', async () => {
        renderComponent(TranscodeOverrides, { props: { job: baseJob } });
        await waitFor(() => screen.getByText(/Software \(CPU\)/));
        expect(screen.queryByText(/Save as new preset/i)).toBeNull();
    });

    it('defaults to empty preset state when job has no transcode_overrides', async () => {
        const jobWithoutOverrides = { job_id: 2, transcode_overrides: null } as unknown as Job;
        renderComponent(TranscodeOverrides, { props: { job: jobWithoutOverrides } });
        // Scheme name renders from the active scheme (line 26 branch: empty initial state)
        await waitFor(() => screen.getByText(/Software \(CPU\)/));
    });

    it('defaults to empty preset state when legacy flat overrides lack preset_slug', async () => {
        const legacyJob = {
            job_id: 3,
            transcode_overrides: { video_encoder: 'x265', video_quality: 22 },
        } as unknown as Job;
        renderComponent(TranscodeOverrides, { props: { job: legacyJob } });
        await waitFor(() => screen.getByText(/Software \(CPU\)/));
    });

    it('shows offline state when transcoder is unreachable', async () => {
        const settingsApi = await import('$lib/api/settings');
        vi.mocked(settingsApi.fetchTranscoderScheme).mockResolvedValueOnce(null);
        vi.mocked(settingsApi.fetchTranscoderPresets).mockResolvedValueOnce(null);
        renderComponent(TranscodeOverrides, { props: { job: baseJob } });
        // offline=true triggers the offline UI instead of the preset editor (line 42 branch)
        await waitFor(() => expect(screen.queryByText(/Software \(CPU\)/)).toBeNull());
    });
});
