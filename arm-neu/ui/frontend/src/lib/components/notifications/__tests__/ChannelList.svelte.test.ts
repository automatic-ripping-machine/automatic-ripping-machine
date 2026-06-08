import { describe, it, expect, afterEach } from 'vitest';
import { renderComponent, screen, cleanup } from '$lib/test-utils';
import ChannelList from '../ChannelList.svelte';
import type { Channel, Catalog } from '$lib/types/notifications';

const catalog: Catalog = { featured: [], services: [] };
const channels: Channel[] = [
	{ id: 1, type: 'webhook', name: 'Hook A', enabled: true, config: { type: 'webhook', url: 'https://a' }, subscribed_events: [], templates: {}, last_fired_at: null, last_success_at: null, last_error: null },
	{ id: 2, type: 'webhook', name: 'Hook B', enabled: false, config: { type: 'webhook', url: 'https://b' }, subscribed_events: [], templates: {}, last_fired_at: null, last_success_at: null, last_error: null }
];

describe('ChannelList', () => {
	afterEach(() => cleanup());

	it('renders a row per channel', () => {
		renderComponent(ChannelList, { props: { channels, catalog, expandedId: null, serviceNameFor: () => 'Service' } });
		expect(screen.getByText('Hook A')).toBeInTheDocument();
		expect(screen.getByText('Hook B')).toBeInTheDocument();
	});

	it('mounts the editor under the expanded channel only', () => {
		renderComponent(ChannelList, { props: { channels, catalog, expandedId: 1, serviceNameFor: () => 'Service' } });
		expect(screen.getAllByRole('button', { name: /save changes/i })).toHaveLength(1);
	});
});
