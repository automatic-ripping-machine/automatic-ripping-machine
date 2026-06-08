<script lang="ts">
	import type { CatalogField } from '$lib/types/notifications';
	import { FIELD_INPUT_CLASS } from '$lib/types/notifications';

	let { field, value = $bindable() }: { field: CatalogField; value: unknown } = $props();

	const inputType = $derived(field.private ? 'password' : 'text');

	let boolValue = $derived(Boolean(value));

	const HIDDEN = '<hidden>';
	const isPrivateHidden = $derived(field.private && value === HIDDEN);
	const displayValue = $derived(isPrivateHidden ? '' : (value ?? ''));
	const placeholder = $derived(isPrivateHidden ? '•••••••• (set, leave blank to keep)' : '');

	function onInput(e: Event) {
		value = (e.currentTarget as HTMLInputElement).value;
	}
</script>

{#if field.type === 'bool'}
	<label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
		<input
			type="checkbox"
			aria-label={field.label}
			checked={boolValue}
			onchange={(e) => (value = e.currentTarget.checked)}
			class="rounded border-primary/40 text-primary focus:ring-primary"
		/>
		<span>{field.label}{field.required ? ' *' : ''}</span>
	</label>
{:else}
	<label class="flex flex-col gap-1">
		<span class="text-sm font-medium text-gray-700 dark:text-gray-300">{field.label}{field.required ? ' *' : ''}</span>
		{#if field.type === 'choice'}
			<select
				aria-label={field.label}
				bind:value
				required={field.required}
				class={FIELD_INPUT_CLASS}
			>
				{#each field.values ?? [] as opt}
					<option value={opt}>{opt}</option>
				{/each}
			</select>
		{:else if field.type === 'int' || field.type === 'float'}
			<input
				type="number"
				aria-label={field.label}
				step={field.type === 'float' ? 'any' : '1'}
				bind:value
				required={field.required}
				class={FIELD_INPUT_CLASS}
			/>
		{:else}
			<input
				type={inputType}
				aria-label={field.label}
				value={displayValue}
				{placeholder}
				oninput={onInput}
				required={field.required}
				class={FIELD_INPUT_CLASS}
			/>
		{/if}
	</label>
{/if}
