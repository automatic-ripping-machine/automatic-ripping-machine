<script lang="ts">
	import { deriveLifecycle, lifecycleColorVar } from '$lib/utils/job-lifecycle';
	import { Pause } from 'lucide-svelte';

	interface Props {
		status: string | null | undefined;
		sourceType: string | null | undefined;
		size?: 'sm' | 'md';
	}

	let { status, sourceType, size = 'md' }: Props = $props();

	let nodes = $derived(deriveLifecycle(status, sourceType));
</script>

{#if size === 'sm'}
	<!-- Compact horizontal segments for the dashboard JobCard.
	     Each segment is a colored bar; the active one pulses; failure
	     segments use the error theme token. No labels rendered. -->
	<div
		class="inline-flex items-center gap-0.5"
		role="img"
		aria-label="Job lifecycle"
		title={nodes.map((n) => `${n.label}: ${n.state}`).join(' · ')}
	>
		{#each nodes as node (node.id)}
			<span
				class="relative h-1.5 w-6 rounded-sm {node.state === 'active' ? 'lifecycle-pulse' : ''}"
				style="background: {lifecycleColorVar(node.state)}; opacity: {node.state === 'pending' ? 0.35 : 1}"
			>
				{#if node.state === 'paused'}
					<Pause
						class="absolute -top-1 left-1/2 h-2.5 w-2.5 -translate-x-1/2 text-[var(--color-status-waiting)]"
					/>
				{/if}
			</span>
		{/each}
	</div>
{:else}
	<!-- Detail-page sized: each stage is a block with the label above a
	     small colored bar. Stages laid out side-by-side. -->
	<ol
		class="grid w-full gap-2 text-xs"
		style="grid-template-columns: repeat({nodes.length}, minmax(0, 1fr));"
		role="list"
		aria-label="Job lifecycle"
	>
		{#each nodes as node (node.id)}
			<li class="flex flex-col gap-1.5" title={`${node.label}: ${node.state}`}>
				<div class="flex items-center gap-1 text-[11px] font-medium uppercase tracking-wider"
					style="color: {node.state === 'pending'
						? 'var(--color-status-pending, #9ca3af)'
						: node.state === 'failed'
						? 'var(--color-status-error)'
						: 'var(--color-text, currentColor)'}; opacity: {node.state === 'pending' ? 0.55 : 1}"
				>
					{#if node.state === 'paused'}
						<Pause class="h-3 w-3" />
					{/if}
					<span class="truncate">{node.label}</span>
				</div>
				<span
					class="block h-2 w-full rounded-sm {node.state === 'active' ? 'lifecycle-pulse' : ''}"
					style="background: {lifecycleColorVar(node.state)}; opacity: {node.state === 'pending' ? 0.35 : 1}"
					aria-hidden="true"
				></span>
			</li>
		{/each}
	</ol>
{/if}

<style>
	.lifecycle-pulse {
		animation: lifecyclePulse 1.4s ease-in-out infinite;
	}
	@keyframes lifecyclePulse {
		0%, 100% {
			filter: brightness(1);
		}
		50% {
			filter: brightness(1.3);
		}
	}
</style>
