import { describe, it, expect, afterEach } from 'vitest';
import { renderComponent, cleanup } from '$lib/test-utils';
import FileIcon from './FileIcon.svelte';

describe('FileIcon', () => {
	afterEach(() => cleanup());

	it.each([
		['video', 'file-icon-video'],
		['directory', 'file-icon-directory'],
		['audio', 'file-icon-audio'],
		['image', 'file-icon-image'],
		['text', 'file-icon-text'],
		['archive', 'file-icon-archive'],
		['something_else', 'file-icon-other']
	])('renders %s icon with %s class', (category, expectedClass) => {
		const { container } = renderComponent(FileIcon, { props: { category } });
		const svg = container.querySelector('svg');
		expect(svg).toBeInTheDocument();
		expect(svg).toHaveClass(expectedClass);
	});
});
