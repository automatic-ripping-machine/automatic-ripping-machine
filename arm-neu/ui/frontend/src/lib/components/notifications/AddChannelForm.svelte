<script lang="ts">
	import type { Catalog, CatalogService, ChannelType, ChannelTemplate } from '$lib/types/notifications';
	import ConfigureSection from './sections/ConfigureSection.svelte';
	import LabelEnabledRow from './sections/LabelEnabledRow.svelte';
	import EventsSection from './sections/EventsSection.svelte';
	import TemplatesSection from './sections/TemplatesSection.svelte';
	import ServiceDropdown from './ServiceDropdown.svelte';
	import { missingRequirements } from './channelHelpers';

	export interface AddChannelBody {
		type: ChannelType;
		name: string;
		enabled: boolean;
		config: Record<string, unknown>;
		subscribed_events: string[];
		templates: Record<string, ChannelTemplate>;
		serviceId: string | null;
	}

	let {
		catalog,
		onsave,
		oncancel,
		ontest
	}: {
		catalog: Catalog;
		onsave: (body: AddChannelBody) => void;
		oncancel: () => void;
		ontest: (body: AddChannelBody) => void;
	} = $props();

	let type = $state<ChannelType>('apprise');
	let serviceId = $state<string | null>(null);
	let name = $state('');
	let enabled = $state(true);
	let config = $state<Record<string, unknown>>({});
	let events = $state<string[]>([]);
	let templates = $state<Record<string, ChannelTemplate>>({});

	const service = $derived<CatalogService | null>(
		serviceId ? catalog.services.find((s) => s.id === serviceId) ?? null : null
	);

	const missing = $derived(missingRequirements({ type, name, config, events, service }));
	const ready = $derived(missing.length === 0);

	function setType(t: ChannelType) {
		type = t;
		config = {};
		if (t !== 'apprise') serviceId = null;
	}
	function pickService(id: string) {
		serviceId = id;
		config = {};
	}
	function body(): AddChannelBody {
		return { type, name, enabled, config, subscribed_events: events, templates, serviceId };
	}

	const types: { key: ChannelType; label: string; recommended?: boolean }[] = [
		{ key: 'apprise', label: 'Service (Apprise)', recommended: true },
		{ key: 'webhook', label: 'Webhook' },
		{ key: 'bash', label: 'Bash script' }
	];
</script>

<div class="rounded-xl border border-primary/25 bg-surface shadow-xl dark:border-primary/30 dark:bg-surface-dark">
	<div class="flex items-center justify-between border-b border-primary/20 px-5 py-4">
		<h3 class="text-sm font-semibold text-primary">Add notification channel</h3>
		<button type="button" onclick={oncancel} class="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300">✕ Cancel</button>
	</div>

	<div class="space-y-5 p-5">
		<fieldset class="relative grid grid-cols-1 gap-3 sm:grid-cols-3">
			<legend class="sr-only">Delivery type</legend>
			{#each types as t}
				<label class="relative flex cursor-pointer flex-col gap-1 rounded-lg border p-4 {type === t.key ? 'border-primary bg-primary/10' : 'border-primary/20 bg-page dark:bg-primary/5'}">
					<input type="radio" name="delivery" class="sr-only" aria-label={t.label} checked={type === t.key} onchange={() => setType(t.key)} />
					<span class="text-sm font-semibold text-gray-800 dark:text-gray-100">{t.label}</span>
					{#if t.recommended}<span class="absolute right-3 top-3 rounded bg-primary/15 px-1.5 py-0.5 text-[9.5px] tracking-wider text-primary">RECOMMENDED</span>{/if}
				</label>
			{/each}
		</fieldset>

		<LabelEnabledRow bind:name bind:enabled />

		{#if type === 'apprise'}
			<div class="rounded-lg border border-primary/15 bg-page p-4 dark:border-primary/20 dark:bg-primary/5">
				<ServiceDropdown {catalog} selectedId={serviceId} onpick={pickService} />
			</div>
		{/if}

		<ConfigureSection {type} bind:name bind:enabled bind:config {service} showLabelRow={false} />
		<EventsSection bind:selected={events} />
		<TemplatesSection subscribedEvents={events} bind:templates />
	</div>

	<div class="flex items-center justify-between border-t border-primary/20 px-5 py-3.5">
		<span class="text-xs {ready ? 'text-status-success' : 'text-gray-500 dark:text-gray-400'}">
			{ready ? '✓ Ready to save' : `Needs: ${missing.join(', ')}`}
		</span>
		<div class="flex gap-2">
			<button type="button" onclick={oncancel} class="rounded-md px-4 py-2 text-sm text-gray-600 hover:bg-primary/10 dark:text-gray-300">Cancel</button>
			<button type="button" onclick={() => ontest(body())} class="rounded-md border border-primary/25 px-4 py-2 text-sm text-primary-text hover:bg-primary/10 dark:border-primary/30 dark:text-primary-text-dark">Send test</button>
			<button type="button" disabled={!ready} onclick={() => onsave(body())} class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-on-primary hover:bg-primary-hover disabled:opacity-40">Save channel</button>
		</div>
	</div>
</div>
