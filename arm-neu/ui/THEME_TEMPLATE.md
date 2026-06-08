# ARM UI Theme Generation Template

Generate new color themes for the ARM (Automatic Ripping Machine) dashboard UI. The UI is a SvelteKit app using Tailwind CSS v4 with a CSS custom property-based theming system.

## How Themes Work

Each theme is a **JSON file** in `backend/themes/builtin/` (built-in) or uploaded by users via the Settings page. Themes define 13 required CSS custom properties applied to `:root` at runtime, plus 7 optional status-color tokens. Dark-only themes set `"mode": "dark"`. Themes may optionally include custom CSS rules in the `"css"` field using the `[data-scheme="<id>"]` selector prefix.

## Theme JSON Format

Each theme is a single `.json` file named `<id>.json`:

```json
{
  "id": "<unique_kebab_id>",
  "label": "<Display Name>",
  "version": 1,
  "author": "<Author Name>",
  "description": "<Short description of the theme>",
  "swatch": "<hex_color>",
  "mode": "dark",
  "tokens": {
    "--color-primary":            "rgb(R, G, B)",
    "--color-primary-hover":      "rgb(R, G, B)",
    "--color-primary-dark":       "rgb(R, G, B)",
    "--color-primary-light-bg":      "rgb(R, G, B)",
    "--color-primary-light-bg-dark": "rgb(R, G, B)",
    "--color-primary-text":      "rgb(R, G, B)",
    "--color-primary-text-dark": "rgb(R, G, B)",
    "--color-primary-border":    "rgb(R, G, B)",
    "--color-on-primary":        "rgb(R, G, B)",
    "--color-page":         "rgb(R, G, B)",
    "--color-page-dark":    "rgb(R, G, B)",
    "--color-surface":      "rgb(R, G, B)",
    "--color-surface-dark": "rgb(R, G, B)"
  },
  "css": ""
}
```

### Field Reference

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | URL-safe, lowercase, kebab-case. Used as filename and `[data-scheme]` value |
| `label` | Yes | Short display name (1-2 words) shown under the swatch |
| `version` | No | Integer version number (default: 1) |
| `author` | No | Theme author name |
| `description` | No | Short description of the theme |
| `swatch` | Yes | Hex color for the preview circle (e.g. `"#3b82f6"`) |
| `mode` | No | Set to `"dark"` to lock dark mode on. Omit for dual light/dark themes |
| `tokens` | Yes | Object with 13 required CSS custom properties (plus 7 optional status colors - see below) |
| `css` | No | Custom CSS string scoped under `[data-scheme="<id>"]` (default: `""`) |

### Token Reference

```
Primary accent color (buttons, active states, links):
  --color-primary              Main accent — 500-600 range
  --color-primary-hover        Hovered accent — one shade darker (600-700)
  --color-primary-dark         Deep accent for borders/outlines (700-800)

Backgrounds with accent tint:
  --color-primary-light-bg      Light mode: highlighted row/card bg (100 range)
  --color-primary-light-bg-dark Dark mode: highlighted row/card bg (900 range, muted)

Text colored with accent:
  --color-primary-text          Light mode: links, headings (700 range)
  --color-primary-text-dark     Dark mode: links, headings (300-400 range)

Misc:
  --color-primary-border        Borders on focused/active elements (500 range)
  --color-on-primary            Text ON primary bg (white or black for contrast)

Page & surface backgrounds:
  --color-page                  Light mode: full page bg (very light, accent-tinted)
  --color-page-dark             Dark mode: full page bg (very dark, accent-tinted)
  --color-surface               Light mode: card/panel bg (slightly lighter than page)
  --color-surface-dark          Dark mode: card/panel bg (slightly lighter than page-dark)
```

#### Optional status-color tokens

The 7 status-color tokens below paint job-state badges, lifecycle nodes,
progress bars, and dashboard chips. They default to a sensible palette in
`frontend/src/app.css` and themes don't need to override them - omit the
keys to inherit defaults. Set them only when the default palette clashes
with your theme accent.

```
  --color-status-ripping      Active rip / "Ripping" lifecycle node (default: blue)
  --color-status-transcoding  Active transcode / "Transcoding" lifecycle (default: violet)
  --color-status-finishing    Copy/eject phase, "Finishing" badge (default: amber)
  --color-status-waiting      Pre-rip "Waiting" lifecycle node (default: yellow)
  --color-status-scanning     Disc scan / metadata fetch in progress (default: cyan)
  --color-status-success      Completed jobs (default: green)
  --color-status-error        Failed jobs (default: red)
```

Pick contrasting hues so users can distinguish "ripping" from "transcoding"
at a glance, and keep `--color-status-finishing` distinct from
`--color-status-waiting` (the dashboard's `.status-warning` class also uses
the waiting token).

## Custom CSS

For themes with distinctive visual styles beyond color tokens. The `"css"` field contains a CSS string where every rule is prefixed with `[data-scheme="<id>"]`.

**Important:** The CSS is stored as a JSON string value, so all double quotes within the CSS must be escaped as `\"`.

### Available Selectors

```css
[data-scheme="<id>"] { }                                /* Root — font-family, etc. */
[data-scheme="<id>"] body { }                           /* Body — gradients, bg images */
[data-scheme="<id>"] aside { }                          /* Sidebar container */
[data-scheme="<id>"] aside nav a { }                    /* Nav links */
[data-scheme="<id>"] aside nav a:hover { }              /* Nav link hover */
[data-scheme="<id>"] aside nav a[data-active="true"] { }/* Active nav link */
[data-scheme="<id>"] aside nav a svg { }                /* Nav icons */
[data-scheme="<id>"] aside [data-logo] img { }          /* Logo image — filters */
[data-scheme="<id>"] aside [data-stats] { }             /* Sidebar stats panel */
[data-scheme="<id>"] aside hr { }                       /* Sidebar dividers */
[data-scheme="<id>"] header { }                         /* Top header bar */
[data-scheme="<id>"] [data-progress-track] { }          /* Progress bar track */
[data-scheme="<id>"] [data-progress-fill] { }           /* Progress bar fill */
[data-scheme="<id>"] aside::before { }                  /* Pseudo-element for decorative lines */

/* Section frames (dashboard panels like "WAITING FOR REVIEW", "ACTIVE RIPS") */
[data-scheme="<id>"] .section-frame { }                 /* Frame container */
[data-scheme="<id>"] .section-frame-bar-top { }         /* Accent bar with label */
[data-scheme="<id>"] .section-frame-bar-bottom { }      /* Bottom accent bar */
[data-scheme="<id>"] .section-frame-sidebar { }         /* Side blocks (full variant) */
[data-scheme="<id>"] .section-frame-block-a { }         /* Top sidebar block */
[data-scheme="<id>"] .section-frame-block-b { }         /* Middle sidebar block */
[data-scheme="<id>"] .section-frame-block-c { }         /* Bottom sidebar block */
[data-scheme="<id>"] .section-frame-body { }            /* Content area */
/* Frame variant attribute: [data-frame-variant="full"] or [data-frame-variant="compact"] */
/* Frame accent variable: --frame-accent (set per-instance, e.g. #f90, #99f) */
```

## Design Guidelines

1. **All RGB values must use `rgb(R, G, B)` format** — not hex, not hsl. The Tailwind v4 `color-mix()` system requires this.
2. **Light/dark dual-mode themes** (no `mode` field): Need visually distinct light AND dark variants. Light-mode backgrounds should be very light (pastel), dark-mode backgrounds very dark. Both must have good text contrast.
3. **Dark-only themes** (`"mode": "dark"`): Set matching values for light/dark token pairs (e.g., `--color-page` = `--color-page-dark`). These are often more stylized/dramatic.
4. **Swatch** must be a hex color string (e.g. `"#3b82f6"`).
5. **`--color-on-primary`**: Use `rgb(255, 255, 255)` (white) for dark accents, `rgb(0, 0, 0)` (black) for light/bright accents. This is the text color shown ON TOP of the primary color.
6. **Contrast**: Ensure `--color-primary-text` is readable on white/light-gray (#f9fafb). Ensure `--color-primary-text-dark` is readable on dark backgrounds (#111827).
7. **Custom CSS is optional** — simple color-swap themes don't need it. Use it for font changes, animations, gradients, glow effects, clip-paths, etc.

## Existing Theme IDs (do NOT reuse)

`blue`, `ocean`, `forest`, `sunset`, `rose`, `violet`, `glass`, `cinema`, `gaming`, `royale`, `lcars`, `tactical`, `craft`, `terminal`, `blockbuster`, `hollywood-video-v2`

## Examples

**Simple dual-mode theme (color swap only, no custom CSS):**

```json
{
  "id": "forest",
  "label": "Forest",
  "version": 1,
  "author": "ARM Team",
  "description": "Emerald green nature theme",
  "swatch": "#10b981",
  "tokens": {
    "--color-primary": "rgb(5, 150, 105)",
    "--color-primary-hover": "rgb(4, 120, 87)",
    "--color-primary-dark": "rgb(6, 95, 70)",
    "--color-primary-light-bg": "rgb(209, 250, 229)",
    "--color-primary-light-bg-dark": "rgb(6, 78, 59)",
    "--color-primary-text": "rgb(4, 120, 87)",
    "--color-primary-text-dark": "rgb(110, 231, 183)",
    "--color-primary-border": "rgb(16, 185, 129)",
    "--color-on-primary": "rgb(255, 255, 255)",
    "--color-page": "rgb(228, 248, 238)",
    "--color-page-dark": "rgb(12, 19, 15)",
    "--color-surface": "rgb(237, 252, 244)",
    "--color-surface-dark": "rgb(21, 54, 37)"
  },
  "css": ""
}
```

**Stylized dark-only theme (with custom CSS):**

```json
{
  "id": "cinema",
  "label": "Cinema",
  "version": 1,
  "author": "ARM Team",
  "description": "Gold on black, inspired by classic movie theaters",
  "swatch": "#ca8a04",
  "mode": "dark",
  "tokens": {
    "--color-primary": "rgb(212, 175, 55)",
    "--color-primary-hover": "rgb(188, 155, 40)",
    "--color-primary-dark": "rgb(138, 109, 59)",
    "--color-primary-light-bg": "rgb(30, 25, 10)",
    "--color-primary-light-bg-dark": "rgb(30, 25, 10)",
    "--color-primary-text": "rgb(212, 175, 55)",
    "--color-primary-text-dark": "rgb(212, 175, 55)",
    "--color-primary-border": "rgb(138, 109, 59)",
    "--color-on-primary": "rgb(13, 13, 13)",
    "--color-page": "rgb(26, 26, 26)",
    "--color-page-dark": "rgb(26, 26, 26)",
    "--color-surface": "rgb(13, 13, 13)",
    "--color-surface-dark": "rgb(13, 13, 13)"
  },
  "css": "[data-scheme=\"cinema\"] {\n\tfont-family: 'Garamond', 'Times New Roman', Georgia, serif;\n}\n[data-scheme=\"cinema\"] aside {\n\tborder-color: #8a6d3b !important;\n}\n[data-scheme=\"cinema\"] aside nav a {\n\ttext-transform: uppercase;\n\tletter-spacing: 0.15em;\n\tfont-family: Arial, Helvetica, sans-serif;\n\tfont-size: 0.75rem;\n\tborder-radius: 0;\n\tborder-left: 2px solid transparent;\n}\n[data-scheme=\"cinema\"] aside nav a:hover {\n\tcolor: #d4af37 !important;\n\tbackground: linear-gradient(90deg, rgba(212, 175, 55, 0.05), transparent) !important;\n}\n[data-scheme=\"cinema\"] aside nav a[data-active=\"true\"] {\n\tcolor: #d4af37 !important;\n\tborder-left: 2px solid #d4af37;\n\tbackground: transparent !important;\n}\n[data-scheme=\"cinema\"] aside nav a svg { display: none; }\n[data-scheme=\"cinema\"] aside [data-logo] img {\n\tfilter: sepia(1) saturate(2) brightness(0.9) hue-rotate(5deg);\n}\n[data-scheme=\"cinema\"] aside hr { border-color: #8a6d3b; }\n[data-scheme=\"cinema\"] [data-progress-track] {\n\tbackground: #222 !important;\n\theight: 2px !important;\n\tborder-radius: 0 !important;\n}\n[data-scheme=\"cinema\"] [data-progress-fill] {\n\tbackground: #d4af37 !important;\n\tbox-shadow: 0 0 8px #d4af37;\n\tborder-radius: 0 !important;\n}\n[data-scheme=\"cinema\"] header { border-color: #8a6d3b !important; }"
}
```
