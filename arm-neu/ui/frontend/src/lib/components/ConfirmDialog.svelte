<script lang="ts">
	interface Props {
		open: boolean;
		title: string;
		message: string;
		confirmLabel?: string;
		variant?: 'danger' | 'primary';
		onconfirm: () => void;
		oncancel: () => void;
	}

	let {
		open,
		title,
		message,
		confirmLabel = 'Confirm',
		variant = 'primary',
		onconfirm,
		oncancel
	}: Props = $props();

	let confirmClasses = $derived(
		variant === 'danger'
			? 'confirm-btn-danger'
			: 'confirm-btn-primary'
	);

	$effect(() => {
		if (!open) return;
		const onKeyDown = (e: KeyboardEvent) => {
			if (e.key === 'Escape') {
				oncancel();
			}
		};
		window.addEventListener('keydown', onKeyDown);
		return () => window.removeEventListener('keydown', onKeyDown);
	});
</script>

{#if open}
	<div class="fixed inset-0 z-50 flex items-center justify-center">
		<!-- Backdrop -->
		<button
			type="button"
			class="absolute inset-0 bg-black/50"
			aria-label="Close dialog"
			onclick={oncancel}
		></button>

		<!-- Dialog -->
		<div class="relative z-10 w-full max-w-md rounded-lg bg-surface p-6 shadow-xl dark:bg-surface-dark" data-dialog role="dialog" aria-modal="true" aria-labelledby="dialog-title">
			<h3 id="dialog-title" class="text-lg font-semibold text-gray-900 dark:text-white">{title}</h3>
			<p class="mt-2 text-sm text-gray-600 dark:text-gray-400">{message}</p>
			<div class="mt-4 flex justify-end gap-3">
				<button
					type="button"
					onclick={oncancel}
					class="rounded-lg px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
				>
					Cancel
				</button>
				<button
					type="button"
					onclick={onconfirm}
					class="rounded-lg px-4 py-2 text-sm font-medium {confirmClasses}"
				>
					{confirmLabel}
				</button>
			</div>
		</div>
	</div>
{/if}
