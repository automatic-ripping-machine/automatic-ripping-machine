import { describe, it, expect, vi } from 'vitest';

const mockFetchSetupStatus = vi.fn();

vi.mock('$lib/api/setup', () => ({
	fetchSetupStatus: (...args: unknown[]) => mockFetchSetupStatus(...args)
}));

// Mock SvelteKit redirect
vi.mock('@sveltejs/kit', () => ({
	redirect: (status: number, location: string) => {
		const err = new Error('redirect');
		(err as any).status = status;
		(err as any).location = location;
		return err;
	}
}));

describe('setup page load', () => {
	it('redirects to / when setup is complete', async () => {
		mockFetchSetupStatus.mockResolvedValue({
			db_initialized: true,
			db_current: true,
			first_run: false,
		});

		const { load } = await import('../+page');

		await expect(load()).rejects.toMatchObject({ status: 302, location: '/' });
	});

	it('returns status when setup is not complete', async () => {
		mockFetchSetupStatus.mockResolvedValue({
			db_initialized: false,
			db_current: false,
			first_run: true,
		});

		const { load } = await import('../+page');
		const result = await load();

		expect(result).toEqual({
			status: { db_initialized: false, db_current: false, first_run: true }
		});
	});

	it('returns status when db not current', async () => {
		mockFetchSetupStatus.mockResolvedValue({
			db_initialized: true,
			db_current: false,
			first_run: false,
		});

		const { load } = await import('../+page');
		const result = await load();

		expect(result.status).toBeTruthy();
		expect(result.status!.db_current).toBe(false);
	});

	it('returns null status on fetch error', async () => {
		mockFetchSetupStatus.mockRejectedValue(new Error('network error'));

		const { load } = await import('../+page');
		const result = await load();

		expect(result).toEqual({ status: null });
	});
});
