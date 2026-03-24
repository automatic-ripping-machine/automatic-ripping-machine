# Episode Matching Overhaul

**Date:** 2026-03-24
**Status:** Draft
**Repos:** automatic-ripping-machine-neu, automatic-ripping-machine-ui
**Depends on:** feat/id-based-log-naming (ARM-neu), feat/folder-import-review (ARM-UI)

## Problem

The TVDB episode matcher can't produce correct results for multi-disc TV series folder imports because:

1. **No season/disc metadata on folder jobs** — the folder import wizard doesn't collect season, disc number, or disc total. The matcher has position bias logic for multi-disc sets but gets no input.
2. **No extraction from folder paths** — paths like `Kolchak - Disc 4 of 4` contain disc info but `folder_scan.py` doesn't extract it. The centralized `parse_label()` in `arm_matcher.py` already handles these patterns but isn't wired into the folder flow.
3. **No way to fix matches** — after the matcher runs, the user sees results but can't reassign which episode maps to which track. The only option is to change parameters and re-run.
4. **Episodes button not discoverable** — currently labeled "TVDB Episodes" which is jargon. The workflow should be Search → Episodes → Start.

## Design

### User Flow

```
1. Search   →  Pick show (sets title, year, IMDB, TVDB ID)
2. Episodes →  Set season/disc → auto-match → review table → fix with dropdowns
3. Start    →  Process with matched episode metadata for naming
```

### Layer 1: Metadata Extraction & Storage

#### 1.1 Extend folder scan to extract disc/season metadata

**File:** `arm/ripper/folder_scan.py`

`scan_folder()` currently returns `disc_type`, `label`, `title_suggestion`, `year_suggestion`, `folder_size_bytes`, `stream_count`.

Extend: after extracting the label, run `parse_label()` from `arm_matcher.py` on it. Add to the return dict:

- `disc_number` — extracted disc number (int or null)
- `disc_total` — extracted disc total (int or null). Note: `parse_label()` extracts disc number from patterns like `Disc 4` but not disc total from `of 4`. Extend the parser to also capture total from `Disc N of M` patterns.
- `season` — extracted season number (int or null)

Also parse the **parent folder** path for season info. Multi-disc sets often have structure like:
```
Show Name (Year) Season 1/
  Show Name - Disc 1 of 4/BDMV/
  Show Name - Disc 2 of 4/BDMV/
```

The disc folder may not contain season info, but the parent does.

#### 1.2 Extend `parse_label()` to extract disc total

**File:** `arm/ripper/arm_matcher.py`

Current `_DISC_SUFFIX_RE` captures `Disc 4` but not `of 4`. Add a new regex or extend the existing one to capture the `of N` pattern:

```
Disc 4 of 4  →  disc_number=4, disc_total=4
D2 of 6      →  disc_number=2, disc_total=6
Disc 1       →  disc_number=1, disc_total=None
```

Update `LabelInfo` dataclass to include `disc_total: int | None`.

Note: `_DISC_SUFFIX_RE` is anchored with `$` (end of string). The "of N" extension should be added as an optional group before the anchor: `(?:\s*of\s*(\d+))?$`. This keeps the existing single-disc match working while also capturing the total when present.

#### 1.3 Add fields to folder create endpoint

**File:** `arm/api/v1/folder.py`

Add to `FolderCreateRequest`:
```python
season: Optional[int] = None
disc_number: Optional[int] = None
disc_total: Optional[int] = None
```

Store on the job object during creation. Follow the existing paired-field convention (`season` + `season_manual`) so the auto-detect logic in `_get_known_season()` picks up the value:
```python
if req.season is not None:
    job.season = str(req.season)
    job.season_manual = str(req.season)
if req.disc_number is not None:
    job.disc_number = req.disc_number
if req.disc_total is not None:
    job.disc_total = req.disc_total
```

#### 1.4 Job metadata update API

**File:** `arm/api/v1/jobs.py`

The existing title update endpoint (`PUT /jobs/{job_id}/title`) already handles title, year, video_type, imdb_id, poster_url, season, artist, album, and episode via `_FIELD_MAP`. Season is already accepted — no change needed for it.

Add `disc_number` and `disc_total` to `_DIRECT_FIELDS` (or handle explicitly) since they are integer columns, not paired string fields:

- `disc_number` (int)
- `disc_total` (int)

The TVDB matcher already reads `job.disc_number` and `job.disc_total` — so setting them via the update endpoint makes the matcher work correctly on the next run.

#### 1.5 TVDB match endpoint enhancement

**File:** `arm/api/v1/jobs.py` (tvdb-match endpoint)

Currently accepts `season`, `tolerance`, `apply`. Add:

- `disc_number` (optional int) — override for position bias
- `disc_total` (optional int) — override for position bias

When provided, these are used instead of the job's stored values for that match run. This lets the user experiment with different disc positions without saving first.

### Layer 2: Episodes Panel UI

#### 2.1 New `EpisodeMatch.svelte` component

**File:** `frontend/src/lib/components/EpisodeMatch.svelte`

Replace or wrap the existing `TvdbMatch.svelte`. The new component has:

**Top controls bar:**
- Season input (prefilled from job or auto-detect)
- Disc number / disc total inputs (prefilled from job)
- Tolerance input (default 300s)
- "Re-match" button — re-runs the matcher with current control values
- Match stats summary: "5 matched · 0 unmatched · 7 skipped"

**Match table:**
- Columns: Track (number + truncated filename), Duration, Matched Episode (dropdown), TVDB Runtime, Delta
- Each episode dropdown contains all episodes from the selected season
- "None (skip)" option to unassign a track
- Short tracks (< 2 min) shown dimmed/collapsed at bottom as "skipped"
- Delta column color-coded: green (< 60s), yellow (< 180s), red (> 180s)

**Bottom actions:**
- "Apply Matches" — saves episode assignments to track records in DB
- "Clear All" — removes all episode assignments

**Data flow:**
1. Component mounts → fetches current match state from job tracks (existing `episode_number`/`episode_name` fields)
2. Fetches all episodes for the selected season via `GET /jobs/{job_id}/tvdb-episodes?season=N` — populates dropdown options
3. User adjusts controls → clicks "Re-match" → calls `POST /jobs/{job_id}/tvdb-match` with `apply: false` (preview)
4. Preview populates the table with proposed matches
5. User adjusts dropdowns manually if needed
6. "Apply Matches" → calls tvdb-match with `apply: true` for auto-matched results, OR calls per-track update API for manual overrides

#### 2.2 Wire into review widget and job detail page

**Dashboard review widget** (`DiscReviewWidget.svelte`):
- Rename "TVDB" button (currently labeled "TVDB") to "Episodes"
- Point to new `EpisodeMatch` component
- Only show for series or when IMDB/TVDB ID is set

**Job detail page** (`/jobs/[id]/+page.svelte`):
- Rename "TVDB Episodes" button (currently labeled "TVDB Episodes") to "Episodes"
- Point to new `EpisodeMatch` component

#### 2.3 Folder import wizard prefill

**File:** `frontend/src/lib/components/FolderImportWizard.svelte`

The scan response now includes `disc_number`, `disc_total`, `season`. Prefill these in the wizard's metadata step. Add editable fields for:
- Season (number input)
- Disc number (number input)
- Disc total (number input)

Pass to the create endpoint so the job starts with correct metadata.

### Layer 3: Matching Algorithm (existing — minimal changes)

The existing greedy nearest-neighbor matcher in `tvdb_matcher.py` already supports:
- Season selection (explicit, auto-detect, or from job)
- Position bias for disc number/total
- Cross-disc exclusion via `cross_disc.py`
- Runtime tolerance

The only change needed: ensure the match endpoint passes `disc_number` and `disc_total` through to the matcher when provided in the request. Currently `match_tracks_to_episodes` reads these from the job object — the endpoint should update the job (or pass overrides) before calling the matcher.

No algorithm changes required for Layer 1. The intelligence improvements (better handling of same-runtime episodes, explicit episode ranges) are future work once the data pipeline is solid.

## Files Affected

### ARM-neu

| File | Change |
|------|--------|
| `arm/ripper/arm_matcher.py` | Add `disc_total` to `LabelInfo`, extend regex for "Disc N of M" |
| `arm/ripper/folder_scan.py` | Run `parse_label()` on folder name, extract season from parent path |
| `arm/api/v1/folder.py` | Add season/disc_number/disc_total to create request and job storage |
| `arm/api/v1/jobs.py` | Extend title update to accept season/disc fields; extend tvdb-match to accept disc overrides |
| `test/test_folder_scan.py` | Test disc/season extraction from folder paths |
| `test/test_arm_matcher.py` | Test disc_total extraction |

### ARM-UI

| File | Change |
|------|--------|
| `frontend/src/lib/components/EpisodeMatch.svelte` | New component — match table with controls and dropdowns |
| `frontend/src/lib/components/DiscReviewWidget.svelte` | Rename "TVDB" → "Episodes", use new component |
| `frontend/src/routes/jobs/[id]/+page.svelte` | Rename "TVDB Episodes" → "Episodes", use new component |
| `frontend/src/lib/components/FolderImportWizard.svelte` | Add season/disc fields, prefill from scan |
| `frontend/src/lib/api/jobs.ts` | Extend tvdb-match API call to pass disc_number/disc_total |
| `frontend/src/lib/components/TvdbMatch.svelte` | May be kept as inner component or replaced by EpisodeMatch |

## Testing

### Backend
- `parse_label("Kolchak Disc 4 of 4")` → `disc_number=4, disc_total=4`
- `parse_label("Show S02D03")` → `season=2, disc_number=3`
- `scan_folder()` returns disc/season metadata from path
- Folder create with season/disc stores on job
- Title update accepts and saves season/disc/disc_total
- TVDB match with disc_number override uses position bias correctly

### Frontend
- Episodes panel shows track-to-episode match table
- Dropdowns allow reassignment
- Re-match with different season/disc produces new results
- Apply saves matches to DB
- Wizard prefills disc/season from scan

### Integration
- Full flow: scan folder → wizard prefills S1 D4/4 → create job → review → Episodes panel → auto-match → correct episodes shown → Apply → Start

## Decisions

1. **Extend `parse_label()` rather than adding new parsing** — centralized label parsing stays in `arm_matcher.py`. `folder_scan.py` calls it instead of duplicating.
2. **Parent folder parsing for season** — disc folders often lack season info, but the containing folder has it. Parse one level up.
3. **New `EpisodeMatch.svelte` component** — cleaner than bolting a match table onto the existing `TvdbMatch.svelte`. May reuse TvdbMatch internals for the TVDB API calls.
4. **Dropdowns for episode reassignment** — simple, accessible, no drag-and-drop complexity. Each track gets a dropdown populated with all episodes from the season.
5. **Disc overrides in match request** — user can experiment without saving, reducing friction for "try disc 3 instead of 4" scenarios.
6. **Rename TVDB → Episodes** — user-facing label should describe the action, not the data source.
