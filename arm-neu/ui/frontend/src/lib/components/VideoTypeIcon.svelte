<script lang="ts">
	import { Clapperboard, Tv, Music, Database, Disc3 } from 'lucide-svelte';

	interface Props {
		icon: string;
		class?: string;
	}

	let { icon, class: className = 'h-4 w-4' }: Props = $props();

	const icons: Record<string, typeof Clapperboard> = {
		clapperboard: Clapperboard,
		tv: Tv,
		music: Music,
		database: Database,
		disc: Disc3,
	};

	let IconComponent = $derived(icons[icon] ?? Disc3);
</script>

<IconComponent class={className} />
