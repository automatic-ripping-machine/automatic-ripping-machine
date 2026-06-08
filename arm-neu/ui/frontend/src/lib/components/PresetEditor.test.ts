import { describe, it, expect, afterEach, vi } from 'vitest';
import { renderComponent, screen, fireEvent, cleanup } from '$lib/test-utils';
import PresetEditor from './PresetEditor.svelte';
import type { Scheme, Preset } from '$lib/types/api.gen';
const mockScheme: Scheme = {
    slug: 'software',
    name: 'Software (CPU)',
    supported_encoders: [
        { slug: 'x265', name: 'x265', tuning_presets: [] },
        { slug: 'x264', name: 'x264', tuning_presets: [] }
    ],
    supported_audio_encoders: ['copy', 'aac'],
    supported_subtitle_modes: ['all', 'first', 'none'],
    advanced_fields: {}
};

const mockPresets: Preset[] = [
    {
        slug: 'software_balanced', name: 'Balanced', scheme: 'software',
        description: 'Balanced encoding', builtin: true,
        shared: { audio_encoder: 'copy', subtitle_mode: 'all' },
        tiers: {
            dvd: { video_encoder: 'x265', video_quality: 22 },
            bluray: { video_encoder: 'x265', video_quality: 22 },
            uhd: { video_encoder: 'x265', video_quality: 22 }
        }
    }
];

describe('PresetEditor', () => {
    afterEach(() => cleanup());

    it('renders the active scheme name in the header', () => {
        renderComponent(PresetEditor, {
            props: {
                scope: 'global',
                initialState: { preset_slug: 'software_balanced', overrides: { shared: {}, tiers: {} } },
                scheme: mockScheme,
                presets: mockPresets,
                offline: false,
                saving: false,
                onSave: async () => {}
            }
        });
        expect(screen.getByText(/Software \(CPU\)/i)).toBeInTheDocument();
    });
});

const customPreset: Preset = {
    slug: 'my-custom', name: 'My Custom', scheme: 'software',
    description: '', builtin: false, parent_slug: 'software_balanced',
    shared: {}, tiers: { dvd: {}, bluray: {}, uhd: {} }
};

const unavailablePreset: Preset = {
    slug: 'nvidia-imp', name: 'Nvidia Import', scheme: 'nvidia',
    description: '', builtin: false, parent_slug: 'nvidia_balanced',
    shared: {}, tiers: { dvd: {}, bluray: {}, uhd: {} },
    unavailable: true, reason: 'scheme mismatch'
};

describe('PresetEditor dropdown', () => {
    afterEach(() => cleanup());

    const baseProps = {
        scope: 'global' as const,
        initialState: { preset_slug: 'software_balanced', overrides: { shared: {}, tiers: {} } },
        scheme: mockScheme,
        offline: false,
        saving: false,
        onSave: async () => {}
    };

    it('renders built-in, custom, and unavailable groups', () => {
        renderComponent(PresetEditor, {
            props: { ...baseProps, presets: [...mockPresets, customPreset, unavailablePreset] }
        });
        expect(screen.getByRole('option', { name: /Balanced/ })).toBeInTheDocument();
        expect(screen.getByRole('option', { name: /My Custom/ })).toBeInTheDocument();
        const unavail = screen.getByRole('option', { name: /Nvidia Import/ }) as HTMLOptionElement;
        expect(unavail.disabled).toBe(true);
    });

    it('shows preset description below the dropdown', () => {
        renderComponent(PresetEditor, { props: { ...baseProps, presets: mockPresets } });
        expect(screen.getByText(/Balanced encoding/)).toBeInTheDocument();
    });

    it('updates selectedSlug when dropdown changes', async () => {
        const second: Preset = { ...mockPresets[0], slug: 'software_quality', name: 'Quality' };
        const { container } = renderComponent(PresetEditor, { props: { ...baseProps, presets: [mockPresets[0], second] } });
        const select = container.querySelector('#preset-select') as HTMLSelectElement;
        await fireEvent.change(select, { target: { value: 'software_quality' } });
        expect(select.value).toBe('software_quality');
    });
});

describe('PresetEditor customize panel', () => {
    afterEach(() => cleanup());

    const props = {
        scope: 'global' as const,
        initialState: { preset_slug: 'software_balanced', overrides: { shared: {}, tiers: {} } },
        scheme: mockScheme,
        presets: mockPresets,
        offline: false,
        saving: false,
        onSave: async () => {}
    };

    it('renders Shared row with audio_encoder and subtitle_mode dropdowns', () => {
        renderComponent(PresetEditor, { props });
        expect(screen.getByText(/Audio encoder/i)).toBeInTheDocument();
        expect(screen.getByText(/Subtitle mode/i)).toBeInTheDocument();
    });

    it('renders three tier sections', () => {
        renderComponent(PresetEditor, { props });
        expect(screen.getByText(/^DVD/)).toBeInTheDocument();
        expect(screen.getByText(/Blu-ray/)).toBeInTheDocument();
        expect(screen.getByText(/^UHD/)).toBeInTheDocument();
    });

    it('only shows scheme-supported encoders (no nvenc options)', () => {
        renderComponent(PresetEditor, { props });
        // mockScheme has x265 and x264 only - no nvenc options should appear
        expect(screen.queryByRole('option', { name: /nvenc/i })).toBeNull();
    });

    it('writes to overrides.tiers[tier][key] when a tier field changes', async () => {
        const { container } = renderComponent(PresetEditor, { props });
        const qualityInput = container.querySelector('input[data-testid="tier-bluray-quality"]') as HTMLInputElement;
        expect(qualityInput).toBeTruthy();
        await fireEvent.input(qualityInput, { target: { value: '18' } });
        // Visual: dirty pill should show "1 change"
        expect(screen.getByText(/1 change/i)).toBeInTheDocument();
    });

    it('writes to overrides.shared[key] when shared field changes', async () => {
        const { container } = renderComponent(PresetEditor, { props });
        // The audio encoder select is the first select inside the Shared section
        const allSelects = container.querySelectorAll('label > div > select');
        const audioEncoderSelect = allSelects[0] as HTMLSelectElement;
        await fireEvent.change(audioEncoderSelect, { target: { value: 'aac' } });
        expect(screen.getByText(/1 change/i)).toBeInTheDocument();
    });

    it('renders advanced enum fields per scheme.advanced_fields', () => {
        const schemeWithAdvanced: Scheme = {
            ...mockScheme,
            advanced_fields: {
                x265_preset: {
                    type: 'enum',
                    values: ['ultrafast', 'medium', 'placebo'],
                    default: 'medium',
                    description: 'x265 speed/quality tradeoff'
                }
            }
        };
        renderComponent(PresetEditor, { props: { ...props, scheme: schemeWithAdvanced } });
        // The label text from the advanced field key should appear (one per tier = 3 occurrences)
        const labels = screen.getAllByText(/x265_preset/);
        expect(labels.length).toBeGreaterThanOrEqual(3);
        // The description should appear
        expect(screen.getAllByText(/speed\/quality tradeoff/).length).toBeGreaterThanOrEqual(1);
    });
});

describe('PresetEditor save bar', () => {
    afterEach(() => cleanup());

    const baseProps = {
        scope: 'global' as const,
        initialState: { preset_slug: 'software_balanced', overrides: { shared: {}, tiers: {} } },
        scheme: mockScheme,
        presets: mockPresets,
        offline: false,
        saving: false
    };

    it('Save button disabled when not dirty and slug unchanged', () => {
        renderComponent(PresetEditor, { props: { ...baseProps, onSave: async () => {} } });
        const btn = screen.getByRole('button', { name: /Save changes/i }) as HTMLButtonElement;
        expect(btn.disabled).toBe(true);
    });

    it('Save button enabled when dirty', async () => {
        const { container } = renderComponent(PresetEditor, { props: { ...baseProps, onSave: async () => {} } });
        const qualityInput = container.querySelector('input[data-testid="tier-bluray-quality"]') as HTMLInputElement;
        await fireEvent.input(qualityInput, { target: { value: '18' } });
        const btn = screen.getByRole('button', { name: /Save changes/i }) as HTMLButtonElement;
        expect(btn.disabled).toBe(false);
    });

    it('calls onSave with current state when Save clicked', async () => {
        const onSave = vi.fn().mockResolvedValue(undefined);
        const { container } = renderComponent(PresetEditor, { props: { ...baseProps, onSave } });
        const qualityInput = container.querySelector('input[data-testid="tier-bluray-quality"]') as HTMLInputElement;
        await fireEvent.input(qualityInput, { target: { value: '18' } });
        await fireEvent.click(screen.getByRole('button', { name: /Save changes/i }));
        expect(onSave).toHaveBeenCalledWith(expect.objectContaining({
            preset_slug: 'software_balanced',
            overrides: expect.objectContaining({ tiers: expect.objectContaining({ bluray: { video_quality: 18 } }) })
        }));
    });

    it('Revert clears overrides', async () => {
        const { container } = renderComponent(PresetEditor, { props: { ...baseProps, onSave: async () => {} } });
        const qualityInput = container.querySelector('input[data-testid="tier-bluray-quality"]') as HTMLInputElement;
        await fireEvent.input(qualityInput, { target: { value: '18' } });
        expect(screen.getByText(/1 change/i)).toBeInTheDocument();
        await fireEvent.click(screen.getByRole('button', { name: /Revert/i }));
        expect(screen.queryByText(/^\d+ changes?$/i)).toBeNull();
    });

    it('hides "Save as new preset" when scope=job', () => {
        renderComponent(PresetEditor, { props: { ...baseProps, scope: 'job', onSave: async () => {} } });
        expect(screen.queryByText(/Save as new preset/i)).toBeNull();
    });

    it('shows "Save as new preset" when scope=global with onSaveAsNew handler', () => {
        renderComponent(PresetEditor, { props: { ...baseProps, onSave: async () => {}, onSaveAsNew: async () => {} } });
        expect(screen.getByText(/Save as new preset/i)).toBeInTheDocument();
    });
});

describe('PresetEditor edge cases', () => {
    afterEach(() => cleanup());

    const baseProps = {
        scope: 'global' as const,
        initialState: { preset_slug: 'software_balanced', overrides: { shared: {}, tiers: {} } },
        scheme: mockScheme,
        presets: mockPresets,
        offline: false,
        onSave: async () => {}
    };

    it('disables form fields while saving=true', () => {
        const { container } = renderComponent(PresetEditor, { props: { ...baseProps, saving: true } });
        const select = container.querySelector('#preset-select') as HTMLSelectElement;
        expect(select.disabled).toBe(true);
    });

    it('shows offline banner when scheme is null', () => {
        const onRetry = vi.fn();
        renderComponent(PresetEditor, { props: { ...baseProps, scheme: null, presets: [], offline: true, saving: false, onRetry } });
        expect(screen.getByText(/Transcoder service unavailable/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Retry/i })).toBeInTheDocument();
    });

    it('Retry button calls onRetry callback', async () => {
        const onRetry = vi.fn();
        renderComponent(PresetEditor, { props: { ...baseProps, scheme: null, presets: [], offline: true, saving: false, onRetry } });
        await fireEvent.click(screen.getByRole('button', { name: /Retry/i }));
        expect(onRetry).toHaveBeenCalled();
    });

    it('disables Save and shows warning when selected preset is unavailable', () => {
        const propsWithUnavailable = {
            ...baseProps,
            saving: false,
            initialState: { preset_slug: 'nvidia-imp', overrides: { shared: {}, tiers: {} } },
            presets: [...mockPresets, unavailablePreset]
        };
        renderComponent(PresetEditor, { props: propsWithUnavailable });
        const btn = screen.getByRole('button', { name: /Save changes/i }) as HTMLButtonElement;
        expect(btn.disabled).toBe(true);
        expect(btn.title).toMatch(/not available/i);
    });

    it('shows undo toast for 5 seconds after dropdown switch with pending changes', async () => {
        vi.useFakeTimers();
        const second: Preset = { ...mockPresets[0], slug: 'software_quality', name: 'Quality' };
        const { container } = renderComponent(PresetEditor, { props: { ...baseProps, saving: false, presets: [mockPresets[0], second] } });
        const qualityInput = container.querySelector('input[data-testid="tier-bluray-quality"]') as HTMLInputElement;
        await fireEvent.input(qualityInput, { target: { value: '18' } });
        const select = container.querySelector('#preset-select') as HTMLSelectElement;
        await fireEvent.change(select, { target: { value: 'software_quality' } });
        expect(screen.getByText(/Cleared.*from/i)).toBeInTheDocument();
        vi.advanceTimersByTime(5500);
        await Promise.resolve();
        expect(screen.queryByText(/Cleared.*from/i)).toBeNull();
        vi.useRealTimers();
    });
});

describe('PresetEditor save-as-new flow', () => {
    afterEach(() => cleanup());

    const twoPresetScheme: Scheme = {
        ...mockScheme,
        slug: 'software',
    };
    const twoPresets: Preset[] = [
        ...mockPresets,
        {
            slug: 'software_quality', name: 'High Quality', scheme: 'software',
            description: 'Higher quality', builtin: true,
            shared: { audio_encoder: 'copy', subtitle_mode: 'all' },
            tiers: {
                dvd: { video_encoder: 'x265', video_quality: 18 },
                bluray: { video_encoder: 'x265', video_quality: 18 },
                uhd: { video_encoder: 'x265', video_quality: 20 }
            }
        }
    ];

    function renderWithSaveAs(onSaveAsNew: ReturnType<typeof vi.fn>) {
        return renderComponent(PresetEditor, {
            props: {
                scope: 'global' as const,
                initialState: { preset_slug: 'software_balanced', overrides: { shared: {}, tiers: {} } },
                scheme: twoPresetScheme,
                presets: twoPresets,
                offline: false,
                saving: false,
                onSave: async () => {},
                onSaveAsNew
            }
        });
    }

    async function makeDirty(container: HTMLElement) {
        const input = container.querySelector('input[data-testid="tier-bluray-quality"]') as HTMLInputElement;
        await fireEvent.input(input, { target: { value: '18' } });
    }

    it('Save as new preset button disabled until form is dirty', () => {
        const { getByRole } = renderWithSaveAs(vi.fn());
        const btn = getByRole('button', { name: /Save as new preset/i }) as HTMLButtonElement;
        expect(btn.disabled).toBe(true);
    });

    it('opens modal, creates preset, closes modal', async () => {
        const onSaveAsNew = vi.fn().mockResolvedValue(undefined);
        const { container, getByRole } = renderWithSaveAs(onSaveAsNew);
        await makeDirty(container);

        await fireEvent.click(getByRole('button', { name: /Save as new preset/i }));
        expect(screen.getByRole('dialog')).toBeInTheDocument();

        const nameInput = container.querySelector('input[placeholder*="Weekend Rips"]') as HTMLInputElement;
        await fireEvent.input(nameInput, { target: { value: 'My Preset' } });
        await fireEvent.click(getByRole('button', { name: /Create preset/i }));

        expect(onSaveAsNew).toHaveBeenCalledWith(expect.objectContaining({
            name: 'My Preset',
            parent_slug: 'software_balanced',
            overrides: expect.objectContaining({
                tiers: expect.objectContaining({ bluray: { video_quality: 18 } })
            })
        }));
    });

    it('shows error when onSaveAsNew throws', async () => {
        const onSaveAsNew = vi.fn().mockRejectedValue(new Error('Slug already exists'));
        const { container, getByRole } = renderWithSaveAs(onSaveAsNew);
        await makeDirty(container);
        await fireEvent.click(getByRole('button', { name: /Save as new preset/i }));
        const nameInput = container.querySelector('input[placeholder*="Weekend Rips"]') as HTMLInputElement;
        await fireEvent.input(nameInput, { target: { value: 'Dup' } });
        await fireEvent.click(getByRole('button', { name: /Create preset/i }));
        await screen.findByText(/Slug already exists/);
    });

    it('Cancel closes modal without calling handler', async () => {
        const onSaveAsNew = vi.fn();
        const { container, getByRole } = renderWithSaveAs(onSaveAsNew);
        await makeDirty(container);
        await fireEvent.click(getByRole('button', { name: /Save as new preset/i }));
        await fireEvent.click(getByRole('button', { name: /Cancel/i }));
        expect(screen.queryByRole('dialog')).toBeNull();
        expect(onSaveAsNew).not.toHaveBeenCalled();
    });

    it('Create preset button disabled until name is entered', async () => {
        const { container, getByRole } = renderWithSaveAs(vi.fn());
        await makeDirty(container);
        await fireEvent.click(getByRole('button', { name: /Save as new preset/i }));
        const createBtn = getByRole('button', { name: /Create preset/i }) as HTMLButtonElement;
        expect(createBtn.disabled).toBe(true);
        const nameInput = container.querySelector('input[placeholder*="Weekend Rips"]') as HTMLInputElement;
        await fireEvent.input(nameInput, { target: { value: 'Foo' } });
        expect(createBtn.disabled).toBe(false);
    });
});

describe('PresetEditor undo', () => {
    afterEach(() => cleanup());

    const twoPresets: Preset[] = [
        ...mockPresets,
        {
            slug: 'software_quality', name: 'High Quality', scheme: 'software',
            description: '', builtin: true,
            shared: { audio_encoder: 'copy', subtitle_mode: 'all' },
            tiers: {
                dvd: { video_encoder: 'x265', video_quality: 18 },
                bluray: { video_encoder: 'x265', video_quality: 18 },
                uhd: { video_encoder: 'x265', video_quality: 20 }
            }
        }
    ];

    it('Undo restores the previous preset and overrides', async () => {
        const { container } = renderComponent(PresetEditor, {
            props: {
                scope: 'global' as const,
                initialState: { preset_slug: 'software_balanced', overrides: { shared: {}, tiers: {} } },
                scheme: mockScheme,
                presets: twoPresets,
                offline: false,
                saving: false,
                onSave: async () => {}
            }
        });
        // Make a change
        const qInput = container.querySelector('input[data-testid="tier-bluray-quality"]') as HTMLInputElement;
        await fireEvent.input(qInput, { target: { value: '17' } });
        // Switch preset to trigger the undo toast
        const select = container.querySelector('#preset-select') as HTMLSelectElement;
        await fireEvent.change(select, { target: { value: 'software_quality' } });
        expect(select.value).toBe('software_quality');
        // Click Undo
        await fireEvent.click(screen.getByRole('button', { name: /Undo/i }));
        expect(select.value).toBe('software_balanced');
        // Toast cleared
        expect(screen.queryByText(/Cleared.*from/i)).toBeNull();
    });
});
