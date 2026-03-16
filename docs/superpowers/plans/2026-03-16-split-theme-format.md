# Split Theme Format Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract theme CSS from JSON string fields into sidecar `.css` files for proper editor support, and update the upload UI to a two-field flow (JSON + CSS).

**Architecture:** The backend theme loader reads `<id>.json` + optional `<id>.css` sidecar. The API response shape stays the same (`{ ...meta, tokens, css }`). The frontend upload form gets a JSON file picker + CSS textarea. Download exposes separate JSON and CSS endpoints.

**Tech Stack:** Python/FastAPI (backend), SvelteKit/TypeScript (frontend), Tailwind v4

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `backend/services/themes.py` | Load sidecar CSS, save split files, delete CSS on theme delete |
| Modify | `backend/routers/themes.py` | Multipart upload endpoint, new CSS download endpoint |
| Modify | `frontend/src/lib/api/themes.ts` | Multipart upload function, CSS download function |
| Modify | `frontend/src/lib/api/client.ts` | Support non-JSON fetch calls |
| Modify | `frontend/src/routes/settings/+page.svelte` | Two-field upload UI |
| Migrate | `backend/themes/builtin/*.json` | Extract `css` field to sidecar `.css` files |
| Modify | `THEME_TEMPLATE.md` | Update docs to reflect split format |

---

### Task 1: Migrate built-in theme files

Extract the `css` field from each JSON file into a sidecar `.css` file. Write a one-shot script.

**Files:**
- Modify: `backend/themes/builtin/*.json` (remove `css` field from 10 themes, keep 6 CSS-less themes unchanged)
- Create: `backend/themes/builtin/*.css` (10 new files)

- [ ] **Step 1: Write migration script**

Create `scripts/split_theme_css.py`:

```python
#!/usr/bin/env python3
"""One-shot migration: extract css field from theme JSON into sidecar .css files."""
import json
from pathlib import Path

theme_dir = Path(__file__).parent.parent / "backend" / "themes" / "builtin"
# Run from repo root of automatic-ripping-machine-ui

for json_path in sorted(theme_dir.glob("*.json")):
    data = json.loads(json_path.read_text("utf-8"))
    css = data.pop("css", "")
    # Rewrite JSON without css field
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", "utf-8")
    # Write CSS sidecar if non-empty
    if css.strip():
        css_path = json_path.with_suffix(".css")
        css_path.write_text(css + "\n", "utf-8")
        print(f"  extracted {css_path.name} ({len(css)} chars)")
    else:
        print(f"  {json_path.name}: no css")

print("Done.")
```

- [ ] **Step 2: Run migration script**

Run: `cd /home/upb/src/automatic-ripping-machine-ui && python3 scripts/split_theme_css.py`

Expected: 10 `.css` files created, 16 `.json` files rewritten without `css` key.

- [ ] **Step 3: Verify output**

Spot-check:
- `blue.json` should have no `css` key and no `blue.css`
- `lcars.json` should have no `css` key; `lcars.css` should exist with full CSS
- `cinema.json` should have no `css` key; `cinema.css` should exist

- [ ] **Step 4: Delete migration script**

```bash
rm scripts/split_theme_css.py
```

- [ ] **Step 5: Commit**

```bash
cd /home/upb/src/automatic-ripping-machine-ui
git add backend/themes/builtin/
git commit -m "refactor: extract theme CSS into sidecar .css files"
```

---

### Task 2: Update backend theme loader

Modify the theme service to read sidecar CSS files and write split files on save/delete.

**Files:**
- Modify: `backend/services/themes.py`

- [ ] **Step 1: Update `_load_theme_file` to read sidecar CSS**

In `_load_theme_file(path)`, after loading JSON, check for `path.with_suffix('.css')`:

```python
def _load_theme_file(path: Path) -> dict[str, Any] | None:
    """Load a theme JSON file and its optional sidecar CSS."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not _validate_theme(data):
            return None
        # Read sidecar CSS if it exists (new split format)
        css_path = path.with_suffix(".css")
        if css_path.is_file():
            data["css"] = css_path.read_text(encoding="utf-8")
        else:
            data.setdefault("css", "")
        return data
    except (json.JSONDecodeError, OSError):
        return None
```

Note: `data.setdefault("css", "")` handles backward compat if a JSON still has an inline `css` field.

- [ ] **Step 2: Update `save_user_theme` to accept and write CSS separately**

```python
def save_user_theme(data: dict[str, Any], css: str = "") -> dict[str, Any]:
    """Save a user theme. JSON and CSS are written as separate files."""
    if not _validate_theme(data):
        raise ValueError("Invalid theme: missing required fields (id, label, tokens)")

    data.setdefault("version", 1)
    data.setdefault("swatch", "#888888")

    user_dir = _user_themes_dir()
    json_path = user_dir / f"{data['id']}.json"
    css_path = user_dir / f"{data['id']}.css"

    # Save JSON without css or builtin fields
    save_data = {k: v for k, v in data.items() if k not in ("builtin", "css")}
    json_path.write_text(json.dumps(save_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Save or remove CSS sidecar
    if css.strip():
        css_path.write_text(css, encoding="utf-8")
        data["css"] = css
    else:
        css_path.unlink(missing_ok=True)
        data["css"] = ""

    data["builtin"] = False
    return data
```

- [ ] **Step 3: Update `delete_user_theme` to also delete CSS sidecar**

```python
def delete_user_theme(theme_id: str) -> bool:
    """Delete a user theme. Returns False if it's a built-in or doesn't exist."""
    builtin_path = _BUILTIN_DIR / f"{theme_id}.json"
    if builtin_path.exists():
        return False

    user_dir = _user_themes_dir()
    json_path = user_dir / f"{theme_id}.json"
    if not json_path.exists():
        return False

    json_path.unlink()
    # Also remove sidecar CSS
    css_path = user_dir / f"{theme_id}.css"
    css_path.unlink(missing_ok=True)
    return True
```

- [ ] **Step 4: Commit**

```bash
cd /home/upb/src/automatic-ripping-machine-ui
git add backend/services/themes.py
git commit -m "feat: load theme CSS from sidecar files, save as split files"
```

---

### Task 3: Update backend API endpoints

Change upload to accept multipart form data. Add CSS download endpoint. Update JSON download to exclude CSS.

**Files:**
- Modify: `backend/routers/themes.py`

- [ ] **Step 1: Update imports and upload endpoint**

```python
"""Theme management API endpoints."""

import json

from fastapi import APIRouter, Form, HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse, PlainTextResponse

from backend.services import themes as theme_service

router = APIRouter(prefix="/api/themes", tags=["themes"])


@router.get("")
async def list_themes():
    """List all available themes (metadata only, no CSS)."""
    return theme_service.get_all_themes()


@router.get("/{theme_id}")
async def get_theme(theme_id: str):
    """Get full theme data including CSS."""
    theme = theme_service.get_theme(theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail=f"Theme '{theme_id}' not found")
    return theme


@router.get("/{theme_id}/download")
async def download_theme(theme_id: str):
    """Download theme JSON (without CSS — CSS is a separate file)."""
    theme = theme_service.get_theme(theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail=f"Theme '{theme_id}' not found")
    download = {k: v for k, v in theme.items() if k not in ("builtin", "css")}
    return JSONResponse(
        content=download,
        headers={"Content-Disposition": f'attachment; filename="{theme_id}.json"'},
    )


@router.get("/{theme_id}/css")
async def download_theme_css(theme_id: str):
    """Download theme CSS file. Returns 404 if theme has no custom CSS."""
    theme = theme_service.get_theme(theme_id)
    if not theme:
        raise HTTPException(status_code=404, detail=f"Theme '{theme_id}' not found")
    css = theme.get("css", "")
    if not css.strip():
        raise HTTPException(status_code=404, detail=f"Theme '{theme_id}' has no custom CSS")
    return PlainTextResponse(
        content=css,
        headers={"Content-Disposition": f'attachment; filename="{theme_id}.css"'},
    )


@router.post("", status_code=201)
async def upload_theme(
    theme_json: UploadFile = File(..., description="Theme JSON file"),
    theme_css: str = Form("", description="Optional custom CSS"),
):
    """Upload a user theme (JSON file + optional CSS text)."""
    try:
        content = await theme_json.read()
        data = json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid JSON file")

    try:
        saved = theme_service.save_user_theme(data, css=theme_css)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return saved


@router.delete("/{theme_id}")
async def delete_theme(theme_id: str):
    """Delete a user theme. Built-in themes cannot be deleted."""
    deleted = theme_service.delete_user_theme(theme_id)
    if not deleted:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete '{theme_id}': built-in theme or not found",
        )
    return {"detail": f"Theme '{theme_id}' deleted"}
```

- [ ] **Step 2: Commit**

```bash
cd /home/upb/src/automatic-ripping-machine-ui
git add backend/routers/themes.py
git commit -m "feat: multipart theme upload, separate CSS download endpoint"
```

---

### Task 4: Update frontend API client

Update `uploadTheme` to send multipart form data. Add `fetchThemeCss` for download. Handle non-JSON content types in `apiFetch`.

**Files:**
- Modify: `frontend/src/lib/api/themes.ts`
- Modify: `frontend/src/lib/api/client.ts`

- [ ] **Step 1: Add `apiFormPost` helper to client.ts**

Add a new function that sends `FormData` without the JSON content-type header (the browser sets `multipart/form-data` with boundary automatically):

```typescript
export async function apiFormPost<T>(path: string, formData: FormData): Promise<T> {
	const res = await fetch(`${BASE}${path}`, {
		method: 'POST',
		body: formData
	});
	if (!res.ok) {
		let message = `API ${res.status}: ${res.statusText}`;
		try {
			const body = await res.json();
			if (body.detail) message = body.detail;
		} catch { /* use default message */ }
		throw new Error(message);
	}
	return res.json();
}
```

- [ ] **Step 2: Update themes.ts**

```typescript
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
```

- [ ] **Step 3: Commit**

```bash
cd /home/upb/src/automatic-ripping-machine-ui
git add frontend/src/lib/api/client.ts frontend/src/lib/api/themes.ts
git commit -m "feat: multipart theme upload and CSS download in API client"
```

---

### Task 5: Update upload UI to two-field form

Replace single file picker with JSON file picker + CSS textarea + upload button.

**Files:**
- Modify: `frontend/src/routes/settings/+page.svelte` (lines ~104-129 for handler, ~2099-2108 for template)

- [ ] **Step 1: Update the upload handler**

Replace `handleThemeUpload` (lines 108-129) with:

```typescript
let themeJsonFile = $state<File | null>(null);
let themeCssText = $state('');

async function handleThemeUpload() {
    if (!themeJsonFile) return;
    themeUploading = true;
    themeFeedback = null;
    try {
        // Quick client-side validation
        const text = await themeJsonFile.text();
        const data = JSON.parse(text);
        if (!data.id || !data.label || !data.tokens) {
            throw new Error('Invalid theme: missing required fields (id, label, tokens)');
        }
        await uploadTheme(themeJsonFile, themeCssText);
        await loadThemesFromApi();
        themeFeedback = { type: 'success', message: `Theme "${data.label}" uploaded` };
        themeJsonFile = null;
        themeCssText = '';
    } catch (e) {
        themeFeedback = { type: 'error', message: e instanceof Error ? e.message : 'Upload failed' };
    } finally {
        themeUploading = false;
    }
}

function handleJsonFileSelect(event: Event) {
    const input = event.target as HTMLInputElement;
    themeJsonFile = input.files?.[0] ?? null;
}
```

- [ ] **Step 2: Update the template**

Replace the Upload Theme section (lines ~2099-2108) with:

```svelte
<!-- Upload Theme -->
<div class="rounded-lg border border-primary/20 bg-surface p-6 shadow-xs dark:border-primary/20 dark:bg-surface-dark">
    <h3 class="mb-1 text-base font-semibold text-gray-900 dark:text-white">Import Theme</h3>
    <p class="mb-4 text-sm text-gray-500 dark:text-gray-400">Upload a theme JSON file and optional custom CSS.</p>
    <div class="space-y-4">
        <!-- JSON file picker -->
        <div>
            <label class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">Theme JSON <span class="text-red-500">*</span></label>
            <label class="inline-flex cursor-pointer items-center gap-2 rounded-lg bg-primary/10 px-4 py-2 text-sm font-medium text-primary-text transition-colors hover:bg-primary/20 dark:text-primary-text-dark">
                <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
                {themeJsonFile ? themeJsonFile.name : 'Choose .json file'}
                <input type="file" accept=".json" class="hidden" onchange={handleJsonFileSelect} disabled={themeUploading} />
            </label>
        </div>
        <!-- CSS textarea -->
        <div>
            <label for="theme-css-input" class="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">Custom CSS <span class="text-xs text-gray-400">(optional)</span></label>
            <textarea
                id="theme-css-input"
                bind:value={themeCssText}
                placeholder={'[data-scheme="my-theme"] {\n  /* custom styles */\n}'}
                rows="6"
                disabled={themeUploading}
                class="w-full rounded-lg border border-primary/25 bg-primary/5 px-3 py-2 font-mono text-sm dark:border-primary/30 dark:bg-primary/10 dark:text-white"
            ></textarea>
        </div>
        <!-- Upload button -->
        <div class="flex items-center gap-3">
            <button
                type="button"
                onclick={handleThemeUpload}
                disabled={!themeJsonFile || themeUploading}
                class="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-on-primary transition-colors hover:bg-primary-hover disabled:opacity-50"
            >
                {themeUploading ? 'Uploading...' : 'Upload Theme'}
            </button>
            {#if themeFeedback}
                <span class="text-sm {themeFeedback.type === 'success' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}">
                    {themeFeedback.message}
                </span>
            {/if}
        </div>
    </div>
</div>
```

- [ ] **Step 3: Rebuild frontend and restart UI**

```bash
cd /home/upb/src/automatic-ripping-machine-ui/frontend && npm run build
docker restart arm-ui
```

- [ ] **Step 4: Visually verify the upload form**

Open `http://localhost:8888/settings`, scroll to Import Theme section. Should show:
- "Theme JSON" file picker (required)
- "Custom CSS" textarea (optional)
- "Upload Theme" button (disabled until a JSON file is selected)

- [ ] **Step 5: Commit**

```bash
cd /home/upb/src/automatic-ripping-machine-ui
git add frontend/src/routes/settings/+page.svelte
git commit -m "feat: two-field theme upload UI (JSON + CSS)"
```

---

### Task 6: Update THEME_TEMPLATE.md

Update the template docs to reflect the split format.

**Files:**
- Modify: `THEME_TEMPLATE.md`

- [ ] **Step 1: Update docs**

Key changes:
- Remove `"css"` field from JSON format section
- Add section about sidecar `.css` files
- Update examples to show JSON without `css` and separate CSS file
- Note that `css` field in JSON is still accepted for backward compat but sidecar is preferred

- [ ] **Step 2: Commit**

```bash
cd /home/upb/src/automatic-ripping-machine-ui
git add THEME_TEMPLATE.md
git commit -m "docs: update theme template for split CSS format"
```

---

### Task 7: Manual verification

- [ ] **Step 1: Verify themes load correctly**

Open `http://localhost:8888/settings`, try switching between themes. All 16 should work.

- [ ] **Step 2: Verify theme upload**

Create a test theme JSON file and upload it via the new form. Verify it appears in the theme list.

- [ ] **Step 3: Verify theme upload with CSS**

Upload a theme with custom CSS in the textarea. Switch to it and verify CSS is applied.

- [ ] **Step 4: Verify theme delete**

Delete the test theme. Verify both `.json` and `.css` are removed.

- [ ] **Step 5: Verify download**

Download a theme's JSON and CSS via the API endpoints.
