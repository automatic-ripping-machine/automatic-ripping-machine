<script lang="ts">
	import type { ChannelTemplate } from '$lib/types/notifications';
	import TemplateEditor from '../TemplateEditor.svelte';

	let {
		subscribedEvents,
		templates = $bindable()
	}: { subscribedEvents: string[]; templates: Record<string, ChannelTemplate> } = $props();
</script>

<div class="rounded-lg border border-primary/15 bg-page p-4 dark:border-primary/20 dark:bg-primary/5">
	<div class="mb-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-primary">Message templates</div>
	<p class="mb-3 text-xs text-gray-500 dark:text-gray-400">Optional — leave blank to use defaults.</p>
	{#if subscribedEvents.length === 0}
		<p class="py-4 text-center text-sm text-gray-500 dark:text-gray-400">No events subscribed. Pick at least one event above to customize templates.</p>
	{:else}
		<TemplateEditor {subscribedEvents} bind:templates />
	{/if}
</div>
