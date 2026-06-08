<script lang="ts">
	import type { ChannelStatus } from './channelHelpers';

	let { status }: { status: ChannelStatus } = $props();

	const cls = $derived(
		status === 'ok' ? 'bg-status-success shadow-[0_0_8px_rgba(52,211,153,0.6)]' :
		status === 'warn' ? 'bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.6)]' :
		status === 'error' ? 'bg-status-error shadow-[0_0_8px_rgba(248,113,113,0.6)]' :
		'bg-gray-500'
	);
</script>

<span class="inline-block h-2 w-2 shrink-0 rounded-full {cls}" title={status} aria-label={status}></span>
