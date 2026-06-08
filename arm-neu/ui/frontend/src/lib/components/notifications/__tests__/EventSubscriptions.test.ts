import { describe, it, expect, afterEach } from 'vitest';
import { renderComponent, screen, fireEvent, cleanup } from '$lib/test-utils';
import EventSubscriptions from '../EventSubscriptions.svelte';

describe('EventSubscriptions', () => {
	afterEach(() => cleanup());

	it('renders a checkbox per event with labels', () => {
		renderComponent(EventSubscriptions, { props: { selected: [] } });
		expect(screen.getByLabelText('Job started')).toBeTruthy();
		expect(screen.getByLabelText('Rip complete')).toBeTruthy();
		expect(screen.getByLabelText('Transcode complete')).toBeTruthy();
		expect(screen.getByLabelText('Job failed')).toBeTruthy();
		expect(screen.getByLabelText('Manual wait required')).toBeTruthy();
		expect(screen.getByLabelText('Duplicate detected')).toBeTruthy();
	});

	it('checks boxes for already-selected events', () => {
		renderComponent(EventSubscriptions, { props: { selected: ['job.started', 'job.failed'] } });
		expect((screen.getByLabelText('Job started') as HTMLInputElement).checked).toBe(true);
		expect((screen.getByLabelText('Rip complete') as HTMLInputElement).checked).toBe(false);
	});

	it('checks a box when its event is clicked', async () => {
		renderComponent(EventSubscriptions, { props: { selected: [] } });
		await fireEvent.click(screen.getByLabelText('Job failed'));
		expect((screen.getByLabelText('Job failed') as HTMLInputElement).checked).toBe(true);
	});
});
