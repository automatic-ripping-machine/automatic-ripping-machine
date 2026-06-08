import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderComponent, screen, fireEvent, cleanup } from '$lib/test-utils';
import ChannelRow from '../ChannelRow.svelte';
import type { Channel } from '$lib/types/notifications';

const ch: Channel = {
	id: 1, type: 'apprise', name: 'Discord', enabled: true,
	config: { type: 'apprise', url: 'discord://a/b' },
	subscribed_events: ['job.started', 'job.failed'], templates: {},
	last_fired_at: new Date(Date.now() - 10 * 60000).toISOString(),
	last_success_at: null, last_error: null
};

describe('ChannelRow', () => {
	afterEach(() => cleanup());

	it('shows name, event count, and last-fired time', () => {
		renderComponent(ChannelRow, { props: { channel: ch, serviceName: 'Discord' } });
		expect(screen.getByText('Discord')).toBeInTheDocument();
		expect(screen.getByText(/2 events/)).toBeInTheDocument();
		expect(screen.getByText(/10m ago/)).toBeInTheDocument();
	});

	it('shows the error in the secondary line when present', () => {
		renderComponent(ChannelRow, { props: { channel: { ...ch, last_error: 'HTTP 502' }, serviceName: 'Discord' } });
		expect(screen.getByText(/HTTP 502/)).toBeInTheDocument();
	});

	it('toggle click fires ontoggle but not onexpand', async () => {
		const ontoggle = vi.fn();
		const onexpand = vi.fn();
		renderComponent(ChannelRow, { props: { channel: ch, serviceName: 'Discord', ontoggle, onexpand } });
		await fireEvent.click(screen.getByRole('switch', { name: /enabled/i }));
		expect(ontoggle).toHaveBeenCalled();
		expect(onexpand).not.toHaveBeenCalled();
	});
});
