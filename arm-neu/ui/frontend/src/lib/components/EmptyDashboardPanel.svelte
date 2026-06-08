<script lang="ts">
    import { transcoderEnabled } from '$lib/stores/config';

    interface Props {
        drivesOnline: number | null;
        armOnline: boolean;
        transcoderOnline: boolean;
    }
    let { drivesOnline, armOnline, transcoderOnline }: Props = $props();
</script>

<section>
    <div class="rounded-lg border border-primary/20 bg-surface p-6 text-center shadow-xs dark:border-primary/20 dark:bg-surface-dark">
        <svg class="mx-auto h-12 w-12 text-gray-300 dark:text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10" />
            <circle cx="12" cy="12" r="3" />
            <circle cx="12" cy="12" r="6.5" stroke-width="0.75" opacity="0.4" />
        </svg>
        <p class="mt-3 text-sm font-medium text-gray-500 dark:text-gray-400">
            {$transcoderEnabled ? 'No active rips or transcodes' : 'No active rips'}
        </p>
        <p class="mt-1 text-xs text-gray-400 dark:text-gray-500">Insert a disc to get started - {drivesOnline} drive{drivesOnline !== 1 ? 's' : ''} online{#if !armOnline}, ARM offline{/if}{#if $transcoderEnabled && !transcoderOnline}, transcoder offline{/if}</p>
    </div>
</section>
