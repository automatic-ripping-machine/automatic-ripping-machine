<script lang="ts">
	import { statusColor, statusLabel } from '$lib/utils/format';

	interface Props {
		status: string | null | undefined;
	}

	let { status }: Props = $props();
</script>

<span class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium text-white {statusColor(status)}">
	{statusLabel(status)}
</span>
