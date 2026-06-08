import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderComponent, screen, fireEvent, cleanup } from '$lib/test-utils';
import CountdownTimer from './CountdownTimer.svelte';

describe('CountdownTimer', () => {
	beforeEach(() => {
		vi.useFakeTimers();
		vi.setSystemTime(new Date('2025-06-15T12:00:00Z'));
	});

	afterEach(() => {
		cleanup();
		vi.useRealTimers();
	});

	describe('rendering', () => {
		it('displays remaining time', () => {
			renderComponent(CountdownTimer, {
				props: { startTime: '2025-06-15T12:00:00Z', waitSeconds: 120 }
			});
			expect(screen.getByText('2m 00s')).toBeInTheDocument();
		});

		it('displays Auto-proceeding when expired', () => {
			renderComponent(CountdownTimer, {
				props: { startTime: '2025-06-15T11:58:00Z', waitSeconds: 60 }
			});
			expect(screen.getByText('Auto-proceeding...')).toBeInTheDocument();
		});

		it('displays Paused when paused and expired', () => {
			renderComponent(CountdownTimer, {
				props: { startTime: '2025-06-15T11:58:00Z', waitSeconds: 60, paused: true }
			});
			expect(screen.getByText('Paused')).toBeInTheDocument();
		});

		it('displays Paused when paused with time remaining', () => {
			renderComponent(CountdownTimer, {
				props: { startTime: '2025-06-15T12:00:00Z', waitSeconds: 120, paused: true }
			});
			expect(screen.getByText('Paused')).toBeInTheDocument();
			expect(screen.queryByText('2m 00s')).not.toBeInTheDocument();
		});

		it('hides progress bar when paused', () => {
			const { container } = renderComponent(CountdownTimer, {
				props: { startTime: '2025-06-15T12:00:00Z', waitSeconds: 120, paused: true }
			});
			const progressBar = container.querySelector('[data-progress-fill]');
			expect(progressBar).not.toBeInTheDocument();
		});
	});

	describe('interactions', () => {
		it('shows pause button title when running', () => {
			renderComponent(CountdownTimer, {
				props: { startTime: '2025-06-15T12:00:00Z', waitSeconds: 120 }
			});
			expect(screen.getByTitle('Pause timer')).toBeInTheDocument();
		});

		it('shows resume button title when paused', () => {
			renderComponent(CountdownTimer, {
				props: { startTime: '2025-06-15T12:00:00Z', waitSeconds: 120, paused: true }
			});
			expect(screen.getByTitle('Resume timer')).toBeInTheDocument();
		});

		it('calls onpause when pause button is clicked', async () => {
			const onpause = vi.fn();
			renderComponent(CountdownTimer, {
				props: { startTime: '2025-06-15T12:00:00Z', waitSeconds: 120, onpause }
			});
			await fireEvent.click(screen.getByTitle('Pause timer'));
			expect(onpause).toHaveBeenCalledOnce();
		});

		it('calls onresume when resume button is clicked while paused', async () => {
			const onresume = vi.fn();
			renderComponent(CountdownTimer, {
				props: { startTime: '2025-06-15T12:00:00Z', waitSeconds: 120, paused: true, onresume }
			});
			await fireEvent.click(screen.getByTitle('Resume timer'));
			expect(onresume).toHaveBeenCalledOnce();
		});
	});
});
