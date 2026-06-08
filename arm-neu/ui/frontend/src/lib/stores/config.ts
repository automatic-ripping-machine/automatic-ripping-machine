import { writable } from 'svelte/store';
import { fetchConfig } from '$lib/api/config';

const _transcoderEnabled = writable<boolean>(true);

export const transcoderEnabled = { subscribe: _transcoderEnabled.subscribe };

export function setTranscoderEnabled(value: boolean): void {
	_transcoderEnabled.set(value);
}

export async function hydrateConfig(): Promise<void> {
	try {
		const cfg = await fetchConfig();
		_transcoderEnabled.set(cfg.transcoder_enabled);
	} catch {
		_transcoderEnabled.set(true);
	}
}
