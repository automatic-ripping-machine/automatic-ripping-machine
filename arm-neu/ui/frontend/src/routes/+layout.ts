import { redirect } from '@sveltejs/kit';
import type { LayoutLoad } from './$types';
import { hydrateConfig } from '$lib/stores/config';

export const prerender = false;
export const ssr = false;

// Once setup is confirmed complete, stop checking on every navigation.
// Only a hard page refresh (F5) resets this, which is the correct behavior
// since completing setup or clearing the DB are deliberate actions.
let setupConfirmedComplete = false;

// Hydrate feature flags once per page load.
let configHydrated = false;

export const load: LayoutLoad = async ({ url, fetch }) => {
	if (!configHydrated) {
		await hydrateConfig();
		configHydrated = true;
	}

	// Skip setup check if already on /setup
	if (url.pathname.startsWith('/setup')) return {};

	// Skip if we already know setup is done (cached from a previous navigation)
	if (setupConfirmedComplete) return {};

	try {
		const resp = await fetch('/api/setup/status');
		if (resp.ok) {
			const status = await resp.json();
			if (status.first_run === true) {
				redirect(307, '/setup');
			}
			// Setup is complete - cache this so we don't re-check on every click
			setupConfirmedComplete = true;
		}
		// Non-ok response (503, etc.) - ARM unreachable, don't redirect
	} catch (e) {
		// Re-throw SvelteKit redirects (they use throw internally)
		if (e && typeof e === 'object' && 'status' in e && 'location' in e) throw e;
		// ARM unreachable - don't redirect, let the normal UI handle it
	}

	return {};
};
