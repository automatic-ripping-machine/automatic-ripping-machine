import { describe, it, expect, afterEach } from 'vitest';
import { renderComponent, screen, cleanup } from '$lib/test-utils';
import StepIndicator from './StepIndicator.svelte';

const steps = [
	{ id: 'welcome', label: 'Welcome' },
	{ id: 'drives', label: 'Drives' },
	{ id: 'settings', label: 'Settings' }
];

describe('StepIndicator', () => {
	afterEach(() => cleanup());

	it('renders all step labels', () => {
		renderComponent(StepIndicator, { props: { steps, currentIndex: 0 } });
		expect(screen.getByText('Welcome')).toBeInTheDocument();
		expect(screen.getByText('Drives')).toBeInTheDocument();
		expect(screen.getByText('Settings')).toBeInTheDocument();
	});

	it('shows step numbers for future steps', () => {
		renderComponent(StepIndicator, { props: { steps, currentIndex: 0 } });
		expect(screen.getByText('2')).toBeInTheDocument();
		expect(screen.getByText('3')).toBeInTheDocument();
	});

	it('shows checkmarks for completed steps', () => {
		const { container } = renderComponent(StepIndicator, { props: { steps, currentIndex: 2 } });
		const svgs = container.querySelectorAll('svg');
		expect(svgs.length).toBeGreaterThanOrEqual(2);
	});
});
