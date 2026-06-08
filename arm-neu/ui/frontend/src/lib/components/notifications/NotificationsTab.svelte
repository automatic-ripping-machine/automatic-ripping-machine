<script lang="ts">
	import type { Channel, Catalog, ChannelCreate, AppriseConfig } from '$lib/types/notifications';
	import {
		fetchChannels, fetchServices, createChannel, updateChannel,
		deleteChannel, testSendChannel, fetchDispatch, composeUrl, testConfig
	} from '$lib/api/channels';
	import { addToast } from '$lib/stores/toast.svelte';
	import StatStrip from './StatStrip.svelte';
	import FilterPills, { type ChannelFilter } from './FilterPills.svelte';
	import ChannelList from './ChannelList.svelte';
	import AddChannelForm, { type AddChannelBody } from './AddChannelForm.svelte';
	import type { EditorBody } from './ChannelEditor.svelte';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';

	let channels = $state<Channel[]>([]);
	let catalog = $state<Catalog>({ featured: [], services: [] });
	let loaded = $state(false);
	let loadError = $state<string | null>(null);
	let addOpen = $state(false);
	let expandedId = $state<number | null>(null);
	let filter = $state<ChannelFilter>('all');
	let deleteTarget = $state<Channel | null>(null);

	$effect(() => { load(); });

	async function load() {
		try {
			const [chans, cat] = await Promise.all([fetchChannels(), fetchServices()]);
			channels = chans;
			catalog = cat;
			loaded = true;
		} catch (e) {
			loadError = e instanceof Error ? e.message : 'Failed to load channels';
		}
	}

	const counts = $derived({
		total: channels.length,
		issues: channels.filter((c) => c.last_error).length,
		subscribedEvents: new Set(channels.flatMap((c) => c.subscribed_events)).size
	});
	const filterCounts = $derived({
		all: channels.length,
		enabled: channels.filter((c) => c.enabled).length,
		paused: channels.filter((c) => !c.enabled).length,
		issues: channels.filter((c) => c.last_error).length
	});
	const visible = $derived(channels.filter((c) =>
		filter === 'all' ? true :
		filter === 'enabled' ? c.enabled :
		filter === 'paused' ? !c.enabled :
		!!c.last_error
	));

	function serviceNameFor(c: Channel): string {
		return c.type === 'apprise' ? 'Service' : c.type;
	}

	async function toConfig(body: { type: string; config: Record<string, unknown>; serviceId: string | null }) {
		if (body.type === 'apprise' && body.serviceId) {
			// neu composes the url server-side from {service_id, fields}.
			return { type: 'apprise', url: '', service_id: body.serviceId, fields: body.config };
		}
		return { type: body.type, ...body.config };
	}

	async function handleAdd(body: AddChannelBody) {
		try {
			const config = await toConfig(body);
			const payload: ChannelCreate = {
				type: body.type, name: body.name, enabled: body.enabled,
				config: config as ChannelCreate['config'],
				subscribed_events: body.subscribed_events,
				templates: body.templates
			};
			const created = await createChannel(payload);
			channels = [created, ...channels];
			addOpen = false;
			addToast({ tone: 'success', title: 'Channel added', body: `${created.name} is now listening for events.` });
		} catch (e) {
			addToast({ tone: 'error', title: 'Add failed', body: e instanceof Error ? e.message : 'Unknown error' });
		}
	}

	async function handleToggle(c: Channel) {
		const next = !c.enabled;
		channels = channels.map((x) => (x.id === c.id ? { ...x, enabled: next } : x));
		try {
			await updateChannel(c.id, { enabled: next });
			addToast({ tone: 'info', title: next ? `Enabled ${c.name}` : `Paused ${c.name}` });
		} catch {
			channels = channels.map((x) => (x.id === c.id ? { ...x, enabled: c.enabled } : x));
			addToast({ tone: 'error', title: 'Update failed', body: c.name });
		}
	}

	// Has the editor changed the apprise field map vs what's stored? When
	// false the editor handlers omit `config` from the PATCH (save) or
	// fall through to the saved-channel test path so neu keeps the
	// stored url + recompose state intact.
	function appriseFieldsDirty(c: Channel, body: EditorBody): boolean {
		const stored = ((c.config as AppriseConfig).fields ?? {}) as Record<string, unknown>;
		return JSON.stringify(body.appriseFields) !== JSON.stringify(stored);
	}

	async function handleEditorSave(c: Channel, body: EditorBody) {
		try {
			const patch: Record<string, unknown> = {
				name: body.name,
				enabled: body.enabled,
				subscribed_events: body.subscribed_events,
				templates: body.templates
			};
			if (c.type === 'apprise') {
				if (appriseFieldsDirty(c, body) && body.serviceId) {
					patch.config = {
						type: 'apprise',
						url: '',
						service_id: body.serviceId,
						fields: body.appriseFields
					};
				}
				// not dirty -> omit config -> neu keeps stored url + fields
			} else {
				patch.config = body.config as unknown as Channel['config'];
			}
			const updated = await updateChannel(c.id, patch as Parameters<typeof updateChannel>[1]);
			channels = channels.map((x) => (x.id === c.id ? updated : x));
			addToast({ tone: 'success', title: 'Saved.' });
		} catch (e) {
			addToast({ tone: 'error', title: 'Save failed', body: e instanceof Error ? e.message : '' });
		}
	}

	async function handleTestSaved(c: Channel) {
		addToast({ tone: 'info', title: `Sending test to ${c.name}…` });
		try {
			const { dispatch_id } = await testSendChannel(c.id, c.subscribed_events[0] ?? 'job.started');
			// Poll up to ~5s for a terminal status.
			for (let i = 0; i < 10; i++) {
				await new Promise((r) => setTimeout(r, 500));
				const status = await fetchDispatch(dispatch_id);
				if (status.status === 'success') {
					addToast({ tone: 'success', title: 'Test delivered' });
					return;
				}
				if (status.status === 'failed') {
					addToast({ tone: 'error', title: 'Test failed', body: status.last_error ?? '' });
					return;
				}
			}
			addToast({ tone: 'info', title: 'Test still pending', body: 'Check delivery status shortly.' });
		} catch (e) {
			addToast({ tone: 'error', title: 'Test failed', body: e instanceof Error ? e.message : '' });
		}
	}

	// Test an unsaved/edited config and toast the result. Shared by the add-form
	// and the inline editor so the success/error toast handling lives in one place.
	async function testConfigAndToast(type: string, config: Record<string, unknown>, eventKey: string) {
		const res = await testConfig({ type, config, event_key: eventKey });
		if (res.ok) addToast({ tone: 'success', title: 'Test delivered' });
		else addToast({ tone: 'error', title: 'Test failed', body: res.error ?? '' });
	}

	async function handleTestUnsaved(body: AddChannelBody) {
		try {
			const config = await toConfig(body);
			await testConfigAndToast(body.type, config, body.subscribed_events[0] ?? 'job.started');
		} catch (e) {
			addToast({ tone: 'error', title: 'Test failed', body: e instanceof Error ? e.message : '' });
		}
	}

	async function handleEditorTest(c: Channel, body: EditorBody) {
		const eventKey = body.subscribed_events[0] ?? 'job.started';
		try {
			if (c.type === 'apprise') {
				if (appriseFieldsDirty(c, body)) {
					const res = await testConfig({
						channel_id: c.id,
						fields: body.appriseFields,
						event_key: eventKey
					});
					if (res.ok) addToast({ tone: 'success', title: 'Test delivered' });
					else addToast({ tone: 'error', title: 'Test failed', body: res.error ?? '' });
					return;
				}
				// Fields unchanged: test the saved channel instead.
				await handleTestSaved(c);
				return;
			}
			// Webhook/bash: test the edited config directly via the unsaved-config
			// endpoint so the user tests their current edits, not the last-saved state.
			await testConfigAndToast(c.type, body.config, eventKey);
		} catch (e) {
			addToast({ tone: 'error', title: 'Test failed', body: e instanceof Error ? e.message : '' });
		}
	}

	async function confirmDelete() {
		const c = deleteTarget;
		if (!c) return;
		deleteTarget = null;
		try {
			await deleteChannel(c.id);
			channels = channels.filter((x) => x.id !== c.id);
			if (expandedId === c.id) expandedId = null;
			addToast({ tone: 'info', title: `Deleted ${c.name}` });
		} catch (e) {
			addToast({ tone: 'error', title: 'Delete failed', body: e instanceof Error ? e.message : '' });
		}
	}

	function toggleExpand(c: Channel) { expandedId = expandedId === c.id ? null : c.id; }
</script>

<div class="space-y-5">
	<div>
		<h2 class="text-lg font-semibold text-gray-900 dark:text-white">Notifications</h2>
		<p class="text-sm text-gray-500 dark:text-gray-400">Manage notification channels — Discord, Slack, webhooks, scripts, and more.</p>
	</div>

	{#if loadError}
		<p class="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-500/40 dark:bg-red-900/20 dark:text-red-300">{loadError}</p>
	{:else if !loaded}
		<div class="py-8 text-center text-gray-400">Loading channels…</div>
	{:else}
		<StatStrip total={counts.total} issues={counts.issues} subscribedEvents={counts.subscribedEvents} />

		{#if addOpen}
			<AddChannelForm {catalog} onsave={handleAdd} oncancel={() => (addOpen = false)} ontest={handleTestUnsaved} />
		{/if}

		{#if channels.length > 0}
			<div class="flex items-center justify-between gap-3 rounded-lg border border-primary/15 bg-page px-4 py-3 dark:border-primary/20 dark:bg-primary/5">
				<FilterPills active={filter} counts={filterCounts} onselect={(f) => (filter = f)} />
				{#if !addOpen}
					<button type="button" onclick={() => (addOpen = true)} class="rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-on-primary hover:bg-primary-hover">+ Add channel</button>
				{/if}
			</div>
			<ChannelList
				channels={visible}
				{catalog}
				{expandedId}
				{serviceNameFor}
				ontoggle={handleToggle}
				ontest={handleTestSaved}
				onexpand={toggleExpand}
				oneditorsave={handleEditorSave}
				oneditortest={handleEditorTest}
				ondelete={(c) => (deleteTarget = c)}
			/>
		{:else if !addOpen}
			<div class="rounded-lg border border-primary/15 bg-page p-8 text-center dark:border-primary/20 dark:bg-primary/5">
				<p class="text-sm font-semibold text-primary">No notification channels yet</p>
				<p class="mt-1 text-sm text-gray-600 dark:text-gray-300">Add one to start receiving alerts for rip and transcode events.</p>
				<button type="button" onclick={() => (addOpen = true)} class="mt-4 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-on-primary hover:bg-primary-hover">Add your first channel</button>
			</div>
		{/if}
	{/if}
</div>

<ConfirmDialog
	open={deleteTarget !== null}
	title="Delete channel?"
	message={deleteTarget ? `${deleteTarget.name} will be removed and stop receiving events. This cannot be undone.` : ''}
	confirmLabel="Delete"
	variant="danger"
	onconfirm={confirmDelete}
	oncancel={() => (deleteTarget = null)}
/>
