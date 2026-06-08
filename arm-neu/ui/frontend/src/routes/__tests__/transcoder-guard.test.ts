import { describe, it, expect, beforeEach, vi } from 'vitest';
import { setTranscoderEnabled } from '$lib/stores/config';

vi.mock('@sveltejs/kit', () => ({
	redirect: (status: number, location: string) => {
		const e = new Error(`redirect ${status} ${location}`) as Error & {
			status: number;
			location: string;
		};
		e.status = status;
		e.location = location;
		throw e;
	}
}));

const GUARDED_ROUTES = [
	{ name: 'transcoder route guard', path: '../transcoder/+page' },
	{ name: 'logs/transcoder/[filename] route guard', path: '../logs/transcoder/[filename]/+page' },
] as const;

describe.each(GUARDED_ROUTES)('$name', ({ path }) => {
	beforeEach(() => {
		setTranscoderEnabled(true);
	});

	it('redirects to / when transcoder is disabled', async () => {
		setTranscoderEnabled(false);
		const { load } = await import(/* @vite-ignore */ path);
		await expect(load({} as never)).rejects.toThrow(/redirect 302 \//);
	});

	it('passes through when transcoder is enabled', async () => {
		setTranscoderEnabled(true);
		const { load } = await import(/* @vite-ignore */ path);
		const result = await load({} as never);
		expect(result).toEqual({});
	});
});
