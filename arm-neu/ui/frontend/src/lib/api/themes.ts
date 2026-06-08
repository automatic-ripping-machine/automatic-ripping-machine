import { apiFetch, apiFormPost } from './client';

export interface ThemeMeta {
	id: string;
	label: string;
	version?: number;
	author?: string;
	description?: string;
	swatch: string;
	mode?: 'light' | 'dark';
	builtin?: boolean;
	tokens: Record<string, string>;
}

export interface ThemeFull extends ThemeMeta {
	css: string;
}

export function fetchThemes(): Promise<ThemeMeta[]> {
	return apiFetch<ThemeMeta[]>('/api/themes');
}

export function fetchTheme(id: string): Promise<ThemeFull> {
	return apiFetch<ThemeFull>(`/api/themes/${encodeURIComponent(id)}`);
}

export function uploadTheme(themeJson: File, css: string = ''): Promise<ThemeFull> {
	const form = new FormData();
	form.append('theme_json', themeJson);
	form.append('theme_css', css);
	return apiFormPost<ThemeFull>('/api/themes', form);
}

export async function fetchThemeCss(id: string): Promise<string> {
	const res = await fetch(`/api/themes/${encodeURIComponent(id)}/css`);
	if (!res.ok) {
		throw new Error(`No CSS for theme '${id}'`);
	}
	return res.text();
}

export function deleteTheme(id: string): Promise<void> {
	return apiFetch<void>(`/api/themes/${encodeURIComponent(id)}`, {
		method: 'DELETE'
	});
}
