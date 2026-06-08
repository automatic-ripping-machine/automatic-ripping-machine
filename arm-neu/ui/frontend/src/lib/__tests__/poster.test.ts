import { describe, it, expect } from 'vitest';
import { posterSrc, posterFallback, POSTER_PLACEHOLDER } from '../utils/poster';

describe('posterSrc', () => {
	it('returns placeholder for null', () => {
		expect(posterSrc(null)).toBe(POSTER_PLACEHOLDER);
	});

	it('returns placeholder for undefined', () => {
		expect(posterSrc(undefined)).toBe(POSTER_PLACEHOLDER);
	});

	it('returns placeholder for empty string', () => {
		expect(posterSrc('')).toBe(POSTER_PLACEHOLDER);
	});

	it('returns relative path unchanged', () => {
		expect(posterSrc('/images/poster.jpg')).toBe('/images/poster.jpg');
	});

	it('proxies https URL through backend', () => {
		const url = 'https://m.media-amazon.com/images/poster.jpg';
		expect(posterSrc(url)).toBe(
			`/api/images/proxy?url=${encodeURIComponent(url)}`
		);
	});

	it('proxies https URL from tmdb through backend', () => {
		const url = 'https://image.tmdb.org/t/p/w500/poster.jpg';
		expect(posterSrc(url)).toBe(
			`/api/images/proxy?url=${encodeURIComponent(url)}`
		);
	});

	it('returns path-only strings unchanged', () => {
		expect(posterSrc('poster.jpg')).toBe('poster.jpg');
	});
});

describe('posterFallback', () => {
	it('sets img src to placeholder on error', () => {
		const img = { src: 'https://broken.com/img.jpg' } as HTMLImageElement;
		posterFallback({ target: img } as unknown as Event);
		expect(img.src).toBe(POSTER_PLACEHOLDER);
	});

	it('does not loop if already showing placeholder', () => {
		const img = { src: POSTER_PLACEHOLDER } as HTMLImageElement;
		posterFallback({ target: img } as unknown as Event);
		expect(img.src).toBe(POSTER_PLACEHOLDER);
	});

	it('does not loop if src ends with placeholder filename', () => {
		const img = { src: 'http://localhost:8888/img/poster-placeholder.svg' } as HTMLImageElement;
		posterFallback({ target: img } as unknown as Event);
		expect(img.src).toBe('http://localhost:8888/img/poster-placeholder.svg');
	});
});
