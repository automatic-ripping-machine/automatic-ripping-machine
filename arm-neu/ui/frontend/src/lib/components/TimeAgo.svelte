<script lang="ts">
	import { timeAgo } from '$lib/utils/format';

	interface Props {
		date: string | null;
	}

	let { date }: Props = $props();
</script>

<span title={date ?? undefined}>{timeAgo(date)}</span>
