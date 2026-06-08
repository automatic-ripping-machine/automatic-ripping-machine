import { redirect } from '@sveltejs/kit';
import { fetchSetupStatus } from '$lib/api/setup';

export async function load() {
	try {
		const status = await fetchSetupStatus();
		if (status.db_initialized && status.db_current && !status.first_run) {
			throw redirect(302, '/');
		}
		return { status };
	} catch (e) {
		// Re-throw redirects
		if (e && typeof e === 'object' && 'status' in e && (e as { status: number }).status === 302) {
			throw e;
		}
		return { status: null };
	}
}
