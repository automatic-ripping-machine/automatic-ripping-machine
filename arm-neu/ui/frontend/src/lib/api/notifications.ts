import type { NotificationSchema as Notification } from '$lib/types/api.gen';
import { apiFetch } from './client';

export function fetchNotifications(): Promise<Notification[]> {
	return apiFetch<Notification[]>('/api/notifications');
}

export function dismissNotification(id: number): Promise<Record<string, unknown>> {
	return apiFetch(`/api/notifications/${id}`, { method: 'PATCH' });
}
