import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderComponent, screen, cleanup } from '$lib/test-utils';
import TranscoderLogDetailPage from '../transcoder/[filename]/+page.svelte';

vi.mock('$app/stores', async () => {
	const { readable } = await import('svelte/store');
	return {
		page: readable({ params: { filename: 'transcode_001.log' } })
	};
});

vi.mock('$lib/api/logs', () => ({
	fetchStructuredTranscoderLogContent: vi.fn(() => Promise.resolve({ entries: [] })),
	fetchStructuredLogContent: vi.fn(() => Promise.resolve({ entries: [] }))
}));

describe('Transcoder Log Detail Page', () => {
	afterEach(() => cleanup());

	it('renders the filename as heading', () => {
		renderComponent(TranscoderLogDetailPage);
		expect(screen.getByText('transcode_001.log')).toBeInTheDocument();
	});

	it('renders Transcoder badge', () => {
		renderComponent(TranscoderLogDetailPage);
		expect(screen.getByText('Transcoder')).toBeInTheDocument();
	});

	it('renders back link to /logs', () => {
		renderComponent(TranscoderLogDetailPage);
		const link = screen.getByText('Logs');
		expect(link.closest('a')).toHaveAttribute('href', '/logs');
	});
});
