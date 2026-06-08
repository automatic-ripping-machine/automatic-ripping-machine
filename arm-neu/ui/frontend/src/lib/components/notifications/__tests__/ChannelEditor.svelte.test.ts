import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderComponent, screen, fireEvent, waitFor, cleanup } from '$lib/test-utils';
import ChannelEditor from '../ChannelEditor.svelte';
import type { Channel, Catalog } from '$lib/types/notifications';
import { discordCatalog, appriseChannel, webhookChannel } from './apprise-fixtures';

const catalog: Catalog = { featured: [], services: [] };
const ch: Channel = webhookChannel({ id: 3 });

describe('ChannelEditor', () => {
	afterEach(() => cleanup());

	function renderEditor(channel: Channel, cat: Catalog = catalog, overrides: Record<string, unknown> = {}) {
		const props = { channel, catalog: cat, onsave: () => {}, ontest: () => {}, onclose: () => {}, ondelete: () => {}, ...overrides };
		return renderComponent(ChannelEditor, { props });
	}

	function appriseDiscord(over: Record<string, unknown> = {}) {
		return appriseChannel({
			id: 7,
			config: { type: 'apprise', url: 'discord://1/2', service_id: 'discord', fields: {} },
			...over
		});
	}

	it('Save changes is disabled until a field changes', async () => {
		renderEditor(ch);
		expect(screen.getByRole('button', { name: /save changes/i })).toBeDisabled();
		await fireEvent.input(screen.getByLabelText('Channel Label'), { target: { value: 'Hook 2' } });
		await waitFor(() => expect(screen.getByRole('button', { name: /save changes/i })).toBeEnabled());
	});

	it('Delete fires ondelete', async () => {
		const ondelete = vi.fn();
		renderEditor(ch, catalog, { ondelete });
		await fireEvent.click(screen.getByRole('button', { name: /delete/i }));
		expect(ondelete).toHaveBeenCalled();
	});

	it('apprise editor renders the service fields resolved from service_id', async () => {
		renderEditor(appriseDiscord(), discordCatalog);
		const wid = await screen.findByLabelText(/Webhook ID/i) as HTMLInputElement;
		expect(wid).toBeInTheDocument();
		expect(wid.value).toBe('');
	});

	it('apprise editor save with blank fields reports empty appriseFields (keep current)', async () => {
		const onsave = vi.fn();
		renderEditor(appriseDiscord(), discordCatalog, { onsave });
		await fireEvent.input(screen.getByLabelText('Channel Label'), { target: { value: 'D2' } });
		await waitFor(() => expect(screen.getByRole('button', { name: /save changes/i })).toBeEnabled());
		await fireEvent.click(screen.getByRole('button', { name: /save changes/i }));
		expect(onsave).toHaveBeenCalledWith(expect.objectContaining({ name: 'D2', serviceId: 'discord' }));
		const arg = onsave.mock.calls[0][0];
		expect(Object.values(arg.appriseFields).filter((v) => v && String(v).trim() !== '')).toEqual([]);
	});

	it('apprise editor save with filled fields reports them in appriseFields', async () => {
		const onsave = vi.fn();
		renderEditor(appriseDiscord(), discordCatalog, { onsave });
		await fireEvent.input(await screen.findByLabelText(/Webhook ID/i), { target: { value: '99' } });
		await waitFor(() => expect(screen.getByRole('button', { name: /save changes/i })).toBeEnabled());
		await fireEvent.click(screen.getByRole('button', { name: /save changes/i }));
		expect(onsave.mock.calls[0][0].appriseFields).toEqual(expect.objectContaining({ webhook_id: '99' }));
	});

	it('shows a notice when service_id is not in the catalog', async () => {
		renderEditor(appriseChannel({ id: 7 }), { featured: [], services: [] });
		expect(await screen.findByText(/Unknown service 'discord'/i)).toBeInTheDocument();
	});

	it('apprise editor seeds appriseFields from stored channel.config.fields', async () => {
		renderEditor(appriseDiscord({
			id: 8,
			config: { type: 'apprise', url: 'discord://...', service_id: 'discord',
			          fields: { webhook_id: '<hidden>', webhook_token: '<hidden>', thread: '5' } }
		}), discordCatalog);
		const wid = await screen.findByLabelText(/Webhook ID/i) as HTMLInputElement;
		expect(wid.type).toBe('password');
		expect(wid.value).toBe('');
		expect(wid.placeholder).toMatch(/leave blank to keep/i);
		const adv = screen.getByText(/Advanced \(/).closest('details') as HTMLDetailsElement;
		adv.open = true;
		const thread = await screen.findByLabelText(/Thread/i) as HTMLInputElement;
		expect(thread.value).toBe('5');
	});

	it('apprise raw-URL channel (no fields) shows inline notice, no apprise inputs', async () => {
		renderEditor(
			appriseChannel({ id: 9, config: { type: 'apprise', url: 'discord://...', service_id: 'discord' } }),
			discordCatalog
		);
		expect(await screen.findByText(/added via a raw URL/i)).toBeInTheDocument();
		expect(screen.queryByLabelText(/Webhook ID/i)).toBeNull();
	});
});
