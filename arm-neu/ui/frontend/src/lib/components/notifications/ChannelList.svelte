<script lang="ts">
	import type { Channel, Catalog } from '$lib/types/notifications';
	import type { EditorBody } from './ChannelEditor.svelte';
	import ChannelRow from './ChannelRow.svelte';
	import ChannelEditor from './ChannelEditor.svelte';

	let {
		channels,
		catalog,
		expandedId,
		serviceNameFor,
		ontoggle,
		ontest,
		onexpand,
		oneditorsave,
		oneditortest,
		ondelete
	}: {
		channels: Channel[];
		catalog: Catalog;
		expandedId: number | null;
		serviceNameFor: (c: Channel) => string;
		ontoggle?: (c: Channel) => void;
		ontest?: (c: Channel) => void;
		onexpand?: (c: Channel) => void;
		oneditorsave?: (c: Channel, body: EditorBody) => void;
		oneditortest?: (c: Channel, body: EditorBody) => void;
		ondelete?: (c: Channel) => void;
	} = $props();
</script>

<div class="overflow-hidden rounded-xl border border-primary/20 bg-surface dark:border-primary/20 dark:bg-surface-dark">
	<div class="grid grid-cols-[44px_1fr_110px_64px_64px] gap-4 border-b border-primary/20 bg-page px-4 py-2 text-[10.5px] font-semibold uppercase tracking-[0.12em] text-gray-500 dark:bg-primary/5 dark:text-gray-400">
		<span></span><span>Channel</span><span class="hidden whitespace-nowrap text-right md:block">Last delivery</span><span class="text-center">Enabled</span><span class="text-center">Actions</span>
	</div>
	{#each channels as c (c.id)}
		<div class="border-b border-primary/15 last:border-0 dark:border-primary/20">
			<ChannelRow
				channel={c}
				serviceName={serviceNameFor(c)}
				expanded={expandedId === c.id}
				ontoggle={() => ontoggle?.(c)}
				ontest={() => ontest?.(c)}
				onexpand={() => onexpand?.(c)}
			/>
			{#if expandedId === c.id}
				<ChannelEditor
					channel={c}
					{catalog}
					onsave={(b) => oneditorsave?.(c, b)}
					ontest={(b) => oneditortest?.(c, b)}
					onclose={() => onexpand?.(c)}
					ondelete={() => ondelete?.(c)}
				/>
			{/if}
		</div>
	{/each}
</div>
