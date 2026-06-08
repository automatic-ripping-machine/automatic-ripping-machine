import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as client from '$lib/api/client';
import {
	fetchChannels, fetchChannel, createChannel, updateChannel,
	deleteChannel, testSendChannel, fetchDispatch, fetchDispatches,
	fetchServices, composeUrl, testConfig
} from '$lib/api/channels';

describe('channels api', () => {
	beforeEach(() => vi.restoreAllMocks());

	it('fetchChannels GETs the list', async () => {
		const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue([{ id: 1 }] as never);
		const out = await fetchChannels();
		expect(spy).toHaveBeenCalledWith('/api/notifications/channels');
		expect(out).toEqual([{ id: 1 }]);
	});

	it('fetchChannel GETs by id', async () => {
		const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({ id: 3 } as never);
		await fetchChannel(3);
		expect(spy).toHaveBeenCalledWith('/api/notifications/channels/3');
	});

	it('createChannel POSTs the body', async () => {
		const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({ id: 9 } as never);
		const body = { type: 'apprise', name: 'x', config: { type: 'apprise', url: 'discord://a/b' }, subscribed_events: [] };
		await createChannel(body as never);
		expect(spy).toHaveBeenCalledWith('/api/notifications/channels', {
			method: 'POST', body: JSON.stringify(body)
		});
	});

	it('updateChannel PATCHes', async () => {
		const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({ id: 9 } as never);
		await updateChannel(9, { name: 'r' } as never);
		expect(spy).toHaveBeenCalledWith('/api/notifications/channels/9', {
			method: 'PATCH', body: JSON.stringify({ name: 'r' })
		});
	});

	it('deleteChannel DELETEs', async () => {
		const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({} as never);
		await deleteChannel(9);
		expect(spy).toHaveBeenCalledWith('/api/notifications/channels/9', { method: 'DELETE' });
	});

	it('testSendChannel POSTs event_key', async () => {
		const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({ dispatch_id: 5 } as never);
		await testSendChannel(2, 'job.started');
		expect(spy).toHaveBeenCalledWith('/api/notifications/channels/2/test', {
			method: 'POST', body: JSON.stringify({ event_key: 'job.started' })
		});
	});

	it('fetchDispatch GETs by id', async () => {
		const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({ status: 'success' } as never);
		await fetchDispatch(5);
		expect(spy).toHaveBeenCalledWith('/api/notifications/dispatch/5');
	});

	it('fetchDispatches builds query', async () => {
		const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue([] as never);
		await fetchDispatches({ channelId: 2, limit: 20 });
		expect(spy).toHaveBeenCalledWith('/api/notifications/dispatches?channel_id=2&limit=20');
	});

	it('fetchServices GETs the catalog', async () => {
		const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({ featured: [], services: [] } as never);
		await fetchServices();
		expect(spy).toHaveBeenCalledWith('/api/notifications/services');
	});

	it('composeUrl POSTs required+advanced', async () => {
		const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({ url: 'discord://1' } as never);
		await composeUrl('discord', { webhook_id: '1' }, { tts: true });
		expect(spy).toHaveBeenCalledWith('/api/notifications/services/discord/compose-url', {
			method: 'POST', body: JSON.stringify({ required: { webhook_id: '1' }, advanced: { tts: true } })
		});
	});

	it('testConfig POSTs the config to /test', async () => {
		const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue({ ok: true, error: null } as never);
		const body = { type: 'apprise', config: { type: 'apprise', url: 'discord://a/b' }, event_key: 'job.started' };
		await testConfig(body);
		expect(spy).toHaveBeenCalledWith('/api/notifications/test', {
			method: 'POST', body: JSON.stringify(body)
		});
	});
});
