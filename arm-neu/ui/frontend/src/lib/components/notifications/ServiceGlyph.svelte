<script lang="ts">
	let { id, name, size = 28 }: { id: string; name: string; size?: number } = $props();

	// Deterministic hue from the service id.
	function hue(s: string): number {
		let h = 0;
		for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) % 360;
		return h;
	}

	const h = $derived(hue(id));
	const bg = $derived(`oklch(0.45 0.13 ${h})`);
	const fg = $derived(`oklch(0.78 0.16 ${h})`);
	const letter = $derived((name?.[0] ?? '?').toUpperCase());
</script>

<span
	data-glyph
	class="inline-flex shrink-0 items-center justify-center rounded-md border border-white/5 font-bold"
	style="width:{size}px; height:{size}px; font-size:{Math.round(size * 0.45)}px; background:{bg}; color:{fg};"
	aria-hidden="true"
>{letter}</span>
