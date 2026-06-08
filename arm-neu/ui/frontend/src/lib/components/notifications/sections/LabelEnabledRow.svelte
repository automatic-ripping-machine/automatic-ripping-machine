<script lang="ts">
	import { FIELD_INPUT_CLASS } from '$lib/types/notifications';
	import Toggle from '../Toggle.svelte';

	let {
		name = $bindable(),
		enabled = $bindable()
	}: { name: string; enabled: boolean } = $props();
</script>

<div class="grid grid-cols-[1fr_auto] items-end gap-4">
	<label class="flex flex-col gap-1">
		<span class="text-sm font-medium text-gray-700 dark:text-gray-300">Channel Label *</span>
		<input class={FIELD_INPUT_CLASS} aria-label="Channel Label" bind:value={name} required />
	</label>
	<div class="flex items-center gap-2 pb-2">
		<Toggle checked={enabled} label="Enabled" onchange={(v) => (enabled = v)} />
		<span class="text-sm text-gray-700 dark:text-gray-300">Enabled</span>
	</div>
</div>
