import { describe, it, expect, afterEach } from 'vitest';
import { renderComponent, screen, cleanup, fireEvent, waitFor } from '$lib/test-utils';
import TemplateEditor from '../TemplateEditor.svelte';

describe('TemplateEditor', () => {
	afterEach(() => cleanup());

	it('renders title/body inputs only for subscribed events', () => {
		renderComponent(TemplateEditor, { props: { subscribedEvents: ['job.started'], templates: {} } });
		expect(screen.getByLabelText('job.started title')).toBeTruthy();
		expect(screen.getByLabelText('job.started body')).toBeTruthy();
		expect(screen.queryByLabelText('job.failed title')).toBeNull();
	});

	it('shows available variables for an event', () => {
		renderComponent(TemplateEditor, { props: { subscribedEvents: ['job.started'], templates: {} } });
		expect(screen.getByText(/\{job_title\}/)).toBeTruthy();
		expect(screen.getByText(/\{drive_mount\}/)).toBeTruthy();
	});

	it('prefills existing template values', () => {
		renderComponent(TemplateEditor, {
			props: {
				subscribedEvents: ['job.started'],
				templates: { 'job.started': { title: 'Hi {job_title}', body: 'B' } }
			}
		});
		expect((screen.getByLabelText('job.started title') as HTMLInputElement).value).toBe('Hi {job_title}');
	});

	it('shows the built-in default as a placeholder when a field is blank', () => {
		renderComponent(TemplateEditor, { props: { subscribedEvents: ['job.started'], templates: {} } });
		expect((screen.getByLabelText('job.started title') as HTMLInputElement).placeholder)
			.toBe('ARM started: {job_title}');
		expect((screen.getByLabelText('job.started body') as HTMLTextAreaElement).placeholder)
			.toBe('Job {job_id} started ripping {job_title} ({job_disc_type}).');
		expect(screen.getByText(/Leave blank to send the default/i)).toBeTruthy();
	});

	it('inserts a variable token at the caret of the focused field', async () => {
		renderComponent(TemplateEditor, { props: { subscribedEvents: ['job.started'], templates: {} } });
		const title = screen.getByLabelText('job.started title') as HTMLInputElement;

		// Type some text, place the caret in the middle, then click a chip.
		await fireEvent.input(title, { target: { value: 'hi  there' } });
		title.focus();
		title.setSelectionRange(3, 3); // after "hi "
		await fireEvent.click(title); // captures caret position

		await fireEvent.click(screen.getByRole('button', { name: 'Insert {job_title}' }));

		await waitFor(() => {
			expect((screen.getByLabelText('job.started title') as HTMLInputElement).value)
				.toBe('hi {job_title} there');
		});
	});

	it('appends a variable to the title when no field is focused', async () => {
		renderComponent(TemplateEditor, { props: { subscribedEvents: ['job.started'], templates: {} } });
		await fireEvent.click(screen.getByRole('button', { name: 'Insert {job_id}' }));
		await waitFor(() => {
			expect((screen.getByLabelText('job.started title') as HTMLInputElement).value)
				.toBe('{job_id}');
		});
	});
});
