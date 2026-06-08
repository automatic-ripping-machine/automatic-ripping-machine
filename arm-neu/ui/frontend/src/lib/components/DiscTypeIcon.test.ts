import { describe, it, expect, afterEach } from 'vitest';
import { renderComponent, screen, cleanup } from '$lib/test-utils';
import DiscTypeIcon from './DiscTypeIcon.svelte';

describe('DiscTypeIcon', () => {
	afterEach(() => cleanup());

	it.each([
		['dvd', 'DVD', '/img/disc-dvd.svg'],
		['bluray', 'Blu-ray', '/img/disc-bluray.svg'],
		['bluray4k', '4K UHD', '/img/disc-bluray4k.svg'],
		['music', 'CD', '/img/disc-music.svg'],
		['laserdisc', 'Unknown', '/img/disc-unknown.svg']
	])('renders %s as alt="%s" with src=%s', (disctype, alt, src) => {
		renderComponent(DiscTypeIcon, { props: { disctype } });
		const img = screen.getByAltText(alt);
		expect(img).toHaveAttribute('src', src);
	});

	it('renders null disctype as Unknown', () => {
		renderComponent(DiscTypeIcon, { props: { disctype: null } });
		const img = screen.getByAltText('Unknown');
		expect(img).toHaveAttribute('src', '/img/disc-unknown.svg');
	});

	it('applies default size class', () => {
		renderComponent(DiscTypeIcon, { props: { disctype: 'dvd' } });
		expect(screen.getByAltText('DVD')).toHaveClass('h-6', 'w-6');
	});

	it('applies custom size class', () => {
		renderComponent(DiscTypeIcon, { props: { disctype: 'dvd', size: 'h-4 w-4' } });
		expect(screen.getByAltText('DVD')).toHaveClass('h-4', 'w-4');
	});
});
