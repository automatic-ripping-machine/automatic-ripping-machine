<script lang="ts">
	import { EVENT_KEYS, EVENT_LABELS, type EventKey } from '$lib/types/notifications';

	let { selected = $bindable() }: { selected: string[] } = $props();

	function toggle(key: EventKey, checked: boolean) {
		if (checked) {
			if (!selected.includes(key)) selected = [...selected, key];
		} else {
			selected = selected.filter((k) => k !== key);
		}
	}
</script>

<fieldset class="relative space-y-2">
	<legend class="sr-only">Events</legend>
	<div class="grid grid-cols-1 gap-2 sm:grid-cols-2 md:grid-cols-3">
		{#each EVENT_KEYS as key}
			<label class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
				<input
					type="checkbox"
					aria-label={EVENT_LABELS[key]}
					checked={selected.includes(key)}
					onchange={(e) => toggle(key, (e.currentTarget as HTMLInputElement).checked)}
					class="rounded border-primary/40 text-primary focus:ring-primary"
				/>
				<span>{EVENT_LABELS[key]}</span>
			</label>
		{/each}
	</div>
</fieldset>
