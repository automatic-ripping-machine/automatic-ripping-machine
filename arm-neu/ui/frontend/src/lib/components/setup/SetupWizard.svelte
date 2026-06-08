<script lang="ts">
	import type { SetupStatus } from '$lib/types/api.gen';
	import type { Component } from 'svelte';
	import { goto } from '$app/navigation';
	import { completeSetup } from '$lib/api/setup';
	import StepIndicator from './StepIndicator.svelte';
	import WelcomeStep from './WelcomeStep.svelte';
	import DriveScanStep from './DriveScanStep.svelte';
	import ReadinessCheckStep from './ReadinessCheckStep.svelte';
	import SettingsReviewStep from './SettingsReviewStep.svelte';

	interface SetupStep {
		id: string;
		label: string;
		component: Component<any>;
	}

	interface Props {
		status: SetupStatus;
	}

	let { status }: Props = $props();

	const steps: SetupStep[] = [
		{ id: 'welcome', label: 'Welcome', component: WelcomeStep },
		{ id: 'drives', label: 'Drives', component: DriveScanStep },
		{ id: 'readiness', label: 'Readiness', component: ReadinessCheckStep },
		{ id: 'settings', label: 'Settings', component: SettingsReviewStep },
	];

	let currentIndex = $state(0);
	let finishing = $state(false);

	let currentStep = $derived(steps[currentIndex]);
	let isFirst = $derived(currentIndex === 0);
	let isLast = $derived(currentIndex === steps.length - 1);

	function next() {
		if (currentIndex < steps.length - 1) currentIndex++;
	}

	function prev() {
		if (currentIndex > 0) currentIndex--;
	}

	async function finish() {
		finishing = true;
		try {
			await completeSetup();
			goto('/');
		} catch {
			finishing = false;
		}
	}
</script>

<div class="mx-auto max-w-2xl space-y-8 px-4 py-8">
	<!-- Logo -->
	<div class="text-center">
		<img src="/img/arm-logo-black.png" alt="ARM" class="mx-auto h-20 w-20 dark:hidden" />
		<img src="/img/arm-logo-white.png" alt="ARM" class="mx-auto hidden h-20 w-20 dark:block" />
	</div>

	<!-- Progress -->
	<StepIndicator steps={steps.map(s => ({ id: s.id, label: s.label }))} {currentIndex} />

	<!-- Step content -->
	<div class="rounded-xl border border-primary/20 bg-surface p-6 shadow-sm dark:border-primary/20 dark:bg-surface-dark">
		{#if currentStep.id === 'welcome'}
			<WelcomeStep {status} />
		{:else if currentStep.id === 'drives'}
			<DriveScanStep />
		{:else if currentStep.id === 'readiness'}
			<ReadinessCheckStep />
		{:else if currentStep.id === 'settings'}
			<SettingsReviewStep />
		{/if}
	</div>

	<!-- Navigation -->
	<div class="flex items-center justify-between">
		<button
			type="button"
			onclick={prev}
			disabled={isFirst}
			class="rounded-lg px-4 py-2 text-sm font-medium text-gray-700 ring-1 ring-gray-300 hover:bg-gray-100 disabled:opacity-0 dark:text-gray-300 dark:ring-gray-600 dark:hover:bg-gray-800 transition-colors"
		>
			Back
		</button>

		{#if isLast}
			<button
				type="button"
				onclick={finish}
				disabled={finishing}
				class="rounded-lg bg-primary px-6 py-2 text-sm font-medium text-on-primary hover:bg-primary-hover disabled:opacity-50 transition-colors"
			>
				{finishing ? 'Finishing...' : 'Finish Setup'}
			</button>
		{:else}
			<button
				type="button"
				onclick={next}
				class="rounded-lg bg-primary px-6 py-2 text-sm font-medium text-on-primary hover:bg-primary-hover transition-colors"
			>
				Next
			</button>
		{/if}
	</div>
</div>
