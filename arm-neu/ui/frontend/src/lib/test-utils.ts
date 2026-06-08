import { render } from '@testing-library/svelte';

export { screen, fireEvent, within, waitFor, cleanup } from '@testing-library/svelte';

// Thin wrapper — extensible for future context providers or global setup.
// Uses permissive types to avoid Svelte 5 component type mismatches with
// @testing-library/svelte v5 internals.
export function renderComponent(
	component: any,
	options: Record<string, unknown> = {}
) {
	return render(component, options);
}
