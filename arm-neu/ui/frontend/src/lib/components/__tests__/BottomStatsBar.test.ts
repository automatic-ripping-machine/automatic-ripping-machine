import { describe, it, expect, afterEach } from 'vitest';
import { renderComponent, screen, fireEvent, cleanup } from '$lib/test-utils';
import BottomStatsBar from '../BottomStatsBar.svelte';

const systemStats = {
	cpu_percent: 25,
	cpu_temp: 0,
	memory: { used_gb: 4, total_gb: 16, percent: 25 },
	storage: [
		{ name: 'Raw', path: '/home/arm/media/raw/', total_gb: 1000, used_gb: 100, free_gb: 900, percent: 10 },
		{ name: 'Completed', path: '/home/arm/media/completed/', total_gb: 1000, used_gb: 200, free_gb: 800, percent: 20 }
	],
	gpu: null
};

const transcoderStats = {
	cpu_percent: 60,
	cpu_temp: 0,
	memory: { used_gb: 8, total_gb: 32, percent: 25 },
	storage: [
		{ name: 'Work', path: '/transcode/work/', total_gb: 500, used_gb: 50, free_gb: 450, percent: 10 }
	],
	gpu: null
};

const gpuData = {
	vendor: 'nvidia',
	utilization_percent: 82,
	encoder_percent: 95,
	memory_used_mb: 4096,
	memory_total_mb: 8192,
	temperature_c: 72,
	power_draw_w: 220,
	power_limit_w: 300,
	clock_core_mhz: 1950,
	clock_memory_mhz: 7500
};

const hwInfo = { cpu: 'Intel i7-12700', memory_total_gb: 16 };
const transcoderInfo = { cpu: 'AMD Ryzen 9', memory_total_gb: 32 };

/** Render BottomStatsBar with ripper defaults. Extra props merged on top. */
function renderBar(extraProps: Record<string, unknown> = {}) {
	return renderComponent(BottomStatsBar, {
		props: { systemInfo: hwInfo, systemStats, ...extraProps }
	});
}

/** Render with full transcoder props (optionally with GPU). */
function renderWithTranscoder(gpu: typeof gpuData | null = null) {
	return renderBar({
		transcoderInfo,
		transcoderStats: gpu ? { ...transcoderStats, gpu } : transcoderStats
	});
}

describe('BottomStatsBar', () => {
	afterEach(() => cleanup());

	it('renders Ripper and Transcoder toggle buttons', () => {
		renderBar();
		expect(screen.getByText('Ripper')).toBeInTheDocument();
		expect(screen.getByText('Transcoder')).toBeInTheDocument();
	});

	it('shows CPU percentage when systemStats provided', () => {
		renderBar();
		expect(screen.getByText('CPU')).toBeInTheDocument();
		expect(screen.getByText('25%')).toBeInTheDocument();
	});

	it('shows memory stats when systemStats provided', () => {
		renderBar();
		expect(screen.getByText('Mem')).toBeInTheDocument();
		expect(screen.getByText('4 / 16 GB')).toBeInTheDocument();
	});

	it('shows storage volumes with links when ripper panel active', () => {
		renderBar();
		expect(screen.getByText('Raw')).toBeInTheDocument();
		expect(screen.getByText('Completed')).toBeInTheDocument();
		const rawLink = screen.getByText('Raw').closest('a');
		expect(rawLink).toBeInTheDocument();
		expect(rawLink).toHaveAttribute('href', '/files?path=%2Fhome%2Farm%2Fmedia%2Fraw');
		const completedLink = screen.getByText('Completed').closest('a');
		expect(completedLink).toBeInTheDocument();
		expect(completedLink).toHaveAttribute('href', '/files?path=%2Fhome%2Farm%2Fmedia%2Fcompleted');
	});

	it('shows free GB for storage volumes', () => {
		renderBar();
		expect(screen.getByText('900 GB')).toBeInTheDocument();
		expect(screen.getByText('800 GB')).toBeInTheDocument();
	});

	it('shows offline message when armOnline is false', () => {
		renderBar({ armOnline: false });
		expect(screen.getByText('Cannot reach the ARM ripping service')).toBeInTheDocument();
	});

	it('switches to transcoder panel and shows transcoder stats', async () => {
		renderWithTranscoder();
		await fireEvent.click(screen.getByText('Transcoder'));
		expect(screen.getByText('60%')).toBeInTheDocument();
		expect(screen.getByText('8 / 32 GB')).toBeInTheDocument();
	});

	it('shows transcoder storage as plain text (not links)', async () => {
		renderWithTranscoder();
		await fireEvent.click(screen.getByText('Transcoder'));
		expect(screen.getByText('Work')).toBeInTheDocument();
		const workEl = screen.getByText('Work');
		expect(workEl.closest('a')).toBeNull();
	});

	it('shows transcoder offline message when transcoderOnline is false', async () => {
		renderBar({ transcoderOnline: false });
		await fireEvent.click(screen.getByText('Transcoder'));
		expect(screen.getByText('Cannot reach the transcoder service')).toBeInTheDocument();
	});

	it('shows nothing when systemStats is null and online', () => {
		renderComponent(BottomStatsBar, {
			props: { systemInfo: null, systemStats: null }
		});
		expect(screen.getByText('Ripper')).toBeInTheDocument();
		expect(screen.queryByText('CPU')).not.toBeInTheDocument();
		expect(screen.queryByText('Mem')).not.toBeInTheDocument();
	});

	describe('GPU tab', () => {
		it('shows GPU toggle when transcoder has GPU data', () => {
			renderWithTranscoder(gpuData);
			expect(screen.getByText('GPU')).toBeInTheDocument();
		});

		it('does not show GPU toggle when gpu is null', () => {
			renderWithTranscoder();
			expect(screen.queryByRole('button', { name: 'GPU' })).not.toBeInTheDocument();
		});

		it('shows GPU metrics when GPU tab clicked', async () => {
			renderWithTranscoder(gpuData);
			await fireEvent.click(screen.getByText('GPU'));
			expect(screen.getByText('nvidia')).toBeInTheDocument();
			expect(screen.getByText('Load')).toBeInTheDocument();
			expect(screen.getByText('82%')).toBeInTheDocument();
			expect(screen.getByText('Encoder')).toBeInTheDocument();
			expect(screen.getByText('95%')).toBeInTheDocument();
			expect(screen.getByText('VRAM')).toBeInTheDocument();
			expect(screen.getByText('4.0 / 8.0 GB')).toBeInTheDocument();
		});

		it('shows power and clock on GPU tab', async () => {
			renderWithTranscoder(gpuData);
			await fireEvent.click(screen.getByText('GPU'));
			expect(screen.getByText(/220W/)).toBeInTheDocument();
			expect(screen.getByText(/300W/)).toBeInTheDocument();
			expect(screen.getByText('1950 MHz')).toBeInTheDocument();
		});

		it('shows GPU temperature on GPU tab', async () => {
			renderWithTranscoder(gpuData);
			await fireEvent.click(screen.getByText('GPU'));
			expect(screen.getByText(/72/)).toBeInTheDocument();
		});
	});
});
