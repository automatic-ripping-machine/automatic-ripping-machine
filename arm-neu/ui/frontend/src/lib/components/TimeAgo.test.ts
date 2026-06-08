import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderComponent, screen, cleanup } from '$lib/test-utils';
import TimeAgo from './TimeAgo.svelte';

describe('TimeAgo', () => {
	beforeEach(() => {
		vi.useFakeTimers();
		vi.setSystemTime(new Date('2025-06-15T12:00:00Z'));
	});

	afterEach(() => {
		cleanup();
		vi.useRealTimers();
	});

	describe('rendering', () => {
		it('renders formatted time for a valid date', () => {
			renderComponent(TimeAgo, { props: { date: '2025-06-15T11:55:00Z' } });
			expect(screen.getByText('5m ago')).toBeInTheDocument();
		});

		it('renders N/A for null date', () => {
			renderComponent(TimeAgo, { props: { date: null } });
			expect(screen.getByText('N/A')).toBeInTheDocument();
		});

		it('sets title attribute to the raw date string', () => {
			renderComponent(TimeAgo, { props: { date: '2025-06-15T11:55:00Z' } });
			const span = screen.getByText('5m ago');
			expect(span).toHaveAttribute('title', '2025-06-15T11:55:00Z');
		});

		it('does not set title attribute for null date', () => {
			renderComponent(TimeAgo, { props: { date: null } });
			const span = screen.getByText('N/A');
			expect(span).not.toHaveAttribute('title');
		});
	});
});
