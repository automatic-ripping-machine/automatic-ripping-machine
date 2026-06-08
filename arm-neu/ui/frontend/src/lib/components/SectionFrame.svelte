<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		variant?: 'full' | 'compact';
		accent?: string;
		label?: string;
		children: Snippet;
	}

	let { variant = 'full', accent = '#f90', label = '', children }: Props = $props();
</script>

<div class="section-frame" data-frame-variant={variant} style:--frame-accent={accent}>
	<div class="section-frame-bar section-frame-bar-top" aria-hidden="true">
		{#if label}<span>{label}</span>{/if}
	</div>
	{#if variant === 'full'}
		<div class="section-frame-sidebar" aria-hidden="true">
			<div class="section-frame-block section-frame-block-a"></div>
			<div class="section-frame-block section-frame-block-b"></div>
			<div class="section-frame-block section-frame-block-c"></div>
		</div>
	{/if}
	<div class="section-frame-body">
		{@render children()}
	</div>
	<div class="section-frame-bar section-frame-bar-bottom" aria-hidden="true"></div>
</div>
