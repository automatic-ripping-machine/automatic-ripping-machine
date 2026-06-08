<script lang="ts">
	import { toasts, dismissToast, type ToastTone } from '$lib/stores/toast.svelte';

	function toneClass(tone: ToastTone): string {
		if (tone === 'success') return 'border-status-success/40 text-status-success';
		if (tone === 'error') return 'border-status-error/40 text-status-error';
		return 'border-primary/40 text-primary';
	}
</script>

<div class="pointer-events-none fixed bottom-6 right-6 z-50 flex flex-col gap-2">
	{#each toasts.value as t (t.id)}
		<div
			class="pointer-events-auto flex min-w-[280px] max-w-[420px] items-start gap-3 rounded-lg border bg-surface px-4 py-3 shadow-xl dark:bg-surface-dark {toneClass(t.tone)}"
			role="status"
		>
			<div class="flex-1">
				<p class="text-sm font-semibold">{t.title}</p>
				{#if t.body}<p class="mt-0.5 text-xs opacity-80">{t.body}</p>{/if}
			</div>
			<button
				type="button"
				aria-label="Dismiss notification"
				onclick={() => dismissToast(t.id)}
				class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
			>×</button>
		</div>
	{/each}
</div>
