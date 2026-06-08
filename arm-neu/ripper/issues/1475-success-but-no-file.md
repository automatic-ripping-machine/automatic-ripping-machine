# #1475 — Successful job but no completed file

**Upstream:** https://github.com/automatic-ripping-machine/automatic-ripping-machine/issues/1475
**Priority:** Medium
**Verdict:** REAL BUG (upstream) — fixed in our fork via `_reconcile_filenames()` + removed move_files pipeline

## Problem

ARM completes "successfully" but the completed directory is empty. MakeMKV's scan phase reports one set of filenames/track numbers, but the rip phase creates files with different names. When ARM tries to move files using database track filenames, the files don't exist on disk.

## Upstream Reports

- **7+ affected users** in comments
- Example: ARM transcodes `title_t00.mkv` successfully, then tries to move `title_t02.mkv` (from DB) which doesn't exist
- Conditions: multi-track disc, longest track is not t00, other tracks excluded by MINLENGTH → off-by-N mismatch between scan-phase track IDs and rip-phase filenames
- Original poster (jamesrodda) identified the root cause clearly

## Root Cause

MakeMKV's `info` scan assigns track IDs in one order. When `mkv` rips only selected tracks (filtered by MINLENGTH), the output files are renumbered sequentially starting from `_t00`. The Track database records still have the scan-phase track numbers. The move_files function trusts the DB filenames, which no longer match disk.

## Our Fork's Status

**Fixed.** Two architectural changes address this:

1. **`_reconcile_filenames()`** at `arm/ripper/makemkv.py:732-808` — called after ripping (line 859), performs three-pass reconciliation:
   - Pass 1: Exact filename match
   - Pass 2: Prefix match (strips `_tNN` suffixes, matches by segment)
   - Pass 3: Positional match (when track counts match file counts)

2. **Removed `move_files` pipeline entirely** — we only rip with MakeMKV and persist `raw_path`. The transcoder service operates on actual filesystem paths, not database Track filenames.

## Affected Code

No changes needed — our fork already addresses this.

## Suggested Fix

N/A — already fixed in our architecture.
