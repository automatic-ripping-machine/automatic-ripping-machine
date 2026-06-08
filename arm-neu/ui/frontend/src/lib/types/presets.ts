/**
 * Frontend-only composition over generated `Overrides`.
 *
 * `PresetEditorState` is the in-memory shape the PresetEditor component
 * passes around; nothing on the wire requires it (the BFF-side
 * `PresetCreateRequest` and `PresetUpdateRequest` both already exist
 * in api.gen.ts). Kept here as a thin alias rather than re-emitted
 * from the BFF to avoid a one-shot endpoint just for codegen.
 */
import type { Overrides } from '$lib/types/api.gen';

export interface PresetEditorState {
    preset_slug: string;
    overrides: Overrides;
}
