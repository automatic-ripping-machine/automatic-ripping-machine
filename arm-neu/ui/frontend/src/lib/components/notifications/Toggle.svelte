<script lang="ts">
	let {
		checked,
		label,
		onchange
	}: { checked: boolean; label: string; onchange?: (next: boolean) => void } = $props();
</script>

<button
	type="button"
	role="switch"
	aria-checked={checked}
	aria-label={label}
	onclick={(e) => { e.stopPropagation(); onchange?.(!checked); }}
	class="relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors {checked ? 'bg-primary' : 'bg-primary/20 dark:bg-primary/25'}"
>
	<span class="inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform {checked ? 'translate-x-[19px]' : 'translate-x-[3px]'}"></span>
</button>
