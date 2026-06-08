<script lang="ts">
	import type { Channel } from '$lib/types/notifications';
	import { ChevronRight, Send } from 'lucide-svelte';
	import StatusDot from './StatusDot.svelte';
	import ServiceGlyph from './ServiceGlyph.svelte';
	import Toggle from './Toggle.svelte';
	import { channelStatus, relativeTime, typeLabel } from './channelHelpers';

	let {
		channel,
		serviceName,
		expanded = false,
		ontoggle,
		ontest,
		onexpand
	}: {
		channel: Channel;
		serviceName: string;
		expanded?: boolean;
		ontoggle?: () => void;
		ontest?: () => void;
		onexpand?: () => void;
	} = $props();

	const status = $derived(channelStatus(channel));
	const secondary = $derived(
		`${typeLabel(channel.type)} · ${channel.subscribed_events.length} events`
	);
</script>

<div
	class="grid cursor-pointer grid-cols-[44px_1fr_110px_64px_64px] items-center gap-4 px-4 py-3 hover:bg-primary/5"
	role="button"
	tabindex="0"
	onclick={() => onexpand?.()}
	onkeydown={(e) => { if (e.key === 'Enter') onexpand?.(); }}
>
	<div class="flex items-center gap-2">
		<StatusDot {status} />
		{#if channel.type === 'apprise'}
			<ServiceGlyph id={(channel.config as { url?: string }).url ?? channel.name} name={serviceName} />
		{:else}
			<span class="inline-flex h-7 w-7 items-center justify-center rounded-md border border-white/5 font-mono text-xs {channel.type === 'webhook' ? 'bg-blue-500/20 text-blue-300' : 'bg-amber-500/20 text-amber-300'}">{channel.type === 'webhook' ? '{}' : '$_'}</span>
		{/if}
	</div>

	<div class="min-w-0">
		<p class="truncate text-sm font-medium text-gray-900 dark:text-white">{channel.name}</p>
		<p class="truncate text-xs text-gray-500 dark:text-gray-400">
			{secondary}{#if channel.last_error}<span class="text-status-error"> · {channel.last_error}</span>{/if}
		</p>
	</div>

	<div class="hidden text-right md:block">
		<p class="font-mono text-xs text-gray-600 dark:text-gray-300">{relativeTime(channel.last_fired_at)}</p>
	</div>

	<div class="flex justify-center" onclick={(e) => e.stopPropagation()} onkeydown={(e) => e.stopPropagation()} role="presentation">
		<Toggle checked={channel.enabled} label="Enabled" onchange={() => ontoggle?.()} />
	</div>

	<div class="flex items-center justify-center gap-1">
		<button
			type="button"
			aria-label="Send test"
			onclick={(e) => { e.stopPropagation(); ontest?.(); }}
			class="rounded p-1.5 text-gray-500 hover:bg-primary/10 hover:text-primary"
		>
			<Send size={14} />
		</button>
		<button
			type="button"
			aria-label={expanded ? 'Collapse' : 'Expand'}
			aria-expanded={expanded}
			onclick={(e) => { e.stopPropagation(); onexpand?.(); }}
			class="rounded p-1.5 text-gray-500 hover:bg-primary/10 hover:text-primary"
		>
			<ChevronRight size={16} class="transform transition-transform {expanded ? 'rotate-90' : ''}" />
		</button>
	</div>
</div>
