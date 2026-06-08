import { writable } from 'svelte/store';

/** Set to true to open the folder import wizard on the dashboard. */
export const showImportWizard = writable(false);
