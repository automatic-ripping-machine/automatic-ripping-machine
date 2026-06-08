<script lang="ts">
	interface Props {
		onselect: (selection: { path: string; kind: 'dir' | 'iso' }) => void;
	}
	let { onselect }: Props = $props();
</script>

<button type="button" data-testid="folder-browser-mock-select" onclick={() => onselect({ path: '/home/arm/ingress/Movie_Folder', kind: 'dir' })}>
	Mock select folder
</button>
<button type="button" data-testid="folder-browser-mock-select-iso" onclick={() => onselect({ path: '/home/arm/ingress/Movie.iso', kind: 'iso' })}>
	Mock select ISO
</button>
