<script lang="ts">
	import type { Channel, Catalog, CatalogService, ChannelTemplate, AppriseConfig } from '$lib/types/notifications';
	import ConfigureSection from './sections/ConfigureSection.svelte';
	import EventsSection from './sections/EventsSection.svelte';
	import TemplatesSection from './sections/TemplatesSection.svelte';

	export interface EditorBody {
		name: string;
		enabled: boolean;
		config: Record<string, unknown>;
		subscribed_events: string[];
		templates: Record<string, ChannelTemplate>;
		appriseFields: Record<string, unknown>;
		serviceId: string | null;
	}

	let {
		channel,
		catalog,
		onsave,
		ontest,
		onclose,
		ondelete
	}: {
		channel: Channel;
		catalog: Catalog;
		onsave: (body: EditorBody) => void;
		ontest: (body: EditorBody) => void;
		onclose: () => void;
		ondelete: () => void;
	} = $props();

	let name = $state(channel.name);
	let enabled = $state(channel.enabled);
	let config = $state<Record<string, unknown>>({ ...channel.config });
	let events = $state<string[]>([...channel.subscribed_events]);
	let templates = $state<Record<string, ChannelTemplate>>({ ...channel.templates });

	// Apprise channels store config.service_id, so resolve the service from the
	// loaded catalog to render the per-service re-entry fields.
	const serviceId = $derived(
		channel.type === 'apprise'
			? ((channel.config as AppriseConfig).service_id ?? null)
			: null
	);
	const service = $derived<CatalogService | null>(
		serviceId ? catalog.services.find((s) => s.id === serviceId) ?? null : null
	);
	const unknownService = $derived(
		channel.type === 'apprise' && serviceId !== null && service === null
	);

	// Apprise re-entry values live in a separate state from config (which holds the
	// composed url + service_id). Seed from stored fields so private values show as
	// <hidden> (SchemaField renders that as empty + placeholder), and non-private
	// values are pre-filled. Empty appriseFields = keep current destination.
	let appriseFields = $state<Record<string, unknown>>({
		...((channel.config as AppriseConfig).fields ?? {})
	});
	const noFields = $derived(
		channel.type === 'apprise' && !(channel.config as AppriseConfig).fields
	);
	const appriseTouched = $derived(
		Object.values(appriseFields).some((v) => v !== undefined && v !== null && String(v).trim() !== '')
	);

	const dirty = $derived(
		name !== channel.name ||
		enabled !== channel.enabled ||
		(channel.type !== 'apprise' && JSON.stringify(config) !== JSON.stringify(channel.config)) ||
		JSON.stringify(events) !== JSON.stringify(channel.subscribed_events) ||
		JSON.stringify(templates) !== JSON.stringify(channel.templates) ||
		appriseTouched
	);

	function body(): EditorBody {
		return { name, enabled, config, subscribed_events: events, templates, appriseFields, serviceId };
	}
</script>

<div class="space-y-4 border-t border-primary/20 px-4 py-4 dark:border-primary/20">
	{#if channel.type === 'apprise'}
		{#if unknownService}
			<p class="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-700 dark:border-amber-500/40 dark:bg-amber-900/20 dark:text-amber-300">
				Unknown service '{serviceId}' — recreate this channel to edit its destination.
			</p>
		{:else if noFields}
			<p class="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-700 dark:border-amber-500/40 dark:bg-amber-900/20 dark:text-amber-300">
				This channel was added via a raw URL. Delete and re-add it to edit its destination.
			</p>
		{:else}
			<ConfigureSection type="apprise" bind:name bind:enabled bind:config={appriseFields} {service} preserveExisting />
		{/if}
	{:else}
		<ConfigureSection type={channel.type} bind:name bind:enabled bind:config {service} />
	{/if}
	<EventsSection bind:selected={events} />
	<TemplatesSection subscribedEvents={events} bind:templates />

	<div class="flex flex-wrap items-center gap-2">
		<button type="button" disabled={!dirty} onclick={() => onsave(body())} class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-on-primary hover:bg-primary-hover disabled:opacity-40">Save changes</button>
		<button type="button" onclick={() => ontest(body())} class="rounded-md border border-primary/25 px-4 py-2 text-sm text-primary-text hover:bg-primary/10 dark:border-primary/30 dark:text-primary-text-dark">Send test</button>
		<button type="button" onclick={onclose} class="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-primary/10 dark:border-gray-600 dark:text-gray-300">Close</button>
		<button type="button" onclick={ondelete} class="ml-auto rounded-md border border-red-300 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 dark:border-red-500/40 dark:text-red-400 dark:hover:bg-red-900/20">Delete</button>
	</div>
</div>
