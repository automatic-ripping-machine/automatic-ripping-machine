import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderComponent, screen, fireEvent, cleanup } from '$lib/test-utils';
import ServiceDropdown from '../ServiceDropdown.svelte';
import type { Catalog } from '$lib/types/notifications';

const catalog: Catalog = {
	featured: ['discord', 'slack'],
	services: [
		{ id: 'discord', name: 'Discord', docs_url: '', url_scheme: 'discord', required_fields: [], advanced_fields: [] },
		{ id: 'slack', name: 'Slack', docs_url: '', url_scheme: 'slack', required_fields: [], advanced_fields: [] },
		{ id: 'gotify', name: 'Gotify', docs_url: '', url_scheme: 'gotify', required_fields: [], advanced_fields: [] }
	]
};

describe('ServiceDropdown', () => {
	afterEach(() => cleanup());

	it('opens and shows Featured then all services', async () => {
		renderComponent(ServiceDropdown, { props: { catalog, selectedId: null } });
		await fireEvent.click(screen.getByRole('button', { name: /select a service/i }));
		expect(screen.getByText('Featured')).toBeInTheDocument();
		expect(screen.getByRole('button', { name: /Gotify/ })).toBeInTheDocument();
	});

	it('filters by search query', async () => {
		renderComponent(ServiceDropdown, { props: { catalog, selectedId: null } });
		await fireEvent.click(screen.getByRole('button', { name: /select a service/i }));
		await fireEvent.input(screen.getByPlaceholderText(/search/i), { target: { value: 'goti' } });
		expect(screen.getByRole('button', { name: /Gotify/ })).toBeInTheDocument();
		expect(screen.queryByRole('button', { name: /^Discord/ })).toBeNull();
	});

	it('calls onpick and closes when a service is chosen', async () => {
		const onpick = vi.fn();
		renderComponent(ServiceDropdown, { props: { catalog, selectedId: null, onpick } });
		await fireEvent.click(screen.getByRole('button', { name: /select a service/i }));
		await fireEvent.click(screen.getByRole('button', { name: /Gotify/ }));
		expect(onpick).toHaveBeenCalledWith('gotify');
	});
});
