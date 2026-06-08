import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderComponent, screen, fireEvent, waitFor, cleanup, within } from '$lib/test-utils';
import NotificationsTab from '../NotificationsTab.svelte';
import * as api from '$lib/api/channels';
import { toasts, dismissToast } from '$lib/stores/toast.svelte';
import type { Channel } from '$lib/types/notifications';
import { discordCatalog, appriseChannel, webhookChannel } from './apprise-fixtures';

const ch: Channel = webhookChannel();

describe('NotificationsTab', () => {
	beforeEach(() => {
		vi.spyOn(api, 'fetchChannels').mockResolvedValue([ch]);
		vi.spyOn(api, 'fetchServices').mockResolvedValue({ featured: [], services: [] });
	});
	afterEach(() => {
		for (const t of toasts.value) dismissToast(t.id);
		vi.restoreAllMocks();
		cleanup();
	});

	it('loads and lists channels', async () => {
		renderComponent(NotificationsTab);
		expect(await screen.findByText('Hook')).toBeInTheDocument();
	});

	it('shows the stat strip counts', async () => {
		renderComponent(NotificationsTab);
		await screen.findByText('Hook');
		const channelsLabel = screen.getByText('Channels');
		expect(channelsLabel).toBeInTheDocument();
		const card = channelsLabel.parentElement as HTMLElement;
		expect(within(card).getByText('1')).toBeInTheDocument();
	});

	it('toggle calls updateChannel and reverts on error', async () => {
		vi.spyOn(api, 'updateChannel').mockRejectedValueOnce(new Error('nope'));
		renderComponent(NotificationsTab);
		await screen.findByText('Hook');
		await fireEvent.click(screen.getByRole('switch', { name: /enabled/i }));
		await waitFor(() => expect(api.updateChannel).toHaveBeenCalledWith(1, { enabled: false }));
		await waitFor(() => expect(screen.getByRole('switch', { name: /enabled/i }).getAttribute('aria-checked')).toBe('true'));
	});

	it('test-send polls until the dispatch reaches a terminal status', async () => {
		vi.useFakeTimers();
		vi.spyOn(api, 'testSendChannel').mockResolvedValue({ sent_at: 'now', dispatch_id: 9 });
		const fetchDispatch = vi.spyOn(api, 'fetchDispatch')
			.mockResolvedValueOnce({ id: 9, status: 'in_flight', attempts: 1, last_error: null, completed_at: null })
			.mockResolvedValueOnce({ id: 9, status: 'success', attempts: 1, last_error: null, completed_at: 'now' });

		renderComponent(NotificationsTab);
		// loaded state — advance microtasks; channels resolve
		await vi.advanceTimersByTimeAsync(0);
		// Click the row's Send test button (aria-label "Send test")
		await fireEvent.click(screen.getByRole('button', { name: /send test/i }));
		// Advance through two 500ms poll iterations
		await vi.advanceTimersByTimeAsync(1100);

		expect(fetchDispatch).toHaveBeenCalledTimes(2);
		expect(toasts.value.some((t) => t.title === 'Test delivered')).toBe(true);
		expect(toasts.value.some((t) => t.title === 'Test failed')).toBe(false);
		vi.useRealTimers();
	});

	it('editor Send test uses testConfig with the edited body, not testSendChannel', async () => {
		const testConfig = vi.spyOn(api, 'testConfig').mockResolvedValue({ ok: true, error: null });
		const testSend = vi.spyOn(api, 'testSendChannel');
		renderComponent(NotificationsTab);
		await screen.findByText('Hook');
		// Expand the row (click the channel name / row, not the toggle or actions)
		await fireEvent.click(screen.getByText('Hook'));
		// The collapsed row's test button uses an icon with aria-label "Send test";
		// the editor's uses visible text "Send test". Filter by visible textContent
		// to reliably target the editor's button.
		const sendTestButtons = await screen.findAllByRole('button', { name: /send test/i });
		const editorBtn = sendTestButtons.find((b) => b.textContent?.toLowerCase().includes('send test'));
		await fireEvent.click(editorBtn!);
		await waitFor(() => expect(testConfig).toHaveBeenCalledWith(
			expect.objectContaining({ type: 'webhook', config: expect.objectContaining({ url: 'https://x' }) })
		));
		expect(testSend).not.toHaveBeenCalled();
	});

	it('editor save with apprise dirty: PATCH config {service_id, fields}', async () => {
		const ch = appriseChannel({
			id: 1,
			config: { type: 'apprise', url: 'discord://1/2', service_id: 'discord',
			          fields: { webhook_id: '<hidden>', webhook_token: '<hidden>', thread: '5' } }
		});
		vi.spyOn(api, 'fetchChannels').mockResolvedValue([ch]);
		vi.spyOn(api, 'fetchServices').mockResolvedValue(discordCatalog);
		const compose = vi.spyOn(api, 'composeUrl');
		const update = vi.spyOn(api, 'updateChannel').mockResolvedValue(ch);
		renderComponent(NotificationsTab);
		await screen.findByText('D');
		await fireEvent.click(screen.getByText('D'));
		// expand advanced + edit a non-private field
		const adv = (await screen.findByText(/Advanced \(/)).closest('details') as HTMLDetailsElement;
		adv.open = true;
		await fireEvent.input(await screen.findByLabelText(/Thread/i), { target: { value: '9' } });
		await fireEvent.click(screen.getByRole('button', { name: /save changes/i }));
		await waitFor(() => expect(update).toHaveBeenCalledWith(1, expect.objectContaining({
			config: expect.objectContaining({
				type: 'apprise', service_id: 'discord',
				fields: expect.objectContaining({ thread: '9', webhook_id: '<hidden>' })
			})
		})));
		expect(compose).not.toHaveBeenCalled();  // server-side recompose
	});

	it('editor save with no apprise edits: omits config', async () => {
		const ch = appriseChannel({
			id: 1,
			config: { type: 'apprise', url: 'discord://1/2', service_id: 'discord',
			          fields: { webhook_id: '<hidden>', webhook_token: '<hidden>', thread: '5' } }
		});
		vi.spyOn(api, 'fetchChannels').mockResolvedValue([ch]);
		vi.spyOn(api, 'fetchServices').mockResolvedValue(discordCatalog);
		const update = vi.spyOn(api, 'updateChannel').mockResolvedValue({ ...ch, name: 'D2' });
		renderComponent(NotificationsTab);
		await screen.findByText('D');
		await fireEvent.click(screen.getByText('D'));
		await fireEvent.input(screen.getByLabelText('Channel Label'), { target: { value: 'D2' } });
		await fireEvent.click(screen.getByRole('button', { name: /save changes/i }));
		await waitFor(() => expect(update).toHaveBeenCalled());
		expect(update.mock.calls[0][1]).not.toHaveProperty('config');
	});

	it('editor Send test with dirty apprise: calls testConfig with {channel_id, fields}', async () => {
		const ch = appriseChannel({
			id: 1,
			config: { type: 'apprise', url: 'discord://1/2', service_id: 'discord',
			          fields: { webhook_id: '<hidden>', webhook_token: '<hidden>', thread: '5' } }
		});
		vi.spyOn(api, 'fetchChannels').mockResolvedValue([ch]);
		vi.spyOn(api, 'fetchServices').mockResolvedValue(discordCatalog);
		const testCfg = vi.spyOn(api, 'testConfig').mockResolvedValue({ ok: true, error: null });
		const testSend = vi.spyOn(api, 'testSendChannel');
		renderComponent(NotificationsTab);
		await screen.findByText('D');
		await fireEvent.click(screen.getByText('D'));
		const adv = (await screen.findByText(/Advanced \(/)).closest('details') as HTMLDetailsElement;
		adv.open = true;
		await fireEvent.input(await screen.findByLabelText(/Thread/i), { target: { value: '9' } });
		// editor "Send test" button (text), not the row's icon button
		const sendTestBtns = await screen.findAllByRole('button', { name: /send test/i });
		const editorBtn = sendTestBtns.find((b) => b.textContent?.toLowerCase().includes('send test'));
		await fireEvent.click(editorBtn!);
		await waitFor(() => expect(testCfg).toHaveBeenCalledWith(expect.objectContaining({
			channel_id: 1,
			fields: expect.objectContaining({ thread: '9' }),
			event_key: 'job.started'
		})));
		expect(testSend).not.toHaveBeenCalled();
	});

	it('editor Send test with NO apprise edits: tests the saved channel (testSendChannel)', async () => {
		const ch = appriseChannel({
			id: 1,
			config: { type: 'apprise', url: 'discord://1/2', service_id: 'discord',
			          fields: { webhook_id: '<hidden>', webhook_token: '<hidden>', thread: '5' } }
		});
		vi.spyOn(api, 'fetchChannels').mockResolvedValue([ch]);
		vi.spyOn(api, 'fetchServices').mockResolvedValue(discordCatalog);
		const testSend = vi.spyOn(api, 'testSendChannel').mockResolvedValue({ sent_at: 'now', dispatch_id: 1 });
		vi.spyOn(api, 'fetchDispatch').mockResolvedValue({ id: 1, status: 'success', attempts: 1, last_error: null, completed_at: 'now' });
		const testCfg = vi.spyOn(api, 'testConfig');
		renderComponent(NotificationsTab);
		await screen.findByText('D');
		await fireEvent.click(screen.getByText('D'));
		const sendTestBtns = await screen.findAllByRole('button', { name: /send test/i });
		const editorBtn = sendTestBtns.find((b) => b.textContent?.toLowerCase().includes('send test'));
		await fireEvent.click(editorBtn!);
		await waitFor(() => expect(testSend).toHaveBeenCalledWith(1, 'job.started'));
		expect(testCfg).not.toHaveBeenCalled();
	});

	it('add: sends {service_id, fields} (no client composeUrl) for apprise', async () => {
		vi.spyOn(api, 'fetchChannels').mockResolvedValue([webhookChannel({ id: 1, name: 'Hook' })]);
		vi.spyOn(api, 'fetchServices').mockResolvedValue(discordCatalog);
		const compose = vi.spyOn(api, 'composeUrl').mockResolvedValue({ url: 'discord://x/y' });
		const create = vi.spyOn(api, 'createChannel').mockResolvedValue(appriseChannel({ id: 5, name: 'New' }));
		renderComponent(NotificationsTab);
		await screen.findByText('Hook');
		await fireEvent.click(screen.getByRole('button', { name: /add channel/i }));
		await fireEvent.input(screen.getByLabelText('Channel Label'), { target: { value: 'New' } });
		await fireEvent.click(await screen.findByRole('button', { name: /select a service/i }));
		await fireEvent.click(await screen.findByRole('button', { name: /Discord/ }));
		await fireEvent.input(screen.getByLabelText(/Webhook ID/i), { target: { value: '1' } });
		await fireEvent.click(screen.getByLabelText('Job started'));
		await fireEvent.click(screen.getByRole('button', { name: /save channel/i }));

		await waitFor(() => expect(create).toHaveBeenCalledWith(
			expect.objectContaining({
				type: 'apprise',
				config: expect.objectContaining({
					type: 'apprise', service_id: 'discord',
					fields: expect.objectContaining({ webhook_id: '1' })
				})
			})
		));
		expect(compose).not.toHaveBeenCalled();
	});
});
