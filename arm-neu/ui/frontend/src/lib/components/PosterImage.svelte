<script lang="ts">
	import { posterSrc } from '$lib/utils/poster';

	interface Props {
		url: string | null | undefined;
		alt?: string;
		class?: string;
		style?: string;
	}

	let { url, alt = '', class: className = 'h-28 w-20 shrink-0 rounded-sm object-cover', style: styleStr = '' }: Props = $props();

	let errored = $state(false);
	let lastUrl: string | null | undefined = url;

	// Reset error state only when the url value actually changes
	$effect(() => {
		if (url !== lastUrl) {
			lastUrl = url;
			errored = false;
		}
	});

	const showFallback = $derived(!url || errored);

	function onError() {
		errored = true;
	}
</script>

{#if showFallback}
	<div class="flex items-center justify-center rounded-sm bg-blue-100 text-blue-400 dark:bg-blue-900/30 dark:text-blue-500 {className}" style={styleStr || undefined}>
		<svg class="h-2/5 w-2/5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
			<circle cx="12" cy="12" r="10" />
			<circle cx="12" cy="12" r="3" />
			<circle cx="12" cy="12" r="6.5" stroke-width="0.75" opacity="0.4" />
		</svg>
	</div>
{:else}
	<img
		src={posterSrc(url)}
		{alt}
		class={className}
		style={styleStr || undefined}
		loading="lazy"
		onerror={onError}
	/>
{/if}
