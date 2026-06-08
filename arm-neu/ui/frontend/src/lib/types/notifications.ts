// Hand-written types for the notification channel + catalog system.
// The BFF proxies channel data as opaque dicts, so these are not in the
// generated api.gen.ts. Catalog types mirror apprise-introspection output.

export const EVENT_KEYS = [
	'job.started',
	'job.rip_complete',
	'job.transcode_complete',
	'job.failed',
	'job.manual_wait_required',
	'job.duplicate_detected'
] as const;

export type EventKey = (typeof EVENT_KEYS)[number];

export type ChannelType = 'apprise' | 'webhook' | 'bash';

export type AppriseFieldValue = string | number | boolean;

export interface AppriseConfig {
	type: 'apprise';
	url: string;
	service_id?: string | null;
	fields?: Record<string, AppriseFieldValue>;
}

export interface WebhookConfig {
	type: 'webhook';
	url: string;
	shared_secret?: string | null;
	headers?: Record<string, string> | null;
}

export interface BashConfig {
	type: 'bash';
	script_path: string;
}

export type ChannelConfig = AppriseConfig | WebhookConfig | BashConfig;

export interface ChannelTemplate {
	title?: string | null;
	body?: string | null;
}

export interface Channel {
	id: number;
	type: ChannelType;
	name: string;
	enabled: boolean;
	config: ChannelConfig;
	subscribed_events: string[];
	templates: Record<string, ChannelTemplate>;
	last_fired_at: string | null;
	last_success_at: string | null;
	last_error: string | null;
}

export interface ChannelCreate {
	type: ChannelType;
	name: string;
	enabled?: boolean;
	config: ChannelConfig;
	subscribed_events: string[];
	templates?: Record<string, ChannelTemplate>;
}

export interface ChannelUpdate {
	name?: string;
	enabled?: boolean;
	config?: ChannelConfig;
	subscribed_events?: string[];
	templates?: Record<string, ChannelTemplate>;
}

export type FieldType = 'string' | 'bool' | 'choice' | 'int' | 'float';

export interface CatalogField {
	key: string;
	label: string;
	type: FieldType;
	private: boolean;
	required: boolean;
	default?: string | number | boolean | null;
	values?: string[];
}

export interface CatalogService {
	id: string;
	name: string;
	docs_url: string;
	url_scheme: string;
	required_fields: CatalogField[];
	advanced_fields: CatalogField[];
}

export interface Catalog {
	featured: string[];
	services: CatalogService[];
}

export interface DispatchRow {
	id: number;
	channel_id: number;
	event_key: string;
	status: 'pending' | 'in_flight' | 'success' | 'failed';
	attempts: number;
	last_error: string | null;
	created_at: string | null;
	completed_at: string | null;
}

export interface DispatchStatus {
	id: number;
	status: 'pending' | 'in_flight' | 'success' | 'failed';
	attempts: number;
	last_error: string | null;
	completed_at: string | null;
}

export interface TestSendResult {
	sent_at: string;
	dispatch_id: number;
}

// Per-event template variable hints, keyed off event_key. Mirrors the
// contracts event schema fields available to str.format_map on the backend.
// Per-event template variables exposed to str.format_map on the backend.
// occurred_at is available on every event (the renderer dumps the full
// event); event_id / event_key are also accepted but omitted here as
// envelope plumbing not useful in a human-facing notification.
export const EVENT_VARIABLES: Record<EventKey, string[]> = {
	'job.started': ['job_id', 'job_title', 'job_disc_type', 'job_imdb_id', 'occurred_at', 'drive_mount'],
	'job.rip_complete': ['job_id', 'job_title', 'job_disc_type', 'job_imdb_id', 'occurred_at', 'rip_duration_seconds', 'track_count'],
	'job.transcode_complete': ['job_id', 'job_title', 'job_disc_type', 'job_imdb_id', 'occurred_at', 'transcode_duration_seconds', 'output_path'],
	'job.failed': ['job_id', 'job_title', 'job_disc_type', 'job_imdb_id', 'occurred_at', 'phase', 'error_message', 'error_code'],
	'job.manual_wait_required': ['job_id', 'job_title', 'job_disc_type', 'job_imdb_id', 'occurred_at', 'wait_minutes_remaining', 'reason'],
	'job.duplicate_detected': ['job_id', 'job_title', 'job_disc_type', 'job_imdb_id', 'occurred_at', 'existing_job_id', 'existing_output_path']
};

export const EVENT_LABELS: Record<EventKey, string> = {
	'job.started': 'Job started',
	'job.rip_complete': 'Rip complete',
	'job.transcode_complete': 'Transcode complete',
	'job.failed': 'Job failed',
	'job.manual_wait_required': 'Manual wait required',
	'job.duplicate_detected': 'Duplicate detected'
};

// Built-in title/body used when a channel leaves a template field blank.
// Mirror of arm-neu arm/notifications/templates.py _DEFAULTS — surfaced as
// placeholders so "optional" templates show what will be sent by default.
export const EVENT_DEFAULT_TEMPLATES: Record<EventKey, { title: string; body: string }> = {
	'job.started': {
		title: 'ARM started: {job_title}',
		body: 'Job {job_id} started ripping {job_title} ({job_disc_type}).'
	},
	'job.rip_complete': {
		title: 'Rip complete: {job_title}',
		body: 'Job {job_id} rip finished in {rip_duration_seconds}s, {track_count} tracks.'
	},
	'job.transcode_complete': {
		title: 'Transcode complete: {job_title}',
		body: 'Job {job_id} transcode finished in {transcode_duration_seconds}s. Output: {output_path}'
	},
	'job.failed': {
		title: 'ARM job failed: {job_title}',
		body: 'Job {job_id} failed during {phase}: {error_message}'
	},
	'job.manual_wait_required': {
		title: 'ARM waiting: {job_title}',
		body: 'Job {job_id} is waiting for manual input ({reason}). {wait_minutes_remaining} minutes remaining.'
	},
	'job.duplicate_detected': {
		title: 'Duplicate detected: {job_title}',
		body: 'Job {job_id} duplicates existing job {existing_job_id}.'
	}
};

export function isCatalogField(v: unknown): v is CatalogField {
	if (typeof v !== 'object' || v === null) return false;
	const f = v as Record<string, unknown>;
	return typeof f.key === 'string' && typeof f.label === 'string' && typeof f.type === 'string';
}

// Shared input styling for the notification form fields, so the long
// Tailwind class string lives in one place (components can't reach the
// settings page's local inputClass constant).
export const FIELD_INPUT_CLASS =
	'rounded-md border border-primary/25 bg-primary/5 px-3 py-2 text-sm focus:border-primary focus:outline-hidden focus:ring-1 focus:ring-primary dark:border-primary/30 dark:bg-primary/10 dark:text-white';
