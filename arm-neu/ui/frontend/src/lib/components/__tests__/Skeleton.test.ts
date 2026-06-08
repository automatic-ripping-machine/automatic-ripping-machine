import { describe, it, expect, afterEach } from 'vitest';
import { renderComponent, cleanup } from '$lib/test-utils';
import Skeleton from '../Skeleton.svelte';

describe('Skeleton', () => {
    afterEach(() => cleanup());

    it('renders a div with the rect variant by default', () => {
        const { container } = renderComponent(Skeleton, { props: {} });
        const div = container.querySelector('div');
        expect(div).not.toBeNull();
        expect(div!.dataset.variant).toBe('rect');
    });

    it('applies width and height as inline styles', () => {
        const { container } = renderComponent(Skeleton, { props: { width: '60%', height: '1rem' } });
        const div = container.querySelector('div') as HTMLElement;
        expect(div.style.width).toBe('60%');
        expect(div.style.height).toBe('1rem');
    });

    it('merges the class prop onto the wrapper', () => {
        const { container } = renderComponent(Skeleton, { props: { class: 'my-extra-class' } });
        const div = container.querySelector('div') as HTMLElement;
        expect(div.className).toContain('my-extra-class');
        expect(div.className).toContain('skeleton-surface');
    });

    it('records the variant attribute for line', () => {
        const { container } = renderComponent(Skeleton, { props: { variant: 'line' } });
        const div = container.querySelector('div') as HTMLElement;
        expect(div.dataset.variant).toBe('line');
    });

    it('records the variant attribute for circle', () => {
        const { container } = renderComponent(Skeleton, { props: { variant: 'circle' } });
        const div = container.querySelector('div') as HTMLElement;
        expect(div.dataset.variant).toBe('circle');
    });
});
