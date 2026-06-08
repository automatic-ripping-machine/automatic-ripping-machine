import { describe, it, expect, afterEach } from 'vitest';
import { renderComponent, screen, cleanup } from '$lib/test-utils';
import JobLifecycle from './JobLifecycle.svelte';

describe('JobLifecycle', () => {
	afterEach(() => cleanup());

	describe('size=md', () => {
		it('renders 5 stages for disc rip with stage labels', () => {
			renderComponent(JobLifecycle, {
				props: { status: 'video_ripping', sourceType: 'disc' }
			});
			expect(screen.getByText('Waiting')).toBeInTheDocument();
			expect(screen.getByText('Identifying')).toBeInTheDocument();
			expect(screen.getByText('Ripping')).toBeInTheDocument();
			expect(screen.getByText('Transcoding')).toBeInTheDocument();
			expect(screen.getByText('Complete')).toBeInTheDocument();
		});

		it('renders the same 5 stages for folder imports', () => {
			// folder_ripper still drives a MakeMKV remux pass, so folder imports
			// share the disc 5-stage lifecycle. An earlier 4-stage variant left
			// video_ripping on folder jobs unmapped.
			renderComponent(JobLifecycle, {
				props: { status: 'video_ripping', sourceType: 'folder' }
			});
			expect(screen.getByText('Waiting')).toBeInTheDocument();
			expect(screen.getByText('Identifying')).toBeInTheDocument();
			expect(screen.getByText('Ripping')).toBeInTheDocument();
			expect(screen.getByText('Transcoding')).toBeInTheDocument();
			expect(screen.getByText('Complete')).toBeInTheDocument();
		});

		it('marks the active stage with pulse animation class', () => {
			const { container } = renderComponent(JobLifecycle, {
				props: { status: 'transcoding', sourceType: 'disc' }
			});
			const pulsing = container.querySelectorAll('.lifecycle-pulse');
			// Exactly one stage should be actively pulsing
			expect(pulsing.length).toBe(1);
		});

		it('does not pulse on terminal failure', () => {
			const { container } = renderComponent(JobLifecycle, {
				props: { status: 'fail', sourceType: 'disc' }
			});
			const pulsing = container.querySelectorAll('.lifecycle-pulse');
			expect(pulsing.length).toBe(0);
		});

		it('does not pulse on success', () => {
			const { container } = renderComponent(JobLifecycle, {
				props: { status: 'success', sourceType: 'disc' }
			});
			const pulsing = container.querySelectorAll('.lifecycle-pulse');
			expect(pulsing.length).toBe(0);
		});
	});

	describe('size=sm', () => {
		it('renders without text labels for compact display', () => {
			renderComponent(JobLifecycle, {
				props: { status: 'transcoding', sourceType: 'disc', size: 'sm' }
			});
			// No stage labels in DOM in sm mode - they live on the title attribute only
			expect(screen.queryByText('Transcoding')).toBeNull();
			expect(screen.queryByText('Waiting')).toBeNull();
		});

		it('exposes lifecycle as accessible aria-label', () => {
			renderComponent(JobLifecycle, {
				props: { status: 'transcoding', sourceType: 'disc', size: 'sm' }
			});
			const widget = screen.getByRole('img', { name: 'Job lifecycle' });
			expect(widget).toBeInTheDocument();
			// Title attr carries the per-stage state for hover tooltip
			expect(widget.getAttribute('title')).toContain('Transcoding: active');
		});

		it('renders the same number of segments as nodes', () => {
			const { container } = renderComponent(JobLifecycle, {
				props: { status: 'transcoding', sourceType: 'disc', size: 'sm' }
			});
			// 5 segments for disc rip
			const segments = container.querySelectorAll('span.relative');
			expect(segments.length).toBe(5);
		});
	});

	describe('paused state', () => {
		it('shows pause icon on the active stage', () => {
			const { container } = renderComponent(JobLifecycle, {
				props: { status: 'manual_paused', sourceType: 'disc' }
			});
			// Lucide Pause renders as an svg with class containing 'lucide-pause'
			const pauseIcons = container.querySelectorAll('svg.lucide-pause');
			expect(pauseIcons.length).toBe(1);
		});
	});
});
