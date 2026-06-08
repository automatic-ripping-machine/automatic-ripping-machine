import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderComponent, screen, fireEvent, waitFor, cleanup } from '$lib/test-utils';
import AddChannelForm from '../AddChannelForm.svelte';
import type { Catalog } from '$lib/types/notifications';

const catalog: Catalog = {
	featured: ['discord'],
	services: [{ id: 'discord', name: 'Discord', docs_url: '', url_scheme: 'discord',
		required_fields: [{ key: 'webhook_id', label: 'Webhook ID', type: 'string', private: false, required: true }],
		advanced_fields: [] }]
};

describe('AddChannelForm', () => {
	afterEach(() => cleanup());

	it('disables Save until required fields are met, then emits body on save', async () => {
		const onsave = vi.fn();
		renderComponent(AddChannelForm, { props: { catalog, onsave, oncancel: () => {}, ontest: () => {} } });

		const save = screen.getByRole('button', { name: /save channel/i });
		expect(save).toBeDisabled();

		await fireEvent.click(screen.getByRole('radio', { name: /webhook/i }));
		await fireEvent.input(screen.getByLabelText('Channel Label'), { target: { value: 'My Hook' } });
		await fireEvent.input(screen.getByLabelText(/webhook url/i), { target: { value: 'https://hooks.example/x' } });
		await fireEvent.click(screen.getByLabelText('Job started'));

		await waitFor(() => expect(screen.getByRole('button', { name: /save channel/i })).toBeEnabled());
		await fireEvent.click(screen.getByRole('button', { name: /save channel/i }));

		expect(onsave).toHaveBeenCalledWith(
			expect.objectContaining({
				type: 'webhook',
				name: 'My Hook',
				config: expect.objectContaining({ url: 'https://hooks.example/x' }),
				subscribed_events: ['job.started']
			})
		);
	});

	it('switching type resets config', async () => {
		renderComponent(AddChannelForm, { props: { catalog, onsave: () => {}, oncancel: () => {}, ontest: () => {} } });
		await fireEvent.click(screen.getByRole('radio', { name: /webhook/i }));
		await fireEvent.input(screen.getByLabelText(/webhook url/i), { target: { value: 'https://x' } });
		await fireEvent.click(screen.getByRole('radio', { name: /bash/i }));
		expect(screen.queryByLabelText(/webhook url/i)).toBeNull();
		expect((screen.getByLabelText(/script path/i) as HTMLInputElement).value).toBe('');
	});
});
