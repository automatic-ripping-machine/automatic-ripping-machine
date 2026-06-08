<script lang="ts">
	import '../../app.css';
	import { theme } from '$lib/stores/theme';
	let { children } = $props();
</script>

<div class={$theme}>
	{@render children()}
</div>
