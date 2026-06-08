<script lang="ts">
	import type { Catalog, CatalogService } from '$lib/types/notifications';
	import { FIELD_INPUT_CLASS } from '$lib/types/notifications';
	import ServiceGlyph from './ServiceGlyph.svelte';

	let {
		catalog,
		selectedId,
		onpick
	}: { catalog: Catalog; selectedId: string | null; onpick?: (id: string) => void } = $props();

	let open = $state(false);
	let search = $state('');
	let rootEl: HTMLDivElement | undefined = $state();

	const byId = $derived(new Map(catalog.services.map((s) => [s.id, s])));
	const selected = $derived(selectedId ? byId.get(selectedId) ?? null : null);

	const featured = $derived(
		catalog.featured.map((id) => byId.get(id)).filter((s): s is CatalogService => !!s)
	);
	const rest = $derived(
		catalog.services
			.filter((s) => !catalog.featured.includes(s.id))
			.sort((a, b) => a.name.localeCompare(b.name))
	);
	const q = $derived(search.trim().toLowerCase());
	const filtered = $derived(
		q ? catalog.services.filter((s) => s.name.toLowerCase().includes(q)) : null
	);

	function choose(id: string) {
		onpick?.(id);
		open = false;
		search = '';
	}

	$effect(() => {
		if (!open) return;
		function onDocClick(ev: MouseEvent) {
			if (rootEl && !rootEl.contains(ev.target as Node)) open = false;
		}
		document.addEventListener('mousedown', onDocClick, true);
		return () => document.removeEventListener('mousedown', onDocClick, true);
	});
</script>

<div class="relative" bind:this={rootEl}>
	<button
		type="button"
		onclick={() => (open = !open)}
		class="flex w-full items-center justify-between rounded-md border border-primary/25 bg-primary/5 px-3 py-2.5 text-left text-sm hover:border-primary dark:border-primary/30 dark:bg-primary/10"
	>
		{#if selected}
			<span class="flex items-center gap-2">
				<ServiceGlyph id={selected.id} name={selected.name} size={22} />
				<span class="text-gray-800 dark:text-gray-100">{selected.name}</span>
			</span>
		{:else}
			<span class="text-gray-500 dark:text-gray-400">Select a service…</span>
		{/if}
		<svg class="h-4 w-4 transform transition-transform {open ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg>
	</button>

	{#if open}
		<div class="absolute z-20 mt-1 w-full overflow-hidden rounded-md border border-primary/25 bg-surface shadow-2xl dark:border-primary/30 dark:bg-surface-dark">
			<div class="p-2">
				<!-- svelte-ignore a11y_autofocus -->
				<input type="search" placeholder="Search services" bind:value={search} autofocus class="w-full {FIELD_INPUT_CLASS}" />
			</div>
			<ul class="max-h-[280px] overflow-y-auto py-1">
				{#if filtered}
					{#each filtered as svc (svc.id)}
						{@render option(svc)}
					{/each}
					{#if filtered.length === 0}
						<li class="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">No services match "{search}".</li>
					{/if}
				{:else}
					<li class="px-3 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-primary">Featured</li>
					{#each featured as svc (svc.id)}{@render option(svc)}{/each}
					<li class="px-3 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-gray-500 dark:text-gray-400">All services</li>
					{#each rest as svc (svc.id)}{@render option(svc)}{/each}
				{/if}
			</ul>
		</div>
	{/if}
</div>

{#snippet option(svc: CatalogService)}
	<li>
		<button
			type="button"
			onclick={() => choose(svc.id)}
			class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-primary/10 dark:hover:bg-primary/15 {svc.id === selectedId ? 'bg-primary/15' : ''}"
		>
			<ServiceGlyph id={svc.id} name={svc.name} size={22} />
			<span class="text-gray-800 dark:text-gray-100">{svc.name}</span>
			<span class="ml-auto font-mono text-[10.5px] text-gray-500">{svc.url_scheme}://</span>
		</button>
	</li>
{/snippet}
