<script lang="ts">
	import { onMount } from 'svelte';

	interface Props {
		startTime: string;
		waitSeconds: number;
		paused?: boolean;
		/** Render with white text/track for use on colored backgrounds */
		inverted?: boolean;
		onpause?: () => void;
		onresume?: () => void;
	}

	let { startTime, waitSeconds, paused = false, inverted = false, onpause, onresume }: Props = $props();

	let now = $state(Date.now());
	let deadline = $derived(new Date(startTime).getTime() + waitSeconds * 1000);
	let remaining = $derived(Math.max(0, Math.ceil((deadline - now) / 1000)));
	let minutes = $derived(Math.floor(remaining / 60));
	let seconds = $derived(remaining % 60);
	let progress = $derived(
		waitSeconds > 0 ? Math.min(1, Math.max(0, 1 - remaining / waitSeconds)) : 1
	);
	let expired = $derived(remaining <= 0);

	function handleClick() {
		if (paused) {
			onresume?.();
		} else {
			onpause?.();
		}
	}

	onMount(() => {
		const id = setInterval(() => {
			if (!paused) {
				now = Date.now();
			}
		}, 1000);
		return () => clearInterval(id);
	});
</script>

<div class="flex items-center gap-2">
	<button
		type="button"
		onclick={handleClick}
		class="flex h-5 w-5 shrink-0 items-center justify-center rounded-full transition-colors
			{inverted
			? 'text-on-primary/90 hover:bg-white/20'
			: 'text-primary-text hover:bg-primary/15 dark:text-primary-text-dark dark:hover:bg-primary/20'}"
		title={paused ? 'Resume timer' : 'Pause timer'}
	>
		{#if paused}
			<!-- Play icon -->
			<svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="currentColor">
				<path d="M8 5v14l11-7z" />
			</svg>
		{:else}
			<!-- Pause icon -->
			<svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="currentColor">
				<path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
			</svg>
		{/if}
	</button>

	{#if paused}
		<span class="text-sm font-medium {inverted ? 'text-on-primary/90' : 'text-primary-text dark:text-primary-text-dark'}">Paused</span>
	{:else if expired}
		<span class="text-sm font-medium {inverted ? 'text-on-primary/90' : 'text-primary-text dark:text-primary-text-dark'}">Auto-proceeding...</span>
	{:else}
		<span class="text-sm font-medium tabular-nums {inverted ? 'text-on-primary' : 'text-primary-text dark:text-primary-text-dark'}">
			{minutes}m {String(seconds).padStart(2, '0')}s
		</span>
		<div class="h-1.5 w-20 overflow-hidden rounded-full {inverted ? 'bg-on-primary/25' : 'bg-primary/15 dark:bg-primary/15'}">
			<div
				data-progress-fill
				class="h-full rounded-full transition-all duration-1000 {inverted ? 'bg-on-primary/80' : 'bg-primary dark:bg-primary-border'}"
				style="width: {progress * 100}%"
			></div>
		</div>
	{/if}
</div>
