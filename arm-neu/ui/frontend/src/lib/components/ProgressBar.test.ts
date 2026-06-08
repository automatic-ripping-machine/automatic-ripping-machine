import { describe, it, expect, afterEach } from 'vitest';
import { renderComponent, screen, cleanup } from '$lib/test-utils';
import ProgressBar from './ProgressBar.svelte';

describe('ProgressBar', () => {
	afterEach(() => cleanup());

	describe('rendering', () => {
		it('renders with a percentage label by default', () => {
			renderComponent(ProgressBar, { props: { value: 50 } });
			expect(screen.getByText('50%')).toBeInTheDocument();
		});

		it('hides label when showLabel is false', () => {
			renderComponent(ProgressBar, { props: { value: 50, showLabel: false } });
			expect(screen.queryByText('50%')).not.toBeInTheDocument();
		});
	});

	describe('props', () => {
		it('calculates percentage from value and max', () => {
			renderComponent(ProgressBar, { props: { value: 25, max: 50 } });
			expect(screen.getByText('50%')).toBeInTheDocument();
		});

		it('clamps percentage to 100', () => {
			renderComponent(ProgressBar, { props: { value: 150 } });
			expect(screen.getByText('100%')).toBeInTheDocument();
		});

		it('clamps percentage to 0', () => {
			renderComponent(ProgressBar, { props: { value: -10 } });
			expect(screen.getByText('0%')).toBeInTheDocument();
		});

		it('applies custom color class to fill bar', () => {
			const { container } = renderComponent(ProgressBar, { props: { value: 50, color: 'custom-bar-color' } });
			const fill = container.querySelector('[data-progress-fill]');
			expect(fill).toHaveClass('custom-bar-color');
		});

		it('sets fill width style based on percentage', () => {
			const { container } = renderComponent(ProgressBar, { props: { value: 75 } });
			const fill = container.querySelector('[data-progress-fill]');
			expect(fill).toHaveStyle({ width: '75%' });
		});
	});
});
