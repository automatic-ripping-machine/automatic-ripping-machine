import type { Channel, ChannelType, CatalogService } from '$lib/types/notifications';

export type ChannelStatus = 'ok' | 'warn' | 'error' | 'off';

export function channelStatus(c: Channel): ChannelStatus {
	if (!c.enabled) return 'off';
	if (c.last_error) return 'error';
	return 'ok';
}

export function relativeTime(iso: string | null): string {
	if (!iso) return 'never';
	const then = new Date(iso).getTime();
	const diffMs = Date.now() - then;
	const min = Math.floor(diffMs / 60000);
	if (min < 1) return 'just now';
	if (min < 60) return `${min}m ago`;
	const hr = Math.floor(min / 60);
	if (hr < 24) return `${hr}h ago`;
	const day = Math.floor(hr / 24);
	return `${day}d ago`;
}

const TYPE_LABELS: Record<ChannelType, string> = {
	apprise: 'Service (Apprise)',
	webhook: 'Webhook',
	bash: 'Bash script'
};

export function typeLabel(type: ChannelType): string {
	return TYPE_LABELS[type] ?? type;
}

export interface FormState {
	type: ChannelType;
	name: string;
	config: Record<string, unknown>;
	events: string[];
	service: CatalogService | null;
}

function requiredKeys(state: FormState): string[] {
	if (state.type === 'apprise') {
		return (state.service?.required_fields ?? []).map((f) => f.key);
	}
	if (state.type === 'webhook') return ['url'];
	return ['script_path'];
}

export function missingRequirements(state: FormState): string[] {
	const missing: string[] = [];
	if (!state.name.trim()) missing.push('channel label');
	const keys = requiredKeys(state);
	const allFilled = keys.every((k) => {
		const v = state.config[k];
		return v !== undefined && v !== null && String(v).trim() !== '';
	});
	if (!allFilled) missing.push('required fields');
	if (state.events.length === 0) missing.push('at least one event');
	return missing;
}

export function isReady(state: FormState): boolean {
	return missingRequirements(state).length === 0;
}
