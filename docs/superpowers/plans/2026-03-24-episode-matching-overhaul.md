# Episode Matching Overhaul Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable correct TVDB episode matching for multi-disc TV series folder imports by extracting disc/season metadata from paths, exposing it as editable fields, and building an episode match table with per-track dropdown reassignment.

**Architecture:** Layer 1 (backend) extends `parse_label()` with disc_total, wires it into folder scan, adds season/disc fields to the create and update APIs. Layer 2 (frontend) builds a new `EpisodeMatch.svelte` component with match controls, a track-to-episode table with dropdowns, and prefills season/disc in the folder wizard.

**Tech Stack:** Python/FastAPI (ARM-neu), SvelteKit/Svelte 5 runes (ARM-UI), pytest, vitest

**Spec:** `docs/superpowers/specs/2026-03-24-episode-matching-overhaul-design.md`

**Repos:**
- ARM-neu: `/home/upb/src/automatic-ripping-machine-neu` (branch: `feat/episode-matching-overhaul`)
- ARM-UI: `/home/upb/src/automatic-ripping-machine-ui` (branch: `feat/episode-matching-overhaul`)

**Testing commands:**
- ARM-neu: `/home/upb/src/automatic-ripping-machine-neu/.venv/bin/python -m pytest /home/upb/src/automatic-ripping-machine-neu/test/ -x -q --tb=short`
- ARM-UI backend: `/home/upb/src/automatic-ripping-machine-ui/.venv/bin/python -m pytest /home/upb/src/automatic-ripping-machine-ui/tests/ -x -q --tb=short`
- ARM-UI frontend build: run `npm run build` then `npx svelte-check --tsconfig ./tsconfig.json` from `/home/upb/src/automatic-ripping-machine-ui/frontend`
- ARM-UI frontend tests: `npx vitest run` from `/home/upb/src/automatic-ripping-machine-ui/frontend`

**Git commands:** Always use `git -C <repo-path>` for cross-repo operations. Never `cd && git`.

---

## Chunk 1: Backend — Label Parser & Folder Scan

### Task 1: Add `disc_total` to `parse_label()`

**Repo:** ARM-neu
**Files:**
- Modify: `arm/ripper/arm_matcher.py` (LabelInfo dataclass, _DISC_SUFFIX_RE, _extract_disc_suffix)
- Modify: `test/test_arm_matcher.py`

- [ ] **Step 1: Write tests for disc_total extraction**

Add to `test/test_arm_matcher.py`:

```python
def test_parse_label_disc_of_total():
    """parse_label extracts disc_total from 'Disc N of M' patterns."""
    from arm.ripper.arm_matcher import parse_label
    info = parse_label("SHOW_NAME_DISC_4_OF_4")
    assert info.disc_number == 4
    assert info.disc_total == 4
    assert info.title == "show name"

def test_parse_label_disc_of_total_spaces():
    """parse_label handles 'Disc 2 of 6' with spaces."""
    from arm.ripper.arm_matcher import parse_label
    info = parse_label("Show Name Disc 2 of 6")
    assert info.disc_number == 2
    assert info.disc_total == 6

def test_parse_label_disc_no_total():
    """parse_label returns disc_total=None when no 'of M' present."""
    from arm.ripper.arm_matcher import parse_label
    info = parse_label("SHOW_DISC_3")
    assert info.disc_number == 3
    assert info.disc_total is None

def test_parse_label_d_of_total():
    """parse_label handles D2 of 4 shorthand."""
    from arm.ripper.arm_matcher import parse_label
    info = parse_label("SHOW_D2_OF_4")
    assert info.disc_number == 2
    assert info.disc_total == 4
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/home/upb/src/automatic-ripping-machine-neu/.venv/bin/python -m pytest /home/upb/src/automatic-ripping-machine-neu/test/test_arm_matcher.py -x -q --tb=short -k disc_total`
Expected: FAIL — LabelInfo has no `disc_total` attribute

- [ ] **Step 3: Add `disc_total` to `LabelInfo`**

In `arm/ripper/arm_matcher.py`, add to the LabelInfo dataclass (around line 22):

```python
disc_total: int | None = None
```

- [ ] **Step 4: Extend `_DISC_SUFFIX_RE` to capture "of N"**

Replace the existing regex (lines 77-80) with one that has an optional `of N` group:

```python
_DISC_SUFFIX_RE = re.compile(
    r'[\s_-](P|D|DISC)[\s_-]?(\d+)(?:\s*(?:OF|of)\s*(\d+))?$',
    re.IGNORECASE,
)
```

- [ ] **Step 5: Update `_extract_disc_suffix` to return disc_total**

In `_extract_disc_suffix()` (around line 147), update the function to return a 4-tuple `(remaining, disc_number, disc_type, disc_total)` instead of 3-tuple. Extract group(3) from the regex match when present.

Update all callers of `_extract_disc_suffix` in `parse_label()` to handle the 4th element and set `disc_total` on LabelInfo.

- [ ] **Step 6: Run tests**

Run: `/home/upb/src/automatic-ripping-machine-neu/.venv/bin/python -m pytest /home/upb/src/automatic-ripping-machine-neu/test/test_arm_matcher.py -x -q --tb=short`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git -C /home/upb/src/automatic-ripping-machine-neu add arm/ripper/arm_matcher.py test/test_arm_matcher.py
git -C /home/upb/src/automatic-ripping-machine-neu commit -m "feat: extract disc_total from 'Disc N of M' patterns in parse_label()"
```

---

### Task 2: Wire `parse_label()` into folder scan

**Repo:** ARM-neu
**Files:**
- Modify: `arm/ripper/folder_scan.py`
- Modify or create: `test/test_folder_scan.py`

- [ ] **Step 1: Write tests for folder scan metadata extraction**

```python
def test_scan_folder_extracts_disc_number(tmp_path):
    """scan_folder returns disc_number/disc_total parsed from folder name."""
    from arm.ripper.folder_scan import extract_metadata
    # Create a minimal BDMV structure
    disc_dir = tmp_path / "Show Name - Disc 3 of 4 - BD50"
    (disc_dir / "BDMV" / "STREAM").mkdir(parents=True)
    (disc_dir / "BDMV" / "STREAM" / "00001.m2ts").write_bytes(b"\x00" * 100)

    meta = extract_metadata(str(disc_dir), "bluray")
    assert meta["disc_number"] == 3
    assert meta["disc_total"] == 4

def test_scan_folder_extracts_season_from_parent(tmp_path):
    """scan_folder extracts season from parent folder path."""
    from arm.ripper.folder_scan import extract_metadata
    parent = tmp_path / "Show Name Season 2"
    disc_dir = parent / "Show Name - Disc 1 of 3"
    (disc_dir / "BDMV" / "STREAM").mkdir(parents=True)
    (disc_dir / "BDMV" / "STREAM" / "00001.m2ts").write_bytes(b"\x00" * 100)

    meta = extract_metadata(str(disc_dir), "bluray")
    assert meta["season"] == 2

def test_scan_folder_no_disc_info():
    """scan_folder returns None for disc fields when not parseable."""
    from arm.ripper.folder_scan import extract_metadata
    # Use a path without disc info (would need actual folder — test with mock)
    # disc_number/disc_total/season should be None when not found
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Update `extract_metadata()` to use `parse_label()`**

In `arm/ripper/folder_scan.py`, import `parse_label` from `arm_matcher`:

```python
from arm.ripper.arm_matcher import parse_label
```

In `extract_metadata()`, after getting the label, run `parse_label()` on the folder basename and also on the parent folder name. Add to the return dict:

```python
label_info = parse_label(Path(folder_path).name)
parent_info = parse_label(Path(folder_path).parent.name)

# Prefer disc info from the folder itself, season from parent if not in folder
disc_number = label_info.disc_number
disc_total = label_info.disc_total
season = label_info.season_number or parent_info.season_number

return {
    "label": label,
    "title_suggestion": title,
    "year_suggestion": year,
    "folder_size_bytes": folder_size,
    "stream_count": stream_count,
    "disc_number": disc_number,
    "disc_total": disc_total,
    "season": season,
}
```

- [ ] **Step 4: Run tests**

Run: `/home/upb/src/automatic-ripping-machine-neu/.venv/bin/python -m pytest /home/upb/src/automatic-ripping-machine-neu/test/test_folder_scan.py -x -q --tb=short`
Expected: ALL PASS

- [ ] **Step 5: Run full test suite**

Run: `/home/upb/src/automatic-ripping-machine-neu/.venv/bin/python -m pytest /home/upb/src/automatic-ripping-machine-neu/test/ -x -q --tb=short`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git -C /home/upb/src/automatic-ripping-machine-neu add arm/ripper/folder_scan.py test/test_folder_scan.py
git -C /home/upb/src/automatic-ripping-machine-neu commit -m "feat: extract disc/season metadata from folder paths via parse_label()"
```

---

### Task 3: Add season/disc fields to folder create & job update APIs

**Repo:** ARM-neu
**Files:**
- Modify: `arm/api/v1/folder.py` (FolderCreateRequest, create_folder_job)
- Modify: `arm/api/v1/jobs.py` (_DIRECT_FIELDS, tvdb-match endpoint)
- Modify: `test/test_folder_api.py`

- [ ] **Step 1: Add fields to `FolderCreateRequest`**

In `arm/api/v1/folder.py`, add to FolderCreateRequest:

```python
season: Optional[int] = None
disc_number: Optional[int] = None
disc_total: Optional[int] = None
```

In `create_folder_job()`, after setting `multi_title`, add:

```python
if req.season is not None:
    job.season = str(req.season)
    job.season_manual = str(req.season)
if req.disc_number is not None:
    job.disc_number = req.disc_number
if req.disc_total is not None:
    job.disc_total = req.disc_total
```

- [ ] **Step 2: Add disc fields to `_DIRECT_FIELDS` in jobs.py**

In `arm/api/v1/jobs.py`, extend `_DIRECT_FIELDS` (line 271):

```python
_DIRECT_FIELDS = ('path', 'label', 'disctype', 'disc_number', 'disc_total')
```

- [ ] **Step 3: Extend tvdb-match endpoint to accept disc overrides**

In the tvdb-match endpoint (around line 618), update the request body parsing:

```python
disc_number = body.get("disc_number")
disc_total = body.get("disc_total")

# Temporarily set on job for this match run if provided
if disc_number is not None:
    job.disc_number = disc_number
if disc_total is not None:
    job.disc_total = disc_total
```

Pass these through before calling `match_episodes_for_api()`.

- [ ] **Step 4: Update tests**

Update `test/test_folder_api.py` test_create_success to pass season/disc fields and assert they're stored.

- [ ] **Step 5: Run full test suite**

Run: `/home/upb/src/automatic-ripping-machine-neu/.venv/bin/python -m pytest /home/upb/src/automatic-ripping-machine-neu/test/ -x -q --tb=short`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git -C /home/upb/src/automatic-ripping-machine-neu add arm/api/v1/folder.py arm/api/v1/jobs.py test/test_folder_api.py
git -C /home/upb/src/automatic-ripping-machine-neu commit -m "feat: add season/disc_number/disc_total to folder create and job update APIs"
```

---

## Chunk 2: Frontend — Episode Match Component

### Task 4: Build `EpisodeMatch.svelte` component

**Repo:** ARM-UI
**Files:**
- Create: `frontend/src/lib/components/EpisodeMatch.svelte`
- Modify: `frontend/src/lib/api/jobs.ts` (extend tvdbMatch to pass disc params)

- [ ] **Step 1: Extend `tvdbMatch` API call**

In `frontend/src/lib/api/jobs.ts`, update the `tvdbMatch` function to accept disc_number and disc_total:

```typescript
export function tvdbMatch(
    jobId: number,
    opts?: {
        season?: number | null;
        tolerance?: number | null;
        apply?: boolean;
        disc_number?: number | null;
        disc_total?: number | null;
    }
): Promise<TvdbMatchResponse> {
    return apiFetch<TvdbMatchResponse>(`/api/jobs/${jobId}/tvdb-match`, {
        method: 'POST',
        body: JSON.stringify({
            season: opts?.season ?? null,
            tolerance: opts?.tolerance ?? null,
            apply: opts?.apply ?? false,
            disc_number: opts?.disc_number ?? null,
            disc_total: opts?.disc_total ?? null,
        })
    });
}
```

- [ ] **Step 2: Create `EpisodeMatch.svelte`**

Create `frontend/src/lib/components/EpisodeMatch.svelte`. The component:

Props:
```typescript
interface Props {
    job: JobDetail;
    onapply?: () => void;
}
```

State:
- `seasonInput` — prefilled from `job.season || job.season_auto`
- `discInput` / `discTotalInput` — prefilled from `job.disc_number` / `job.disc_total`
- `toleranceInput` — default 300
- `matches` — array from match API response
- `episodes` — all episodes for the season (from tvdb-episodes endpoint)
- `assignments` — map of track_number → episode_number (editable)
- `loading` / `error` states

Layout:
1. **Controls bar**: Season, Disc N of M, Tolerance inputs + "Match" button + stats
2. **Match table**: Track | Duration | Episode (dropdown) | TVDB Runtime | Delta
3. **Actions**: Apply Matches / Clear All

Key behaviors:
- On mount: if job already has tracks with episode_number set, show those
- "Match" button: calls `tvdbMatch(job.job_id, { season, tolerance, disc_number, disc_total, apply: false })`
- Populate dropdowns from `fetchTvdbEpisodes(job.job_id, season)`
- Dropdown change updates local `assignments` map
- "Apply" button: calls `tvdbMatch(...)` with `apply: true` OR updates tracks individually
- Short tracks (< 120s) shown dimmed/collapsed

- [ ] **Step 3: Run build check**

Run from `/home/upb/src/automatic-ripping-machine-ui/frontend`:
```
npm run build && npx svelte-check --tsconfig ./tsconfig.json
```
Expected: 0 errors

- [ ] **Step 4: Commit**

```bash
git -C /home/upb/src/automatic-ripping-machine-ui add frontend/src/lib/components/EpisodeMatch.svelte frontend/src/lib/api/jobs.ts
git -C /home/upb/src/automatic-ripping-machine-ui commit -m "feat: add EpisodeMatch component with match table and dropdown reassignment"
```

---

### Task 5: Wire EpisodeMatch into review widget and job detail page

**Repo:** ARM-UI
**Files:**
- Modify: `frontend/src/lib/components/DiscReviewWidget.svelte`
- Modify: `frontend/src/routes/jobs/[id]/+page.svelte`

- [ ] **Step 1: Update DiscReviewWidget**

In `DiscReviewWidget.svelte`:
- Change the import from `TvdbMatch` to `EpisodeMatch`
- Rename button text from "TVDB" to "Episodes"
- Update the panel to use `<EpisodeMatch job={detail} onapply={loadDetail} />`

- [ ] **Step 2: Update job detail page**

In `/routes/jobs/[id]/+page.svelte`:
- Change the import from `TvdbMatch` to `EpisodeMatch`
- Rename button text from "TVDB Episodes" to "Episodes"
- Update the panel to use `<EpisodeMatch {job} onapply={loadJob} />`
- Keep existing `TvdbMatch.svelte` file — don't delete it yet (may have other dependents)

- [ ] **Step 3: Run build and tests**

Run from `/home/upb/src/automatic-ripping-machine-ui/frontend`:
```
npm run build && npx svelte-check --tsconfig ./tsconfig.json && npx vitest run
```
Expected: 0 errors, all tests pass

- [ ] **Step 4: Commit**

```bash
git -C /home/upb/src/automatic-ripping-machine-ui add frontend/src/lib/components/DiscReviewWidget.svelte frontend/src/routes/jobs/\[id\]/+page.svelte
git -C /home/upb/src/automatic-ripping-machine-ui commit -m "feat: replace TVDB button with Episodes panel using EpisodeMatch component"
```

---

### Task 6: Add season/disc fields to folder import wizard

**Repo:** ARM-UI
**Files:**
- Modify: `frontend/src/lib/components/FolderImportWizard.svelte`
- Modify: `frontend/src/lib/api/folder.ts` (or wherever FolderCreateRequest is defined)

- [ ] **Step 1: Update FolderCreateRequest type**

Add `season`, `disc_number`, `disc_total` to the request type:

```typescript
season?: number | null;
disc_number?: number | null;
disc_total?: number | null;
```

- [ ] **Step 2: Add state and prefill from scan**

In `FolderImportWizard.svelte`, add state variables:

```typescript
let editSeason = $state<string>('');
let editDiscNumber = $state<string>('');
let editDiscTotal = $state<string>('');
```

In the scan response handler, prefill:

```typescript
editSeason = scanResult.season?.toString() || '';
editDiscNumber = scanResult.disc_number?.toString() || '';
editDiscTotal = scanResult.disc_total?.toString() || '';
```

- [ ] **Step 3: Add input fields to wizard step 2**

Add fields for Season, Disc Number, Disc Total in the metadata editing step (step 2 of the wizard). Show these when `editType === 'series'` or always if you want movies to optionally have disc info too.

- [ ] **Step 4: Pass to create API**

Update the `handleImport` function to include the new fields:

```typescript
const data: FolderCreateRequest = {
    ...existing fields,
    season: editSeason ? Number(editSeason) : null,
    disc_number: editDiscNumber ? Number(editDiscNumber) : null,
    disc_total: editDiscTotal ? Number(editDiscTotal) : null,
};
```

- [ ] **Step 5: Run build and tests**

Run from `/home/upb/src/automatic-ripping-machine-ui/frontend`:
```
npm run build && npx svelte-check --tsconfig ./tsconfig.json && npx vitest run
```
Expected: 0 errors, all tests pass

- [ ] **Step 6: Commit**

```bash
git -C /home/upb/src/automatic-ripping-machine-ui add frontend/src/lib/components/FolderImportWizard.svelte frontend/src/lib/api/folder.ts
git -C /home/upb/src/automatic-ripping-machine-ui commit -m "feat: prefill season/disc fields in folder import wizard from scan"
```

---

## Chunk 3: Full Test Pass & Deploy

### Task 7: Full backend test suite

**Repo:** ARM-neu

- [ ] **Step 1: Run full test suite**

Run: `/home/upb/src/automatic-ripping-machine-neu/.venv/bin/python -m pytest /home/upb/src/automatic-ripping-machine-neu/test/ -x -q --tb=short`
Expected: ALL PASS

- [ ] **Step 2: Fix any failures and commit**

### Task 8: Full frontend test suite

**Repo:** ARM-UI

- [ ] **Step 1: Run backend tests**

Run: `/home/upb/src/automatic-ripping-machine-ui/.venv/bin/python -m pytest /home/upb/src/automatic-ripping-machine-ui/tests/ -x -q --tb=short`
Expected: ALL PASS

- [ ] **Step 2: Run frontend build + type check + tests**

Run from `/home/upb/src/automatic-ripping-machine-ui/frontend`:
```
npm run build && npx svelte-check --tsconfig ./tsconfig.json && npx vitest run
```
Expected: Build succeeds, 0 type errors, all tests pass

- [ ] **Step 3: Fix any failures and commit**

### Task 9: Push and create PRs

- [ ] **Step 1: Push ARM-neu**

```bash
git -C /home/upb/src/automatic-ripping-machine-neu push -u origin feat/episode-matching-overhaul
```

- [ ] **Step 2: Push ARM-UI**

```bash
git -C /home/upb/src/automatic-ripping-machine-ui push -u origin feat/episode-matching-overhaul
```

- [ ] **Step 3: Create PRs**

Create PRs for both repos against their respective parent branches (`feat/id-based-log-naming` for ARM-neu, `feat/folder-import-review` for ARM-UI) using `GITHUB_TOKEN= gh pr create`.

- [ ] **Step 4: Check CI**

Wait for CI to pass on both PRs. Fix any failures.
