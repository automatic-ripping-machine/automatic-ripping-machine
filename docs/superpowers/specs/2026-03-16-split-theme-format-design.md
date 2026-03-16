# Split Theme Format Design

## Problem

Theme custom CSS is stored as a JSON string value in `<id>.json`. This means:

- No syntax highlighting or editor support
- All quotes must be escaped (`\"`)
- No formatting/indentation preserved in a readable way
- Large themes like LCARS (30KB) are nearly impossible to edit directly

## Solution

Split each theme into two sidecar files:

```
themes/builtin/
  blue.json          # metadata + tokens only
  lcars.json         # metadata + tokens only
  lcars.css          # custom CSS (real CSS file)
  cinema.json
  cinema.css
```

The `css` field is removed from the JSON schema. The loader pairs `<id>.css` with `<id>.json` automatically.

## Changes

### File Format

**JSON** (remove `css` field):
```json
{
  "id": "cinema",
  "label": "Cinema",
  "version": 1,
  "author": "ARM Team",
  "description": "Gold on black, inspired by classic movie theaters",
  "swatch": "#ca8a04",
  "mode": "dark",
  "tokens": { ... }
}
```

**CSS** (standalone file, no escaping):
```css
[data-scheme="cinema"] {
    font-family: 'Garamond', 'Times New Roman', Georgia, serif;
}
[data-scheme="cinema"] aside {
    border-color: #8a6d3b !important;
}
```

### Built-in Theme Migration

Extract the `css` field from each JSON file into a sidecar `.css` file. 10 of 16 themes have custom CSS:

- `cinema.css`, `craft.css`, `gaming.css`, `glass.css`, `royale.css`
- `tactical.css`, `terminal.css`, `blockbuster.css`, `hollywood-video-v2.css`, `lcars.css`

6 themes have no CSS (`blue`, `ocean`, `forest`, `sunset`, `rose`, `violet`) and get no `.css` file.

### Backend: Theme Loader (`services/themes.py`)

- `_load_theme_file(path)`: After loading JSON, check for `path.with_suffix('.css')`. If it exists, read its contents and set `data["css"]`. If not, set `data["css"] = ""`.
- `_validate_theme(data)`: No change to validation — `css` was never validated.
- `save_user_theme(data, css)`: Accept optional CSS string. Write JSON to `<id>.json` (without `css` key). If CSS is non-empty, write to `<id>.css`. If CSS is empty/None, delete any existing `<id>.css`.

### Backend: API Endpoints (`routers/themes.py`)

- `GET /api/themes` — No change (already excludes CSS).
- `GET /api/themes/{id}` — No change (loader assembles `css` from file).
- `POST /api/themes` — Change to accept multipart form: `theme_json` (file/text, required) + `theme_css` (text, optional). Parse JSON, validate, pass CSS string to `save_user_theme`.
- `GET /api/themes/{id}/download` — Return JSON without `css` field (as today).
- New: `GET /api/themes/{id}/css` — Return raw CSS text (404 if no CSS file).
- `DELETE /api/themes/{id}` — Also delete `<id>.css` if it exists.

### Frontend: Theme API Client (`api/themes.ts`)

- `uploadTheme(theme, css?)` — Change from JSON POST to multipart form POST with `theme_json` + `theme_css` fields.
- New: `fetchThemeCss(id)` — Fetch raw CSS for download.

### Frontend: Upload UI (settings page)

Replace single file picker with two-field form:

1. **Theme JSON** — file picker (`.json`, required)
2. **Custom CSS** — textarea or file picker (optional)
3. **Upload button** — sends both to `POST /api/themes`

### Frontend: Theme Apply Logic (`colorScheme.ts`)

No changes. `applyScheme()` already receives `{ tokens, css }` from `fetchTheme(id)` and injects CSS via `injectThemeCss()`. The API response shape doesn't change.

### THEME_TEMPLATE.md

Update to reflect the split format: JSON example without `css` field, separate CSS file example, note that sidecar `.css` is optional.

## Out of Scope

- Token format changes (staying with `rgb(R, G, B)`)
- Theme editor UI (future work)
- Theme versioning/migration beyond this format change
