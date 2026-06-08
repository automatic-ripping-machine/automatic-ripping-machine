import { writable, derived, get } from 'svelte/store';
import { browser } from '$app/environment';
import { fetchThemes, fetchTheme } from '$lib/api/themes';

export interface ColorScheme {
	id: string;
	label: string;
	/** Hex color for the swatch preview */
	swatch: string;
	/** Lock the theme to light or dark mode when this scheme is active */
	mode?: 'light' | 'dark';
	tokens: Record<string, string>;
	/** Custom CSS injected at runtime */
	css?: string;
	/** Theme author */
	author?: string;
	/** Theme description */
	description?: string;
	/** Whether this is a built-in theme */
	builtin?: boolean;
}

/**
 * Color tokens applied as CSS custom properties on :root.
 * Tailwind v4 references them via `color-mix()` for opacity modifiers.
 * These are the compiled-in fallbacks that work even when the backend is down.
 */
export const COLOR_SCHEMES: ColorScheme[] = [
	{
		id: 'blue',
		label: 'Default',
		swatch: '#3b82f6',
		tokens: {
			'--color-primary': 'rgb(37, 99, 235)',          // blue-600
			'--color-primary-hover': 'rgb(29, 78, 216)',    // blue-700
			'--color-primary-dark': 'rgb(30, 64, 175)',     // blue-800
			'--color-primary-light-bg': 'rgb(219, 234, 254)', // blue-100
			'--color-primary-light-bg-dark': 'rgb(30, 58, 138)', // blue-900
			'--color-primary-text': 'rgb(29, 78, 216)',     // blue-700
			'--color-primary-text-dark': 'rgb(96, 165, 250)', // blue-400
			'--color-primary-border': 'rgb(59, 130, 246)',  // blue-500
			'--color-on-primary': 'rgb(255, 255, 255)',     // white
			'--color-page': 'rgb(232, 240, 255)',           // blue-tinted light
			'--color-page-dark': 'rgb(13, 16, 28)',         // dark navy
			'--color-surface': 'rgb(241, 247, 255)',        // blue-tinted surface
			'--color-surface-dark': 'rgb(22, 28, 45)',      // blue-tinted dark
			'--radius': '0.5rem'
		}
	},
	{
		id: 'sunset',
		label: 'Red Alert',
		swatch: '#ef4444',
		tokens: {
			'--color-primary': 'rgb(220, 38, 38)',          // red-600
			'--color-primary-hover': 'rgb(185, 28, 28)',    // red-700
			'--color-primary-dark': 'rgb(153, 27, 27)',     // red-800
			'--color-primary-light-bg': 'rgb(254, 226, 226)', // red-100
			'--color-primary-light-bg-dark': 'rgb(127, 29, 29)', // red-900
			'--color-primary-text': 'rgb(185, 28, 28)',     // red-700
			'--color-primary-text-dark': 'rgb(248, 113, 113)', // red-400
			'--color-primary-border': 'rgb(239, 68, 68)',   // red-500
			'--color-on-primary': 'rgb(255, 255, 255)',     // white
			'--color-page': 'rgb(255, 235, 235)',           // red-tinted light
			'--color-page-dark': 'rgb(38, 0, 0)',           // dark red
			'--color-surface': 'rgb(255, 243, 243)',        // red-tinted surface
			'--color-surface-dark': 'rgb(68, 1, 0)',         // red alert dark
			'--radius': '0.5rem'
		}
	},
	{
		id: 'stealth-ops',
		label: 'Stealth',
		swatch: '#ef4444',
		mode: 'dark',
		author: 'Gemini',
		description: 'Tactical monochrome with critical red highlights',
		tokens: {
			'--color-primary': 'rgb(239, 68, 68)',
			'--color-primary-hover': 'rgb(220, 38, 38)',
			'--color-primary-dark': 'rgb(153, 27, 27)',
			'--color-primary-light-bg': 'rgb(30, 10, 10)',
			'--color-primary-light-bg-dark': 'rgb(20, 5, 5)',
			'--color-primary-text': 'rgb(248, 113, 113)',
			'--color-primary-text-dark': 'rgb(252, 165, 165)',
			'--color-primary-border': 'rgb(239, 68, 68)',
			'--color-on-primary': 'rgb(255, 255, 255)',
			'--color-page': 'rgb(10, 10, 10)',
			'--color-page-dark': 'rgb(5, 5, 5)',
			'--color-surface': 'rgb(20, 20, 20)',
			'--color-surface-dark': 'rgb(15, 15, 15)',
			'--radius': '0.5rem'
		},
		css: '[data-scheme="stealth-ops"] .section-frame {\n\tborder: 1px solid #222 !important;\n}\n[data-scheme="stealth-ops"] .section-frame-bar-top {\n\tbackground: #111 !important;\n\tcolor: #666 !important;\n\tborder-bottom: 1px solid #222;\n\ttext-transform: uppercase;\n\tletter-spacing: 0.2em;\n}\n[data-scheme="stealth-ops"] aside nav a[data-active="true"] {\n\tcolor: #ef4444 !important;\n\tbackground: transparent !important;\n\tborder-right: 2px solid #ef4444;\n}\n[data-scheme="stealth-ops"] [data-progress-fill] {\n\tbackground: #ef4444 !important;\n\tbox-shadow: 0 0 15px rgba(239, 68, 68, 0.4);\n}'
	},
	{
		id: 'library-archive',
		label: 'Library',
		swatch: '#7f1d1d',
		mode: 'light',
		author: 'Gemini',
		description: 'Paper and ink aesthetic for a classic media library feel',
		tokens: {
			'--color-primary': 'rgb(127, 29, 29)',
			'--color-primary-hover': 'rgb(153, 27, 27)',
			'--color-primary-dark': 'rgb(69, 10, 10)',
			'--color-primary-light-bg': 'rgb(254, 242, 242)',
			'--color-primary-light-bg-dark': 'rgb(24, 10, 10)',
			'--color-primary-text': 'rgb(127, 29, 29)',
			'--color-primary-text-dark': 'rgb(248, 113, 113)',
			'--color-primary-border': 'rgb(185, 28, 28)',
			'--color-on-primary': 'rgb(255, 255, 255)',
			'--color-page': 'rgb(250, 247, 240)',
			'--color-page-dark': 'rgb(20, 18, 16)',
			'--color-surface': 'rgb(255, 255, 255)',
			'--color-surface-dark': 'rgb(28, 25, 23)',
			'--radius': '0.5rem'
		},
		css: '[data-scheme="library-archive"] {\n\tfont-family: \'Georgia\', serif;\n}\n[data-scheme="library-archive"] aside {\n\tbackground-color: rgb(240, 235, 220) !important;\n\tborder-right: 2px solid #ddd !important;\n}\n[data-scheme="library-archive"] .section-frame-bar-top {\n\tborder-bottom: 2px solid #333 !important;\n\tbackground: transparent !important;\n\tcolor: #333 !important;\n\tfont-family: \'Times New Roman\', serif;\n\tfont-variant: small-caps;\n}\n[data-scheme="library-archive"] [data-progress-fill] {\n\tbackground: #7f1d1d !important;\n\tborder-radius: 0 !important;\n}'
	},
	{
		id: 'synth-retro',
		label: 'Synth Retro',
		swatch: '#ff007f',
		mode: 'dark',
		author: 'Gemini',
		description: '80s neon synthwave aesthetic with pink and violet glows',
		tokens: {
			'--color-primary': 'rgb(255, 0, 127)',
			'--color-primary-hover': 'rgb(220, 0, 110)',
			'--color-primary-dark': 'rgb(150, 0, 80)',
			'--color-primary-light-bg': 'rgb(40, 0, 30)',
			'--color-primary-light-bg-dark': 'rgb(30, 0, 20)',
			'--color-primary-text': 'rgb(255, 0, 127)',
			'--color-primary-text-dark': 'rgb(255, 120, 200)',
			'--color-primary-border': 'rgb(255, 0, 127)',
			'--color-on-primary': 'rgb(255, 255, 255)',
			'--color-page': 'rgb(18, 12, 28)',
			'--color-page-dark': 'rgb(12, 8, 20)',
			'--color-surface': 'rgb(30, 20, 45)',
			'--color-surface-dark': 'rgb(22, 14, 32)',
			'--radius': '0.5rem'
		},
		css: '[data-scheme="synth-retro"] {\n\tfont-family: \'Inter\', sans-serif;\n}\n[data-scheme="synth-retro"] body {\n\tbackground-image: linear-gradient(to bottom, rgb(18, 12, 28) 0%, rgb(12, 8, 20) 100%);\n}\n[data-scheme="synth-retro"] aside nav a[data-active="true"] {\n\ttext-shadow: 0 0 10px rgb(255, 0, 127);\n\tborder-right: 3px solid rgb(255, 0, 127);\n}\n[data-scheme="synth-retro"] [data-progress-fill] {\n\tbackground: linear-gradient(90deg, rgb(150, 0, 80), rgb(255, 0, 127)) !important;\n\tbox-shadow: 0 0 12px rgba(255, 0, 127, 0.6);\n}'
	},
	{
		id: 'synth-retro-v2',
		label: 'Synth Noir',
		swatch: '#ff007f',
		mode: 'dark',
		author: 'Gemini',
		description: 'Refined vaporwave aesthetic focusing on neon outlines and depth',
		tokens: {
			'--color-primary': 'rgb(255, 0, 127)',
			'--color-primary-hover': 'rgb(220, 0, 110)',
			'--color-primary-dark': 'rgb(80, 0, 40)',
			'--color-primary-light-bg': 'rgb(25, 10, 20)',
			'--color-primary-light-bg-dark': 'rgb(20, 5, 15)',
			'--color-primary-text': 'rgb(255, 100, 180)',
			'--color-primary-text-dark': 'rgb(255, 150, 210)',
			'--color-primary-border': 'rgb(150, 0, 80)',
			'--color-on-primary': 'rgb(255, 255, 255)',
			'--color-page': 'rgb(10, 6, 14)',
			'--color-page-dark': 'rgb(8, 4, 10)',
			'--color-surface': 'rgb(18, 12, 24)',
			'--color-surface-dark': 'rgb(14, 10, 18)',
			'--radius': '0.5rem'
		},
		css: '[data-scheme="synth-retro-v2"] .section-frame {\n\tborder: 1px solid rgba(255, 0, 127, 0.2) !important;\n\tbackground: rgba(255, 0, 127, 0.02) !important;\n\tborder-radius: 4px;\n}\n[data-scheme="synth-retro-v2"] .section-frame-bar-top {\n\tbackground: linear-gradient(90deg, rgba(255, 0, 127, 0.4), transparent) !important;\n\tborder-bottom: 1px solid rgba(255, 0, 127, 0.3);\n\theight: 28px !important;\n}\n[data-scheme="synth-retro-v2"] aside {\n\tbackground: linear-gradient(180deg, rgb(14, 10, 18) 0%, rgb(8, 4, 10) 100%) !important;\n\tborder-right: 1px solid rgba(255, 0, 127, 0.1) !important;\n}\n[data-scheme="synth-retro-v2"] [data-progress-track] {\n\tbackground: rgba(255, 0, 127, 0.05) !important;\n\tborder: 1px solid rgba(255, 0, 127, 0.1);\n\theight: 6px !important;\n}\n[data-scheme="synth-retro-v2"] [data-progress-fill] {\n\tbackground: linear-gradient(90deg, #9333ea, #ff007f) !important;\n\tbox-shadow: 0 0 10px rgba(255, 0, 127, 0.5);\n}\n[data-scheme="synth-retro-v2"] aside nav a[data-active="true"] {\n\tcolor: #ff007f !important;\n\tbackground: rgba(255, 0, 127, 0.05) !important;\n\tborder-left: 3px solid #ff007f;\n\ttext-shadow: 0 0 8px rgba(255, 0, 127, 0.3);\n}'
	},
	{
		id: 'research-outpost',
		label: 'Outpost',
		swatch: '#f97316',
		mode: 'dark',
		author: 'Gemini',
		description: 'Arctic research facility aesthetic with safety orange accents',
		tokens: {
			'--color-primary': 'rgb(249, 115, 22)',
			'--color-primary-hover': 'rgb(234, 88, 12)',
			'--color-primary-dark': 'rgb(154, 52, 18)',
			'--color-primary-light-bg': 'rgb(40, 20, 10)',
			'--color-primary-light-bg-dark': 'rgb(25, 12, 8)',
			'--color-primary-text': 'rgb(251, 146, 60)',
			'--color-primary-text-dark': 'rgb(253, 186, 116)',
			'--color-primary-border': 'rgb(249, 115, 22)',
			'--color-on-primary': 'rgb(255, 255, 255)',
			'--color-page': 'rgb(15, 15, 20)',
			'--color-page-dark': 'rgb(12, 12, 16)',
			'--color-surface': 'rgb(28, 28, 35)',
			'--color-surface-dark': 'rgb(20, 20, 26)',
			'--radius': '0.5rem'
		},
		css: '[data-scheme="research-outpost"] .section-frame {\n\tborder: 1px solid rgba(249, 115, 22, 0.2) !important;\n\tborder-left: 4px solid #f97316 !important;\n}\n[data-scheme="research-outpost"] .section-frame-bar-top {\n\tbackground: linear-gradient(90deg, rgba(249, 115, 22, 0.3), transparent) !important;\n\tborder-bottom: 1px solid rgba(249, 115, 22, 0.2);\n\tcolor: #fdba74 !important;\n}\n[data-scheme="research-outpost"] aside {\n\tbackground: #0f0f14 !important;\n\tborder-right: 2px solid #1e1e24 !important;\n}\n[data-scheme="research-outpost"] [data-progress-fill] {\n\tbackground: linear-gradient(90deg, #f97316, #fbbf24) !important;\n}'
	},
	{
		id: 'lcars',
		label: 'LCARS',
		swatch: '#fb923c',
		mode: 'dark',
		tokens: {
			'--color-primary': 'rgb(255, 153, 0)',            // lcars orange
			'--color-primary-hover': 'rgb(255, 204, 51)',     // lcars yellow
			'--color-primary-dark': 'rgb(40, 30, 0)',         // dark orange
			'--color-primary-light-bg': 'rgb(153, 153, 255)', // lcars blue
			'--color-primary-light-bg-dark': 'rgb(30, 30, 60)', // dark blue
			'--color-primary-text': 'rgb(255, 204, 51)',      // yellow
			'--color-primary-text-dark': 'rgb(255, 153, 0)',  // orange
			'--color-primary-border': 'rgb(255, 153, 0)',     // orange
			'--color-on-primary': 'rgb(0, 0, 0)',             // black
			'--color-page': 'rgb(0, 0, 0)',                   // pure black
			'--color-page-dark': 'rgb(0, 0, 0)',
			'--color-surface': 'rgb(0, 0, 0)',                // pure black
			'--color-surface-dark': 'rgb(0, 0, 0)',
			'--radius': '20px'
		}
	},
	{
		id: 'coffee',
		label: 'Coffee',
		swatch: '#a0816c',
		mode: 'dark',
		author: 'Gemini',
		description: 'Warm earthy tones inspired by roasted coffee beans',
		tokens: {
			'--color-primary': 'rgb(160, 129, 108)',
			'--color-primary-hover': 'rgb(138, 108, 88)',
			'--color-primary-dark': 'rgb(90, 70, 55)',
			'--color-primary-light-bg': 'rgb(60, 56, 54)',
			'--color-primary-light-bg-dark': 'rgb(40, 40, 40)',
			'--color-primary-text': 'rgb(160, 129, 108)',
			'--color-primary-text-dark': 'rgb(235, 219, 178)',
			'--color-primary-border': 'rgb(160, 129, 108)',
			'--color-on-primary': 'rgb(40, 40, 40)',
			'--color-page': 'rgb(29, 32, 33)',
			'--color-page-dark': 'rgb(29, 32, 33)',
			'--color-surface': 'rgb(40, 40, 40)',
			'--color-surface-dark': 'rgb(40, 40, 40)',
			'--radius': '0.5rem'
		},
		css: '[data-scheme="coffee"] .section-frame {\n\tborder: 1px solid #504945 !important;\n\tborder-radius: var(--radius) !important;\n\toverflow: hidden;\n}\n[data-scheme="coffee"] .section-frame-bar-top {\n\tbackground: #504945 !important;\n\tcolor: #ebdbb2 !important;\n}\n[data-scheme="coffee"] [data-progress-fill] {\n\tbackground: rgb(160, 129, 108) !important;\n}'
	},
	{
		id: 'cinema',
		label: 'Cinema',
		swatch: '#ca8a04',
		mode: 'dark',
		tokens: {
			'--color-primary': 'rgb(212, 175, 55)',          // gold
			'--color-primary-hover': 'rgb(188, 155, 40)',    // darker gold
			'--color-primary-dark': 'rgb(138, 109, 59)',     // muted gold
			'--color-primary-light-bg': 'rgb(30, 25, 10)',   // dark gold tint
			'--color-primary-light-bg-dark': 'rgb(30, 25, 10)', // dark gold tint
			'--color-primary-text': 'rgb(212, 175, 55)',     // gold
			'--color-primary-text-dark': 'rgb(212, 175, 55)', // gold
			'--color-primary-border': 'rgb(138, 109, 59)',   // muted gold
			'--color-on-primary': 'rgb(13, 13, 13)',         // cinema black
			'--color-page': 'rgb(26, 26, 26)',               // dark gray
			'--color-page-dark': 'rgb(26, 26, 26)',          // dark gray
			'--color-surface': 'rgb(13, 13, 13)',            // cinema black
			'--color-surface-dark': 'rgb(13, 13, 13)',        // cinema black
			'--radius': '0.5rem'
		}
	},
	{
		id: 'royal-archive',
		label: 'Archive',
		swatch: '#fbbf24',
		mode: 'dark',
		author: 'Gemini',
		description: 'Sophisticated navy and gold for a premium archival feel',
		tokens: {
			'--color-primary': 'rgb(251, 191, 36)',
			'--color-primary-hover': 'rgb(245, 158, 11)',
			'--color-primary-dark': 'rgb(180, 83, 9)',
			'--color-primary-light-bg': 'rgb(30, 25, 10)',
			'--color-primary-light-bg-dark': 'rgb(20, 15, 5)',
			'--color-primary-text': 'rgb(251, 191, 36)',
			'--color-primary-text-dark': 'rgb(253, 230, 138)',
			'--color-primary-border': 'rgb(251, 191, 36)',
			'--color-on-primary': 'rgb(0, 0, 0)',
			'--color-page': 'rgb(15, 17, 23)',
			'--color-page-dark': 'rgb(10, 12, 18)',
			'--color-surface': 'rgb(30, 41, 59)',
			'--color-surface-dark': 'rgb(15, 23, 42)',
			'--radius': '0.5rem'
		},
		css: '[data-scheme="royal-archive"] .section-frame {\n\tborder: 1px solid rgba(251, 191, 36, 0.1) !important;\n}\n[data-scheme="royal-archive"] .section-frame-bar-top {\n\tbackground: #1e293b !important;\n\tcolor: #fbbf24 !important;\n\tborder-bottom: 2px solid #fbbf24;\n}\n[data-scheme="royal-archive"] [data-progress-fill] {\n\tbackground: linear-gradient(90deg, #b45309, #fbbf24) !important;\n}\n[data-scheme="royal-archive"] aside nav a[data-active="true"] {\n\tcolor: #fbbf24 !important;\n\tfont-weight: 900;\n}'
	},
	{
		id: 'royale',
		label: 'Royale',
		swatch: '#facc15',
		mode: 'dark',
		tokens: {
			'--color-primary': 'rgb(0, 123, 255)',            // fortnite blue
			'--color-primary-hover': 'rgb(248, 251, 17)',     // fortnite yellow
			'--color-primary-dark': 'rgb(17, 42, 94)',        // deep blue border
			'--color-primary-light-bg': 'rgb(11, 26, 61)',    // item bg
			'--color-primary-light-bg-dark': 'rgb(11, 26, 61)', // item bg
			'--color-primary-text': 'rgb(248, 251, 17)',      // yellow
			'--color-primary-text-dark': 'rgb(248, 251, 17)', // yellow
			'--color-primary-border': 'rgb(17, 42, 94)',      // deep blue
			'--color-on-primary': 'rgb(255, 255, 255)',       // white
			'--color-page': 'rgb(5, 5, 5)',                   // near-black
			'--color-page-dark': 'rgb(5, 5, 5)',              // near-black
			'--color-surface': 'rgb(2, 11, 36)',              // dark blue
			'--color-surface-dark': 'rgb(2, 11, 36)',          // dark blue
			'--radius': '0.5rem'
		}
	},
	{
		id: 'craft',
		label: 'Craft',
		swatch: '#22c55e',
		mode: 'dark',
		tokens: {
			'--color-primary': 'rgb(30, 130, 30)',            // darker MC green (readable headers)
			'--color-primary-hover': 'rgb(128, 128, 255)',    // MC hover blue
			'--color-primary-dark': 'rgb(34, 34, 34)',        // dark stone
			'--color-primary-light-bg': 'rgb(74, 74, 74)',    // pressed button
			'--color-primary-light-bg-dark': 'rgb(74, 74, 74)',
			'--color-primary-text': 'rgb(56, 255, 56)',       // MC green
			'--color-primary-text-dark': 'rgb(56, 255, 56)',
			'--color-primary-border': 'rgb(0, 0, 0)',         // black
			'--color-on-primary': 'rgb(255, 255, 255)',       // white
			'--color-page': 'rgb(30, 30, 30)',                // dark bg
			'--color-page-dark': 'rgb(30, 30, 30)',
			'--color-surface': 'rgb(49, 49, 49)',             // stone
			'--color-surface-dark': 'rgb(49, 49, 49)',
			'--radius': '0px'
		}
	},
	{
		id: 'terminal',
		label: 'Terminal',
		swatch: '#4ade80',
		mode: 'dark',
		tokens: {
			'--color-primary': 'rgb(57, 255, 20)',          // terminal green
			'--color-primary-hover': 'rgb(45, 200, 16)',    // dimmer green
			'--color-primary-dark': 'rgb(10, 26, 5)',       // dark green
			'--color-primary-light-bg': 'rgb(10, 26, 5)',   // dark green (light bg unused)
			'--color-primary-light-bg-dark': 'rgb(10, 26, 5)', // dark green
			'--color-primary-text': 'rgb(57, 255, 20)',     // terminal green
			'--color-primary-text-dark': 'rgb(57, 255, 20)', // terminal green
			'--color-primary-border': 'rgb(57, 255, 20)',   // terminal green
			'--color-on-primary': 'rgb(5, 5, 5)',           // near-black
			'--color-page': 'rgb(5, 5, 5)',                 // CRT black
			'--color-page-dark': 'rgb(5, 5, 5)',            // CRT black
			'--color-surface': 'rgb(8, 8, 8)',              // barely-off-black
			'--color-surface-dark': 'rgb(8, 8, 8)',          // barely-off-black
			'--radius': '0px'
		}
	},
	{
		id: 'forest',
		label: 'Forest',
		swatch: '#10b981',
		tokens: {
			'--color-primary': 'rgb(5, 150, 105)',          // emerald-600
			'--color-primary-hover': 'rgb(4, 120, 87)',     // emerald-700
			'--color-primary-dark': 'rgb(6, 95, 70)',       // emerald-800
			'--color-primary-light-bg': 'rgb(209, 250, 229)', // emerald-100
			'--color-primary-light-bg-dark': 'rgb(6, 78, 59)', // emerald-900
			'--color-primary-text': 'rgb(4, 120, 87)',      // emerald-700
			'--color-primary-text-dark': 'rgb(110, 231, 183)', // emerald-400
			'--color-primary-border': 'rgb(16, 185, 129)',  // emerald-500
			'--color-on-primary': 'rgb(255, 255, 255)',     // white
			'--color-page': 'rgb(228, 248, 238)',           // emerald-tinted light
			'--color-page-dark': 'rgb(12, 19, 15)',         // dark forest
			'--color-surface': 'rgb(237, 252, 244)',        // emerald-tinted surface
			'--color-surface-dark': 'rgb(21, 54, 37)',       // emerald-tinted dark
			'--radius': '0.5rem'
		}
	},
	{
		id: 'ocean',
		label: 'Ocean',
		swatch: '#14b8a6',
		tokens: {
			'--color-primary': 'rgb(13, 148, 136)',         // teal-600
			'--color-primary-hover': 'rgb(15, 118, 110)',   // teal-700
			'--color-primary-dark': 'rgb(17, 94, 89)',      // teal-800
			'--color-primary-light-bg': 'rgb(204, 251, 241)', // teal-100
			'--color-primary-light-bg-dark': 'rgb(19, 78, 74)', // teal-900
			'--color-primary-text': 'rgb(15, 118, 110)',    // teal-700
			'--color-primary-text-dark': 'rgb(94, 234, 212)', // teal-400
			'--color-primary-border': 'rgb(20, 184, 166)',  // teal-500
			'--color-on-primary': 'rgb(255, 255, 255)',     // white
			'--color-page': 'rgb(228, 248, 245)',           // teal-tinted light
			'--color-page-dark': 'rgb(12, 19, 20)',         // dark teal
			'--color-surface': 'rgb(238, 252, 249)',        // teal-tinted surface
			'--color-surface-dark': 'rgb(9, 69, 79)',        // teal-tinted dark
			'--radius': '0.5rem'
		}
	},
	{
		id: 'tactical',
		label: 'Tactical',
		swatch: '#2dd4bf',
		mode: 'dark',
		tokens: {
			'--color-primary': 'rgb(0, 120, 100)',            // darker teal (readable headers)
			'--color-primary-hover': 'rgb(80, 200, 175)',     // dimmer teal
			'--color-primary-dark': 'rgb(10, 25, 47)',        // navy
			'--color-primary-light-bg': 'rgb(10, 25, 47)',    // navy
			'--color-primary-light-bg-dark': 'rgb(10, 25, 47)',
			'--color-primary-text': 'rgb(100, 255, 218)',     // teal
			'--color-primary-text-dark': 'rgb(100, 255, 218)',
			'--color-primary-border': 'rgb(100, 255, 218)',   // teal
			'--color-on-primary': 'rgb(255, 255, 255)',       // white
			'--color-page': 'rgb(2, 6, 23)',                  // deep navy
			'--color-page-dark': 'rgb(2, 6, 23)',
			'--color-surface': 'rgb(10, 25, 47)',             // navy
			'--color-surface-dark': 'rgb(10, 25, 47)',
			'--radius': '0px'
		}
	},
	{
		id: 'deep-sea-abyss',
		label: 'Deep Sea',
		swatch: '#0ea5e9',
		mode: 'dark',
		author: 'Gemini',
		description: 'Deep oceanic blues with bioluminescent coral accents',
		tokens: {
			'--color-primary': 'rgb(0, 109, 109)',
			'--color-primary-hover': 'rgb(2, 132, 199)',
			'--color-primary-dark': 'rgb(7, 89, 133)',
			'--color-primary-light-bg': 'rgb(8, 20, 30)',
			'--color-primary-light-bg-dark': 'rgb(4, 15, 25)',
			'--color-primary-text': 'rgb(56, 189, 248)',
			'--color-primary-text-dark': 'rgb(125, 211, 252)',
			'--color-primary-border': 'rgb(12, 74, 110)',
			'--color-on-primary': 'rgb(255, 255, 255)',
			'--color-page': 'rgb(6, 10, 15)',
			'--color-page-dark': 'rgb(4, 7, 12)',
			'--color-surface': 'rgb(15, 23, 42)',
			'--color-surface-dark': 'rgb(10, 15, 25)',
			'--radius': '0.5rem'
		},
		css: '[data-scheme="deep-sea-abyss"] .section-frame {\n\tborder: 1px solid rgba(14, 165, 233, 0.1) !important;\n\tbox-shadow: inset 0 0 20px rgba(0, 0, 0, 0.5);\n}\n[data-scheme="deep-sea-abyss"] .section-frame-bar-top {\n\tbackground: rgba(14, 165, 233, 0.2) !important;\n\tcolor: rgb(125, 211, 252) !important;\n\tborder-bottom: 1px solid rgba(14, 165, 233, 0.15);\n}\n[data-scheme="deep-sea-abyss"] .section-frame-bar-bottom {\n\tbackground: rgba(14, 165, 233, 0.1) !important;\n}\n[data-scheme="deep-sea-abyss"] [data-progress-fill] {\n\tbackground: linear-gradient(90deg, #0ea5e9, #2dd4bf) !important;\n}\n[data-scheme="deep-sea-abyss"] aside nav a:hover {\n\tbackground: linear-gradient(90deg, rgba(14, 165, 233, 0.1), transparent) !important;\n}'
	},
	{
		id: 'nordic-frost',
		label: 'Nordic Frost',
		swatch: '#88c0d0',
		author: 'Gemini',
		description: 'Arctic-inspired dual-mode theme with frosty blues',
		tokens: {
			'--color-primary': 'rgb(136, 192, 208)',
			'--color-primary-hover': 'rgb(129, 161, 193)',
			'--color-primary-dark': 'rgb(94, 129, 172)',
			'--color-primary-light-bg': 'rgb(236, 239, 244)',
			'--color-primary-light-bg-dark': 'rgb(46, 52, 64)',
			'--color-primary-text': 'rgb(94, 129, 172)',
			'--color-primary-text-dark': 'rgb(143, 188, 187)',
			'--color-primary-border': 'rgb(136, 192, 208)',
			'--color-on-primary': 'rgb(46, 52, 64)',
			'--color-page': 'rgb(229, 233, 240)',
			'--color-page-dark': 'rgb(46, 52, 64)',
			'--color-surface': 'rgb(240, 244, 250)',
			'--color-surface-dark': 'rgb(59, 66, 82)',
			'--radius': '0.5rem'
		},
		css: '[data-scheme="nordic-frost"] .section-frame {\n\tborder: 1px solid rgba(136, 192, 208, 0.2) !important;\n}\n[data-scheme="nordic-frost"] .section-frame-bar-top {\n\tbackground: rgba(76, 86, 106, 0.8) !important;\n\tcolor: rgb(236, 239, 244) !important;\n}\n[data-scheme="nordic-frost"] .section-frame-bar-bottom {\n\tbackground: rgba(136, 192, 208, 0.15) !important;\n}\n[data-scheme="nordic-frost"] aside nav a[data-active="true"] {\n\tbackground: rgba(136, 192, 208, 0.15) !important;\n\tcolor: rgb(94, 129, 172) !important;\n}\n[data-scheme="nordic-frost"] [data-progress-track] {\n\tbackground: rgba(76, 86, 106, 0.3) !important;\n}'
	},
	{
		id: 'solarized-dark',
		label: 'Solarized',
		swatch: '#268bd2',
		mode: 'dark',
		author: 'Gemini',
		description: 'The classic precision-engineered developer theme',
		tokens: {
			'--color-primary': 'rgb(38, 139, 210)',
			'--color-primary-hover': 'rgb(42, 161, 152)',
			'--color-primary-dark': 'rgb(7, 54, 66)',
			'--color-primary-light-bg': 'rgb(0, 43, 54)',
			'--color-primary-light-bg-dark': 'rgb(0, 30, 38)',
			'--color-primary-text': 'rgb(38, 139, 210)',
			'--color-primary-text-dark': 'rgb(147, 161, 161)',
			'--color-primary-border': 'rgb(38, 139, 210)',
			'--color-on-primary': 'rgb(255, 255, 255)',
			'--color-page': 'rgb(0, 43, 54)',
			'--color-page-dark': 'rgb(0, 43, 54)',
			'--color-surface': 'rgb(7, 54, 66)',
			'--color-surface-dark': 'rgb(7, 54, 66)',
			'--radius': '0.25rem'
		},
		css: '[data-scheme="solarized-dark"] {\n\tletter-spacing: 0.02em;\n}\n[data-scheme="solarized-dark"] aside {\n\tbackground: #002b36 !important;\n\tborder-right: 1px solid #073642 !important;\n}\n[data-scheme="solarized-dark"] .section-frame-bar-top {\n\tbackground: #073642 !important;\n\tcolor: #93a1a1 !important;\n}'
	},
	{
		id: 'blockbuster',
		label: 'Blockbuster Video',
		swatch: '#2563eb',
		mode: 'dark',
		tokens: {
			'--color-primary': 'rgb(255, 235, 0)',            // vibrant yellow
			'--color-primary-hover': 'rgb(215, 200, 0)',      // slightly darker yellow
			'--color-primary-dark': 'rgb(180, 160, 0)',       // deep gold for borders
			'--color-primary-light-bg': 'rgb(0, 51, 153)',    // rich blue
			'--color-primary-light-bg-dark': 'rgb(0, 31, 103)', // deep blue
			'--color-primary-text': 'rgb(255, 235, 0)',       // yellow
			'--color-primary-text-dark': 'rgb(255, 235, 0)',  // yellow
			'--color-primary-border': 'rgb(255, 235, 0)',     // yellow
			'--color-on-primary': 'rgb(0, 0, 0)',             // black on yellow
			'--color-page': 'rgb(0, 41, 123)',                // darker blue page
			'--color-page-dark': 'rgb(0, 41, 123)',
			'--color-surface': 'rgb(0, 51, 153)',             // standard blue surface
			'--color-surface-dark': 'rgb(0, 51, 153)',
			'--radius': '0px'
		}
	},
	{
		id: 'vcr-osd',
		label: 'VCR OSD',
		swatch: '#0000bb',
		mode: 'dark',
		author: 'Gemini',
		description: 'Classic 90s blue screen VCR menu aesthetic',
		tokens: {
			'--color-primary': 'rgb(255, 255, 255)',
			'--color-primary-hover': 'rgb(200, 200, 200)',
			'--color-primary-dark': 'rgb(150, 150, 150)',
			'--color-primary-light-bg': 'rgb(0, 0, 130)',
			'--color-primary-light-bg-dark': 'rgb(0, 0, 80)',
			'--color-primary-text': 'rgb(255, 255, 255)',
			'--color-primary-text-dark': 'rgb(180, 180, 180)',
			'--color-primary-border': 'rgb(255, 255, 255)',
			'--color-on-primary': 'rgb(0, 0, 187)',
			'--color-page': 'rgb(0, 0, 187)',
			'--color-page-dark': 'rgb(0, 0, 150)',
			'--color-surface': 'rgb(0, 0, 220)',
			'--color-surface-dark': 'rgb(0, 0, 180)',
			'--radius': '0px'
		},
		css: '[data-scheme="vcr-osd"] {\n\tfont-family: \'Courier New\', monospace !important;\n\ttext-transform: uppercase;\n}\n[data-scheme="vcr-osd"] .section-frame-bar-top {\n\tbackground: white !important;\n\tcolor: #0000bb !important;\n\tfont-weight: 900 !important;\n}\n[data-scheme="vcr-osd"] [data-progress-fill] {\n\tbackground: #00ff00 !important;\n\tbox-shadow: 0 0 10px #00ff00;\n}\n[data-scheme="vcr-osd"] aside nav a[data-active="true"] {\n\tbackground: white !important;\n\tcolor: #0000bb !important;\n}'
	},
	{
		id: 'glass',
		label: 'Glass',
		swatch: '#818cf8',
		mode: 'dark',
		tokens: {
			'--color-primary': 'rgb(129, 140, 248)',        // indigo-400
			'--color-primary-hover': 'rgb(99, 102, 241)',   // indigo-500
			'--color-primary-dark': 'rgb(67, 56, 202)',     // indigo-700
			'--color-primary-light-bg': 'rgb(49, 46, 129)', // indigo-900
			'--color-primary-light-bg-dark': 'rgb(49, 46, 129)', // indigo-900
			'--color-primary-text': 'rgb(165, 180, 252)',   // indigo-300
			'--color-primary-text-dark': 'rgb(165, 180, 252)', // indigo-300
			'--color-primary-border': 'rgb(129, 140, 248)', // indigo-400
			'--color-on-primary': 'rgb(255, 255, 255)',     // white
			'--color-page': 'rgb(15, 23, 42)',              // slate-900
			'--color-page-dark': 'rgb(15, 23, 42)',         // slate-900
			'--color-surface': 'rgb(30, 27, 75)',           // indigo-950
			'--color-surface-dark': 'rgb(30, 27, 75)',       // indigo-950
			'--radius': '0.5rem'
		}
	},
	{
		id: 'tokyo-night',
		label: 'Tokyo Night',
		swatch: '#7aa2f7',
		mode: 'dark',
		author: 'Gemini',
		description: 'Modern sleek aesthetic with deep blues and neon accents',
		tokens: {
			'--color-primary': 'rgb(122, 162, 247)',
			'--color-primary-hover': 'rgb(187, 154, 247)',
			'--color-primary-dark': 'rgb(65, 72, 104)',
			'--color-primary-light-bg': 'rgb(26, 27, 38)',
			'--color-primary-light-bg-dark': 'rgb(22, 22, 30)',
			'--color-primary-text': 'rgb(122, 162, 247)',
			'--color-primary-text-dark': 'rgb(158, 206, 106)',
			'--color-primary-border': 'rgb(122, 162, 247)',
			'--color-on-primary': 'rgb(26, 27, 38)',
			'--color-page': 'rgb(26, 27, 38)',
			'--color-page-dark': 'rgb(15, 15, 21)',
			'--color-surface': 'rgb(36, 37, 52)',
			'--color-surface-dark': 'rgb(22, 22, 30)',
			'--radius': '0.5rem'
		},
		css: '[data-scheme="tokyo-night"] .section-frame {\n\tborder: 1px solid rgba(122, 162, 247, 0.1) !important;\n}\n[data-scheme="tokyo-night"] .section-frame-bar-top {\n\tbackground: rgba(122, 162, 247, 0.15) !important;\n\tcolor: rgb(122, 162, 247) !important;\n}\n[data-scheme="tokyo-night"] .section-frame-bar-bottom {\n\tbackground: rgba(122, 162, 247, 0.08) !important;\n}\n[data-scheme="tokyo-night"] aside nav a[data-active="true"] {\n\tcolor: #7aa2f7 !important;\n\tbackground: rgba(122, 162, 247, 0.1) !important;\n}\n[data-scheme="tokyo-night"] [data-progress-fill] {\n\tbackground: linear-gradient(90deg, #7aa2f7, #bb9af7) !important;\n}'
	},
	{
		id: 'violet',
		label: 'Grape',
		swatch: '#a855f7',
		tokens: {
			'--color-primary': 'rgb(147, 51, 234)',         // purple-600
			'--color-primary-hover': 'rgb(126, 34, 206)',   // purple-700
			'--color-primary-dark': 'rgb(107, 33, 168)',    // purple-800
			'--color-primary-light-bg': 'rgb(237, 226, 255)', // purple-100
			'--color-primary-light-bg-dark': 'rgb(76, 29, 149)', // purple-900
			'--color-primary-text': 'rgb(126, 34, 206)',    // purple-700
			'--color-primary-text-dark': 'rgb(192, 132, 252)', // purple-400
			'--color-primary-border': 'rgb(168, 85, 247)',  // purple-500
			'--color-on-primary': 'rgb(255, 255, 255)',     // white
			'--color-page': 'rgb(243, 235, 255)',           // purple-tinted light
			'--color-page-dark': 'rgb(16, 13, 26)',         // dark violet
			'--color-surface': 'rgb(247, 243, 255)',        // purple-tinted surface
			'--color-surface-dark': 'rgb(48, 22, 92)',       // grape dark
			'--radius': '0.5rem'
		}
	},
	{
		id: 'retro-console',
		label: '90s Console',
		swatch: '#7c3aed',
		author: 'Gemini',
		description: 'Industrial gray and royal purple inspired by 32-bit consoles',
		tokens: {
			'--color-primary': 'rgb(124, 58, 237)',
			'--color-primary-hover': 'rgb(109, 40, 217)',
			'--color-primary-dark': 'rgb(76, 29, 149)',
			'--color-primary-light-bg': 'rgb(243, 244, 246)',
			'--color-primary-light-bg-dark': 'rgb(31, 41, 55)',
			'--color-primary-text': 'rgb(109, 40, 217)',
			'--color-primary-text-dark': 'rgb(167, 139, 250)',
			'--color-primary-border': 'rgb(124, 58, 237)',
			'--color-on-primary': 'rgb(255, 255, 255)',
			'--color-page': 'rgb(209, 213, 219)',
			'--color-page-dark': 'rgb(17, 24, 39)',
			'--color-surface': 'rgb(229, 231, 235)',
			'--color-surface-dark': 'rgb(31, 41, 55)',
			'--radius': '0px'
		},
		css: '[data-scheme="retro-console"] .section-frame {\n\tborder: 2px solid #4b5563 !important;\n\tbox-shadow: 2px 2px 0px #000;\n}\n[data-scheme="retro-console"] .section-frame-bar-top {\n\tbackground: rgb(124, 58, 237) !important;\n\tcolor: white !important;\n\ttext-transform: uppercase;\n\tclip-path: polygon(0 0, 98% 0, 100% 100%, 0% 100%);\n\tletter-spacing: 0.15em;\n\tfont-weight: 800;\n}\n[data-scheme="retro-console"] aside nav a[data-active="true"] {\n\tbox-shadow: inset 4px 0 0 rgb(124, 58, 237);\n\ttext-shadow: 0 0 8px rgba(124, 58, 237, 0.5);\n}\n[data-scheme="retro-console"] [data-progress-track] {\n\tbackground: #000 !important;\n\tborder: 1px solid #4b5563;\n}'
	},
	{
		id: 'hollywood-video-v2',
		label: 'Hollywood Video',
		swatch: '#4c1d95',
		mode: 'dark',
		tokens: {
			'--color-primary': 'rgb(217, 11, 28)',             // #D90B1C Red
			'--color-primary-hover': 'rgb(170, 8, 22)',        // darker red
			'--color-primary-dark': 'rgb(110, 5, 14)',         // deep red
			'--color-primary-light-bg': 'rgb(35, 22, 64)',     // #231640 Purple
			'--color-primary-light-bg-dark': 'rgb(22, 14, 38)', // #160E26 Deep Purple
			'--color-primary-text': 'rgb(242, 183, 5)',        // #F2B705 Gold
			'--color-primary-text-dark': 'rgb(242, 183, 5)',   // #F2B705 Gold
			'--color-primary-border': 'rgb(35, 22, 64)',       // #231640 Purple
			'--color-on-primary': 'rgb(255, 255, 255)',        // White on Red
			'--color-page': 'rgb(22, 14, 38)',                 // #160E26 Deep Purple
			'--color-page-dark': 'rgb(22, 14, 38)',            // #160E26 Deep Purple
			'--color-surface': 'rgb(35, 22, 64)',              // #231640 Purple
			'--color-surface-dark': 'rgb(35, 22, 64)',          // #231640 Purple
			'--radius': '0.5rem'
		}
	},
	{
		id: 'dracula-pro',
		label: 'Dracula',
		swatch: '#bd93f9',
		mode: 'dark',
		author: 'Gemini',
		description: 'The world\'s most popular dark theme with vibrant purple accents',
		tokens: {
			'--color-primary': 'rgb(189, 147, 249)',
			'--color-primary-hover': 'rgb(255, 121, 198)',
			'--color-primary-dark': 'rgb(98, 114, 164)',
			'--color-primary-light-bg': 'rgb(68, 71, 90)',
			'--color-primary-light-bg-dark': 'rgb(40, 42, 54)',
			'--color-primary-text': 'rgb(189, 147, 249)',
			'--color-primary-text-dark': 'rgb(139, 233, 253)',
			'--color-primary-border': 'rgb(189, 147, 249)',
			'--color-on-primary': 'rgb(40, 42, 54)',
			'--color-page': 'rgb(40, 42, 54)',
			'--color-page-dark': 'rgb(33, 34, 44)',
			'--color-surface': 'rgb(68, 71, 90)',
			'--color-surface-dark': 'rgb(40, 42, 54)',
			'--radius': '0.5rem'
		},
		css: '[data-scheme="dracula-pro"] .section-frame {\n\tborder: 1px solid rgba(189, 147, 249, 0.15) !important;\n\tborder-radius: var(--radius) !important;\n\toverflow: hidden;\n}\n[data-scheme="dracula-pro"] .section-frame-bar-top {\n\tbackground: #44475a !important;\n\tcolor: #f8f8f2 !important;\n}\n[data-scheme="dracula-pro"] .section-frame-bar-bottom {\n\tbackground: #44475a !important;\n}\n[data-scheme="dracula-pro"] [data-progress-fill] {\n\tbackground: linear-gradient(90deg, #bd93f9, #ff79c6) !important;\n}\n[data-scheme="dracula-pro"] aside nav a[data-active="true"] {\n\tborder-left: 2px solid #ff79c6;\n\tbackground: rgba(189, 147, 249, 0.1) !important;\n}'
	},
	{
		id: 'gaming',
		label: 'Gaming',
		swatch: '#d946ef',
		mode: 'dark',
		tokens: {
			'--color-primary': 'rgb(0, 135, 164)',            // darker neon blue (headers)
			'--color-primary-hover': 'rgb(188, 19, 254)',     // neon purple
			'--color-primary-dark': 'rgb(27, 27, 47)',        // border dark
			'--color-primary-light-bg': 'rgb(0, 210, 255)',   // blue (unused in dark)
			'--color-primary-light-bg-dark': 'rgb(0, 30, 50)', // dark blue tint
			'--color-primary-text': 'rgb(0, 210, 255)',       // neon blue
			'--color-primary-text-dark': 'rgb(0, 210, 255)',  // neon blue
			'--color-primary-border': 'rgb(0, 210, 255)',     // neon blue
			'--color-on-primary': 'rgb(255, 255, 255)',       // white
			'--color-page': 'rgb(5, 5, 10)',                  // bg dark
			'--color-page-dark': 'rgb(5, 5, 10)',             // bg dark
			'--color-surface': 'rgb(12, 12, 18)',             // surface
			'--color-surface-dark': 'rgb(12, 12, 18)',         // surface
			'--radius': '0px'
		}
	},
	{
		id: 'rose',
		label: 'Rose',
		swatch: '#ec4899',
		tokens: {
			'--color-primary': 'rgb(219, 39, 119)',         // pink-600
			'--color-primary-hover': 'rgb(190, 24, 93)',    // pink-700
			'--color-primary-dark': 'rgb(157, 23, 77)',     // pink-800
			'--color-primary-light-bg': 'rgb(252, 231, 243)', // pink-100
			'--color-primary-light-bg-dark': 'rgb(131, 24, 67)', // pink-900
			'--color-primary-text': 'rgb(190, 24, 93)',     // pink-700
			'--color-primary-text-dark': 'rgb(244, 114, 182)', // pink-400
			'--color-primary-border': 'rgb(236, 72, 153)',  // pink-500
			'--color-on-primary': 'rgb(255, 255, 255)',     // white
			'--color-page': 'rgb(252, 232, 243)',           // pink-tinted light
			'--color-page-dark': 'rgb(47, 0, 23)',          // dark rose
			'--color-surface': 'rgb(253, 242, 249)',        // pink-tinted surface
			'--color-surface-dark': 'rgb(132, 28, 81)',      // rose dark
			'--radius': '0.5rem'
		}
	}
];

const DEFAULT_SCHEME = COLOR_SCHEMES[0];

/** Writable store of all available schemes (built-in + API-loaded) */
export const allSchemes = writable<ColorScheme[]>([...COLOR_SCHEMES]);

/** Cache of full theme data (with CSS) fetched from the API */
const cssCache = new Map<string, string>();

/** In-flight fetch promises keyed by theme id - prevents duplicate concurrent fetches */
const inFlight = new Map<string, Promise<void>>();

function getInitialScheme(): string {
	if (!browser) return DEFAULT_SCHEME.id;
	return localStorage.getItem('colorScheme') ?? DEFAULT_SCHEME.id;
}

function applyScheme(id: string) {
	if (!browser) return;
	const schemes = get(allSchemes);
	const scheme = schemes.find((s) => s.id === id) ?? DEFAULT_SCHEME;
	const root = document.documentElement;
	for (const [prop, value] of Object.entries(scheme.tokens)) {
		root.style.setProperty(prop, value);
	}

	root.dataset.scheme = scheme.id;


	// Inject theme CSS into a managed <style> element
	injectThemeCss(scheme);

	if (scheme.mode === 'dark') {
		root.classList.add('dark');
	} else if (scheme.mode === 'light') {
		root.classList.remove('dark');
	} else {
		// Restore the user's saved theme preference
		const saved = localStorage.getItem('theme');
		const prefersDark = saved === 'dark' || (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches);
		root.classList.toggle('dark', prefersDark);
	}
}

function injectThemeCss(scheme: ColorScheme) {
	const styleId = 'arm-theme-css';
	let el = document.getElementById(styleId) as HTMLStyleElement | null;

	// Get CSS from scheme object or cache
	const css = scheme.css ?? cssCache.get(scheme.id) ?? '';

	if (!css) {
		// No custom CSS — remove any existing injected style
		el?.remove();
		return;
	}

	if (!el) {
		el = document.createElement('style');
		el.id = styleId;
		document.head.appendChild(el);
	}
	el.textContent = css;
}

export const colorScheme = writable<string>(getInitialScheme());

/** True when the active color scheme locks the mode (light or dark) */
export const schemeLocksMode = derived(colorScheme, (id) => {
	const schemes = get(allSchemes);
	const scheme = schemes.find((s) => s.id === id);
	return scheme?.mode != null;
});

/**
 * Load themes from the API, merging with built-in fallbacks.
 * Call this on app startup. Falls back silently if backend is unreachable.
 */
export async function loadThemesFromApi(): Promise<void> {
	try {
		const apiThemes = await fetchThemes();
		if (!apiThemes?.length) return;

		// Build merged list: API themes take precedence, keep built-in order
		const merged = new Map<string, ColorScheme>();

		// Start with built-in fallbacks
		for (const s of COLOR_SCHEMES) {
			merged.set(s.id, { ...s, builtin: true });
		}

		// Overlay API themes (merge tokens so built-in defaults like --radius aren't lost)
		for (const t of apiThemes) {
			const existing = merged.get(t.id);
			merged.set(t.id, {
				id: t.id,
				label: t.label,
				swatch: t.swatch,
				mode: t.mode,
				tokens: { ...(existing?.tokens ?? {}), ...t.tokens },
				author: t.author,
				description: t.description,
				builtin: t.builtin ?? false
			});
		}

		allSchemes.set(Array.from(merged.values()));

		// Fetch full CSS for the currently active scheme
		const currentId = get(colorScheme);
		await loadThemeCss(currentId);
	} catch {
		// Backend unreachable — built-in themes are already loaded
	}
}

/**
 * Fetch and cache full theme CSS from the API, then re-apply the scheme.
 * Concurrent calls for the same id share one in-flight promise so the network
 * request is issued only once even when loadThemesFromApi() and the subscribe
 * handler both call this on page load.
 */
export async function loadThemeCss(id: string): Promise<void> {
	if (cssCache.has(id)) {
		// Already cached — update the scheme object and re-apply
		const schemes = get(allSchemes);
		const scheme = schemes.find((s) => s.id === id);
		if (scheme) {
			scheme.css = cssCache.get(id);
			applyScheme(id);
		}
		return;
	}

	if (inFlight.has(id)) {
		return inFlight.get(id);
	}

	const promise = (async () => {
		try {
			const full = await fetchTheme(id);
			if (full?.css) {
				cssCache.set(id, full.css);
				try {
					globalThis.window?.localStorage?.setItem(`theme-cache-v1-${id}`, full.css);
				} catch {
					// localStorage unavailable or quota exceeded - non-fatal
				}
				// Update the scheme in the store
				allSchemes.update((schemes) =>
					schemes.map((s) => (s.id === id ? { ...s, css: full.css } : s))
				);
			}
			applyScheme(id);
		} catch {
			// Fetch failed — apply without CSS
			applyScheme(id);
		} finally {
			inFlight.delete(id);
		}
	})();

	inFlight.set(id, promise);
	return promise;
}

if (browser) {
	colorScheme.subscribe(async (id) => {
		localStorage.setItem('colorScheme', id);
		// Apply tokens synchronously so there's no flash of default-blue
		// between page load and API response.  loadThemeCss will re-apply
		// with custom CSS once the fetch completes.
		applyScheme(id);
		await loadThemeCss(id);
	});
}
