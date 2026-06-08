<script lang="ts">
    interface Props {
        variant?: 'line' | 'rect' | 'circle';
        width?: string;
        height?: string;
        class?: string;
    }
    let { variant = 'rect', width, height, class: cls = '' }: Props = $props();
</script>

<div
    class="rounded skeleton-surface {cls}"
    data-variant={variant}
    style:width
    style:height
    aria-hidden="true"
></div>

<style>
    .skeleton-surface {
        background: var(--skeleton-base, rgb(229 231 235));
    }
    :global(.dark) .skeleton-surface {
        background: var(--skeleton-base-dark, rgb(31 41 55));
    }
    @media (prefers-reduced-motion: no-preference) {
        .skeleton-surface {
            animation: pulse 1.5s ease-in-out infinite;
        }
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.6; }
    }
</style>
