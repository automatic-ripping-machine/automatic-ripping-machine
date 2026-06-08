import { redirect } from '@sveltejs/kit';
import { get } from 'svelte/store';
import { transcoderEnabled } from '$lib/stores/config';
import type { PageLoad } from './$types';

export const load: PageLoad = async () => {
	if (!get(transcoderEnabled)) {
		throw redirect(302, '/');
	}
	return {};
};
