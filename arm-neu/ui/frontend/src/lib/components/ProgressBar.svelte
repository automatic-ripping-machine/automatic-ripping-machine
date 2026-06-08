<script lang="ts">
	interface Props {
		value: number;
		max?: number;
		color?: string;
		colorVar?: string | null;
		showLabel?: boolean;
	}

	let {
		value,
		max = 100,
		color = 'bg-primary',
		colorVar = null,
		showLabel = true
	}: Props = $props();
	let pct = $derived(Math.min(100, Math.max(0, (value / max) * 100)));
	let fillStyle = $derived(
		colorVar ? `width: ${pct}%; background: ${colorVar}` : `width: ${pct}%`
	);
	let fillClasses = $derived(
		colorVar ? 'h-2.5 rounded-full transition-all duration-500' : `h-2.5 rounded-full transition-all duration-500 ${color}`
	);
</script>

<div class="flex items-center gap-2">
	<div data-progress-track class="h-2.5 flex-1 rounded-full bg-primary/15 dark:bg-primary/15">
		<div data-progress-fill class={fillClasses} style={fillStyle}></div>
	</div>
	{#if showLabel}
		<span class="min-w-[3ch] text-right text-xs text-gray-500 dark:text-gray-400">
			{Math.round(pct)}%
		</span>
	{/if}
</div>
