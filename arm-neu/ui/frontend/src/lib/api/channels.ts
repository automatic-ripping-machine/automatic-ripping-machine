import { apiFetch } from './client';
import type {
	Channel, ChannelCreate, ChannelUpdate, Catalog,
	DispatchRow, DispatchStatus, TestSendResult, EventKey
} from '$lib/types/notifications';

export function fetchChannels(): Promise<Channel[]> {
	return apiFetch<Channel[]>('/api/notifications/channels');
}

export function fetchChannel(id: number): Promise<Channel> {
	return apiFetch<Channel>(`/api/notifications/channels/${id}`);
}

export function createChannel(body: ChannelCreate): Promise<Channel> {
	return apiFetch<Channel>('/api/notifications/channels', {
		method: 'POST',
		body: JSON.stringify(body)
	});
}

export function updateChannel(id: number, body: ChannelUpdate): Promise<Channel> {
	return apiFetch<Channel>(`/api/notifications/channels/${id}`, {
		method: 'PATCH',
		body: JSON.stringify(body)
	});
}

export function deleteChannel(id: number): Promise<unknown> {
	return apiFetch<unknown>(`/api/notifications/channels/${id}`, { method: 'DELETE' });
}

export function testSendChannel(id: number, eventKey: EventKey | string): Promise<TestSendResult> {
	return apiFetch<TestSendResult>(`/api/notifications/channels/${id}/test`, {
		method: 'POST',
		body: JSON.stringify({ event_key: eventKey })
	});
}

export function fetchDispatch(id: number): Promise<DispatchStatus> {
	return apiFetch<DispatchStatus>(`/api/notifications/dispatch/${id}`);
}

export function fetchDispatches(params?: {
	channelId?: number;
	status?: string;
	limit?: number;
}): Promise<DispatchRow[]> {
	const query = new URLSearchParams();
	if (params?.channelId !== undefined) query.set('channel_id', String(params.channelId));
	if (params?.status) query.set('status', params.status);
	if (params?.limit !== undefined) query.set('limit', String(params.limit));
	const qs = query.toString();
	return apiFetch<DispatchRow[]>(`/api/notifications/dispatches${qs ? `?${qs}` : ''}`);
}

export function fetchServices(): Promise<Catalog> {
	return apiFetch<Catalog>('/api/notifications/services');
}

export function composeUrl(
	serviceId: string,
	required: Record<string, unknown>,
	advanced: Record<string, unknown>
): Promise<{ url: string }> {
	return apiFetch<{ url: string }>(`/api/notifications/services/${serviceId}/compose-url`, {
		method: 'POST',
		body: JSON.stringify({ required, advanced })
	});
}

export function testConfig(body:
	| { type: string; config: Record<string, unknown>; event_key?: string }
	| { channel_id: number; fields: Record<string, unknown>; event_key?: string }
): Promise<{ ok: boolean; error: string | null }> {
	return apiFetch<{ ok: boolean; error: string | null }>('/api/notifications/test', {
		method: 'POST',
		body: JSON.stringify(body)
	});
}
